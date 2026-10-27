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
from .kinematics import ArmKinematics, Pose
from .planner import TrajectoryPlanner


class ArmError(RuntimeError):
    pass


class Arm:
    def __init__(self, transport, kin=None, planner=None,
                 state_timeout=1.0):
        self.t = transport
        self.kin = kin or ArmKinematics()
        self.planner = planner or TrajectoryPlanner()
        self._parser = link.FrameParser()
        self._seq = 0
        self.state = None            # last parsed STATE dict
        self.events = []
        self._state_timeout = state_timeout
        self.q = [0.0] * 6           # last known/commanded joint state

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
            self.q = list(self.state["pos"])
        elif ftype == link.T.EVENT:
            if payload:
                self.events.append((payload[0], payload[1] if len(payload) > 1 else 0))
                if payload[0] == link.EV_ESTOP_ASSERTED:
                    self._estopped = True
                elif payload[0] == link.EV_ESTOP_CLEARED:
                    self._estopped = False
        elif ftype == link.T.PONG:
            self.pong = payload
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

    def estop(self):
        self._send(link.T.ESTOP)

    def clear_estop(self):
        self._send(link.T.CLEAR_ESTOP)

    def set_current_limit(self, joint, amps):
        """joint 1..3 (CAN brushless) — amps phase-current cap."""
        if not 1 <= joint <= 3:
            raise ArmError("current limit applies to CAN joints 1..3")
        self._send(link.T.SET_CURRENT_LIM,
                   link.p_set_current_lim(joint, amps))

    def set_servo_reg(self, servo_id, addr, data):
        self._send(link.T.SET_SERVO_REG, link.p_set_servo_reg(
            servo_id, addr, data))

    # ------------------------------------------------------------ motion
    def stream_joints(self, q, blocking=False, dt=config.STREAM_DT_S):
        """Send one joint setpoint. q = 6 rad."""
        self.kin.clamp_limits(q)
        self.planner.check_in_limits(q)
        self._send(link.T.SET_JOINT_POS, link.p_set_joint_pos(q))
        self.q = list(q)
        if blocking:
            time.sleep(dt)

    def move_joints(self, q_target, speed_scale=0.5, q_start=None,
                    dt=config.STREAM_DT_S, realtime=True):
        """Planned joint move; streams setpoints. Returns duration T."""
        q0 = list(q_start if q_start is not None else self.q)
        T, pts = self.planner.plan(q0, q_target, speed_scale, dt)
        t0 = time.monotonic()
        for (t, q) in pts:
            self._send(link.T.SET_JOINT_POS, link.p_set_joint_pos(q))
            if realtime:
                while time.monotonic() - t0 < t:
                    time.sleep(0.001)
        self.q = list(q_target)
        return T

    def move_tcp(self, x, y, z, pitch=0.0, roll=0.0, speed_scale=0.5,
                 elbow=+1, gripper=None, realtime=True):
        """Cartesian move: IK then a planned joint move."""
        pose = Pose(x=x, y=y, z=z, pitch=pitch, roll=roll)
        q6 = self.q[5] if gripper is None else gripper
        sol = self.kin.ik(pose, elbow=elbow, q_seed=self.q, q6=q6)
        return self.move_joints(sol.q, speed_scale=speed_scale,
                                realtime=realtime)

    def set_gripper(self, v):
        """v in [0,1]: 0 open, 1 closed -> J6 setpoint."""
        v = max(0.0, min(1.0, v))
        q = list(self.q)
        q[5] = config.JOINT_MIN[5] + v * (config.JOINT_MAX[5]
                                        - config.JOINT_MIN[5])
        self.stream_joints(q)

    def tcp_pose(self):
        return self.kin.fk(self.q)
