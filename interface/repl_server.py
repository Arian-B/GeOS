# interface/repl_server.py

import json
import os
import socket
import threading

from control.os_control import read_control, write_control
from state.os_state import read_state

HOST = "127.0.0.1"
PORT = 5050


def _format_status():
    state = read_state()
    control = read_control()
    lines = [
        f"MODE: {state.get('current_mode')}",
        f"ML: {state.get('ml_suggested_mode')}",
        f"RL: {state.get('rl_action')}",
        f"CONTROL: {control.get('mode')}",
        f"MAINTENANCE: {control.get('maintenance')}",
    ]
    return "\n".join(lines) + "\n"


def _handle_command(line):
    parts = line.strip().split()
    if not parts:
        return ""
    cmd = parts[0].lower()
    if cmd == "help":
        return (
            "Commands:\n"
            "  status\n"
            "  mode ENERGY_SAVER|BALANCED|PERFORMANCE\n"
            "  auto\n"
            "  control key value\n"
            "  quit\n"
        )
    if cmd == "status":
        return _format_status()
    if cmd == "mode" and len(parts) == 2:
        mode = parts[1].upper()
        if mode not in ("ENERGY_SAVER", "BALANCED", "PERFORMANCE"):
            return "Invalid mode\n"
        control = read_control()
        control["mode"] = "MANUAL"
        control["manual_override_mode"] = mode
        control["forced_mode"] = mode
        write_control(control)
        return f"Manual override set to {mode}\n"
    if cmd == "auto":
        control = read_control()
        control["mode"] = "AUTO"
        control["manual_override_mode"] = None
        control["forced_mode"] = None
        write_control(control)
        return "Returned to AUTO\n"
    if cmd == "control" and len(parts) >= 3:
        key = parts[1]
        value = " ".join(parts[2:])
        control = read_control()
        if value.lower() in ("true", "false"):
            control[key] = value.lower() == "true"
        else:
            try:
                control[key] = json.loads(value)
            except Exception:
                control[key] = value
        write_control(control)
        return f"Updated {key}\n"
    if cmd == "quit":
        return "__QUIT__"
    return "Unknown command\n"


def _client_thread(conn, addr):
    conn.sendall(b"GeOS REPL. Type 'help'.\n")
    buffer = b""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                response = _handle_command(line.decode("utf-8", errors="ignore"))
                if response == "__QUIT__":
                    conn.sendall(b"bye\n")
                    return
                if response:
                    conn.sendall(response.encode("utf-8"))
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_server(host=HOST, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    while True:
        conn, addr = sock.accept()
        t = threading.Thread(target=_client_thread, args=(conn, addr), daemon=True)
        t.start()


def run_cli():
    print("GeOS REPL. Type 'help'.")
    while True:
        try:
            line = input("geos> ")
        except (EOFError, KeyboardInterrupt):
            break
        response = _handle_command(line)
        if response == "__QUIT__":
            break
        if response:
            print(response, end="")


if __name__ == "__main__":
    run_server()
