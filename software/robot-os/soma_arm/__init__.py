"""soma_arm — Orange Pi side software for the SOMA v3 hybrid arm.

6-DOF arm: J1-J3 printed cycloidal actuators (5010 + B-G431B-ESC1) on CAN,
J4-J6 Feetech STS3215 on TTL bus. See docs/can-protocol.md and
docs/host-protocol.md.
"""

from . import config
from .kinematics import ArmKinematics, IKSolution, Pose
from .planner import TrajectoryPlanner
from .arm import Arm, ArmError

__all__ = [
    "config",
    "ArmKinematics",
    "IKSolution",
    "Pose",
    "TrajectoryPlanner",
    "Arm",
    "ArmError",
]
__version__ = "0.1.0"
