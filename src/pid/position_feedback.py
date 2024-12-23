import math
from enum import Enum
from dataclasses import dataclass

MIN_ANGLE_TO_MOVE = math.radians(0.5)


def saturate(control: float, sat_min: float, sat_max: float) -> float:
    """Helper function to keep the PID controller between the limits

    Args:
        control (float): Control angle (deg)
        sat_min (float): Minimum angle (deg)
        sat_max (float): Maximum angle (deg)

    Returns:
        float: Control angle within the saturation limits (deg)
    """
    return max(min(sat_max, control), sat_min)


SAT_MAX_DEGREES = 8.25
SAT_MIN_DEGREES = 0

INTEGRAL_BOUND = 0.4


@dataclass
class PID_Parameters:
    kp: float
    ki: float
    kd: float


class PID_Mode(Enum):
    DisturbanceRejection = PID_Parameters(kp=0.80, ki=0.01, kd=0.55)  # high rise time
    PathPlanning = PID_Parameters(kp=0.8, ki=0.1, kd=1.2)  # quick convergence with no disturbance


class Controller:
    dt = 0.1

    def __init__(self, pid_mode: PID_Mode, print_errors=False, dead_zone=False):
        self.kp = pid_mode.value.kp
        self.ki = pid_mode.value.ki
        self.kd = pid_mode.value.kd
        self.prev_e_x = 0
        self.prev_e_y = 0
        self.int_x = 0
        self.int_y = 0

        self.print_errors = print_errors
        self.dead_zone = dead_zone

    def calculate(
        self, desired_pos: tuple[float, float], actual_pos: tuple[float, float]
    ) -> tuple[float, float, float]:
        """Main PID function

        Args:
            desired_pos (tuple of two floats): desired x and y position of the ball
            actual_pos (tuple of two floats): current x and y position of the ball

        Returns:
             tuple of three floats: [dir_x, dir_y, sat_theta_mag]
                  dir_x: x-component of the unit direction vector to tilt the plate
                  dir_y: y-component of the unit direction vector to tilt the plate
                  sat_theta_mag: angle to tilt the plate (rad)
        """

        x_r, y_r = desired_pos
        x, y = actual_pos

        # Calculate error
        e_x = x_r - x
        e_y = y_r - y

        # Calculate proportional term
        p_x = self.kp * e_x
        p_y = self.kp * e_y

        # Calculate derivative term
        d_x = self.kd * ((e_x - self.prev_e_x) / self.dt)
        d_y = self.kd * ((e_y - self.prev_e_y) / self.dt)

        # Calculate integral term
        self.int_x += e_x * self.dt
        self.int_y += e_y * self.dt
        i_x = self.ki * self.int_x
        i_y = self.ki * self.int_y

        # prevent windup
        if i_x > INTEGRAL_BOUND:
            i_x = INTEGRAL_BOUND
        elif i_x < -INTEGRAL_BOUND:
            i_x = -INTEGRAL_BOUND

        if i_y > INTEGRAL_BOUND:
            i_y = INTEGRAL_BOUND
        elif i_y < -INTEGRAL_BOUND:
            i_y = -INTEGRAL_BOUND

        if self.print_errors:
            print(f"p: {p_x:.5f}, {p_y:.5f}, d: {d_x:.5f}, {d_y:.5f}, i: {i_x:.5f}, {i_y:.5f}")

        # Update error
        self.prev_e_x = e_x
        self.prev_e_y = e_y

        # Calculate control signal
        u_x = p_x + d_x + i_x
        u_y = p_y + d_y + i_y

        # Calculate theta as the magnitude of the control signal
        theta_mag = math.sqrt(u_x**2 + u_y**2)

        # Calculate the unit vector components
        if theta_mag != 0:
            dir_x = u_x / theta_mag
            dir_y = u_y / theta_mag
        else:
            dir_x, dir_y = 0, 0

        # Saturate plate tilt and convert to radians
        sat_theta_mag = math.radians(saturate(theta_mag, SAT_MIN_DEGREES, SAT_MAX_DEGREES))
        if self.dead_zone and sat_theta_mag < MIN_ANGLE_TO_MOVE:
            sat_theta_mag = 0

        return dir_x, dir_y, sat_theta_mag
