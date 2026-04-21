# network.py

import socket


def is_connected(host="8.8.8.8", port=53, timeout=0.5):
    """
    Lightweight connectivity check. Returns True if a socket connection succeeds.
    Uses a short timeout to avoid blocking the OS loop.
    """
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
        return True
    except OSError:
        return False
