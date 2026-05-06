#!/usr/bin/env python3
"""Native Messaging Host bridge.

Reads length-prefixed JSON messages from stdin (Chrome Native Messaging protocol),
forwards them via TCP to the RealTimeMix main program on localhost:35421,
and writes the TCP response back to stdout as length-prefixed JSON.
"""
import json
import socket
import struct
import sys

HOST = "127.0.0.1"
PORT = int(os.environ.get("RTM_PORT", "35421"))


def send_message(msg):
    data = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def read_message():
    raw = sys.stdin.buffer.read(4)
    if not raw:
        return None
    length = struct.unpack("=I", raw)[0]
    data = sys.stdin.buffer.read(length).decode("utf-8")
    return json.loads(data)


def forward_to_tcp(msg):
    try:
        with socket.create_connection((HOST, PORT), timeout=2.0) as sock:
            line = (json.dumps(msg) + "\n").encode("utf-8")
            sock.sendall(line)
            sock.shutdown(socket.SHUT_WR)
            resp = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
            if resp:
                return json.loads(resp.decode("utf-8"))
    except (socket.error, OSError, ConnectionRefusedError) as e:
        return {"status": "error", "message": f"Main program not running: {e}"}
    return {"status": "ok"}


def main():
    while True:
        msg = read_message()
        if msg is None:
            break
        resp = forward_to_tcp(msg)
        send_message(resp)


if __name__ == "__main__":
    main()
