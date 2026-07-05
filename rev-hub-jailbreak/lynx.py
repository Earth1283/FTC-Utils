"""
Raw REV Lynx Module protocol implementation.

The Lynx protocol is what a Control Hub / Driver Station talks to a REV
Expansion Hub over. It's not secret - it's baked into the open-source FTC
SDK (com.qualcomm.hardware.lynx), REV's own Saleae analyzer plugin, and the
community REVHubInterface project. This module re-implements the wire
format directly in Python so you can talk to a hub without the Android
Robot Controller app anywhere in the loop.

Frame layout (little-endian), per LynxDatagram:
    0x44 0x4B                  sync bytes ("DK")
    packetLength   u16         total length incl. frame + checksum
    destAddress    u8          RS485 module address, 255 = broadcast
    sourceAddress  u8
    messageNumber  u8          increments per transmission (retry tracking)
    referenceNumber u8         echoes the request's messageNumber in a reply
    packetId       u16         command number; bit 0x8000 set on responses
    payload        bytes
    checksum       u8          sum of all preceding bytes (mod 256), sync bytes excluded
"""
from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field

import serial
from serial.tools import list_ports

SYNC = b"\x44\x4b"
RESPONSE_BIT = 0x8000
BROADCAST_ADDRESS = 255

BAUD_RATE = 460800
FTDI_VID = 0x0403
FTDI_PID = 0x6015

# Standard commands - fixed opcodes, always available on every Lynx module.
CMD_ACK = 0x7F01
CMD_NACK = 0x7F02
CMD_GET_MODULE_STATUS = 0x7F03
CMD_KEEP_ALIVE = 0x7F04
CMD_FAIL_SAFE = 0x7F05
CMD_SET_NEW_MODULE_ADDRESS = 0x7F06
CMD_QUERY_INTERFACE = 0x7F07
CMD_START_DOWNLOAD = 0x7F08  # deliberately unused - see README
CMD_DOWNLOAD_CHUNK = 0x7F09  # deliberately unused - see README
CMD_SET_MODULE_LED_COLOR = 0x7F0A
CMD_GET_MODULE_LED_COLOR = 0x7F0B
CMD_SET_MODULE_LED_PATTERN = 0x7F0C
CMD_GET_MODULE_LED_PATTERN = 0x7F0D
CMD_DEBUG_LOG_LEVEL = 0x7F0E
CMD_DISCOVERY = 0x7F0F

CH_EMBEDDED_MODULE_ADDRESS = 173


class LynxError(Exception):
    pass


class LynxTimeout(LynxError):
    pass


class LynxNack(LynxError):
    def __init__(self, nack_reason: int):
        self.nack_reason = nack_reason
        super().__init__(f"hub NACKed with reason 0x{nack_reason:02x}")


@dataclass
class LynxPacket:
    dest: int
    source: int
    message_number: int
    reference_number: int
    command_id: int
    payload: bytes = b""

    @property
    def is_response(self) -> bool:
        return bool(self.command_id & RESPONSE_BIT)

    def encode(self) -> bytes:
        body = struct.pack(
            "<BBBBH",
            self.dest,
            self.source,
            self.message_number,
            self.reference_number,
            self.command_id,
        ) + self.payload
        total_len = 2 + 2 + len(body) + 1  # sync + length field + body + checksum
        frame = SYNC + struct.pack("<H", total_len) + body
        checksum = sum(frame[2:]) & 0xFF  # sync bytes excluded per spec
        return frame + bytes([checksum])

    @staticmethod
    def decode(frame: bytes) -> "LynxPacket":
        if frame[:2] != SYNC:
            raise LynxError(f"bad sync bytes: {frame[:2]!r}")
        checksum = frame[-1]
        computed = sum(frame[2:-1]) & 0xFF
        if checksum != computed:
            raise LynxError(f"checksum mismatch: got 0x{checksum:02x}, expected 0x{computed:02x}")
        dest, source, msg_num, ref_num, cmd_id = struct.unpack("<BBBBH", frame[4:10])
        payload = frame[10:-1]
        return LynxPacket(dest, source, msg_num, ref_num, cmd_id, payload)


def find_hub_port() -> str | None:
    """Scan serial ports for the FTDI chip REV solders onto every Expansion Hub."""
    for port in list_ports.comports():
        if port.vid == FTDI_VID and port.pid == FTDI_PID:
            return port.device
    return None


@dataclass
class LynxHub:
    port: str
    dest_address: int = CH_EMBEDDED_MODULE_ADDRESS
    source_address: int = 0
    timeout: float = 0.5
    _ser: serial.Serial | None = field(default=None, repr=False)
    _msg_number: int = field(default=1, repr=False)

    def open(self) -> None:
        self._ser = serial.Serial(self.port, BAUD_RATE, timeout=self.timeout)

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def __enter__(self) -> "LynxHub":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _next_message_number(self) -> int:
        n = self._msg_number
        self._msg_number = (self._msg_number % 255) + 1
        return n

    def _read_frame(self) -> bytes:
        assert self._ser is not None
        deadline = time.monotonic() + self.timeout
        buf = bytearray()
        # sync
        while len(buf) < 2:
            if time.monotonic() > deadline:
                raise LynxTimeout("no sync bytes received")
            b = self._ser.read(1)
            if not b:
                continue
            buf += b
            if bytes(buf[-2:]) != SYNC:
                if len(buf) > 2:
                    buf = buf[-2:]
        length_bytes = self._ser.read(2)
        if len(length_bytes) < 2:
            raise LynxTimeout("truncated length field")
        buf += length_bytes
        (total_len,) = struct.unpack("<H", length_bytes)
        remaining = total_len - len(buf)
        rest = self._ser.read(remaining)
        if len(rest) < remaining:
            raise LynxTimeout("truncated packet body")
        buf += rest
        return bytes(buf)

    def transact(self, command_id: int, payload: bytes = b"", dest: int | None = None) -> LynxPacket:
        """Send a command and wait for the matching response (or raise on NACK/timeout)."""
        assert self._ser is not None, "call .open() first"
        msg_num = self._next_message_number()
        pkt = LynxPacket(
            dest=dest if dest is not None else self.dest_address,
            source=self.source_address,
            message_number=msg_num,
            reference_number=0,
            command_id=command_id,
            payload=payload,
        )
        self._ser.reset_input_buffer()
        self._ser.write(pkt.encode())

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            frame = self._read_frame()
            resp = LynxPacket.decode(frame)
            if resp.reference_number != msg_num:
                continue  # stale/unrelated frame, keep waiting
            if resp.command_id == CMD_NACK:
                reason = resp.payload[0] if resp.payload else 0xFF
                raise LynxNack(reason)
            return resp
        raise LynxTimeout(f"no response to command 0x{command_id:04x}")

    # --- standard commands -------------------------------------------------

    def keep_alive(self) -> None:
        self.transact(CMD_KEEP_ALIVE)

    def get_module_status(self, clear_on_read: bool = False) -> bytes:
        return self.transact(CMD_GET_MODULE_STATUS, bytes([1 if clear_on_read else 0])).payload

    def query_interface(self, name: str) -> tuple[int, int]:
        """Returns (first_command_number, number_of_commands) for a named interface, e.g. 'DEKAInterface'."""
        name_bytes = name.encode("ascii")[:99].ljust(100, b"\x00")
        resp = self.transact(CMD_QUERY_INTERFACE, name_bytes)
        first_cmd, count = struct.unpack("<HH", resp.payload[:4])
        return first_cmd, count

    def set_led_color(self, r: int, g: int, b: int) -> None:
        self.transact(CMD_SET_MODULE_LED_COLOR, bytes([r, g, b]))

    def get_led_color(self) -> tuple[int, int, int]:
        payload = self.transact(CMD_GET_MODULE_LED_COLOR).payload
        return payload[0], payload[1], payload[2]

    def debug_log_level(self, group: int, verbosity: int) -> None:
        self.transact(CMD_DEBUG_LOG_LEVEL, bytes([group, verbosity]))

    def discover(self) -> list[int]:
        """Broadcast discovery and collect whatever module addresses answer."""
        assert self._ser is not None
        msg_num = self._next_message_number()
        pkt = LynxPacket(BROADCAST_ADDRESS, self.source_address, msg_num, 0, CMD_DISCOVERY)
        self._ser.reset_input_buffer()
        self._ser.write(pkt.encode())
        found = []
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            try:
                frame = self._read_frame()
                resp = LynxPacket.decode(frame)
                if resp.reference_number == msg_num:
                    found.append(resp.source)
            except LynxTimeout:
                break
        return found

    def raw_command(self, command_id: int, payload: bytes) -> LynxPacket:
        """Escape hatch: send whatever opcode you want. This is the whole point."""
        return self.transact(command_id, payload)
