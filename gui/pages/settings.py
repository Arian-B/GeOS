from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QScrollArea,
    QScroller,
)
from PySide6.QtCore import QTimer, Qt
import json
import os

from core_os import provisioning
from core_os import update_manager
from core_os.kernel_interface import tune_for_mode, current_governor, read_swappiness
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


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.BACKGROUND};
                font-family: {theme.MONO_FONT};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
            }}
            QLineEdit {{
                background-color: {theme.BACKGROUND};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.TEXT_SECONDARY};
                border-radius: 6px;
                padding: 6px;
            }}
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background-color: {theme.BUTTON_HOVER};
            }}
            QCheckBox {{
                color: {theme.TEXT_PRIMARY};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        self.page_title = QLabel("SYSTEM SETTINGS")
        self.page_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.page_title)

        self.status_banner = QLabel("Ready")
        self.status_banner.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY};")
        self.status_banner.setWordWrap(True)
        layout.addWidget(self.status_banner)

        self.os_frame = self._make_frame("Operating System")
        self.os_labels = self._add_lines(
            self.os_frame,
            [
                "Name: GeOS",
                "Version: 1.0 (Prototype)",
                "Boot Phase: --",
                "Slot: --",
            ],
        )
        layout.addWidget(self.os_frame)

        self.device_frame = self._make_frame("Device Identity")
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

        self.network_frame = self._make_frame("Network")
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

        self.update_frame = self._make_frame("Update Policy")
        self.update_labels = self._add_lines(
            self.update_frame,
            [
                "Require Signature: --",
                "Require SHA256: --",
                "Auto Stage: --",
                "Auto Apply: --",
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

        self.kernel_frame = self._make_frame("Kernel Integration (Software)")
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
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BUTTON_BG};
                border-radius: 10px;
                border: none;
            }}
        """)
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
        color = theme.TEXT_PRIMARY if not error else "#E63946"
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
        self._set_status("Network config saved")
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
        # Persist immediately so user toggles never get lost on auto-refresh.
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

        self.os_labels[0].setText("Name: GeOS")
        self.os_labels[1].setText("Version: 1.0 (Prototype)")
        self.os_labels[2].setText(f"Boot Phase: {boot_state.get('phase', state.get('boot_phase', '--'))}")
        self.os_labels[3].setText(f"Slot: {current_slot} (pending: {pending_slot})")

        self.device_labels[0].setText(f"Device ID: {device.get('device_id', '--')}")
        self.device_labels[1].setText(f"Label: {device.get('label', '--')}")
        self.device_labels[2].setText(f"Provisioned: {device.get('provisioned', '--')}")
        self.device_labels[3].setText(f"Created: {device.get('created_at', '--')}")

        self.network_labels[0].setText(f"SSID: {network_cfg.get('ssid', '--')}")
        self.network_labels[1].setText(f"Source: {network_cfg.get('source', '--')}")
        self.network_labels[2].setText(f"Updated: {network_cfg.get('updated_at', '--')}")
        self.network_labels[3].setText(f"Connectivity: {'ONLINE' if is_connected() else 'OFFLINE'}")

        self.update_labels[0].setText(f"Require Signature: {update_policy.get('require_signature', False)}")
        self.update_labels[1].setText(f"Require SHA256: {update_policy.get('require_sha256', False)}")
        self.update_labels[2].setText(f"Auto Stage: {update_policy.get('auto_stage_updates', True)}")
        self.update_labels[3].setText(f"Auto Apply: {update_policy.get('auto_apply_updates', False)}")

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
        self.kernel_labels[0].setText(f"CPU Governor: {current_governor() or '--'}")
        self.kernel_labels[1].setText(f"VM Swappiness: {read_swappiness() if read_swappiness() is not None else '--'}")
        self.kernel_labels[2].setText(
            f"Last Tune: {kernel_state.get('time', '--')} ({kernel_state.get('mode', '--')})"
        )

        os_mode = state.get("current_mode", "UNKNOWN")
        control_mode = control.get("mode", "UNKNOWN")
        network = state.get("sensors", {}).get("network", "UNKNOWN")
        safe_mode = control.get("safe_mode", False)

        self.status_labels[0].setText(f"OS Mode: {os_mode}")
        self.status_labels[1].setText(f"Control Mode: {control_mode}")
        self.status_labels[2].setText(f"Safe Mode: {safe_mode}")
        self.status_labels[3].setText(f"Network: {network}")
