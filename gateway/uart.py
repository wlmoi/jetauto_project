"""UART codec derived from the supplied SDK wire implementation."""
import struct


def crc8(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x8C if value & 1 else 0)
    return value


def encode_packet(function, payload):
    if not 0 <= function <= 10 or len(payload) > 255:
        raise ValueError("Invalid UART frame")
    body = bytes([function, len(payload)]) + bytes(payload)
    return b"\xaa\x55" + body + bytes([crc8(body)])


def encode_motors(speeds):
    if len(speeds) != 4:
        raise ValueError("Four motor speeds required")
    payload = bytes([1, 4]) + b"".join(struct.pack("<Bf", index, speed) for index, speed in enumerate(speeds))
    return encode_packet(3, payload)


class FrameParser:
    def __init__(self):
        self.buffer = bytearray()
        self.invalid = 0

    def feed(self, data):
        self.buffer.extend(data)
        packets = []
        while self.buffer:
            start = self.buffer.find(b"\xaa\x55")
            if start < 0:
                self.buffer[:] = b"\xaa" if self.buffer[-1] == 0xAA else b""
                break
            del self.buffer[:start]
            if len(self.buffer) < 5:
                break
            if self.buffer[2] > 10:
                self.invalid += 1
                del self.buffer[0]
                continue
            size = self.buffer[3] + 5
            if len(self.buffer) < size:
                break
            candidate = self.buffer[:size]
            if crc8(candidate[2:-1]) != candidate[-1]:
                self.invalid += 1
                del self.buffer[0]
                continue
            packets.append((candidate[2], bytes(candidate[4:-1])))
            del self.buffer[:size]
        return packets
