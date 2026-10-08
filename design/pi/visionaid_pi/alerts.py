"""Alert manager on the Pi: turns FPGA status + camera detections into short spoken phrases.

Priorities (lower = more urgent):
  0  safety status from the FPGA: drop-off, sensor / LiDAR fault        (haptics already fired in the FPGA)
  1  hazard naming: camera label + FPGA distance on the same side          e.g. "car, left, 1.4 metres"
  2  text read-out after the READ button
The Pi never controls the motors - the FPGA does. Speech only adds information.
"""
import time

ZONE_SPEAK_MM = 3000          # name objects only when the FPGA sees something within 3 m


def _metres(mm):
    return 'under half a metre' if mm < 500 else '%.1f metres' % (mm / 1000.0)


class AlertManager:
    def __init__(self, cooldown_s=4.0, clock=time.monotonic):
        self.cooldown = cooldown_s
        self.clock = clock
        self.last = {}

    def _ok(self, key):
        now = self.clock()
        if now - self.last.get(key, -1e9) >= self.cooldown:
            self.last[key] = now
            return True
        return False

    def update(self, status, detections=(), ocr_text=None):
        """Returns a list of (priority, phrase), most urgent first."""
        msgs = []
        if status is not None:
            if status.drop_off and self._ok('drop'):
                msgs.append((0, 'Step down ahead. Stop.'))
            if status.any_fault() and self._ok('fault'):
                which = [n for n, f in (('left', status.fault_left), ('right', status.fault_right),
                                        ('head', status.fault_head), ('floor', status.lidar_stale)) if f]
                msgs.append((0, 'Check device: %s sensor.' % ' and '.join(which)))
            side_mm = {'left': status.left_mm, 'right': status.right_mm,
                       'ahead': min(status.left_mm, status.right_mm, status.head_mm)}
            for d in detections:
                mm = side_mm[d['side']]
                if mm < ZONE_SPEAK_MM and self._ok('obj:' + d['label'] + d['side']):
                    msgs.append((1, '%s, %s, %s' % (d['spoken'], d['side'], _metres(mm))))
                    break                                            # one object per update - keep it short
        if ocr_text:
            msgs.append((2, ocr_text if len(ocr_text) < 200 else ocr_text[:200]))
        return sorted(msgs)
