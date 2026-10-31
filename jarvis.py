import sys
import os
import time
import json
import uuid
import subprocess
import webbrowser
import calendar
import re
import markdown
import threading
from datetime import datetime, date, timedelta
from html import escape
import psutil
from PySide6.QtCore import QThread, Signal, Qt, QTimer, QDate, QLocale, QUrl
from PySide6.QtGui import QColor, QTextCharFormat, QPen, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QLineEdit, QPushButton, QCalendarWidget, QListWidget,
    QListWidgetItem, QDialog, QFormLayout, QComboBox, QSpinBox,
    QDateEdit, QMessageBox, QColorDialog, QGridLayout,
    QTableView, QTextEdit, QInputDialog, QSizePolicy, QTextBrowser
)

EVENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_events.json")
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "jarvis_settings.json"
)
CHATS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "jarvis_chats.json"
)

EVENT_RETENTION_OPTIONS = [
    "Never",
    "1 Day",
    "3 Days",
    "1 Week",
    "2 Weeks",
    "1 Month",
    "2 Months",
    "3 Months",
    "6 Months",
    "1 Year",
]

# Liczba dni przechowywania. Miesiące i rok
# są liczone jako kalendarzowe okresy, nie przybliżona liczba dni.
EVENT_RETENTION_DAYS = {
    "Never": None,
    "1 Day": 1,
    "3 Days": 3,
    "1 Week": 7,
    "2 Weeks": 14,
    "1 Month": 30,
    "2 Months": 60,
    "3 Months": 90,
    "6 Months": 180,
    "1 Year": 365,
}


def load_settings():
    default_settings = {
        "event_retention": "Never"
    }

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            saved_settings = json.load(file)

        if isinstance(saved_settings, dict):
            retention = saved_settings.get("event_retention", "Never")

            if retention in EVENT_RETENTION_OPTIONS:
                default_settings["event_retention"] = retention

    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    return default_settings


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)
    except OSError as exc:
        print(f"Could not save J.A.R.V.I.S. settings: {exc}")

def subtract_retention_period(today, retention):
    """Zwraca datę graniczną dla wybranego okresu."""
    periods = {
        "1 Day": (0, 0, 1),
        "3 Days": (0, 0, 3),
        "1 Week": (0, 0, 7),
        "2 Weeks": (0, 0, 14),
        "1 Month": (0, 1, 0),
        "2 Months": (0, 2, 0),
        "3 Months": (0, 3, 0),
        "6 Months": (0, 6, 0),
        "1 Year": (1, 0, 0),
    }

    if retention == "Never" or retention not in periods:
        return None

    years, months, days = periods[retention]

    # Najpierw odejmij lata i miesiące.
    total_months = today.year * 12 + today.month - 1
    total_months -= years * 12 + months

    target_year = total_months // 12
    target_month = total_months % 12 + 1

    # Jeśli np. odejmujemy miesiąc od 31 marca,
    # wybierz ostatni istniejący dzień lutego.
    target_day = min(
        today.day,
        calendar.monthrange(target_year, target_month)[1]
    )

    return date(
        target_year,
        target_month,
        target_day
    ) - timedelta(days=days)

EVENT_COLORS = [
    "Red",
    "Green",
    "Blue",
    "Forest",
    "Yellow",
    "Turquoise",
    "Cyan",
    "Pink",
    "Orange",
    "Purple",
    "Brown",
    "Black",
    "White"
]

COLOR_HEX = {
    "Red":    "#ff4545",
    "Green":  "#35e875",
    "Blue":   "#398cff",
    "Forest": "#2e6f40",
    "Yellow": "#ffe34d",
    "Turquoise":   "#40e0d0",
    "Cyan":   "#00bfff",
    "Pink":   "#ff70bd",
    "Orange":   "#ff982f",
    "Purple":   "#b16cff",
    "Brown":  "#a56a43",
    "Black":  "#303846",
    "White":  "#ffffff",
}

CUSTOM_COLORS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "jarvis_custom_colors.json"
)

DEFAULT_CUSTOM_COLORS = {
    "Custom 1": "#ff0000",
    "Custom 2": "#00ff00",
    "Custom 3": "#0000ff",
}

def load_custom_colors():
    colors = DEFAULT_CUSTOM_COLORS.copy()

    if os.path.exists(CUSTOM_COLORS_FILE):
        try:
            with open(CUSTOM_COLORS_FILE, "r", encoding="utf-8") as file:
                saved_colors = json.load(file)

            for name in DEFAULT_CUSTOM_COLORS:
                value = saved_colors.get(name)

                if isinstance(value, str) and QColor(value).isValid():
                    colors[name] = QColor(value).name()

        except (OSError, json.JSONDecodeError):
            pass

    return colors

def save_custom_colors():
    with open(CUSTOM_COLORS_FILE, "w", encoding="utf-8") as file:
        json.dump(CUSTOM_COLORS, file, indent=4, ensure_ascii=False)
CUSTOM_COLORS = load_custom_colors()

class AIWorker(QThread):
    answer_ready = Signal(str)
    tool_requested = Signal(str, str)

    def __init__(self, message, history=None, other_chats=None):
        super().__init__()

        self.message = message
        self.history = history or []
        self.other_chats = other_chats or ""

        self._tool_event = threading.Event()
        self._tool_result = None

    def request_tool(self, name, arguments):
        self._tool_result = None
        self._tool_event.clear()

        self.tool_requested.emit(
            name,
            json.dumps(arguments, ensure_ascii=False),
        )

        # Wait for the main GUI thread to execute the function.
        if not self._tool_event.wait(timeout=120):
            return {
                "ok": False,
                "message": "The application did not respond to the action.",
            }

        try:
            return json.loads(self._tool_result)
        except (TypeError, json.JSONDecodeError):
            return {
                "ok": False,
                "message": "The application returned an invalid result.",
            }

    def provide_tool_result(self, result):
        self._tool_result = result
        self._tool_event.set()

    def run(self):
        try:
            from jarvis_ai import ask_jarvis

            answer = ask_jarvis(
                self.message,
                history=self.history,
                other_chats=self.other_chats,
                tool_executor=self.request_tool,
            )

            self.answer_ready.emit(str(answer))

        except Exception as exc:
            self.answer_ready.emit(f"AI error: {exc}")

class CustomColorDialog(QDialog):
    def __init__(self, initial_color, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Choose custom color")
        self.setMinimumWidth(320)

        color = QColor(initial_color)
        if not color.isValid():
            color = QColor("#398cff")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.hex_input = QLineEdit(color.name())
        self.hex_input.setPlaceholderText("#RRGGBB")
        form.addRow("HEX:", self.hex_input)

        self.red = QSpinBox()
        self.green = QSpinBox()
        self.blue = QSpinBox()

        for spin in (self.red, self.green, self.blue):
            spin.setRange(0, 255)

        self.red.setValue(color.red())
        self.green.setValue(color.green())
        self.blue.setValue(color.blue())

        form.addRow("Red:", self.red)
        form.addRow("Green:", self.green)
        form.addRow("Blue:", self.blue)

        layout.addLayout(form)

        self.preview = QLabel("Color preview")
        self.preview.setMinimumHeight(55)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)

        buttons = QHBoxLayout()
        ok_button = QPushButton("Select color")
        cancel_button = QPushButton("Cancel")

        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self.red.valueChanged.connect(self.update_from_rgb)
        self.green.valueChanged.connect(self.update_from_rgb)
        self.blue.valueChanged.connect(self.update_from_rgb)
        self.hex_input.editingFinished.connect(self.update_from_hex)

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        self.update_from_rgb()

    def update_from_rgb(self):
        color = QColor(
            self.red.value(),
            self.green.value(),
            self.blue.value()
        )

        self.hex_input.blockSignals(True)
        self.hex_input.setText(color.name())
        self.hex_input.blockSignals(False)

        self.preview.setStyleSheet(
            f"background-color: {color.name()};"
            "border: 1px solid #ffffff;"
            "border-radius: 8px;"
        )

    def update_from_hex(self):
        color = QColor(self.hex_input.text().strip())

        if not color.isValid():
            self.update_from_rgb()
            return

        self.red.setValue(color.red())
        self.green.setValue(color.green())
        self.blue.setValue(color.blue())

    def selected_color(self):
        return QColor(
            self.red.value(),
            self.green.value(),
            self.blue.value()
        )


class CustomColorPicker(QDialog):
    def __init__(self, initial_color, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose event color")
        self.setMinimumWidth(340)

        self.selected_color = QColor(initial_color)

        layout = QVBoxLayout(self)

        title = QLabel("SELECT COLOR")
        title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #42d9ff;"
        )
        layout.addWidget(title)

        # Paleta gotowych kolorów
        palette_layout = QGridLayout()
        palette_layout.setSpacing(6)

        self.palette_colors = [
            "#ff0000", "#ff4040", "#ff8080", "#800000", "#cc3333", "#ff6666",
            "#00ff00", "#40ff40", "#80ff80", "#008000", "#00aa55", "#66cc66",
            "#0000ff", "#4040ff", "#8080ff", "#000080", "#4169e1", "#6495ed",
            "#ffff00", "#ffd700", "#ffa500", "#ff8000", "#ffcc00", "#ffee88",
            "#00ffff", "#40e0d0", "#00aaaa", "#008080", "#66cccc", "#99ffff",
            "#ff00ff", "#ff69b4", "#cc00cc", "#800080", "#dda0dd", "#ffb6c1",
        ]

        for i, color_hex in enumerate(self.palette_colors):
            button = QPushButton()
            button.setFixedSize(38, 30)
            button.setToolTip(color_hex)
            button.setStyleSheet(
                f"background-color: {color_hex};"
                "border: 1px solid #777;"
                "border-radius: 5px;"
            )
            button.clicked.connect(
                lambda checked=False, c=color_hex: self.select_color(c)
            )
            palette_layout.addWidget(button, i // 6, i % 6)

        layout.addLayout(palette_layout)

        # Własny kolor HEX i RGB
        form = QFormLayout()

        self.hex_input = QLineEdit(self.selected_color.name())
        self.red_input = QSpinBox()
        self.green_input = QSpinBox()
        self.blue_input = QSpinBox()

        for spin in (
            self.red_input,
            self.green_input,
            self.blue_input
        ):
            spin.setRange(0, 255)

        self.red_input.setValue(self.selected_color.red())
        self.green_input.setValue(self.selected_color.green())
        self.blue_input.setValue(self.selected_color.blue())

        form.addRow("HEX:", self.hex_input)
        form.addRow("Red:", self.red_input)
        form.addRow("Green:", self.green_input)
        form.addRow("Blue:", self.blue_input)

        layout.addLayout(form)

        # Podgląd wybranego koloru
        self.preview = QLabel("Color preview")
        self.preview.setMinimumHeight(45)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)

        self.hex_input.textChanged.connect(self.update_from_hex)
        self.red_input.valueChanged.connect(self.update_from_rgb)
        self.green_input.valueChanged.connect(self.update_from_rgb)
        self.blue_input.valueChanged.connect(self.update_from_rgb)

        # Przyciski
        buttons = QHBoxLayout()

        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self.update_preview(self.selected_color)

    def select_color(self, color_hex):
        color = QColor(color_hex)

        self.red_input.blockSignals(True)
        self.green_input.blockSignals(True)
        self.blue_input.blockSignals(True)
        self.hex_input.blockSignals(True)

        self.red_input.setValue(color.red())
        self.green_input.setValue(color.green())
        self.blue_input.setValue(color.blue())
        self.hex_input.setText(color.name())

        self.red_input.blockSignals(False)
        self.green_input.blockSignals(False)
        self.blue_input.blockSignals(False)
        self.hex_input.blockSignals(False)

        self.update_preview(color)


    def update_preview(self, color):
        self.selected_color = QColor(color)

        # Oblicz jasność koloru, aby dobrać kontrastowy tekst
        brightness = (
            0.299 * self.selected_color.red()
            + 0.587 * self.selected_color.green()
            + 0.114 * self.selected_color.blue()
        )

        text_color = "#000000" if brightness > 150 else "#ffffff"

        self.preview.setText(self.selected_color.name())
        self.preview.setStyleSheet(
            f"background-color: {self.selected_color.name()};"
            f"color: {text_color};"
            "border: 1px solid #42d9ff;"
            "border-radius: 6px;"
        )

    def update_from_hex(self, value):
        color = QColor(value.strip())

        if color.isValid() and value.strip().startswith("#"):
            self.red_input.blockSignals(True)
            self.green_input.blockSignals(True)
            self.blue_input.blockSignals(True)

            self.red_input.setValue(color.red())
            self.green_input.setValue(color.green())
            self.blue_input.setValue(color.blue())

            self.red_input.blockSignals(False)
            self.green_input.blockSignals(False)
            self.blue_input.blockSignals(False)

            self.update_preview(color)

    def update_from_rgb(self, *_):
        color = QColor(
            self.red_input.value(),
            self.green_input.value(),
            self.blue_input.value()
        )

        self.hex_input.blockSignals(True)
        self.hex_input.setText(color.name())
        self.hex_input.blockSignals(False)

        self.update_preview(color)

    def get_color(self):
        return QColor(self.selected_color)

class EventDateCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setGridVisible(True)
        self.setNavigationBarVisible(True)
        self.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )

        self.setStyleSheet("""
            QCalendarWidget QTableView {
                selection-background-color: #42d9ff;
                selection-color: #07111f;
            }
        """)

        self.currentPageChanged.connect(
            self.hide_outside_month_days
        )

        self.hide_outside_month_days(
            self.yearShown(),
            self.monthShown()
        )

    def hide_outside_month_days(self, year, month):
        first_day = QDate(year, month, 1)
        last_day = first_day.addMonths(1).addDays(-1)

        hidden_format = QTextCharFormat()
        hidden_format.setForeground(QColor("#0c1b2c"))

        current = first_day.addDays(
            1 - first_day.dayOfWeek()
        )

        last_visible = last_day.addDays(
            7 - last_day.dayOfWeek()
        )

        while current <= last_visible:
            if current.month() != month or current.year() != year:
                self.setDateTextFormat(current, hidden_format)
            else:
                self.setDateTextFormat(current, QTextCharFormat())

            current = current.addDays(1)

    def paintCell(self, painter, rect, cell_date):
        if (
            cell_date.month() != self.monthShown()
            or cell_date.year() != self.yearShown()
        ):
            painter.save()
            painter.fillRect(rect, QColor("#0c1b2c"))
            painter.restore()
            return

        super().paintCell(painter, rect, cell_date)

class EventDialog(QDialog):
    def __init__(self, parent=None, event=None, initial_date=None):
        super().__init__(parent)

        self.setWindowTitle("Calendar event")
        self.setMinimumWidth(360)

        self.selected_custom_color = QColor("#398cff")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Math test")

        self.date_input = QDateEdit()
        self.date_input.setLocale(
            QLocale(QLocale.Language.English)
        )
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")

        event_calendar = EventDateCalendar(self.date_input)
        self.date_input.setCalendarWidget(event_calendar)
        if initial_date:
            self.date_input.setDate(
                QDate(
                    initial_date.year,
                    initial_date.month,
                    initial_date.day
                )
            )
        else:
            self.date_input.setDate(QDate.currentDate())



        self.color_input = QComboBox()

        # Standardowe kolory — bez duplikatów
        for color_name in dict.fromkeys(EVENT_COLORS):
            self.color_input.addItem(color_name)
            self.color_input.setItemData(
                self.color_input.count() - 1,
                QColor(COLOR_HEX[color_name]),
                Qt.ItemDataRole.ForegroundRole
            )

        # Dokładnie trzy własne kolory
        for slot_name, color_hex in CUSTOM_COLORS.items():
            self.color_input.addItem(slot_name)
            self.color_input.setItemData(
                self.color_input.count() - 1,
                QColor(color_hex),
                Qt.ItemDataRole.ForegroundRole
            )



        # Przycisk otwierający paletę kolorów
        self.custom_color_button = QPushButton("Choose custom color")
        self.custom_color_button.clicked.connect(
            self.choose_custom_color
        )

        self.priority_input = QSpinBox()
        self.priority_input.setRange(1, 10)
        self.priority_input.setValue(5)

        form.addRow("Event name:", self.title_input)
        form.addRow("Date:", self.date_input)
        form.addRow("Color:", self.color_input)
        form.addRow("Custom color:", self.custom_color_button)
        form.addRow("Priority (1–10):", self.priority_input)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")

        save_button.clicked.connect(self.validate_and_accept)
        cancel_button.clicked.connect(self.reject)

        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        # Wczytaj dane podczas edycji wydarzenia
        if event:
            self.title_input.setText(event.get("title", ""))

            try:
                y, m, d = map(int, event["date"].split("-"))
                self.date_input.setDate(QDate(y, m, d))
            except (KeyError, ValueError, TypeError):
                pass

            saved_color = event.get("color", "Blue")

            if saved_color.startswith("#"):
                custom_color = QColor(saved_color)

                if custom_color.isValid():
                    self.selected_custom_color = custom_color

                    slot_name = next(
                        (
                            name for name, value in CUSTOM_COLORS.items()
                            if QColor(value).name().lower()
                            == custom_color.name().lower()
                        ),
                        None
                    )

                    if slot_name is None:
                        slot_name = "Custom 1"
                        CUSTOM_COLORS[slot_name] = custom_color.name()
                        save_custom_colors()

                    self.color_input.setCurrentText(slot_name)

            elif saved_color in EVENT_COLORS or saved_color in CUSTOM_COLORS:
                self.color_input.setCurrentText(saved_color)

            else:
                self.color_input.setCurrentText("Blue")



    def choose_custom_color(self):
        slot_name = self.color_input.currentText()

        if slot_name not in CUSTOM_COLORS:
            slot_name = "Custom 1"

        dialog = CustomColorPicker(
            QColor(CUSTOM_COLORS[slot_name]),
            self
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        color = dialog.get_color()

        if not color.isValid():
            return

        CUSTOM_COLORS[slot_name] = color.name()
        save_custom_colors()

        index = self.color_input.findText(slot_name)
        self.color_input.setItemData(
            index,
            color,
            Qt.ItemDataRole.ForegroundRole
        )

    def validate_and_accept(self):
        title = self.title_input.text().strip()

        if not title:
            QMessageBox.warning(
                self,
                "Invalid event name",
                "Event name cannot be empty."
            )
            return

        if ":" in title or ";" in title:
            QMessageBox.warning(
                self,
                "Invalid event name",
                "Event name cannot contain ':' or ';'."
            )
            return

        self.accept()

    def event_data(self):
        selected_color = self.color_input.currentText()

        if selected_color in CUSTOM_COLORS:
            color_value = CUSTOM_COLORS[selected_color]
        else:
            color_value = selected_color


        return {
            "title": self.title_input.text().strip(),
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "color": color_value,
            "priority": self.priority_input.value(),
        }


class CleanCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.events = []
        self.view_mode = "Month"
        self.span_start = QDate.currentDate()
        self.span_end = QDate.currentDate()

        # Wiele zaznaczonych okresów: (data_początkowa, data_końcowa).
        self.selected_periods = []

        self.mode_border_colors = {
            "Year": QColor("#ffe34d"),
            "Month": QColor("#40e0d0"),
            "Week": QColor("#2e6f40"),
            "Day": QColor("#ff982f"),
            "Span": QColor("#ffffff"),
        }
        self.setGridVisible(True)
        self.setDateEditEnabled(False)
        self.setNavigationBarVisible(True)
        self.setLocale(QLocale(QLocale.Language.English))
        self.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )

        table = self.findChild(QTableView)
        if table is not None:
            table.setShowGrid(True)

        self.currentPageChanged.connect(self.update_calendar_formats)
        self.currentPageChanged.connect(self.update)

        self.selectionChanged.connect(self.update)
        self.clicked.connect(self.handle_period_click)
        self.update_calendar_formats(
            self.yearShown(),
            self.monthShown()
        )

        # Ukryj nagłówki dni spoza bieżącego miesiąca,
        # a weekendy oznacz kolorem czerwonym.
        self.setStyleSheet("""
            QCalendarWidget QTableView {
                selection-background-color: #42d9ff;
                selection-color: #07111f;
            }
        """)

    def set_events(self, events):
        self.events = events
        self.update()

    def update_calendar_formats(self, year, month):
        first_day = QDate(year, month, 1)
        first_visible = first_day.addDays(
            1 - first_day.dayOfWeek()
        )

        last_day = first_day.addMonths(1).addDays(-1)
        last_visible = last_day.addDays(
            7 - last_day.dayOfWeek()
        )

        hidden_format = QTextCharFormat()
        hidden_format.setForeground(QColor("#0c1b2c"))

        current = first_visible
        while current <= last_visible:
            if current.month() != month or current.year() != year:
                self.setDateTextFormat(current, hidden_format)
            else:
                self.setDateTextFormat(current, QTextCharFormat())

            current = current.addDays(1)

    def set_view_mode(self, mode):
        self.view_mode = mode

        if mode in ("Day", "Week", "Month", "Year"):
            self.selected_periods = [
                self.get_period_range(self.selectedDate())
            ]

        self.update()

    def get_period_range(self, selected_date):
        mode = self.view_mode

        if mode == "Day":
            return selected_date, selected_date

        if mode == "Week":
            start = selected_date.addDays(
                1 - selected_date.dayOfWeek()
            )
            return start, start.addDays(6)

        if mode == "Month":
            start = QDate(
                selected_date.year(),
                selected_date.month(),
                1
            )
            return start, start.addMonths(1).addDays(-1)

        if mode == "Year":
            start = QDate(selected_date.year(), 1, 1)
            return start, QDate(selected_date.year(), 12, 31)

        return selected_date, selected_date


    def handle_period_click(self, clicked_date):
        # Span pomijamy.
        if self.view_mode not in ("Day", "Week", "Month", "Year"):
            return

        from PySide6.QtWidgets import QApplication

        ctrl_pressed = bool(
            QApplication.keyboardModifiers()
            & Qt.KeyboardModifier.ControlModifier
        )

        period = self.get_period_range(clicked_date)

        if not ctrl_pressed:
            # Zwykłe kliknięcie usuwa poprzednie zaznaczenia.
            self.selected_periods = [period]
        else:
            # Ctrl + kliknięcie przełącza zaznaczenie okresu.
            if period in self.selected_periods:
                self.selected_periods.remove(period)
            else:
                self.selected_periods.append(period)

        self.update()

        # Odśwież listę wydarzeń po zmianie zaznaczenia.
        self.selectionChanged.emit()

    def set_span_dates(self, start_date, end_date):
        self.span_start = min(start_date, end_date)
        self.span_end = max(start_date, end_date)
        self.update()

    def date_is_in_range(self, cell_date):
        if self.selected_periods:
            return any(
                start <= cell_date <= end
                for start, end in self.selected_periods
            )

        selected = self.selectedDate()
        start, end = self.get_period_range(selected)

        return start <= cell_date <= end

    def date_is_in_border_range(self, cell_date):
        if (
            cell_date.month() != self.monthShown()
            or cell_date.year() != self.yearShown()
        ):
            return False

        return self.date_is_in_range(cell_date)

    def draw_mode_border(self, painter, rect, cell_date):
        if not self.date_is_in_border_range(cell_date):
            return

        def inside(day):
            return self.date_is_in_border_range(day)

        painter.save()
        painter.setPen(
            QPen(self.mode_border_colors[self.view_mode], 2)
        )

        left = rect.left() + 1
        right = rect.right() - 1
        top = rect.top() + 1
        bottom = rect.bottom() - 1

        if not inside(cell_date.addDays(-1)):
            painter.drawLine(left, top, left, bottom)

        if not inside(cell_date.addDays(1)):
            painter.drawLine(right, top, right, bottom)

        if not inside(cell_date.addDays(-7)):
            painter.drawLine(left, top, right, top)

        if not inside(cell_date.addDays(7)):
            painter.drawLine(left, bottom, right, bottom)

        painter.restore()

    def paintCell(self, painter, rect, cell_date):
        # Ukryj dni spoza miesiąca, ale nadal rysuj ramkę.
        if (
            cell_date.month() != self.monthShown()
            or cell_date.year() != self.yearShown()
        ):
            painter.save()
            painter.fillRect(rect, QColor("#0c1b2c"))
            painter.restore()

            self.draw_mode_border(painter, rect, cell_date)
            return

        date_string = cell_date.toString("yyyy-MM-dd")

        day_events = sorted(
            [
                event for event in self.events
                if event.get("date") == date_string
            ],
            key=lambda event: int(event.get("priority", 5)),
            reverse=True
        )[:4]

        if not day_events:
            super().paintCell(painter, rect, cell_date)

            if cell_date.dayOfWeek() in (6, 7):
                painter.save()
                painter.setPen(QColor("#ff4d5e"))
                painter.drawText(
                    rect,
                    Qt.AlignmentFlag.AlignCenter,
                    str(cell_date.day())
                )
                painter.restore()

        else:
            painter.save()

            width = rect.width()
            count = len(day_events)

            for i, event in enumerate(day_events):
                color_value = event.get("color", "Blue")

                if color_value.startswith("#"):
                    color = QColor(color_value)
                else:
                    color = QColor(
                        COLOR_HEX.get(color_value, "#6bcaff")
                    )

                left = rect.left() + width * i // count
                right = rect.left() + width * (i + 1) // count

                segment = rect.adjusted(0, 0, 0, 0)
                segment.setLeft(left)
                segment.setRight(right - 1)
                painter.fillRect(segment, color)

            color_value = day_events[0].get("color", "Blue")

            if color_value.startswith("#"):
                avg_color = QColor(color_value)
            else:
                avg_color = QColor(
                    COLOR_HEX.get(color_value, "#6bcaff")
                )

            brightness = (
                0.299 * avg_color.red()
                + 0.587 * avg_color.green()
                + 0.114 * avg_color.blue()
            )

            text_color = (
                QColor("#07111f")
                if brightness > 150
                else QColor("#ffffff")
            )

            painter.setPen(text_color)
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                str(cell_date.day())
            )
            painter.restore()

        # Ramka zakresu — dla dni z wydarzeniami i bez nich
        self.draw_mode_border(painter, rect, cell_date)

        # Biała ramka aktualnie wybranego dnia
        if cell_date == self.selectedDate():
            painter.save()
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawRect(rect.adjusted(3, 3, -4, -4))
            painter.restore()

class ChatInput(QTextEdit):
    send_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setPlaceholderText("Message J.A.R.V.I.S...")
        self.setFixedHeight(42)
        self.setTabChangesFocus(True)

    def keyPressEvent(self, event):
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter
        ):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()

            return

        super().keyPressEvent(event)

class JarvisDashboard(QWidget):
    def update_span_range(self):
        self.calendar_widget.set_span_dates(
            self.span_start_input.date(),
            self.span_end_input.date()
        )
        self.refresh_event_list()

    def handle_ai_tool_call(self, name, arguments_json):
        worker = self.ai_worker

        if worker is None:
            return

        try:
            args = json.loads(arguments_json)
            result = self.execute_ai_tool(name, args)

        except Exception as exc:
            result = {
                "ok": False,
                "message": f"Action failed: {exc}",
            }

        worker.provide_tool_result(
            json.dumps(result, ensure_ascii=False)
        )

    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S. Dashboard")
        self.resize(1400, 900)
        self.last_net = psutil.net_io_counters()
        self.last_net_time = time.monotonic()
        self.events = self.load_events()
        self.settings = load_settings()
        self.event_retention = self.settings["event_retention"]

        self.setStyleSheet("""
            QWidget { background: #07111f; color: #d8f5ff; font-family: Segoe UI; }
            QFrame { background: #0c1b2c; border: 1px solid #15506b; border-radius: 14px; }
            QLabel#heading { color: #42d9ff; font-size: 17px; font-weight: bold; }
            QLabel#value { color: #ffffff; font-size: 25px; font-weight: bold; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit {
                background: #10243a; border: 1px solid #2498c4; border-radius: 8px;
                padding: 8px; font-size: 14px;
            }
            QPushButton { background: #087da5; border: none; border-radius: 9px;
                padding: 10px 15px; font-weight: bold; }
            QPushButton:hover { background: #10a6d6; }
            QListWidget, QCalendarWidget QAbstractItemView { background: #0a1726;
                alternate-background-color: #10243a; selection-background-color: #087da5;
                border: 1px solid #15506b; }
            QCalendarWidget QWidget { background: #0c1b2c; }
        """)
        self.pending_calendar_deletion = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 8)
        main_layout.setSpacing(7)

        header = QHBoxLayout()
        title = QLabel("J.A.R.V.I.S.")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #42d9ff;")
        self.system_status = QLabel("SYSTEM ONLINE")
        self.system_status.setStyleSheet("color: #63ffbb; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.system_status)
        main_layout.addLayout(header)

        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet("font-size: 42px; font-weight: bold; color: white;")
        main_layout.addWidget(self.clock_label)

        # Large calendar panel + two separate system cards.
        upper = QHBoxLayout()
        calendar_frame = QFrame()
        calendar_frame.setMinimumHeight(280)

        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_heading = QLabel("CALENDAR")
        calendar_heading.setObjectName("heading")
        calendar_layout.addWidget(calendar_heading)
        self.calendar_widget = CleanCalendar()
        self.calendar_widget.setMinimumHeight(210)
        self.calendar_widget.setGridVisible(True)
        self.calendar_widget.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar_widget.setLocale(
            __import__("PySide6.QtCore", fromlist=["QLocale"]).QLocale(
                __import__("PySide6.QtCore", fromlist=["QLocale"]).QLocale.Language.English,
                __import__("PySide6.QtCore", fromlist=["QLocale"]).QLocale.Country.UnitedKingdom
            )
        )

        # Ukryj dni należące do poprzedniego i następnego miesiąca
        self.calendar_widget.setDateEditEnabled(False)
        self.calendar_widget.setNavigationBarVisible(True)
        self.calendar_widget.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar_widget.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.calendar_widget.selectionChanged.connect(self.refresh_event_list)
        self.calendar_widget.currentPageChanged.connect(
        lambda year, month: self.refresh_event_list()
        )
        calendar_layout.addWidget(self.calendar_widget, 1)

        event_buttons = QHBoxLayout()

        add_button = QPushButton("+ Add event")
        edit_button = QPushButton("/ Edit selected")
        delete_button = QPushButton("- Delete selected")

        # Add = zielony
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #00ff00;
                color: #07111f;
                border: none;
                border-radius: 9px;
                padding: 10px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66ff66;
            }
        """)

        # Edit = żółty
        edit_button.setStyleSheet("""
            QPushButton {
                background-color: #ffff00;
                color: #07111f;
                border: none;
                border-radius: 9px;
                padding: 10px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffff66;
            }
        """)

        # Delete = czerwony
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #ff0000;
                color: white;
                border: none;
                border-radius: 9px;
                padding: 10px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff5555;
            }
        """)

        add_button.clicked.connect(self.add_event)
        edit_button.clicked.connect(self.edit_event)
        delete_button.clicked.connect(self.delete_event)

        event_buttons.addWidget(add_button)
        event_buttons.addWidget(edit_button)
        event_buttons.addWidget(delete_button)

        calendar_layout.addLayout(event_buttons)
        
        right_column = QVBoxLayout()
        self.stat_values = {}
        for card_title, key in [("BATTERY", "battery"), ("DOWNLOAD SPEED", "download")]:
            card = QFrame()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            heading = QLabel(card_title)
            heading.setObjectName("heading")
            value = QLabel("--")
            value.setObjectName("value")
            value.setWordWrap(True)
            card_layout.addWidget(heading)
            card_layout.addWidget(value)
            card_layout.addStretch()
            right_column.addWidget(card, 1)
            self.stat_values[key] = value
        upper.addWidget(calendar_frame, 4)
        upper.addLayout(right_column, 1)
        main_layout.addLayout(upper, 5)

        events_frame = QFrame()
        events_layout = QVBoxLayout(events_frame)
        events_header = QHBoxLayout()

        self.events_heading = QLabel("EVENTS IN THIS MONTH")
        self.events_heading.setObjectName("heading")
        events_header.addWidget(self.events_heading)

        events_header.addStretch()

        self.event_sort_mode = "Month"

        self.sort_button = QComboBox()
        self.sort_button.addItems([
            "Day",
            "Week",
            "Month",
            "Year",
        ])
        self.sort_button.setCurrentText(self.event_sort_mode)
        self.sort_button.setFixedWidth(190)
        self.sort_button.setStyleSheet("""
            QComboBox {
                background-color: #10243a;
                color: #40e0d0;
                border: 1px solid #2498c4;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #0c1b2c;
                color: #d8f5ff;
                selection-background-color: #087da5;
            }
        """)
        self.sort_button.currentTextChanged.connect(
            self.change_event_sort
        )
        # Start with the current date and its week selected.
        self.calendar_widget.setSelectedDate(QDate.currentDate())
        self.sort_button.setCurrentText("Week")
        self.change_event_sort("Week")
        # AUTOMATIC EVENT CLEANUP SETTINGS
        retention_label = QLabel("AUTO-DELETE:")
        retention_label.setStyleSheet(
            "color: #8ebbd0; font-weight: bold;"
        )
        events_header.addWidget(retention_label)

        self.retention_combo = QComboBox()
        self.retention_combo.addItems(EVENT_RETENTION_OPTIONS)
        self.retention_combo.setCurrentText(self.event_retention)
        self.retention_combo.setMinimumWidth(150)
        self.retention_combo.setStyleSheet("""
            QComboBox {
                background-color: #10243a;
                color: #40e0d0;
                border: 1px solid #2498c4;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #0c1b2c;
                color: #d8f5ff;
                selection-background-color: #087da5;
            }
        """)

        self.retention_combo.currentTextChanged.connect(
            self.change_event_retention
        )

        events_header.addWidget(self.retention_combo)

        # Wybór trybu kalendarza po Auto-Delete
        events_header.addWidget(self.sort_button)

        events_layout.addLayout(events_header)

        self.event_list = QListWidget()
        self.event_list.setMaximumHeight(100)
        self.event_list.itemDoubleClicked.connect(
            lambda _item: self.edit_event()
        )
        events_layout.addWidget(self.event_list)

        main_layout.addWidget(events_frame)

        # =========================
        # J.A.R.V.I.S. CHAT CENTER
        # =========================

        chat_frame = QFrame()
        chat_frame.setMinimumHeight(180)
        chat_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(14, 14, 14, 14)
        chat_layout.setSpacing(10)

        chat_header = QHBoxLayout()

        chat_title = QLabel("J.A.R.V.I.S. CHAT")
        chat_title.setObjectName("heading")
        chat_title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #42d9ff;"
        )

        self.new_chat_button = QPushButton("+ New chat")
        self.new_chat_button.clicked.connect(self.create_new_chat)
        self.rename_chat_button = QPushButton("Rename")
        self.rename_chat_button.clicked.connect(self.rename_current_chat)
        

        chat_header.addWidget(chat_title)
        chat_header.addStretch()
        chat_header.addWidget(self.rename_chat_button)
        chat_header.addWidget(self.new_chat_button)

        chat_layout.addLayout(chat_header)

        self.response_label = QLabel("J.A.R.V.I.S.: Ready.")
        self.response_label.setWordWrap(True)
        self.response_label.setStyleSheet(
            "color: #8ebbd0; font-size: 12px; padding: 2px;"
        )
        chat_layout.addWidget(self.response_label)

        # Lista rozmów po lewej
        chat_body = QHBoxLayout()
        chat_body.setSpacing(12)

        self.chat_list = QListWidget()
        self.chat_list.setMinimumWidth(190)
        self.chat_list.setMaximumWidth(260)
        self.chat_list.setStyleSheet("""
            QListWidget {
                background: #0a1726;
                border: 1px solid #15506b;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background: #087da5;
                color: white;
            }
        """)

        self.chat_list.currentItemChanged.connect(
            self.select_chat
        )

        self.chat_list.itemDoubleClicked.connect(
            lambda _item: self.rename_current_chat()
        )

        chat_body.addWidget(self.chat_list)

        # Prawa część: wiadomości i pole wpisywania
        conversation_layout = QVBoxLayout()
        conversation_layout.setSpacing(8)
        self.chat_messages = QTextBrowser()
        self.chat_messages.setMinimumHeight(60)
        self.chat_messages.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.chat_messages.setReadOnly(True)
        self.chat_messages.setOpenExternalLinks(True)
        self.chat_messages.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self.chat_messages.setPlaceholderText(
            "Your conversation with J.A.R.V.I.S. will appear here."
        )
        self.chat_messages.setStyleSheet("""
            QTextEdit {
                background: #0a1726;
                border: 1px solid #15506b;
                border-radius: 8px;
                padding: 10px;
                color: #d8f5ff;
                font-size: 14px;
            }
        """)

        conversation_layout.addWidget(self.chat_messages, 1)

        self.command_input = ChatInput()
        self.command_input.setFixedHeight(50)
        self.command_input.setPlaceholderText(
            "Message J.A.R.V.I.S..."
        )

        self.command_input.send_requested.connect(
            self.run_command
        )

        self.send_button = QPushButton("SEND")
        self.send_button.clicked.connect(
            self.run_command
        )

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        input_layout.addWidget(self.command_input, 1)
        input_layout.addWidget(self.send_button)

        conversation_layout.addLayout(input_layout)
        chat_body.addLayout(conversation_layout, 1)

        chat_layout.addLayout(chat_body, 1)
        main_layout.addWidget(chat_frame, 1)

        # Dane rozmów
        self.chats = self.load_chats()
        self.current_chat_id = None
        self.ai_worker = None

        self.refresh_chat_list()

        if self.chats:
            self.open_chat(self.chats[0]["id"])
        else:
            self.create_new_chat()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(1000)

        # Automatyczne czyszczenie co 10 minut.
        # Nie wykonujemy czyszczenia natychmiast przy starcie.
        self.retention_timer = QTimer(self)
        self.retention_timer.timeout.connect(
            self.cleanup_old_events
        )
        self.retention_timer.start(1000 * 60 * 1000)

        self.refresh_dashboard()
        self.mark_calendar_events()
        self.refresh_event_list()

    def load_chats(self):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                return []

            chats = data.get("chats", [])

            if not isinstance(chats, list):
                return []

            valid_chats = []

            for chat in chats:
                if not isinstance(chat, dict):
                    continue

                chat.setdefault("id", uuid.uuid4().hex)
                chat.setdefault("title", "New chat")
                chat.setdefault(
                    "created_at",
                    datetime.now().isoformat(timespec="seconds")
                )

                if not isinstance(chat.get("messages"), list):
                    chat["messages"] = []

                valid_chats.append(chat)

            return valid_chats

        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    def save_chats(self):
        try:
            temporary_file = CHATS_FILE + ".tmp"

            with open(temporary_file, "w", encoding="utf-8") as file:
                json.dump(
                    {"chats": self.chats},
                    file,
                    ensure_ascii=False,
                    indent=4
                )

            os.replace(temporary_file, CHATS_FILE)

        except OSError as exc:
            QMessageBox.warning(
                self,
                "Chat history",
                f"Could not save chats:\n{exc}"
            )

    def refresh_chat_list(self):
        self.chat_list.blockSignals(True)
        self.chat_list.clear()

        for chat in reversed(self.chats):
            item = QListWidgetItem(chat.get("title", "New chat"))
            item.setData(
                Qt.ItemDataRole.UserRole,
                chat["id"]
            )
            self.chat_list.addItem(item)

            if chat["id"] == self.current_chat_id:
                self.chat_list.setCurrentItem(item)

        self.chat_list.blockSignals(False)

    def get_current_chat(self):
        for chat in self.chats:
            if chat["id"] == self.current_chat_id:
                return chat

        return None

    def create_new_chat(self):
        current_chat = self.get_current_chat()

        # Jeśli bieżący czat jest pusty, po prostu do niego wróć.
        if current_chat is not None and not current_chat.get("messages"):
            self.open_chat(current_chat["id"])
            self.command_input.setFocus()
            return

        # Nie twórz kolejnego pustego czatu, jeśli taki już istnieje.
        empty_chat = next(
            (
                chat for chat in reversed(self.chats)
                if not chat.get("messages")
            ),
            None
        )

        if empty_chat is not None:
            self.open_chat(empty_chat["id"])
            self.command_input.setFocus()
            return

        chat = {
            "id": uuid.uuid4().hex,
            "title": "New chat",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "messages": []
        }

        self.chats.append(chat)
        self.current_chat_id = chat["id"]

        self.save_chats()
        self.refresh_chat_list()
        self.chat_messages.clear()
        self.command_input.setFocus()

    def open_chat(self, chat_id):
        chat = next(
            (item for item in self.chats if item["id"] == chat_id),
            None
        )

        if chat is None:
            return

        self.current_chat_id = chat_id
        self.chat_messages.clear()

        for message in chat.get("messages", []):
            role = message.get("role", "assistant")
            content = message.get("content", "")

            if role == "user":
                self.show_chat_message("YOU", content, "#40e0d0")
            else:
                self.show_chat_message(
                    "J.A.R.V.I.S.",
                    content,
                    "#7ce7ff"
                )

        self.refresh_chat_list()

    def select_chat(self, current, previous):
        if current is None:
            return

        chat_id = current.data(Qt.ItemDataRole.UserRole)

        if chat_id:
            self.open_chat(chat_id)

    def show_chat_message(self, speaker, content, color):
        safe_text = str(content).replace("\r\n", "\n")

        # Oddziel etykietę YOU od list Markdown.
        safe_text = re.sub(
            r"(?m)^[ \t]*[-*+][ \t]+\*\*YOU\*\*[ \t]*$",
            "\n\n**YOU**\n",
            safe_text,
        )

        # Oddzielaj zwykłe linie tekstu od list Markdown.
        safe_text = re.sub(r"(?m)^([^\s\-*+>#`|].*)\n([-*+] )", r"\1\n\n\2", safe_text)

        formatted_content = markdown.markdown(
            safe_text,
            extensions=[
                "fenced_code",
                "tables",
                "sane_lists",
                "nl2br",
            ],
            output_format="html",
        )

        # Zamknij listy, jeśli renderer pozostawił je otwarte.
        formatted_content = re.sub(
            r"</li>\s*(?=<p\b)",
            "</li></ul>",
            formatted_content,
            flags=re.IGNORECASE,
        )

        # Jeśli treść kończy się listą Markdown, zakończ ją przed etykietą YOU.
        safe_text = re.sub(
            r"(?m)^[ \t]*[-*+][ \t]+\*\*YOU\*\*[ \t]*$",
            "\n\n**YOU**\n",
            safe_text,
        )

        # Otwieraj tylko bezpieczne linki HTTP/HTTPS.
        formatted_content = re.sub(
            r'<a\s+([^>]*?)href=["\'](?!https?://)[^"\']*["\']([^>]*)>',
            r'<span>',
            formatted_content,
            flags=re.IGNORECASE,
        )

        self.chat_messages.append(
            f'<div style="margin-top:10px; margin-bottom:12px;">'
            f'<p style="margin:0 0 4px 0; padding:0; '
            f'margin-left:0; text-indent:0; '
            f'color:{color}; font-weight:bold;">'
            f'{escape(str(speaker))}</p>'
            f'<div style="margin:0; padding:0; '
            f'margin-left:0; text-indent:0; '
            f'color:#d8f5ff;">'
            f'{formatted_content}'
            f'</div>'
            f'</div>'
        )

        scrollbar = self.chat_messages.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_chat_message(self, role, content, chat_id=None):
        if chat_id is None:
            chat = self.get_current_chat()
        else:
            chat = next(
                (item for item in self.chats if item["id"] == chat_id),
                None
            )

        if chat is None:
            self.create_new_chat()
            chat = self.get_current_chat()

        if chat is None:
            return

        chat["messages"].append({
            "role": role,
            "content": str(content),
            "timestamp": datetime.now().isoformat(timespec="seconds")
        })

        # The first user message sets the chat title.
        if role == "user" and chat["title"] == "New chat":
            title = " ".join(str(content).split())
            chat["title"] = title[:35] or "New chat"

        self.save_chats()
        self.refresh_chat_list()

    def rename_current_chat(self):
        chat = self.get_current_chat()

        if chat is None:
            return

        new_name, accepted = QInputDialog.getText(
            self,
            "Rename chat",
            "Enter a new chat name:",
            QLineEdit.EchoMode.Normal,
            chat.get("title", "New chat")
        )

        if not accepted:
            return

        new_name = new_name.strip()

        if not new_name:
            QMessageBox.information(
                self,
                "Rename chat",
                "Chat name cannot be empty."
            )
            return

        chat["title"] = new_name[:60]
        self.save_chats()
        self.refresh_chat_list()

    def delete_current_chat(self):
        chat = self.get_current_chat()

        if chat is None:
            return

        result = QMessageBox.question(
            self,
            "Delete chat",
            f"Delete '{chat['title']}'?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self.chats = [
            item for item in self.chats
            if item["id"] != self.current_chat_id
        ]

        self.current_chat_id = None
        self.save_chats()
        self.refresh_chat_list()

        if self.chats:
            self.open_chat(self.chats[0]["id"])
        else:
            self.create_new_chat()

    def change_event_retention(self, retention):
        if retention not in EVENT_RETENTION_OPTIONS:
            return

        self.event_retention = retention
        self.settings["event_retention"] = retention
        save_settings(self.settings)

    def cleanup_old_events(self):
        # Never oznacza, że niczego automatycznie nie usuwamy.
        if self.event_retention == "Never":
            return

        cutoff_date = subtract_retention_period(
            date.today(),
            self.event_retention
        )

        if cutoff_date is None:
            return

        kept_events = []
        removed_count = 0

        for event in self.events:
            try:
                event_date = date.fromisoformat(event.get("date", ""))
            except (ValueError, TypeError):
                # Nie usuwaj wydarzeń z nieprawidłową datą.
                kept_events.append(event)
                continue

            # Usuń wydarzenia z datą równą granicy lub starszą.
            if event_date <= cutoff_date:
                removed_count += 1
            else:
                kept_events.append(event)

        if removed_count:
            self.events = kept_events
            self.save_events()
            self.mark_calendar_events()
            print(
                f"Auto-cleanup: removed {removed_count} old event(s)."
            )

    def load_events(self):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    def save_events(self):
        try:
            with open(EVENTS_FILE, "w", encoding="utf-8") as file:
                json.dump(
                    self.events,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            return True

        except OSError as exc:
            QMessageBox.warning(
                self,
                "Calendar",
                f"Could not save events:\n{exc}",
            )
            return False

    def selected_date_string(self):
        return self.calendar_widget.selectedDate().toString("yyyy-MM-dd")

    def update_events_heading(self):
        mode = self.event_sort_mode

        selected_count = len(
            self.calendar_widget.selected_periods
        )

        if selected_count > 1:
            mode_titles = {
                "Day": "EVENTS ON THESE DAYS",
                "Week": "EVENTS IN THESE WEEKS",
                "Month": "EVENTS IN THESE MONTHS",
                "Year": "EVENTS IN THESE YEARS",
            }
        else:
            mode_titles = {
                "Day": "EVENTS THIS DAY",
                "Week": "EVENTS THIS WEEK",
                "Month": "EVENTS THIS MONTH",
                "Year": "EVENTS THIS YEAR",
                "Span": "EVENTS IN THIS DATE RANGE",
            }

        self.events_heading.setText(
            mode_titles.get(mode, "EVENTS")
        )

    def change_event_sort(self, mode):
        mode_colors = {
            "Year": "#ffe34d",
            "Month": "#40e0d0",
            "Week": "#228b22",
            "Day": "#ff982f",
            "Span": "#ffffff",
        }

        self.event_sort_mode = mode

        self.update_events_heading()

        self.sort_button.setStyleSheet(f"""
            QComboBox {{
                background-color: #10243a;
                color: {mode_colors[mode]};
                border: 1px solid #2498c4;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background-color: #0c1b2c;
                color: #d8f5ff;
                selection-background-color: #087da5;
            }}
        """)

        self.calendar_widget.set_view_mode(mode)
        self.refresh_event_list()

    def event_is_in_current_view(self, event):
        event_date = QDate.fromString(
            event.get("date", ""),
            "yyyy-MM-dd"
        )

        if not event_date.isValid():
            return False

        mode = self.event_sort_mode

        if mode in ("Day", "Week", "Month", "Year"):
            return self.calendar_widget.date_is_in_range(
                event_date
            )

        if mode == "Span":
            start = self.calendar_widget.span_start
            end = self.calendar_widget.span_end

            if not start.isValid() or not end.isValid():
                return False

            return start <= event_date <= end

        return False

    def refresh_event_list(self):
        if not hasattr(self, "event_list"):
            return
        self.update_events_heading()

        self.event_list.clear()

        selected_date = self.calendar_widget.selectedDate()

        if self.event_sort_mode in ("Day", "Week", "Month", "Year"):
            filtered_events = []

            for event in self.events:
                event_date = QDate.fromString(
                    event.get("date", ""),
                    "yyyy-MM-dd"
                )

                if (
                    event_date.isValid()
                    and self.calendar_widget.date_is_in_range(event_date)
                ):
                    filtered_events.append(event)

        elif self.event_sort_mode == "Span":
            start = self.calendar_widget.span_start
            end = self.calendar_widget.span_end

            filtered_events = []

            for event in self.events:
                event_date = QDate.fromString(
                    event.get("date", ""),
                    "yyyy-MM-dd"
                )

                if (
                    event_date.isValid()
                    and start <= event_date <= end
                ):
                    filtered_events.append(event)

        # Niższy numer priorytetu = wyższy priorytet na liście.
        def event_sort_key(event):
            try:
                priority = int(event.get("priority", 5))
            except (TypeError, ValueError):
                priority = 5

            return (
                priority,
                event.get("date", ""),
                event.get("title", "").lower()
            )

        filtered_events.sort(key=event_sort_key)

        # Dodaj wszystkie eventy do listy.
        for event in filtered_events:
            item = QListWidgetItem(
                f"{event.get('date', '')} | "
                f"[P{event.get('priority', 5)}] "
                f"{event.get('title', 'Untitled')}"
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                event.get("id")
            )

            color_value = event.get("color", "Blue")

            if color_value.startswith("#"):
                text_color = QColor(color_value)
            else:
                text_color = QColor(
                    COLOR_HEX.get(color_value, "#6bcaff")
                )

            item.setForeground(text_color)
            self.event_list.addItem(item)

        # Zaznacz pierwszy event dopiero po dodaniu wszystkich.
        if self.event_list.count() > 0:
            self.event_list.setCurrentRow(0)
        else:
            selected_count = len(
                self.calendar_widget.selected_periods
            )

            if selected_count > 1:
                empty_messages = {
                    "Day": "NO EVENTS ON THESE DAYS.",
                    "Week": "NO EVENTS IN THESE WEEKS.",
                    "Month": "NO EVENTS IN THESE MONTHS.",
                    "Year": "NO EVENTS IN THESE YEARS.",
                }
            else:
                empty_messages = {
                    "Day": "NO EVENTS THIS DAY.",
                    "Week": "NO EVENTS THIS WEEK.",
                    "Month": "NO EVENTS THIS MONTH.",
                    "Year": "NO EVENTS THIS YEAR.",
                    "Span": "NO EVENTS IN THIS DATE RANGE.",
                }

            self.event_list.addItem(
                empty_messages.get(
                    self.event_sort_mode,
                    "NO EVENTS FOUND."
                )
            )

    def mark_calendar_events(self):
        self.calendar_widget.set_events(self.events)
        self.refresh_event_list()

    def add_event(self):
        try:
            selected = date.fromisoformat(
                self.selected_date_string()
            )
        except ValueError:
            selected = date.today()

        dialog = EventDialog(self, initial_date=selected)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        event = dialog.event_data()

        if not event["title"]:
            QMessageBox.information(
                self, "Calendar", "Enter an event name first."
            )
            return

        day_count = sum(
            1 for existing in self.events
            if existing.get("date") == event["date"]
        )

        if day_count >= 4:
            QMessageBox.warning(
                self,
                "Daily event limit",
                "You can add a maximum of 4 events per day."
            )
            return

        event["id"] = uuid.uuid4().hex
        self.events.append(event)
        self.save_events()
        self.mark_calendar_events()

    def selected_event_index(self):
        item = self.event_list.currentItem()

        if item is None:
            return None

        event_id = item.data(Qt.ItemDataRole.UserRole)

        if not event_id:
            return None

        for index, event in enumerate(self.events):
            if event.get("id") == event_id:
                return index

        return None

    def edit_event(self):
        index = self.selected_event_index()

        if index is None:
            QMessageBox.information(
                self, "Calendar", "Select an event first."
            )
            return

        dialog = EventDialog(
            self, event=self.events[index]
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        updated = dialog.event_data()

        if not updated["title"]:
            QMessageBox.information(
                self, "Calendar", "Enter an event name first."
            )
            return

        # Sprawdź limit na nową datę, nie licząc edytowanego eventu.
        day_count = sum(
            1
            for i, existing in enumerate(self.events)
            if i != index
            and existing.get("date") == updated["date"]
        )

        if day_count >= 4:
            QMessageBox.warning(
                self,
                "Daily event limit",
                "This day already has 4 events. Choose another date."
            )
            return

        updated["id"] = self.events[index].get(
            "id", uuid.uuid4().hex
        )
        self.events[index] = updated
        self.save_events()
        self.mark_calendar_events()

    def delete_event(self):
        index = self.selected_event_index()

        if index is None:
            QMessageBox.information(
                self, "Calendar", "Select an event first."
            )
            return

        name = self.events[index].get("title", "this event")

        result = QMessageBox.question(
            self,
            "Delete event",
            f"Delete '{name}'?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            self.events.pop(index)
            self.save_events()
            self.mark_calendar_events()

    def refresh_dashboard(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        battery = psutil.sensors_battery()
        if battery is None:
            self.stat_values["battery"].setText("Reading unavailable")
        else:
            if battery.power_plugged:
                self.stat_values["battery"].setTextFormat(
                    Qt.TextFormat.RichText
                )
                self.stat_values["battery"].setText(
                    f'{battery.percent:.0f}% '
                    '<span style="color:#66ff00; font-weight:bold;">'
                    '• CHARGING</span>'
                )
            else:
                self.stat_values["battery"].setTextFormat(
                    Qt.TextFormat.PlainText
                )
                self.stat_values["battery"].setText(
                    f"{battery.percent:.0f}%"
                )
        current_net = psutil.net_io_counters()
        current_time = time.monotonic()
        elapsed = current_time - self.last_net_time
        if elapsed > 0:
            speed = max(0, current_net.bytes_recv - self.last_net.bytes_recv) / elapsed / 1024
            self.stat_values["download"].setText(f"{speed:.1f} KB/s")
        self.last_net = current_net
        self.last_net_time = current_time


    def find_related_chats(self, message, current_chat_id=None):
        stop_words = {
            "the", "and", "for", "that", "this", "with", "from",
            "what", "when", "where", "have", "about", "into",
            "czy", "jak", "co", "jaki", "jaka", "jakie", "jest",
            "są", "było", "była", "były", "mam", "mamy", "miał",
            "miała", "oraz", "ale", "lub", "żeby", "który",
            "która", "które", "się", "nie", "tak", "mi", "mnie",
            "ten", "ta", "to", "te", "tam", "poprzednim",
            "poprzedni", "czacie", "czat", "rozmowie", "rozmowa",
        }

        def words(text):
            return {
                word for word in re.findall(r"\w+", str(text).lower())
                if len(word) > 2 and word not in stop_words
            }

        query_words = words(message)

        # Give the AI the names of saved chats.
        title_lines = [
            f"- {chat.get('title', 'New chat')}"
            for chat in self.chats
        ]

        current_chat = next(
            (
                chat for chat in self.chats
                if chat.get("id") == current_chat_id
            ),
            None,
        )

        current_chat_title = (
            str(current_chat.get("title", "New chat"))
            if current_chat
            else "New chat"
        )

        sections = [
            f"CURRENT CHAT NAME: {current_chat_title}\n"
            "This is the name of the chat currently open in the app. "
            "If the user asks for the name of this chat, answer with this exact name.\n\n"
            "AVAILABLE SAVED CHAT TITLES:\n"
            + ("\n".join(title_lines[:100]) if title_lines else "No saved chats.")
        ]

        # Search chats other than the one currently open.
        candidates = []

        for chat in self.chats:
            if chat.get("id") == current_chat_id:
                continue

            title = str(chat.get("title", "New chat"))
            messages = chat.get("messages", [])

            title_matches = len(query_words & words(title))
            message_matches = []

            for item in messages:
                content = str(item.get("content", ""))
                score = len(query_words & words(content))

                if score > 0:
                    message_matches.append((score, item))

            best_message_score = max(
                (score for score, _ in message_matches),
                default=0,
            )

            score = title_matches * 4 + best_message_score

            candidates.append({
                "chat": chat,
                "score": score,
                "message_matches": message_matches,
            })

        candidates.sort(
            key=lambda item: (
                item["score"],
                str(item["chat"].get("created_at", "")),
            ),
            reverse=True,
        )

        # Prefer relevant chats. If the question is vague, use recent chats.
        selected = [item for item in candidates if item["score"] > 0][:4]

        if not selected:
            selected = candidates[:3]

        for result in selected:
            chat = result["chat"]
            title = str(chat.get("title", "New chat"))
            messages = chat.get("messages", [])

            matching = sorted(
                result["message_matches"],
                key=lambda pair: pair[0],
                reverse=True,
            )

            if matching:
                chosen_messages = [item for _, item in matching[:5]]
            else:
                chosen_messages = messages[-4:]

            lines = [f"\nCHAT: {title}"]

            for item in chosen_messages:
                role = str(item.get("role", "unknown")).upper()
                content = str(item.get("content", "")).strip()

                if content:
                    content = content[:700]
                    lines.append(f"{role}: {content}")

            sections.append("\n".join(lines))

        return "\n".join(sections)

    def execute_ai_tool(self, name, args):
        if name == "get_current_time":
            return {
                "ok": True,
                "time": datetime.now().strftime("%H:%M:%S"),
            }

        if name == "get_current_date":
            return {
                "ok": True,
                "date": date.today().strftime("%d.%m.%Y"),
            }

        if name == "open_website":
            site = args.get("site")

            urls = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
            }

            if site not in urls:
                return {
                    "ok": False,
                    "message": "Unsupported website.",
                }

            opened = webbrowser.open(urls[site])

            if not opened:
                return {
                    "ok": False,
                    "message": "The browser could not open the website.",
                }

            return {
                "ok": True,
                "message": f"Opened {site}.",
            }

        if name == "launch_notepad":
            try:
                subprocess.Popen(["notepad.exe"])
                return {
                    "ok": True,
                    "message": "Notepad was launched.",
                }
            except OSError as exc:
                return {
                    "ok": False,
                    "message": f"Could not launch Notepad: {exc}",
                }

        if name == "set_window_mode":
            mode = args.get("mode")

            if mode == "fullscreen":
                self.showFullScreen()
                return {
                    "ok": True,
                    "message": "Fullscreen mode activated.",
                }

            if mode == "windowed":
                self.showNormal()
                return {
                    "ok": True,
                    "message": "Windowed mode restored.",
                }

            return {
                "ok": False,
                "message": "Unsupported window mode.",
            }

        if name == "get_calendar_events":
            return {
                "ok": True,
                "events": [
                    {
                        "id": event.get("id"),
                        "title": event.get("title", ""),
                        "date": event.get("date", ""),
                        "priority": event.get("priority"),
                        "color": event.get("color", ""),
                    }
                    for event in self.events
                ],
            }

        if name == "add_calendar_event":
            title = str(args.get("title", "")).strip()
            date_text = str(args.get("date", "")).strip()
            color = str(args.get("color", "")).strip()
            priority = args.get("priority")

            # Validate the required fields again in the application.
            if not title or not date_text or not color or priority is None:
                return {
                    "ok": False,
                    "message": (
                        "Missing required information: title, date, "
                        "color, and priority are all required."
                    ),
                }

            if isinstance(priority, bool) or not isinstance(priority, int):
                return {
                    "ok": False,
                    "message": "Priority must be an integer from 1 to 10.",
                }

            if not 1 <= priority <= 10:
                return {
                    "ok": False,
                    "message": "Priority must be from 1 to 10.",
                }

            # Validate and normalize the date.
            try:
                date_formats = (
                    "%Y-%m-%d",
                    "%d.%m.%Y",
                    "%d-%m-%Y",
                )

                event_date = None

                for date_format in date_formats:
                    try:
                        event_date = datetime.strptime(
                            date_text, date_format
                        ).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue

                if event_date is None:
                    raise ValueError("Invalid date format")

            except ValueError:
                return {
                    "ok": False,
                    "message": (
                        "Invalid date. Use YYYY-MM-DD or DD.MM.YYYY."
                    ),
                }

            standard_colors = [
                "Red",
                "Green",
                "Blue",
                "Forest",
                "Yellow",
                "Turquoise",
                "Cyan",
                "Pink",
                "Orange",
                "Purple",
                "Brown",
                "Black",
                "White",
            ]

            custom_colors = [
                "Custom 1",
                "Custom 2",
                "Custom 3",
            ]

            # Match standard color names without case sensitivity.
            standard_color = next(
                (
                    item for item in standard_colors
                    if item.lower() == color.lower()
                ),
                None,
            )

            custom_color = next(
                (
                    item for item in custom_colors
                    if item.lower() == color.lower()
                ),
                None,
            )

            if standard_color is not None:
                resolved_color = standard_color

            elif custom_color is not None:
                resolved_color = self.get_custom_calendar_color(
                    custom_color
                )

                if resolved_color is None:
                    return {
                        "ok": False,
                        "message": (
                            f"Could not load the color for {custom_color}."
                        ),
                    }

            elif (
                color.startswith("#")
                and len(color) in (4, 5, 7, 9)
                and QColor(color).isValid()
            ):
                resolved_color = color

            else:
                return {
                    "ok": False,
                    "message": (
                        "Invalid color. Use a listed color, Custom 1-3, "
                        "or a valid HEX code such as #398cff."
                    ),
                }

            # Preserve the existing limit of four events per day.
            day_count = sum(
                1 for event in self.events
                if event.get("date") == event_date
            )

            if day_count >= 4:
                return {
                    "ok": False,
                    "message": (
                        "This date already has the maximum of 4 events."
                    ),
                }

            event = {
                "title": title,
                "date": event_date,
                "color": resolved_color,
                "priority": priority,
                "id": uuid.uuid4().hex,
            }

            self.events.append(event)

            if not self.save_events():
                self.events.pop()
                return {
                    "ok": False,
                    "message": (
                        "The event could not be saved. "
                        "Check the calendar file and try again."
                    ),
                }

            self.mark_calendar_events()

            return {
                "ok": True,
                "message": "Calendar event saved successfully.",
                "event": {
                    "title": title,
                    "date": event_date,
                    "color": resolved_color,
                    "priority": priority,
                },
            }



        if name == "delete_calendar_event":
            event_ids = args.get("event_ids", [])

            if (
                not isinstance(event_ids, list)
                or not event_ids
                or any(
                    not isinstance(event_id, str) or not event_id.strip()
                    for event_id in event_ids
                )
            ):
                return {
                    "ok": False,
                    "message": "Provide a non-empty list of valid event IDs.",
                }

            # Remove duplicate IDs while preserving their order.
            event_ids = list(dict.fromkeys(
                event_id.strip() for event_id in event_ids
            ))

            events_by_id = {
                str(event.get("id", "")): event
                for event in self.events
                if event.get("id") is not None
            }

            # Validate every requested ID before staging anything.
            if any(event_id not in events_by_id for event_id in event_ids):
                return {
                    "ok": False,
                    "message": (
                        "At least one event ID was not found. "
                        "No deletion was staged."
                    ),
                }

            selected_events = [
                events_by_id[event_id] for event_id in event_ids
            ]

            # Keep only events inside the currently selected calendar view.
            selected_events = [
                event
                for event in selected_events
                if self.event_is_in_current_view(event)
            ]

            if not selected_events:
                return {
                    "ok": False,
                    "message": (
                        "No matching events were found in the currently "
                        "selected calendar view. Nothing was staged for deletion."
                    ),
                }

            event_ids = [event["id"] for event in selected_events]

            self.pending_calendar_deletion = {
                "chat_id": self.pending_chat_id,
                "event_ids": event_ids,
            }

            return {
                "ok": True,
                "requires_confirmation": True,
                "message": (
                    "Deletion is pending confirmation. Show the user "
                    "every selected event, including its ID, title, date, "
                    "priority, and color. Ask for one explicit confirmation "
                    "covering the entire list. Do not delete anything yet."
                ),
                "events": [
                    {
                        "id": event.get("id"),
                        "title": event.get("title", ""),
                        "date": event.get("date", ""),
                        "priority": event.get("priority"),
                        "color": event.get("color", ""),
                    }
                    for event in selected_events
                ],
            }

        if name == "edit_calendar_event":
            event_id = str(args.get("event_id", "")).strip()
            title = str(args.get("title", "")).strip()
            if not title or ":" in title or ";" in title:
                return {
                    "ok": False,
                    "message": (
                        "Invalid event title. The title must not be empty "
                        "or contain ':' or ';'."
                    ),
                }
            date_text = str(args.get("date", "")).strip()
            color = str(args.get("color", "")).strip()
            priority = args.get("priority")

            matches = [
                event for event in self.events
                if str(event.get("id", "")) == event_id
            ]

            if not event_id or len(matches) != 1:
                return {
                    "ok": False,
                    "message": (
                        "The event ID was not found or is not unique. "
                        "No event was changed."
                    ),
                }

            if not title or not date_text or not color:
                return {
                    "ok": False,
                    "message": (
                        "Title, date, and color cannot be empty."
                    ),
                }

            if (
                isinstance(priority, bool)
                or not isinstance(priority, int)
                or not 1 <= priority <= 10
            ):
                return {
                    "ok": False,
                    "message": "Priority must be an integer from 1 to 10.",
                }

            try:
                try:
                    event_date = datetime.strptime(
                        date_text, "%Y-%m-%d"
                    ).strftime("%Y-%m-%d")
                except ValueError:
                    event_date = datetime.strptime(
                        date_text, "%d.%m.%Y"
                    ).strftime("%Y-%m-%d")
            except ValueError:
                return {
                    "ok": False,
                    "message": (
                        "Invalid date. Use YYYY-MM-DD or DD.MM.YYYY."
                    ),
                }

            standard_colors = [
                "Red", "Green", "Blue", "Forest", "Yellow",
                "Turquoise", "Cyan", "Pink", "Orange", "Purple",
                "Brown", "Black", "White",
            ]

            custom_colors = ["Custom 1", "Custom 2", "Custom 3"]

            standard_color = next(
                (
                    item for item in standard_colors
                    if item.casefold() == color.casefold()
                ),
                None,
            )

            custom_color = next(
                (
                    item for item in custom_colors
                    if item.casefold() == color.casefold()
                ),
                None,
            )

            if standard_color is not None:
                resolved_color = standard_color

            elif custom_color is not None:
                resolved_color = self.get_custom_calendar_color(
                    custom_color
                )

                if resolved_color is None:
                    return {
                        "ok": False,
                        "message": (
                            f"Could not load the color for {custom_color}."
                        ),
                    }

            elif (
                color.startswith("#")
                and len(color) in (4, 5, 7, 9)
                and QColor(color).isValid()
            ):
                resolved_color = color

            else:
                return {
                    "ok": False,
                    "message": (
                        "Invalid color. Use a standard color, Custom 1-3, "
                        "or a valid HEX code."
                    ),
                }

            event = matches[0]

            if not self.event_is_in_current_view(event):
                return {
                    "ok": False,
                    "message": (
                        "Edit rejected: the event is outside "
                        "the currently selected calendar view."
                    ),
                }

            # Preserve the four-events-per-day limit, excluding
            # the event currently being edited.
            day_count = sum(
                1 for item in self.events
                if item.get("date") == event_date
                and str(item.get("id", "")) != event_id
            )

            if day_count >= 4:
                return {
                    "ok": False,
                    "message": (
                        "The target date already has four other events."
                    ),
                }

            old_event = dict(event)

            event.update({
                "title": title,
                "date": event_date,
                "color": resolved_color,
                "priority": priority,
                "id": event_id,
            })

            if not self.save_events():
                event.clear()
                event.update(old_event)
                self.mark_calendar_events()

                return {
                    "ok": False,
                    "message": (
                        "Could not save the edit. "
                        "The original event has been restored."
                    ),
                }

            self.mark_calendar_events()

            return {
                "ok": True,
                "message": "Calendar event updated successfully.",
                "event": {
                    "id": event_id,
                    "title": title,
                    "date": event_date,
                    "priority": priority,
                    "color": resolved_color,
                },
            }

        return {
            "ok": False,
            "message": f"Unknown function: {name}",
        }

    def ask_ai(self, message):
        chat = self.get_current_chat()

        if chat is None:
            self.create_new_chat()
            chat = self.get_current_chat()

        if chat is None:
            self.response_label.setText(
                "J.A.R.V.I.S.: Could not open a chat."
            )
            return

        target_chat_id = chat["id"]

        # Najpierw sprawdź, czy użytkownik odpowiada
        # na pytanie o zgodę na usunięcie wydarzeń.
        if self.handle_pending_deletion_confirmation(
            message,
            target_chat_id,
        ):
            return

        if self.ai_worker is not None and self.ai_worker.isRunning():
            self.response_label.setText(
                "J.A.R.V.I.S.: Please wait for the next response."
            )
            return

        history = [
            {
                "role": item.get("role", "assistant"),
                "content": item.get("content", ""),
            }
            for item in chat.get("messages", [])[-30:]
        ]

        other_chats = (
            f"CURRENT CHAT NAME: {chat.get('title', 'New chat')}\n"
            "When asked for the current chat name, use this exact name.\n\n"
            + self.find_related_chats(
                message,
                current_chat_id=target_chat_id,
            )
        )

        self.add_chat_message("user", message, target_chat_id)

        if self.current_chat_id == target_chat_id:
            self.show_chat_message("YOU", message, "#40e0d0")

        self.response_label.setText("J.A.R.V.I.S.: Thinking...")
        self.send_button.setEnabled(False)
        self.pending_chat_id = target_chat_id

        self.ai_worker = AIWorker(
            message,
            history,
            other_chats,
        )

        self.ai_worker.answer_ready.connect(self.on_ai_answer)
        self.ai_worker.tool_requested.connect(
            self.handle_ai_tool_call
        )
        self.ai_worker.finished.connect(
            lambda: self.send_button.setEnabled(True)
        )
        self.ai_worker.start()

    def handle_pending_deletion_confirmation(self, message, chat_id):
        pending = self.pending_calendar_deletion

        if not pending or pending.get("chat_id") != chat_id:
            return False

        normalized = message.strip().lower()
        normalized = re.sub(r"[.!?,;:]+", "", normalized)
        normalized = " ".join(normalized.split())
        yes_words = {
            "yes",
            "y",
            "yep",
            "yeah",
            "k",
            "yes please",
            "yes delete",
            "yes delete it",
            "yes confirm",
            "confirm",
            "confirm deletion",
            "delete it",
            "do it",
            "sure",
            "ok",
            "okay"
        }

        no_words = {
            "no",
            "n",
            "nope",
            "nah",
            "no thanks",
            "cancel",
            "cancel deletion",
            "don't delete",
            "do not delete"
        }

        if normalized not in yes_words and normalized not in no_words:
            return False

        elif normalized in no_words:
            self.pending_calendar_deletion = None
            answer = "Deletion cancelled. Events remain in the calendar."

        else:
            event_ids = set(pending.get("event_ids", []))

            matched_events = [
                event for event in self.events
                if event.get("id") in event_ids
            ]

            if len(matched_events) != len(event_ids):
                self.pending_calendar_deletion = None
                answer = (
                    "Failed to find all events. "
                    "No events were deleted."
                )
            else:
                old_events = list(self.events)

                self.events = [
                    event for event in self.events
                    if event.get("id") not in event_ids
                ]

                saved = self.save_events()

                if saved is False:
                    self.events = old_events
                    self.mark_calendar_events()
                    answer = (
                        "Failed to save changes. "
                        "The events were not deleted."
                    )
                else:
                    self.mark_calendar_events()
                    names = ", ".join(
                        event.get("title", "No title")
                        for event in matched_events
                    )
                    answer = (
                        f"Ready! Deleted Events: {names}."
                    )

                self.pending_calendar_deletion = None

        self.add_chat_message("user", message, chat_id)
        self.add_chat_message("assistant", answer, chat_id)

        if self.current_chat_id == chat_id:
            self.show_chat_message("YOU", message, "#40e0d0")
            self.show_chat_message("J.A.R.V.I.S.", answer, "#7ce7ff")

        self.response_label.setText("J.A.R.V.I.S.: Response received.")
        return True

    def on_ai_answer(self, answer):
        target_chat_id = getattr(
            self,
            "pending_chat_id",
            self.current_chat_id
        )

        chat = next(
            (item for item in self.chats if item["id"] == target_chat_id),
            None
        )

        if chat is None:
            self.response_label.setText(
                "J.A.R.V.I.S.: The target chat no longer exists."
            )
            return

        self.add_chat_message("assistant", answer, target_chat_id)

        # Wyświetl odpowiedź tylko wtedy, gdy ten czat jest aktualnie otwarty.
        if self.current_chat_id == target_chat_id:
            self.show_chat_message(
                "J.A.R.V.I.S.",
                answer,
                "#7ce7ff"
            )

        self.response_label.setText(
            "J.A.R.V.I.S.: Response received."
        )

    def get_calendar_color(self, color_name):
        if color_name.lower() not in (
            "custom 1", "custom 2", "custom 3"
        ):
            return color_name

        # Find the current custom color in the calendar settings.
        # Change these attribute names if your settings use different ones.
        custom_colors = getattr(self, "custom_colors", {})

        if isinstance(custom_colors, dict):
            return custom_colors.get(color_name, color_name)

        return color_name

    def get_custom_calendar_color(self, color_name):
        custom_colors_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "jarvis_custom_colors.json"
        )

        try:
            with open(custom_colors_file, "r", encoding="utf-8") as file:
                custom_colors = json.load(file)

            color = custom_colors.get(color_name)
            if color and QColor(color).isValid():
                return color

        except (OSError, json.JSONDecodeError):
            pass

        return None

    def run_command(self):
        raw_command = self.command_input.toPlainText().strip()

        if not raw_command:
            return

        command = raw_command.lower()

        if self.ai_worker is not None and self.ai_worker.isRunning():
            self.response_label.setText(
                "J.A.R.V.I.S.: Please wait for the next response."
            )
            return

        self.command_input.clear()

        # Local system commands
        if command in ("/time",):
            answer = datetime.now().strftime("Current time: %H:%M:%S")

        elif command in ("/date",):
            answer = datetime.now().strftime("Current date: %d.%m.%Y")

        elif command == "/youtube":
            webbrowser.open("https://www.youtube.com")
            answer = "Opening YouTube in your browser."

        elif command == "/google":
            webbrowser.open("https://www.google.com")
            answer = "Opening Google in your browser."

        elif command == "/notepad":
            subprocess.Popen(["notepad.exe"])
            answer = "Launching Notepad."

        elif command in ("/fullscreen", "/full"):
            self.showFullScreen()
            answer = "Fullscreen mode activated."

        elif command in ("/window", "/windowmode"):
            self.showNormal()
            answer = "Windowed mode restored."

        elif command in ("/help", "/commands"):
            answer = (
                "Available commands:\n"
                "/time - Current time\n"
                "/date - Current date\n"
                "/youtube - Open YouTube\n"
                "/google - Open Google\n"
                "/notepad - Launch Notepad\n"
                "/fullscreen - Enable fullscreen\n"
                "/window - Restore windowed mode\n"
                "/help - Show available commands\n"
                "/calendar;title;color;priority;date - Add a calendar event\n"
                "Date is optional. Default: today.\n"
                "You can also ask J.A.R.V.I.S. other questions."
            )

        # Calendar command:
        # /calendar;title;color;priority
        # /calendar;title;color;priority;date
        elif command == "/calendar" or command.startswith("/calendar;"):
            segments = raw_command.strip().split(":")
            new_events = []
            error = None

            standard_colors = [
                "Red", "Green", "Blue", "Forest", "Yellow",
                "Turquoise", "Cyan", "Pink", "Orange", "Purple",
                "Brown", "Black", "White",
            ]

            custom_color_names = ["Custom 1", "Custom 2", "Custom 3"]

            # Validate every event before saving any of them.
            for index, segment in enumerate(segments):
                parts = segment.strip().split(";")

                expected_prefix = "/calendar" if index == 0 else "calendar"

                if len(parts) != 5 or parts[0].strip() != expected_prefix:
                    error = (
                        f"Invalid format in event {index + 1}.\n"
                        "Use:\n"
                        "/calendar;title;color;priority;date"
                        ":calendar;title;color;priority;date"
                    )
                    break

                title = parts[1].strip()
                color = parts[2].strip()
                priority_text = parts[3].strip()
                date_text = parts[4].strip()

                if not title:
                    error = f"Event {index + 1}: title cannot be empty."
                    break

                if ":" in title or ";" in title:
                    error = (
                        f"Event {index + 1}: titles cannot contain "
                        "':' or ';'."
                    )
                    break

                try:
                    priority = int(priority_text)
                    if not 1 <= priority <= 10:
                        raise ValueError

                    date_formats = (
                        "%Y-%m-%d",
                        "%d.%m.%Y",
                        "%d-%m-%Y",
                    )

                    event_date = None

                    for date_format in date_formats:
                        try:
                            event_date = datetime.strptime(
                                date_text, date_format
                            ).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue

                    if event_date is None:
                        raise ValueError("Invalid date format")

                except ValueError:
                    error = (
                        f"Event {index + 1}: invalid priority or date.\n"
                        "Priority: 1-10. Date: YYYY-MM-DD or DD.MM.YYYY."
                    )
                    break

                # Resolve the color.
                resolved_color = None

                standard_color = next(
                    (
                        name for name in standard_colors
                        if name.lower() == color.lower()
                    ),
                    None,
                )

                custom_color = next(
                    (
                        name for name in custom_color_names
                        if name.lower() == color.lower()
                    ),
                    None,
                )

                if standard_color:
                    resolved_color = standard_color

                elif custom_color:
                    resolved_color = self.get_custom_calendar_color(
                        custom_color
                    )

                    if not resolved_color:
                        error = (
                            f"Event {index + 1}: could not load "
                            f"the color {custom_color}."
                        )
                        break

                elif color.startswith("#") and QColor(color).isValid():
                    resolved_color = QColor(color).name()

                else:
                    error = (
                        f"Event {index + 1}: invalid color '{color}'. "
                        "Use a listed color, Custom 1-3, "
                        "or a HEX code such as #398cff."
                    )
                    break

                new_events.append({
                    "title": title,
                    "date": event_date,
                    "color": resolved_color,
                    "priority": priority,
                    "id": uuid.uuid4().hex,
                })

            # Check the four-event daily limit for all additions.
            if error is None:
                additions_per_date = {}

                for event in new_events:
                    date_key = event["date"]
                    additions_per_date[date_key] = (
                        additions_per_date.get(date_key, 0) + 1
                    )

                for date_key, addition_count in additions_per_date.items():
                    existing_count = sum(
                        1 for event in self.events
                        if event.get("date") == date_key
                    )

                    if existing_count + addition_count > 4:
                        error = (
                            f"Cannot add events for {date_key}: "
                            "the limit is 4 events per day."
                        )
                        break

            if error:
                answer = "No events were added.\n" + error

            else:
                old_events = list(self.events)
                self.events.extend(new_events)

                if self.save_events() is False:
                    self.events = old_events
                    answer = (
                        "Could not save the events. "
                        "No changes were kept."
                    )
                else:
                    self.mark_calendar_events()

                    summary = "\n".join(
                        f"- {event['title']} | "
                        f"{event['color']} | "
                        f"Priority {event['priority']}/10 | "
                        f"{event['date']}"
                        for event in new_events
                    )

                    answer = (
                        f"Successfully added {len(new_events)} event(s):\n"
                        f"{summary}"
                    )

        else:
            # Unknown slash commands should not be sent to the AI.
            if command.startswith("/"):
                answer = (
                    "Unknown command. Type /help to see available commands."
                )
            else:
                self.ask_ai(raw_command)
                return

        # Display and save local command messages in chat history.
        self.add_chat_message("user", raw_command)
        self.show_chat_message("YOU", raw_command, "#40e0d0")

        self.add_chat_message("assistant", answer)
        self.show_chat_message("J.A.R.V.I.S.", answer, "#7ce7ff")

        self.response_label.setText("J.A.R.V.I.S.: " + answer)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JarvisDashboard()
    window.showMaximized()
    sys.exit(app.exec())