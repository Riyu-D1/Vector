"""High-level Arm API — ties kinematics, planner and the link together.

Typical use (dry run):
    from soma_arm import Arm
    from soma_arm.sim import SimBaseNode
    from soma_arm.link import SimTransport
    arm = Arm(SimTransport(SimBaseNode()))
    arm.enable()
    arm.move_tcp(0.20, 0.0, 0.12, pitch=0.0)
"""

import struct
import time

from . import config, link
from .gravity import gravity_torques, max_payload
from .kinematics import ArmKinematics, Pose
from .planner import TrajectoryPlanner, PlanError


class ArmError(RuntimeError):
    pass


class Arm:
    def __init__(self, transport, kin=None, planner=None,
                 state_timeout=1.0, payload_kg=0.0):
        self.t = transport
        self.kin = kin or ArmKinematics()
        self.planner = planner or TrajectoryPlanner()
        self._parser = link.FrameParser()
        self._seq = 0
        self._param_resp = None
        self.state = None            # last parsed STATE dict
        self.events = []
        self._state_timeout = state_timeout
        self.q = [0.0] * 6           # last known/commanded joint state
        self.g = 0.0                 # jaw channel (rad)
        self.payload_kg = payload_kg  # carried TCP load for derating

    # --------------------------------------------------------- low level
    def _send(self, ftype, payload=b""):
        self._seq = (self._seq + 1) & 0xFF
        self.t.write(link.build_frame(self._seq, ftype, payload))

    def _pump(self):
        data = self.t.read(4096)
        for (seq, ftype, payload) in self._parser.feed(data):
            self._dispatch(ftype, payload)

    def _dispatch(self, ftype, payload):
        if ftype == link.T.STATE:
            self.state = link.parse_state(payload)
            self.q = list(self.state["pos"][:6])
            self.g = self.state["pos"][6]
        elif ftype == link.T.EVENT:
            if payload:
                self.events.append((payload[0], payload[1] if len(payload) > 1 else 0))
                if payload[0] == link.EV_ESTOP_ASSERTED:
                    self._estopped = True
                elif payload[0] == link.EV_ESTOP_CLEARED:
                    self._estopped = False
        elif ftype == link.T.PONG:
            self.pong = payload
        elif ftype == link.T.PARAM:
            self._param_resp = payload[4:8] if len(payload) >= 8 else payload
        elif ftype == link.T.NACK:
            self.events.append(("nack", list(payload)))

    # ------------------------------------------------------------ cmds
    def ping(self):
        self.pong = None
        self._send(link.T.PING)
        t0 = time.monotonic()
        while time.monotonic() - t0 < self._state_timeout:
            self._pump()
            if self.pong is not None:
                (ver,) = struct.unpack("<I", self.pong[:4])
                return {"fw": ver, "flags": self.pong[4]}
            time.sleep(0.005)
        raise ArmError("no PONG from base node")

    def sense(self, refresh=True):
        if refresh:
            self._send(link.T.GET_STATE)
            t0 = time.monotonic()
            while time.monotonic() - t0 < self._state_timeout:
                self._pump()
                if self.state is not None:
                    return self.state
                time.sleep(0.005)
            raise ArmError("no STATE from base node")
        return self.state

    def heartbeat(self, n=0):
        self._send(link.T.HEARTBEAT, struct.pack("<I", n))

    def enable(self):
        self._send(link.T.SET_MODE, link.p_set_mode(0, 1))

    def disable(self):
        self._send(link.T.SET_MODE, link.p_set_mode(0, 0))

    def arm_motors(self):
        """Explicit MOTOR_EN arm command — required after boot and after
        every safety drop; enables only while e-stop is clear and both
        ESCs report fresh heartbeats."""
        self._send(link.T.ARM_MOTOR)

    def home(self, joint=0):
        """NMT_HOME to one CAN joint (node 2/3) or both (joint=0)."""
        self._send(link.T.SET_MODE, link.p_set_mode(joint, 3))

    def calibrate(self, joint=0):
        """NMT_CALIBRATE — rotor free, one node or both."""
        self._send(link.T.SET_MODE, link.p_set_mode(joint, 2))

    def estop(self):
        self._send(link.T.ESTOP)

    def clear_estop(self):
        self._send(link.T.CLEAR_ESTOP)

    def set_current_limit(self, joint, amps):
        """joint 2|3 (CAN node ids J2/J3) — amps phase-current cap."""
        if joint not in (2, 3):
            raise ArmError("current limit applies to CAN joints 2|3")
        self._send(link.T.SET_CURRENT_LIM,
                   link.p_set_current_lim(joint, amps))

    def set_servo_reg(self, servo_id, addr, data):
        self._send(link.T.SET_SERVO_REG, link.p_set_servo_reg(
            servo_id, addr, data))

    def read_param(self, bus, node, addr, timeout=1.0):
        """READ_PARAM -> PARAM response payload (last 4 bytes) or None."""
        self._param_resp = None
        self._send(link.T.READ_PARAM, link.p_read_param(bus, node, addr))
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            self._pump()
            if self._param_resp is not None:
                return self._param_resp
            time.sleep(0.005)
        return None

    # ------------------------------------------------------------ motion
    def _pack(self, q):
        """6 joints + jaw -> 7-channel wire vector."""
        return list(q) + [self.g]

    def stream_joints(self, q, blocking=False, dt=config.STREAM_DT_S):
        """Send one joint setpoint. q = 6 rad."""
        q = self.kin.clamp_limits(q)
        self.planner.check_in_limits(q)
        self._send(link.T.SET_JOINT_POS,
                   link.p_set_joint_pos(self._pack(q)))
        self.q = list(q)
        if blocking:
            time.sleep(dt)

    def move_joints(self, q_target, speed_scale=0.5, q_start=None,
                    dt=config.STREAM_DT_S, realtime=True):
        """Planned joint move; streams setpoints. Refuses paths where a
        joint would exceed 80% of rated torque under payload_kg."""
        q0 = list(q_start if q_start is not None else self.q)
        T, pts = self.planner.plan(q0, q_target, speed_scale, dt,
                                   payload_kg=self.payload_kg)
        t0 = time.monotonic()
        for (t, q) in pts:
            self._send(link.T.SET_JOINT_POS,
                       link.p_set_joint_pos(self._pack(q)))
            if realtime:
                while time.monotonic() - t0 < t:
                    time.sleep(0.001)
        self.q = list(q_target)
        return T

    def move_tcp(self, x, y, z, pitch=0.0, roll=0.0, speed_scale=0.5,
                 elbow=+1, gripper=None, realtime=True):
        """Cartesian move: IK then a planned joint move."""
        pose = Pose(x=x, y=y, z=z, pitch=pitch, roll=roll)
        sol = self.kin.ik(pose, elbow=elbow, q_seed=self.q)
        if gripper is not None:
            self.g = gripper
        return self.move_joints(sol.q, speed_scale=speed_scale,
                                realtime=realtime)

    def set_gripper(self, v):
        """v in [0,1]: 0 open, 1 closed -> GRIP channel setpoint."""
        v = max(0.0, min(1.0, v))
        self.g = config.GRIP_MIN + v * (config.GRIP_MAX - config.GRIP_MIN)
        self.stream_joints(self.q)

    # --------------------------------------------------------- payloads
    def max_payload(self, pose=None, q=None):
        """Allowed TCP payload (kg) at a Pose or joint vector — the
        80%-of-rated derate; J4-limited at full reach."""
        if q is None:
            sol = self.kin.ik(pose, q_seed=self.q)
            q = sol.q
        return max_payload(q)

    def joint_torques(self, payload_kg=None):
        """Static gravity torques (N·m) at the current q."""
        return gravity_torques(self.q,
                               self.payload_kg if payload_kg is None
                               else payload_kg)

    def tcp_pose(self):
        return self.kin.fk(self.q)
