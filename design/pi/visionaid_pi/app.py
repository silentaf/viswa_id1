"""VisionAid Raspberry Pi application (AI path). Same code runs on the Pi 5 and, for testing, on a laptop.

Loop (status frames arrive every 20 ms from the FPGA):
  1. decode FPGA status (protocol.StatusParser)
  2. IMU pitch -> floor-baseline command for the FPGA drop-off detector (floor.FloorBaseline)
  3. EVENT-TRIGGERED AI: run object detection only when the FPGA reports something within 3 m
     (power analysis: continuous AI ~3.1 h battery, event-triggered ~4.3 h assuming ~50 % AI duty), at most every 0.5 s
  4. READ button (flag from the FPGA) -> OCR -> speech
  5. alert manager -> Piper speech (safety messages first)
  6. toggle the heartbeat GPIO so the FPGA watchdog knows the AI path is alive
On a laptop: --replay feeds the bytes the Verilog FPGA produced in simulation and --images stands in for the camera.
On the Pi:   --serial /dev/ttyAMA0 --camera  (picamera2, gpiozero, smbus2 for the MPU-6050).
"""
import argparse
import glob
import os
import time

import cv2

from .protocol import StatusParser
from .floor import FloorBaseline
from .alerts import AlertManager, ZONE_SPEAK_MM
from .vision import Detector, hazards
from .speech import Reader, Speaker

MODELS = os.environ.get('VISIONAID_MODELS', '/tmp/visionaid-tools/models')


class ReplayLink:
    """Plays back FPGA->Pi bytes recorded from the Verilog simulation, 11 bytes per 20 ms frame."""
    def __init__(self, hexfile):
        self.data = bytes(int(x, 16) for x in open(hexfile).read().split())
        self.pos = 0
        self.sent = []

    def read(self, n=11):
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def write(self, b):
        self.sent.append(bytes(b))

    def done(self):
        return self.pos >= len(self.data)


class ImageCamera:
    def __init__(self, folder):
        self.files = sorted(glob.glob(os.path.join(folder, '*.jpg')))
        self.i = 0

    def capture(self):
        f = self.files[self.i % len(self.files)]
        self.i += 1
        return cv2.imread(f)


def run(link, camera, speak_dir, log, imu_pitch=lambda: 0.0, heartbeat=lambda: None, realtime=False):
    parser, floor, alerts = StatusParser(), FloorBaseline(), AlertManager(cooldown_s=4.0)
    det = Detector(os.path.join(MODELS, 'yolov5n.onnx'))
    reader = Reader()
    voice = Speaker(os.path.join(MODELS, 'en_US-lessac-medium.onnx'))
    stats = {'frames': 0, 'detections_run': 0, 'ocr_run': 0, 'spoken': 0, 'floor_cmds': 0}
    last_det, t_sim, n_spoken = -1e9, 0.0, 0
    while not link.done():
        frames = parser.feed(link.read())
        for st in frames:
            stats['frames'] += 1
            t_sim += 0.020                                       # frame period of the FPGA status stream
            cmd = floor.command(imu_pitch())
            if cmd:
                link.write(cmd)
                stats['floor_cmds'] += 1
            dets = []
            nearest = min(st.left_mm, st.right_mm, st.head_mm)
            if nearest < ZONE_SPEAK_MM and t_sim - last_det >= 0.5:          # event-triggered AI
                dets, _ = det.detect(camera.capture())
                dets = hazards(dets)
                stats['detections_run'] += 1
                last_det = t_sim
            text = None
            if st.read_pressed:
                text, _ = reader.read(camera.capture())
                stats['ocr_run'] += 1
            for prio, phrase in alerts.update(st, dets, text):
                wav = os.path.join(speak_dir, 'say_%03d.wav' % n_spoken)
                voice.synth(phrase, wav)
                n_spoken += 1
                stats['spoken'] += 1
                log.write('%8.2f s  P%d  %-36s L=%5s R=%5s H=%5s floor=%3d cm flags=%s\n' % (
                    t_sim, prio, phrase, st.left_mm, st.right_mm, st.head_mm, st.lidar_cm, format(st.flags, '08b')))
            heartbeat()
            if realtime:
                time.sleep(0.02)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--replay', help='hex file of FPGA->Pi bytes (from the Verilog testbench)')
    ap.add_argument('--images', help='folder of JPEGs standing in for the camera')
    ap.add_argument('--out', default='results/replay')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'replay_log.txt'), 'w') as log:
        stats = run(ReplayLink(a.replay), ImageCamera(a.images), a.out, log)
        log.write('\nSTATS %s\n' % stats)
    print(stats)


if __name__ == '__main__':
    main()
