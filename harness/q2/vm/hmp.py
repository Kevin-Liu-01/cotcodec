"""Minimal client for the QEMU human monitor (HMP) on the pinned OSWorld image.

The image starts QEMU with ``-monitor telnet:localhost:7100,server,nowait``
(``/run/config.sh``). The monitor listens on the VM container's loopback, so it
is reachable only from inside that network namespace: from the runner container
started with ``--network container:<vm>``. Nothing publishes it.

HMP is the independent device-level input path (R-dev) of the reviewed plan:
``sendkey`` and ``mouse_button`` drive QEMU's emulated PS/2 keyboard and
USB tablet, so events reach the guest through its kernel, evdev and xkb like
real hardware, without the guest-side code under test.

Standard library only; Python 3.10 compatible.
"""

from __future__ import annotations

import re
import socket
import time

PROMPT = b"(qemu) "
IAC = 255
# Telnet command bytes that carry one option byte after them.
_OPTION_COMMANDS = {251, 252, 253, 254}  # WILL, WONT, DO, DONT
_SB, _SE = 250, 240
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
# QEMU qcode names accepted by ``sendkey`` that the action-path suite uses.
SENDKEY_NAME_RE = re.compile(r"^[a-z0-9_]+(-[a-z0-9_]+)*$")


class HmpError(RuntimeError):
    """The monitor was unreachable or answered with an error."""


def strip_telnet(data: bytes) -> bytes:
    """Remove telnet negotiation (IAC sequences) from a byte stream."""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        byte = data[i]
        if byte != IAC:
            out.append(byte)
            i += 1
            continue
        if i + 1 >= n:
            break
        command = data[i + 1]
        if command == IAC:  # escaped 0xff
            out.append(IAC)
            i += 2
        elif command in _OPTION_COMMANDS:
            i += 3
        elif command == _SB:
            end = data.find(bytes([IAC, _SE]), i + 2)
            i = n if end < 0 else end + 2
        else:
            i += 2
    return bytes(out)


def clean_reply(raw: bytes, command: str) -> str:
    """Turn the bytes between a command and the next prompt into plain text.

    QEMU's readline echoes the command with cursor-redraw sequences, so the
    first line of a reply is the (garbled) echo and is dropped whenever a
    command was sent. Trailing prompts are dropped too.
    """
    text = strip_telnet(raw).decode("utf-8", errors="replace")
    text = _ANSI_RE.sub("", text).replace("\r", "")
    lines = text.split("\n")
    if command.strip() and lines:
        lines = lines[1:]
    while lines and lines[-1].strip() in ("", PROMPT.decode().strip()):
        lines.pop()
    return "\n".join(line.rstrip() for line in lines).strip()


class HmpClient:
    """Line-oriented HMP session over the container-local telnet socket."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7100, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.banner = ""

    def __enter__(self) -> HmpClient:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def connect(self) -> str:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        raw = self._read_until_prompt()
        self.banner = clean_reply(raw, "")
        return self.banner

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _read_until_prompt(self) -> bytes:
        assert self.sock is not None
        deadline = time.monotonic() + self.timeout
        buffer = b""
        while True:
            if strip_telnet(buffer).endswith(PROMPT):
                return buffer
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HmpError(f"no HMP prompt within {self.timeout}s")
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(65536)
            if not chunk:
                raise HmpError("HMP connection closed")
            buffer += chunk

    def command(self, line: str) -> str:
        if "\n" in line or "\r" in line:
            raise HmpError("one HMP command per call")
        if self.sock is None:
            raise HmpError("not connected")
        self.sock.sendall(line.encode("ascii") + b"\r")
        reply = clean_reply(self._read_until_prompt(), line)
        lowered = reply.lower()
        if lowered.startswith("unknown command") or "invalid parameter" in lowered:
            raise HmpError(f"HMP rejected {line!r}: {reply}")
        return reply

    def sendkey(self, combo: str, hold_ms: int = 100) -> str:
        if not SENDKEY_NAME_RE.fullmatch(combo):
            raise HmpError(f"unsafe sendkey combo {combo!r}")
        if not 1 <= hold_ms <= 5000:
            raise HmpError("hold_ms out of range")
        return self.command(f"sendkey {combo} {hold_ms}")

    def mouse_button(self, state: int) -> str:
        # HMP's bitmask: 1 left, 2 right, 4 middle (QEMU 9.1 hmp_mouse_button).
        if not 0 <= state <= 7:
            raise HmpError("mouse button state must be a 3-bit mask")
        return self.command(f"mouse_button {state}")

    def mouse_move(self, dx: int, dy: int, dz: int | None = None) -> str:
        for value in (dx, dy, dz or 0):
            if not -4096 <= value <= 4096:
                raise HmpError("mouse_move delta out of range")
        line = f"mouse_move {dx} {dy}" if dz is None else f"mouse_move {dx} {dy} {dz}"
        return self.command(line)
