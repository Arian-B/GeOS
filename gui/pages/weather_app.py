import json
import urllib.parse
import urllib.request

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScroller,
    QVBoxLayout,
    QWidget,
)

from gui import theme

LOCATION_URL = "https://ipapi.co/json/"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_LABELS = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Strong showers",
    82: "Violent showers",
    95: "Thunderstorm",
}

WEATHER_FRAMES = {
    "sunny": [
        "   \\  |  /   \n     .-.     \n  -- ( ) --  \n     `-'     \n   /  |  \\   ",
        "    . | .    \n     .-.     \n  -- ( ) --  \n     `-'     \n    ' | '    ",
    ],
    "cloudy": [
        "      .--.   \n   .-(    ). \n  (___.__)__) \n             \n             ",
        "     .--.    \n  .-(    ).  \n (___.__)__) \n             \n             ",
    ],
    "rainy": [
        "     .--.    \n  .-(    ).  \n (___.__)__) \n   ' ' ' '   \n  ' ' ' '    ",
        "     .--.    \n  .-(    ).  \n (___.__)__) \n    ' ' ' '  \n   ' ' ' '   ",
    ],
    "storm": [
        "     .--.    \n  .-(    ).  \n (___.__)__) \n    / / /    \n   /_/ /_    ",
        "     .--.    \n  .-(    ).  \n (___.__)__) \n     / /     \n    /_/      ",
    ],
    "snow": [
        "     .--.    \n  .-(    ).  \n (___.__)__) \n   *  *  *   \n  *  *  *    ",
        "     .--.    \n  .-(    ).  \n (___.__)__) \n    *  *  *  \n   *  *  *   ",
    ],
}


def fetch_json(url, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "GeOS/1.0"})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def condition_key(code):
    if code in {0, 1}:
        return "sunny"
    if code in {2, 3, 45, 48}:
        return "cloudy"
    if code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "rainy"
    if code in {71, 73, 75}:
        return "snow"
    if code in {95}:
        return "storm"
    return "cloudy"


class WeatherWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            location_data = fetch_json(LOCATION_URL)
            city = location_data.get("city") or location_data.get("region") or "Unknown"
            region = location_data.get("region") or location_data.get("country_name") or "Unknown"
            latitude = location_data.get("latitude")
            longitude = location_data.get("longitude")

            if latitude is None or longitude is None:
                geo = fetch_json(GEOCODE_URL, {"name": city, "count": 1, "language": "en", "format": "json"})
                results = geo.get("results") or []
                if not results:
                    raise RuntimeError("Location lookup failed.")
                first = results[0]
                latitude = first["latitude"]
                longitude = first["longitude"]
                city = first.get("name") or city
                region = first.get("country") or region

            weather = fetch_json(
                WEATHER_URL,
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                    "timezone": "auto",
                },
            )
            current = weather.get("current") or {}
            code = int(current.get("weather_code", 3))
            payload = {
                "city": city,
                "region": region,
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": code,
                "weather_label": WEATHER_LABELS.get(code, "Unknown weather"),
                "condition_key": condition_key(code),
            }
            self.finished.emit(payload)
        except Exception as exc:
            self.failed.emit(str(exc))


class WeatherAppPage(QWidget):
    def __init__(self):
        super().__init__()
        self._animation_index = 0
        self._weather_data = {}
        self._weather_thread = None
        self._weather_worker = None

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
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 2px solid {theme.SHELL_BORDER};
                border-bottom: 4px solid #051f1c;
                border-radius: 8px;
                padding: 10px 12px;
                font-weight: bold;
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
                padding-top: 12px;
                padding-bottom: 8px;
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
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)
        outer.addWidget(self.scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("WEATHER")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_weather)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.refresh_button)
        layout.addLayout(title_row)

        subtitle = QLabel("Live local weather with terminal-style animation based on the current condition.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        layout.addWidget(subtitle)

        self.status = QLabel("Fetching live weather...")
        self.status.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_SECONDARY};")
        layout.addWidget(self.status)

        self.animation_frame = QFrame()
        self.animation_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.SHELL_BG};
                border: 2px solid {theme.TEXT_SECONDARY};
                border-radius: 12px;
            }}
            """
        )
        frame_layout = QVBoxLayout(self.animation_frame)
        frame_layout.setContentsMargins(16, 16, 16, 16)
        frame_layout.setSpacing(8)

        self.condition_label = QLabel("Condition: --")
        self.condition_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        self.ascii_label = QLabel("  ...")
        self.ascii_label.setAlignment(Qt.AlignCenter)
        self.ascii_label.setStyleSheet("font-size: 18px;")
        frame_layout.addWidget(self.condition_label)
        frame_layout.addWidget(self.ascii_label)
        layout.addWidget(self.animation_frame)

        self.temperature_label = QLabel("Temperature: --")
        self.humidity_label = QLabel("Humidity: --")
        self.wind_label = QLabel("Wind: --")
        self.location_label = QLabel("Location: --")
        for label in (self.location_label, self.temperature_label, self.humidity_label, self.wind_label):
            label.setStyleSheet("font-size: 15px;")
            layout.addWidget(label)

        layout.addStretch()

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.advance_animation)
        self.animation_timer.start(400)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_weather)
        self.refresh_timer.start(600000)

        self.refresh_weather()

    def on_page_activated(self):
        self.animation_timer.start(400)
        self.refresh_timer.start(600000)
        if not self._weather_data:
            self.refresh_weather()

    def on_page_deactivated(self):
        self.animation_timer.stop()
        self.refresh_timer.stop()

    def refresh_weather(self):
        if self._weather_thread is not None:
            try:
                if self._weather_thread.isRunning():
                    return
            except RuntimeError:
                self._weather_thread = None
                self._weather_worker = None
        self.status.setText("Refreshing live weather...")
        self._weather_thread = QThread(self)
        self._weather_worker = WeatherWorker()
        self._weather_worker.moveToThread(self._weather_thread)
        self._weather_thread.started.connect(self._weather_worker.run)
        self._weather_worker.finished.connect(self._on_weather_loaded)
        self._weather_worker.failed.connect(self._on_weather_failed)
        self._weather_worker.finished.connect(self._weather_thread.quit)
        self._weather_worker.failed.connect(self._weather_thread.quit)
        self._weather_thread.finished.connect(self._weather_worker.deleteLater)
        self._weather_thread.finished.connect(self._weather_thread.deleteLater)
        self._weather_thread.finished.connect(self._reset_worker_handles)
        self._weather_thread.start()

    def _reset_worker_handles(self):
        self._weather_thread = None
        self._weather_worker = None

    def _on_weather_loaded(self, payload):
        self._weather_data = payload
        self._animation_index = 0
        self.status.setText("Live weather loaded.")
        self.location_label.setText(f"Location: {payload['city']}, {payload['region']}")
        self.temperature_label.setText(f"Temperature: {payload.get('temperature', '--')} C")
        self.humidity_label.setText(f"Humidity: {payload.get('humidity', '--')}%")
        self.wind_label.setText(f"Wind: {payload.get('wind_speed', '--')} km/h")
        self.condition_label.setText(f"Condition: {payload['weather_label']}")
        self.advance_animation()

    def _on_weather_failed(self, message):
        self.status.setText(f"Weather unavailable: {message}")
        self.condition_label.setText("Condition: unavailable")
        self.ascii_label.setText("  [ no signal ]")

    def advance_animation(self):
        key = self._weather_data.get("condition_key", "cloudy")
        frames = WEATHER_FRAMES.get(key, WEATHER_FRAMES["cloudy"])
        self.ascii_label.setText(frames[self._animation_index % len(frames)])
        self._animation_index += 1
