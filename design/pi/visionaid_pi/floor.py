"""IMU-compensated floor baseline for the FPGA drop-off detector.

Why: the analysis in design/analysis/sensor_geometry.py showed that +/-3 deg of chest sway while walking moves
the LiDAR floor range by up to ~30 cm - more than the 15 cm drop-off threshold - giving 25 false alarms in 20 s
with a fixed baseline, and 0 when the baseline follows the IMU pitch.
How: the Pi reads the MPU-6050 pitch, computes the expected flat-floor range  r = H / sin(35 deg + pitch),
and sends it to the FPGA (command 4) at up to 20 Hz. The FPGA still makes the drop-off decision itself.
"""
import math
from .protocol import build_command, CMD_LIDAR_BASELINE_CM

LIDAR_PITCH_DEG = 35.0


class FloorBaseline:
    def __init__(self, height_m=1.30, min_step_cm=1):
        self.h = height_m
        self.last_cm = None
        self.min_step = min_step_cm

    def calibrate(self, lidar_cm, pitch_deg):
        """Stand still for 2 s at start-up: derive the real chest height from the measured flat-floor range."""
        self.h = (lidar_cm / 100.0) * math.sin(math.radians(LIDAR_PITCH_DEG + pitch_deg))
        return self.h

    def expected_cm(self, pitch_deg):
        return 100.0 * self.h / math.sin(math.radians(LIDAR_PITCH_DEG + pitch_deg))

    def command(self, pitch_deg):
        """Returns the 5-byte command to send, or None if the baseline hasn't changed enough to bother."""
        cm = int(round(self.expected_cm(pitch_deg)))
        if self.last_cm is not None and abs(cm - self.last_cm) < self.min_step:
            return None
        self.last_cm = cm
        return build_command(CMD_LIDAR_BASELINE_CM, cm)
