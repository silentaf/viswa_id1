"""FPGA <-> Raspberry Pi UART protocol (115200 8N1). Mirrors rtl/va_pilink.v exactly.

FPGA -> Pi, every 20 ms, 11 bytes:
    0xA5, dL_hi, dL_lo, dR_hi, dR_lo, dH_hi, dH_lo, lidar_hi, lidar_lo, flags, checksum
    checksum = (sum of bytes 1..9) & 0xFF;  distances in mm (0xFFFF = nothing in range), LiDAR in cm
    flags: b0 fault L, b1 fault R, b2 fault H, b3 LiDAR stale, b4 drop-off,
           b5 READ pressed, b6 MODE pressed, b7 quiet mode
Pi -> FPGA, 5 bytes: 0x5A, addr, val_hi, val_lo, (addr + val_hi + val_lo) & 0xFF
    addr 1 urgent mm, 2 warn mm, 3 info mm, 4 LiDAR floor baseline cm, 5 quiet (0/1)
"""
from dataclasses import dataclass

STATUS_SYNC = 0xA5
CMD_SYNC = 0x5A
NO_ECHO = 0xFFFF
CMD_URGENT_MM, CMD_WARN_MM, CMD_INFO_MM, CMD_LIDAR_BASELINE_CM, CMD_QUIET = 1, 2, 3, 4, 5


@dataclass
class Status:
    left_mm: int
    right_mm: int
    head_mm: int
    lidar_cm: int
    flags: int

    fault_left = property(lambda s: bool(s.flags & 0x01))
    fault_right = property(lambda s: bool(s.flags & 0x02))
    fault_head = property(lambda s: bool(s.flags & 0x04))
    lidar_stale = property(lambda s: bool(s.flags & 0x08))
    drop_off = property(lambda s: bool(s.flags & 0x10))
    read_pressed = property(lambda s: bool(s.flags & 0x20))
    mode_pressed = property(lambda s: bool(s.flags & 0x40))
    quiet = property(lambda s: bool(s.flags & 0x80))

    def any_fault(self):
        return bool(self.flags & 0x0F)


def build_command(addr: int, value: int) -> bytes:
    hi, lo = (value >> 8) & 0xFF, value & 0xFF
    return bytes([CMD_SYNC, addr & 0xFF, hi, lo, (addr + hi + lo) & 0xFF])


def encode_status(st: Status) -> bytes:
    """Reference encoder (used for tests and the simulated link)."""
    body = [st.left_mm >> 8, st.left_mm & 0xFF, st.right_mm >> 8, st.right_mm & 0xFF,
            st.head_mm >> 8, st.head_mm & 0xFF, st.lidar_cm >> 8, st.lidar_cm & 0xFF, st.flags]
    body = [b & 0xFF for b in body]
    return bytes([STATUS_SYNC] + body + [sum(body) & 0xFF])


class StatusParser:
    """Byte-stream parser; resynchronises on 0xA5 and drops frames with a bad checksum."""

    def __init__(self):
        self.buf = bytearray()
        self.good = 0
        self.bad = 0

    def feed(self, data: bytes):
        out = []
        self.buf.extend(data)
        while True:
            i = self.buf.find(bytes([STATUS_SYNC]))
            if i < 0:
                self.buf.clear()
                break
            del self.buf[:i]
            if len(self.buf) < 11:
                break
            frame = self.buf[:11]
            if (sum(frame[1:10]) & 0xFF) == frame[10]:
                b = frame
                out.append(Status((b[1] << 8) | b[2], (b[3] << 8) | b[4], (b[5] << 8) | b[6],
                                  (b[7] << 8) | b[8], b[9]))
                self.good += 1
                del self.buf[:11]
            else:
                self.bad += 1
                del self.buf[:1]          # false sync byte: slide by one
        return out
