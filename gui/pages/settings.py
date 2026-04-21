import datetime
import json
import os
import platform
import shutil
import socket

import psutil
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QScroller,
    QVBoxLayout,
    QWidget,
)

from core_os import provisioning
from core_os import update_manager
from core_os.kernel_interface import current_governor, read_swappiness, tune_for_mode
from core_os.network import is_connected
from gui import theme

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")
BOOT_STATE_FILE = os.path.join(BASE_DIR, "state", "boot_state.json")
DEVICE_FILE = os.path.join(BASE_DIR, "state", "device.json")
NETWORK_FILE = os.path.join(BASE_DIR, "state", "network.json")
UPDATE_POLICY_FILE = os.path.join(BASE_DIR, "state", "update_policy.json")
KERNEL_STATE_FILE = os.path.join(BASE_DIR, "state", "kernel_tuning.json")
SYSTEM_DIR = os.path.join(BASE_DIR, "system")
SLOT_CURRENT_FILE = os.path.join(SYSTEM_DIR, "slot_current")
SLOT_PENDING_FILE = os.path.join(SYSTEM_DIR, "slot_pending.json")

GEOS_SERVICE_MODULES = (
    "core_os.boot_manager",
    "core_os.energy_controller",
    "workloads.workload_manager",
    "telemetry.collector",
    "core_os.resource_daemon",
    "core_os.update_watcher",
    "interface.workflow_server",
    "interface.repl_server",
    "telemetry.metrics_server",
)


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def read_text(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def format_bytes(num_bytes):
    if not isinstance(num_bytes, (int, float)):
        return "--"
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return "--"


def format_uptime(seconds):
    if not isinstance(seconds, (int, float)):
        return "--"
    total = int(seconds)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def local_ip_addresses():
    ips = []
    try:
        for addrs in psutil.net_if_addrs().values():
            for addr in addrs:
                if getattr(addr, "family", None) == socket.AF_INET:
                    address = getattr(addr, "address", None)
                    if address and not address.startswith("127."):
                        ips.append(address)
    except Exception:
        return []
    return sorted(set(ips))


def running_geos_services():
    active = set()
    try:
        for proc in psutil.process_iter(attrs=["cmdline"]):
            cmdline = proc.info.get("cmdline") or []
            if not cmdline:
                continue
            for module in GEOS_SERVICE_MODULES:
                if module in cmdline:
                    active.add(module)
    except Exception:
        return 0
    return len(active)


def read_temperature_summary():
    try:
        groups = psutil.sensors_temperatures()
    except Exception:
        return "N/A"
    if not groups:
        return "N/A"
    for entries in groups.values():
        if not entries:
            continue
        current = getattr(entries[0], "current", None)
        if isinstance(current, (int, float)):
            return f"{current:.1f} C"
    return "N/A"


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {theme.BACKGROUND};
                font-family: {theme.MONO_FONT};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                border: none;
                background: transparent;
            }}
            QLineEdit {{
                background-color: {theme.SHELL_PANEL_ALT};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 6px;
            }}
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 6px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_HOVER};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-bottom: 4px solid #051f1c;
            }}
            QPushButton:pressed {{
                background-color: {theme.BUTTON_ACTIVE};
                border: 2px solid {theme.TEXT_PRIMARY};
                border-bottom: 2px solid #051f1c;
                padding-top: 10px;
                padding-bottom: 6px;
            }}
            QCheckBox {{
                color: {theme.TEXT_PRIMARY};
            }}
        """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        QScroller.grabGesture(self.scroll.viewport(), QScroller.TouchGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        self.page_title = QLabel("DEVICE CENTER")
        self.page_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.page_title)

        self.status_banner = QLabel("GeOS device software ready")
        self.status_banner.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY};")
        self.status_banner.setWordWrap(True)
        layout.addWidget(self.status_banner)

        self.overview_frame = self._make_frame("Device Overview")
        self.overview_labels = self._add_lines(
            self.overview_frame,
            [
                "Hostname: --",
                "Platform: --",
                "Uptime: --",
                "Live Status: --",
            ],
        )
        layout.addWidget(self.overview_frame)

        self.os_frame = self._make_frame("Operating System")
        self.os_labels = self._add_lines(
            self.os_frame,
            [
                "Name: GeOS",
                "Version: --",
                "Boot Phase: --",
                "Slot: --",
                "Kernel: --",
            ],
        )
        layout.addWidget(self.os_frame)

        self.hardware_frame = self._make_frame("Hardware")
        self.hardware_labels = self._add_lines(
            self.hardware_frame,
            [
                "Machine: --",
                "CPU: --",
                "Memory: --",
                "Storage: --",
                "Battery: --",
                "Temperature: --",
            ],
        )
        layout.addWidget(self.hardware_frame)

        self.device_frame = self._make_frame("Identity and Provisioning")
        self.device_labels = self._add_lines(
            self.device_frame,
            [
                "Device ID: --",
                "Label: --",
                "Provisioned: --",
                "Created: --",
            ],
        )
        device_actions = QHBoxLayout()
        self.device_label_input = QLineEdit()
        self.device_label_input.setPlaceholderText("Device label")
        self.save_label_btn = QPushButton("Save Label")
        self.provision_btn = QPushButton("Mark Provisioned")
        self.save_label_btn.clicked.connect(self.save_label)
        self.provision_btn.clicked.connect(self.mark_provisioned)
        device_actions.addWidget(self.device_label_input, 2)
        device_actions.addWidget(self.save_label_btn, 1)
        device_actions.addWidget(self.provision_btn, 1)
        self.device_frame.layout().addLayout(device_actions)
        layout.addWidget(self.device_frame)

        self.network_frame = self._make_frame("Connectivity")
        self.network_labels = self._add_lines(
            self.network_frame,
            [
                "SSID: --",
                "Source: --",
                "Updated: --",
                "Connectivity: --",
            ],
        )
        net_actions = QHBoxLayout()
        self.ssid_input = QLineEdit()
        self.ssid_input.setPlaceholderText("SSID")
        self.psk_input = QLineEdit()
        self.psk_input.setPlaceholderText("PSK (optional)")
        self.psk_input.setEchoMode(QLineEdit.Password)
        self.save_network_btn = QPushButton("Save Network")
        self.save_network_btn.clicked.connect(self.save_network)
        net_actions.addWidget(self.ssid_input, 1)
        net_actions.addWidget(self.psk_input, 1)
        net_actions.addWidget(self.save_network_btn, 1)
        self.network_frame.layout().addLayout(net_actions)
        layout.addWidget(self.network_frame)

        self.runtime_frame = self._make_frame("Runtime")
        self.runtime_labels = self._add_lines(
            self.runtime_frame,
            [
                "CPU Usage: --",
                "Memory Usage: --",
                "Load Average: --",
                "Active GeOS Services: --",
                "Current Mode: --",
            ],
        )
        layout.addWidget(self.runtime_frame)

        self.update_frame = self._make_frame("Update Policy")
        self.update_labels = self._add_lines(
            self.update_frame,
            [
                "Require Signature: --",
                "Require SHA256: --",
                "Auto Stage: --",
                "Auto Apply: --",
                "Update Slot: --",
            ],
        )
        self.require_sig = QCheckBox("Require Signature")
        self.require_sha = QCheckBox("Require SHA256")
        self.auto_stage = QCheckBox("Auto Stage Updates")
        self.auto_apply = QCheckBox("Auto Apply Updates")
        self._policy_checkboxes = (
            self.require_sig,
            self.require_sha,
            self.auto_stage,
            self.auto_apply,
        )
        for checkbox in self._policy_checkboxes:
            self.update_frame.layout().addWidget(checkbox)
            checkbox.toggled.connect(self._policy_toggled)
        self.save_policy_btn = QPushButton("Save Update Policy")
        self.save_policy_btn.clicked.connect(self.save_policy)
        self.update_frame.layout().addWidget(self.save_policy_btn)
        layout.addWidget(self.update_frame)

        self.kernel_frame = self._make_frame("Kernel Integration")
        self.kernel_labels = self._add_lines(
            self.kernel_frame,
            [
                "CPU Governor: --",
                "VM Swappiness: --",
                "Last Tune: --",
            ],
        )
        kernel_actions = QHBoxLayout()
        self.kernel_energy_btn = QPushButton("Apply ENERGY_SAVER Tune")
        self.kernel_balanced_btn = QPushButton("Apply BALANCED Tune")
        self.kernel_perf_btn = QPushButton("Apply PERFORMANCE Tune")
        self.kernel_energy_btn.clicked.connect(lambda: self.apply_kernel_tune("ENERGY_SAVER"))
        self.kernel_balanced_btn.clicked.connect(lambda: self.apply_kernel_tune("BALANCED"))
        self.kernel_perf_btn.clicked.connect(lambda: self.apply_kernel_tune("PERFORMANCE"))
        kernel_actions.addWidget(self.kernel_energy_btn)
        kernel_actions.addWidget(self.kernel_balanced_btn)
        kernel_actions.addWidget(self.kernel_perf_btn)
        self.kernel_frame.layout().addLayout(kernel_actions)
        layout.addWidget(self.kernel_frame)

        self.status_frame = self._make_frame("System Status")
        self.status_labels = self._add_lines(
            self.status_frame,
            [
                "OS Mode: --",
                "Control Mode: --",
                "Safe Mode: --",
                "Network: --",
                "Provisioning: --",
            ],
        )
        layout.addWidget(self.status_frame)

        self.services_frame = self._make_frame("Service Endpoints")
        self.services_labels = self._add_lines(
            self.services_frame,
            [
                "Workflow API: 8080",
                "Metrics API: 8090",
                "REPL: 5050",
            ],
        )
        layout.addWidget(self.services_frame)
        layout.addStretch()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self.refresh()

    def _make_frame(self, title):
        frame = QFrame()
        frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
                border: none;
            }}
        """
        )
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 14, 16, 14)
        header = QLabel(title)
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.setWordWrap(True)
        layout.addWidget(header)
        return frame

    def _add_lines(self, frame, lines):
        labels = []
        for line in lines:
            lbl = QLabel(line)
            lbl.setStyleSheet("font-size: 13px;")
            lbl.setWordWrap(True)
            frame.layout().addWidget(lbl)
            labels.append(lbl)
        return labels

    def _set_status(self, message, error=False):
        color = theme.TEXT_PRIMARY if not error else theme.ACCENT_DANGER
        self.status_banner.setText(message)
        self.status_banner.setStyleSheet(f"font-size: 13px; color: {color};")

    def save_label(self):
        label = self.device_label_input.text().strip() or None
        provisioning.set_device_label(label)
        self._set_status("Device label saved")
        self.refresh()

    def mark_provisioned(self):
        provisioning.mark_provisioned()
        self._set_status("Device marked as provisioned")
        self.refresh()

    def save_network(self):
        ssid = self.ssid_input.text().strip()
        psk = self.psk_input.text().strip()
        provisioning.set_network_config(
            ssid=ssid if ssid else None,
            psk=psk if psk else None,
            source="settings",
        )
        self._set_status("Network configuration saved")
        self.refresh()

    def save_policy(self):
        policy = update_manager.read_policy()
        policy["require_signature"] = self.require_sig.isChecked()
        policy["require_sha256"] = self.require_sha.isChecked()
        policy["auto_stage_updates"] = self.auto_stage.isChecked()
        policy["auto_apply_updates"] = self.auto_apply.isChecked()
        write_json(UPDATE_POLICY_FILE, policy)
        self._set_status("Update policy saved")
        self.refresh()

    def _policy_toggled(self, _checked):
        self.save_policy()

    def apply_kernel_tune(self, mode_name):
        result = tune_for_mode(mode_name)
        gov = result.get("governor_result", {})
        swap = result.get("swappiness_result", {})
        if gov.get("ok") or swap.get("ok"):
            self._set_status(f"Kernel tuning applied for {mode_name}")
        else:
            self._set_status(
                f"Kernel tuning attempted for {mode_name} but requires elevated permissions",
                error=True,
            )
        self.refresh()

    def refresh(self):
        state = read_json(STATE_FILE) or {}
        control = read_json(CONTROL_FILE) or {}
        boot_state = read_json(BOOT_STATE_FILE) or {}
        device = read_json(DEVICE_FILE) or {}
        network_cfg = read_json(NETWORK_FILE) or {}
        update_policy = update_manager.read_policy()
        current_slot = read_text(SLOT_CURRENT_FILE) or "--"
        pending_slot = "--"
        pending = read_json(SLOT_PENDING_FILE)
        if isinstance(pending, dict):
            pending_slot = pending.get("slot") or "--"

        uname = platform.uname()
        hostname = socket.gethostname()
        live_status = "ONLINE" if is_connected() else "OFFLINE"
        uptime_seconds = max(0.0, datetime.datetime.now().timestamp() - psutil.boot_time())
        self.overview_labels[0].setText(f"Hostname: {hostname}")
        self.overview_labels[1].setText(f"Platform: {uname.system} {uname.release}")
        self.overview_labels[2].setText(f"Uptime: {format_uptime(uptime_seconds)}")
        self.overview_labels[3].setText(f"Live Status: {live_status}")

        self.os_labels[0].setText("Name: GeOS")
        self.os_labels[1].setText("Version: Demo OS Prototype")
        self.os_labels[2].setText(f"Boot Phase: {boot_state.get('phase', state.get('boot_phase', '--'))}")
        self.os_labels[3].setText(f"Slot: {current_slot} (pending: {pending_slot})")
        self.os_labels[4].setText(f"Kernel: {uname.release}")

        cpu_model = uname.processor or platform.processor() or uname.machine or "--"
        cpu_count = psutil.cpu_count() or 1
        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/")
        battery = psutil.sensors_battery()
        battery_text = "N/A"
        if battery is not None:
            source = "charging" if battery.power_plugged else "battery"
            battery_text = f"{int(round(battery.percent))}% ({source})"

        self.hardware_labels[0].setText(f"Machine: {uname.machine or '--'}")
        self.hardware_labels[1].setText(f"CPU: {cpu_model} | Cores: {cpu_count}")
        self.hardware_labels[2].setText(
            f"Memory: {format_bytes(memory.used)} used / {format_bytes(memory.total)} total ({memory.percent:.0f}%)"
        )
        self.hardware_labels[3].setText(
            f"Storage: {format_bytes(disk.used)} used / {format_bytes(disk.total)} total"
        )
        self.hardware_labels[4].setText(f"Battery: {battery_text}")
        self.hardware_labels[5].setText(f"Temperature: {read_temperature_summary()}")

        self.device_labels[0].setText(f"Device ID: {device.get('device_id', '--')}")
        self.device_labels[1].setText(f"Label: {device.get('label', '--')}")
        self.device_labels[2].setText(f"Provisioned: {device.get('provisioned', '--')}")
        self.device_labels[3].setText(f"Created: {device.get('created_at', '--')}")

        ip_text = ", ".join(local_ip_addresses()) or "--"
        self.network_labels[0].setText(f"SSID: {network_cfg.get('ssid', '--')}")
        self.network_labels[1].setText(f"Source: {network_cfg.get('source', '--')}")
        self.network_labels[2].setText(f"Updated: {network_cfg.get('updated_at', '--')}")
        self.network_labels[3].setText(f"Connectivity: {live_status} | IP: {ip_text}")

        sensors = state.get("sensors", {}) if isinstance(state.get("sensors"), dict) else {}
        self.runtime_labels[0].setText(f"CPU Usage: {sensors.get('cpu_percent', '--')}%")
        self.runtime_labels[1].setText(f"Memory Usage: {sensors.get('memory_percent', '--')}%")
        self.runtime_labels[2].setText(f"Load Average: {sensors.get('load_avg', '--')}")
        self.runtime_labels[3].setText(
            f"Active GeOS Services: {running_geos_services()} / {len(GEOS_SERVICE_MODULES)}"
        )
        self.runtime_labels[4].setText(f"Current Mode: {state.get('current_mode', '--')}")

        self.update_labels[0].setText(f"Require Signature: {update_policy.get('require_signature', False)}")
        self.update_labels[1].setText(f"Require SHA256: {update_policy.get('require_sha256', False)}")
        self.update_labels[2].setText(f"Auto Stage: {update_policy.get('auto_stage_updates', True)}")
        self.update_labels[3].setText(f"Auto Apply: {update_policy.get('auto_apply_updates', False)}")
        self.update_labels[4].setText(f"Update Slot: {current_slot} (pending: {pending_slot})")

        target_states = (
            bool(update_policy.get("require_signature", False)),
            bool(update_policy.get("require_sha256", False)),
            bool(update_policy.get("auto_stage_updates", True)),
            bool(update_policy.get("auto_apply_updates", False)),
        )
        for checkbox, target in zip(self._policy_checkboxes, target_states):
            checkbox.blockSignals(True)
            checkbox.setChecked(target)
            checkbox.blockSignals(False)

        kernel_state = read_json(KERNEL_STATE_FILE) or {}
        swappiness = read_swappiness()
        self.kernel_labels[0].setText(f"CPU Governor: {current_governor() or '--'}")
        self.kernel_labels[1].setText(f"VM Swappiness: {swappiness if swappiness is not None else '--'}")
        self.kernel_labels[2].setText(
            f"Last Tune: {kernel_state.get('time', '--')} ({kernel_state.get('mode', '--')})"
        )

        os_mode = state.get("current_mode", "UNKNOWN")
        control_mode = control.get("mode", "UNKNOWN")
        network = sensors.get("network", "UNKNOWN")
        safe_mode = control.get("safe_mode", False)
        provisioned = device.get("provisioned", False)

        self.status_labels[0].setText(f"OS Mode: {os_mode}")
        self.status_labels[1].setText(f"Control Mode: {control_mode}")
        self.status_labels[2].setText(f"Safe Mode: {safe_mode}")
        self.status_labels[3].setText(f"Network: {network}")
        self.status_labels[4].setText(f"Provisioning: {'COMPLETE' if provisioned else 'PENDING'}")
