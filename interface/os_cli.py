# os_cli.py

from state.os_state import read_state
from control.os_control import read_control, write_control

def show_status():
    state = read_state()
    print("\n=== GeOS Status ===")
    print(f"Current Mode      : {state['current_mode']}")
    print(f"ML Suggested Mode : {state['ml_suggested_mode']}")
    print(f"ML Thresholds     : {state['ml_thresholds']}")
    print(f"Sensors           : {state['sensors']}")
    print("========================\n")

def set_manual_mode(mode):
    control = read_control()
    control["auto_mode"] = False
    control["mode_override"] = mode
    write_control(control)
    print(f"Manual override set to {mode}")

def set_auto_mode():
    control = read_control()
    control["auto_mode"] = True
    control["mode_override"] = None
    write_control(control)
    print("Returned to AI-controlled auto mode")

def run_cli():
    print("GeOS CLI started")
    print("Commands:")
    print("  status")
    print("  set mode ENERGY_SAVER | BALANCED | PERFORMANCE")
    print("  set auto")
    print("  exit")

    while True:
        cmd = input("geos> ").strip()

        if cmd == "status":
            show_status()

        elif cmd.startswith("set mode"):
            parts = cmd.split()
            if len(parts) == 3:
                mode = parts[2].upper()
                if mode in ["ENERGY_SAVER", "BALANCED", "PERFORMANCE"]:
                    set_manual_mode(mode)
                else:
                    print("Invalid mode")
            else:
                print("Usage: set mode ENERGY_SAVER | BALANCED | PERFORMANCE")

        elif cmd == "set auto":
            set_auto_mode()

        elif cmd == "exit":
            print("Exiting CLI")
            break

        else:
            print("Unknown command")
            print("Commands:")
            print("  status")
            print("  set mode ENERGY_SAVER | BALANCED | PERFORMANCE")
            print("  set auto")
            print("  exit")

if __name__ == "__main__":
    run_cli()
