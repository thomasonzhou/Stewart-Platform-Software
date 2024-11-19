"""Full integration of software components with sanity checks"""

import computer_vision
import serial2py
import inverse_kinematics
import py2motor
import pid

import math
from enum import Enum
import serial

HOMING_COMPLETED_STRING = "HOME"

PLATFORM_TILT_MIN_RAD = 0.0
PLATFORM_TILT_MAX_RAD = math.pi / 12.0

MOTOR_MIN_RAD = -math.pi / 2.0
MOTOR_MAX_RAD = math.pi / 2.0

ARDUINO_PORT = "/dev/cu.usbmodem1301"
MOTOR_CONTROLLER_PORT = "/dev/cu.usbmodem1401"
# other ports: 'COM5' '/dev/ttyUSB0'
BAUD_RATE = 115200


class OperationMode(Enum):
    COMPUTER_VISION = 1
    WASD_JOYSTICK = 2
    ARDUINO_JOYSTICK = 3


def main(operation_mode=OperationMode.COMPUTER_VISION):
    # --------------------------------------------------
    # Initialize Components
    # --------------------------------------------------
    controller = pid.Controller()
    ball_detector = computer_vision.BallDetector()
    homing_completed = False

    with serial.Serial(MOTOR_CONTROLLER_PORT, BAUD_RATE, timeout=1) as motor_serial:
        while not homing_completed:
            homing_string = motor_serial.read()
            if homing_string and homing_string.decode("ascii").strip() == HOMING_COMPLETED_STRING:
                homing_completed = True

        with serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1) as arduino_serial:
            while True:
                match operation_mode:
                    case OperationMode.COMPUTER_VISION:
                        # set target position
                        target_position_plate_view = (0.0, 0.0)
                        # ball detection
                        ball_position_plate_view = ball_detector.get_ball_position_plate_view()

                        dir_x, dir_y, theta_rad = controller.calculate(
                            desired_pos=target_position_plate_view,
                            actual_pos=ball_position_plate_view,
                        )
                    case OperationMode.WASD_JOYSTICK:
                        (dir_x, dir_y), theta_rad = serial2py.read_wasd()
                    case OperationMode.ARDUINO_JOYSTICK:
                        dir_x, dir_y, theta_rad = serial2py.read_arduino_joystick(arduino_serial)
                # print(f"{dir_x:.2f}, {dir_y:.2f}, {theta_rad*180/math.pi:.2f}")
                # --------------------------------------------------
                # Inverse Kinematics
                # --------------------------------------------------
                assert PLATFORM_TILT_MIN_RAD <= theta_rad <= PLATFORM_TILT_MAX_RAD

                # IK
                abs_motor_angles = inverse_kinematics.translate_dir_to_motor_angles(
                    dir_x, dir_y, theta_rad
                )
                for angle in abs_motor_angles:
                    assert MOTOR_MIN_RAD <= angle <= MOTOR_MAX_RAD

                py2motor.write_to_motors(motor_serial, abs_motor_angles)


if __name__ == "__main__":
    # main(operation_mode=OperationMode.ARDUINO_JOYSTICK)
    main(operation_mode=OperationMode.COMPUTER_VISION)
