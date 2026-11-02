"""soma CLI — drive the arm from the Orange Pi (or any POSIX host).

  python -m soma_arm.cli --sim demo
  python -m soma_arm.cli --port /dev/ttyUSB0 ping
  python -m soma_arm.cli --sim move-tcp 0.20 0.0 0.12 --pitch 0
  python -m soma_arm.cli --sim move-joints 0 0.4 0.6 0 0 0.4
  python -m soma_arm.cli --sim fk 0 0.4 0.6 0 0 0
  python -m soma_arm.cli --sim ik 0.20 0.0 0.12 --pitch 0
  python -m soma_arm.cli --sim sense | estop | clear-estop | enable | disable
  python -m soma_arm.cli --sim gripper 0.5
  python -m soma_arm.cli --sim arm-motors | home | calibrate | max-payload
"""

import argparse
import math
import sys

from . import config
from .arm import Arm, ArmError
from .kinematics import Pose
from .link import SerialTransport, SimTransport, T as LT, p_set_mode
from .sim import SimBaseNode


def _fmtq(q):
    return "[" + ", ".join("%+.3f" % v for v in q) + "]"


def _connect(args):
    if args.port and not args.sim:
        return Arm(SerialTransport(args.port, baud=args.baud)), None
    node = SimBaseNode()
    return Arm(SimTransport(node)), node


def main(argv=None):
    ap = argparse.ArgumentParser(prog="soma", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial device (default: simulator)")
    ap.add_argument("--baud", type=int, default=config.LINK_BAUD)
    ap.add_argument("--sim", action="store_true",
                    help="use the built-in simulator (default if no --port)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping")
    sub.add_parser("sense")
    sub.add_parser("enable")
    sub.add_parser("disable")
    sub.add_parser("estop")
    sub.add_parser("clear-estop")
    sub.add_parser("arm-motors")
    sub.add_parser("home")
    sub.add_parser("calibrate")
    sub.add_parser("max-payload")

    p = sub.add_parser("move-joints", help="planned move, 6 rad args")
    p.add_argument("q", type=float, nargs=6)
    p.add_argument("--speed", type=float, default=0.5)

    p = sub.add_parser("move-tcp", help="Cartesian move")
    p.add_argument("x", type=float); p.add_argument("y", type=float)
    p.add_argument("z", type=float)
    p.add_argument("--pitch", type=float, default=0.0)
    p.add_argument("--roll", type=float, default=0.0)
    p.add_argument("--elbow", type=int, default=+1, choices=[+1, -1])
    p.add_argument("--speed", type=float, default=0.5)

    p = sub.add_parser("fk", help="forward kinematics of 6 joint angles")
    p.add_argument("q", type=float, nargs=6)

    p = sub.add_parser("ik", help="inverse kinematics of a pose")
    p.add_argument("x", type=float); p.add_argument("y", type=float)
    p.add_argument("z", type=float)
    p.add_argument("--pitch", type=float, default=0.0)
    p.add_argument("--roll", type=float, default=0.0)
    p.add_argument("--elbow", type=int, default=+1, choices=[+1, -1])

    p = sub.add_parser("gripper", help="0=open 1=closed")
    p.add_argument("v", type=float)

    p = sub.add_parser("limit", help="set CAN phase-current cap")
    p.add_argument("joint", type=int, choices=[2, 3])
    p.add_argument("amps", type=float)

    p = sub.add_parser("mode", help="NMT mode: joint(0=all,2,3) "
                                    "cmd(0=dis,1=en,2=cal,3=home,127=estop)")
    p.add_argument("joint", type=int, choices=[0, 2, 3])
    p.add_argument("cmd", type=int)

    p = sub.add_parser("param", help="read a CAN SDO or Feetech register")
    p.add_argument("bus", type=int, choices=[0, 1], help="0=CAN,1=Feetech")
    p.add_argument("node", type=int)
    p.add_argument("addr", type=lambda s: int(s, 0))

    sub.add_parser("demo", help="small dry-run motion sequence")

    args = ap.parse_args(argv)
    arm, sim = _connect(args)

    try:
        if args.cmd == "fk":
            pose = arm.kin.fk(args.q)
            print(f"tcp = ({pose.x:.4f}, {pose.y:.4f}, {pose.z:.4f}) m  "
                  f"pitch={math.degrees(pose.pitch):+.1f}deg "
                  f"roll={math.degrees(pose.roll):+.1f}deg")
            return 0

        if args.cmd == "ik":
            sol = arm.kin.ik(Pose(args.x, args.y, args.z,
                                  args.pitch, args.roll), elbow=args.elbow)
            print(f"q = {_fmtq(sol.q)} rad  (elbow branch {sol.branch:+d})")
            print("  = " + _fmtq([math.degrees(v) for v in sol.q]) + " deg")
            return 0

        # commands below need the node
        if args.cmd == "ping":
            print("PONG:", arm.ping())
        elif args.cmd == "enable":
            arm.enable(); print("enabled")
        elif args.cmd == "disable":
            arm.disable(); print("disabled")
        elif args.cmd == "estop":
            arm.estop(); print("ESTOP sent")
        elif args.cmd == "clear-estop":
            arm.clear_estop(); print("estop cleared")
        elif args.cmd == "arm-motors":
            arm.arm_motors(); print("ARM_MOTOR sent")
        elif args.cmd == "home":
            arm.home(); print("HOME sent to J2/J3")
        elif args.cmd == "calibrate":
            arm.calibrate(); print("CALIBRATE sent to J2/J3")
        elif args.cmd == "max-payload":
            m, wi, bounds = arm.max_payload(q=arm.q)
            print(f"max payload at current pose: {m:.3f} kg "
                  f"(limited by {config.JOINT_NAMES[wi]})")
            for i, name in enumerate(config.JOINT_NAMES):
                print(f"  {name}: bound {bounds[i]:.3f} kg")
        elif args.cmd == "sense":
            s = arm.sense()
            print("pos:", _fmtq(s["pos"]))
            print("flags: 0x%02X can_ok: 0x%02X" % (s["flags"], s["can_ok_mask"]))
        elif args.cmd == "move-joints":
            arm.arm_motors(); arm.enable()
            T = arm.move_joints(args.q, speed_scale=args.speed,
                                realtime=not args.sim)
            if sim:
                for _ in range(50):
                    sim.step(0.02)
            print(f"move done, T={T:.2f}s  q={_fmtq(arm.q)}")
        elif args.cmd == "move-tcp":
            arm.arm_motors(); arm.enable()
            T = arm.move_tcp(args.x, args.y, args.z, pitch=args.pitch,
                             roll=args.roll, speed_scale=args.speed,
                             elbow=args.elbow, realtime=not args.sim)
            if sim:
                for _ in range(50):
                    sim.step(0.02)
            p = arm.tcp_pose()
            print(f"move done, T={T:.2f}s  tcp=({p.x:.3f},{p.y:.3f},{p.z:.3f})")
        elif args.cmd == "gripper":
            arm.set_gripper(args.v); print(f"gripper -> {args.v}")
        elif args.cmd == "limit":
            arm.set_current_limit(args.joint, args.amps)
            print(f"J{args.joint} current limit -> {args.amps} A")
        elif args.cmd == "mode":
            arm._send(LT.SET_MODE, p_set_mode(args.joint, args.cmd))
            print(f"mode cmd {args.cmd} -> joint {args.joint or 'all'}")
        elif args.cmd == "param":
            v = arm.read_param(args.bus, args.node, args.addr)
            print(f"param bus={args.bus} node={args.node} "
                  f"addr=0x{args.addr:04X}: {v.hex() if v else 'no resp'}")
        elif args.cmd == "demo":
            print("[demo] ping:", arm.ping())
            arm.arm_motors()
            arm.enable()
            for target in [(0.20, 0.0, 0.15), (0.20, 0.06, 0.15),
                           (0.20, -0.06, 0.15), (0.20, 0.0, 0.15)]:
                T = arm.move_tcp(*target, speed_scale=0.4,
                                 realtime=not args.sim)
                if sim:
                    for _ in range(60):
                        sim.step(0.02)
                p = arm.tcp_pose()
                print(f"[demo] -> {target}: T={T:.2f}s "
                      f"tcp=({p.x:.3f},{p.y:.3f},{p.z:.3f})")
            arm.set_gripper(0.7)
            if sim:
                for _ in range(60):
                    sim.step(0.02)
            print("[demo] gripper closed, sense:",
                  _fmtq(arm.sense()["pos"]))
            arm.disable()
            print("[demo] done")
        return 0
    except ArmError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
