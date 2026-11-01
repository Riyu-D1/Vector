"""soma_arm — Orange Pi side software for the SOMA v3 hybrid arm.

6-DOF arm + gripper on carrier PCB v1.3: J1 STS3250 + J4/J5/J6/GRIP
STS3215 on Feetech bus A; J2/J3 printed 40:1 cycloidal actuators
(Tarot 4008 330KV + B-G431B-ESC1) on CAN. MOTOR_EN hardware relay gated
by the base node. See docs/can-protocol.md, docs/host-protocol.md and
docs/bringup.md.
"""

from . import config
from .gravity import gravity_torques, max_payload, torque_ok
from .kinematics import ArmKinematics, IKSolution, Pose
from .planner import TrajectoryPlanner, PlanError
from .arm import Arm, ArmError

__all__ = [
    "config",
    "gravity_torques",
    "max_payload",
    "torque_ok",
    "ArmKinematics",
    "IKSolution",
    "Pose",
    "TrajectoryPlanner",
    "PlanError",
    "Arm",
    "ArmError",
]
__version__ = "0.2.0"
