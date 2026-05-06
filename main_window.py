#!/usr/bin/env python3
"""Main application window with modern dark UI."""
import os
import time
import logging
import json
import socket
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QSlider,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QComboBox,
    QInputDialog, QDoubleSpinBox, QFrame, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import cv2
import numpy as np
from seed import Seed
from scrambler import scramble_image, descramble_image, scramble_video
from lens_window import LensWindow

logger = logging.getLogger(__name__)

PRESETS_FILE = Path(os.environ.get("RTM_PRESETS_FILE", "presets.json"))

# ── Modern Dark Palette ──────────────────────────────────────────────
APP_STYLE = """
QMainWindow {
    background-color: #0f0f1a;
}
QWidget {
    background-color: #0f0f1a;
    color: #e2e8f0;
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 15px;
}

/* ── Tab Widget ───────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    background-color: #161622;
    padding: 12px;
    top: -1px;
}
QTabBar::tab {
    background-color: #1a1a2e;
    color: #94a3b8;
    border: 1px solid #2a2a3a;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 12px 32px;
    margin-right: 4px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #161622;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}
QTabBar::tab:hover:!selected {
    background-color: #1e1e32;
    color: #cbd5e1;
}

/* ── Group Box (Card) ────────────────────────────────────────────── */
QGroupBox {
    background-color: #1a1a2e;
    border: 1px solid #2a2a3a;
    border-radius: 10px;
    margin-top: 32px;
    padding: 6px 18px 18px 18px;
    font-weight: 600;
    color: #e2e8f0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 8px;
    padding: 2px 10px;
    background-color: #1a1a2e;
    color: #38bdf8;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 20px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #27354f;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #334155;
}
QPushButton:disabled {
    background-color: #13131f;
    color: #475569;
    border-color: #1e1e32;
}
QPushButton#accentBtn {
    background-color: #0ea5e9;
    color: #ffffff;
    border: none;
    font-weight: 600;
}
QPushButton#accentBtn:hover {
    background-color: #0284c7;
}
QPushButton#accentBtn:pressed {
    background-color: #0369a1;
}
QPushButton#accentBtn:disabled {
    background-color: #1e293b;
    color: #475569;
}
QPushButton#dangerBtn {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    font-weight: 600;
}
QPushButton#dangerBtn:hover {
    background-color: #dc2626;
}
QPushButton#dangerBtn:pressed {
    background-color: #b91c1c;
}

/* ── Line Edit ───────────────────────────────────────────────────── */
QLineEdit {
    background-color: #0f0f1a;
    color: #e2e8f0;
    border: 1px solid #2a2a3a;
    border-radius: 6px;
    padding: 9px 12px;
    selection-background-color: #0ea5e9;
}
QLineEdit:focus {
    border: 1px solid #38bdf8;
}
QLineEdit::placeholder {
    color: #475569;
}

/* ── Text Edit ───────────────────────────────────────────────────── */
QTextEdit {
    background-color: #0f0f1a;
    color: #e2e8f0;
    border: 1px solid #2a2a3a;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #0ea5e9;
}
QTextEdit:focus {
    border: 1px solid #38bdf8;
}

/* ── Combo Box ───────────────────────────────────────────────────── */
QComboBox {
    background-color: #0f0f1a;
    color: #e2e8f0;
    border: 1px solid #2a2a3a;
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 140px;
}
QComboBox:focus {
    border: 1px solid #38bdf8;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #94a3b8;
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    color: #e2e8f0;
    border: 1px solid #2a2a3a;
    selection-background-color: #0ea5e9;
    selection-color: #ffffff;
    outline: none;
}

/* ── Slider ──────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #0ea5e9;
    border-radius: 3px;
}
QSlider::add-page:horizontal {
    background: #1e293b;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #38bdf8;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -5px 0;
}
QSlider::handle:horizontal:hover {
    background: #7dd3fc;
}

/* ── Spin Box ────────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox {
    background-color: #0f0f1a;
    color: #e2e8f0;
    border: 1px solid #2a2a3a;
    border-radius: 6px;
    padding: 8px 10px;
    min-width: 80px;
}
QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    width: 18px;
    border: none;
    background: #1e293b;
    border-radius: 3px;
    margin: 1px;
}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
    background: #27354f;
}

/* ── Progress Bar ────────────────────────────────────────────────── */
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #1e293b;
    height: 8px;
    text-align: center;
    color: #94a3b8;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #0ea5e9;
    border-radius: 6px;
}

/* ── Scroll Bars ─────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0f0f1a;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0f0f1a;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #475569;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel#statusLabel {
    color: #64748b;
    font-size: 14px;
    padding: 6px 4px;
}
QLabel#titleLabel {
    color: #38bdf8;
    font-size: 20px;
    font-weight: 700;
}
QLabel#sectionLabel {
    color: #94a3b8;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QLabel#previewLabel {
    background-color: #0a0a12;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
}
QLabel#hintLabel {
    color: #64748b;
    font-size: 14px;
}
QLabel#okLabel {
    color: #10b981;
    font-size: 12px;
}
"""


class NativeMessagingServer(QThread):
    """TCP server that receives JSON commands from the browser extension
    (via Native Messaging host bridge) and forwards them to MainWindow."""
    message_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)

    def __init__(self, port=35421, parent=None):
        super().__init__(parent)
        self.port = port
        self._running = True
        self._sock = None

    def run(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(("127.0.0.1", self.port))
            self._sock.listen(1)
            self.status_changed.emit(f"Auto-align ready on port {self.port}")
            logger.info("NativeMessagingServer listening on %s:%d", "127.0.0.1", self.port)
        except Exception as e:
            self.status_changed.emit(f"Auto-align server failed: {e}")
            logger.exception("NativeMessagingServer bind failed")
            return

        while self._running:
            try:
                self._sock.settimeout(1.0)
                conn, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                conn.settimeout(2.0)
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                if data:
                    msg = json.loads(data.decode("utf-8"))
                    self.message_received.emit(msg)
                    resp = {"status": "ok"}
                    conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
            except Exception as e:
                logger.exception("TCP handler error")
                try:
                    conn.sendall((json.dumps({"status": "error", "message": str(e)}) + "\n").encode("utf-8"))
                except Exception:
                    pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass


class VideoWorker(QThread):
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, input_path, output_path, seed):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.seed = seed

    def run(self):
        ok = scramble_video(self.input_path, self.output_path, self.seed,
                           progress_callback=lambda p: self.progress.emit(p))
        if ok:
            self.finished_ok.emit()
        else:
            self.error.emit("Video processing failed.")


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RealTimeMix")
        self.resize(960, 720)
        self.setStyleSheet(APP_STYLE)
        self.lens = LensWindow()
        self.lens.on_close = self._stop_lens
        self.worker = None
        self._custom_presets = []
        self._auto_align = False

        central = QWidget()
        self.setCentralWidget(central)
        vlay = QVBoxLayout(central)
        vlay.setContentsMargins(20, 16, 20, 12)
        vlay.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────
        header = QHBoxLayout()
        self._icon_label = QLabel("🔒")
        self._icon_label.setStyleSheet("font-size: 22px; background: transparent;")
        self._title = QLabel("RealTimeMix")
        self._title.setObjectName("titleLabel")
        self._title.setStyleSheet("background: transparent;")
        self._subtitle = QLabel("Pixel Scrambler & Decrypt Lens")
        self._subtitle.setStyleSheet("color: #64748b; font-size: 15px; background: transparent;")
        header.addWidget(self._icon_label)
        header.addWidget(self._title)
        header.addWidget(self._subtitle)
        header.addStretch()
        vlay.addLayout(header)

        # ── Tabs ──────────────────────────────────────────────────────
        tabs = QTabWidget()
        self.tab_encrypt = QWidget()
        self.tab_lens = QWidget()
        self._setup_encrypt_tab(self.tab_encrypt)
        self._setup_lens_tab(self.tab_lens)
        tabs.addTab(self.tab_encrypt, "  🔐 Encrypt  ")
        tabs.addTab(self.tab_lens, "  🔍 Decrypt Lens  ")
        vlay.addWidget(tabs, 1)

        self._load_presets()

        # ── Status Bar ────────────────────────────────────────────────
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        vlay.addWidget(self.status_label)

        # Native Messaging TCP server (must be after status_label is created)
        self._native_server = NativeMessagingServer(port=int(os.environ.get("RTM_PORT", "35421")))
        self._native_server.message_received.connect(self._on_native_message)
        self._native_server.status_changed.connect(self.status_label.setText)
        self._native_server.start()

    def _setup_encrypt_tab(self, tab):
        vlay = QVBoxLayout(tab)
        vlay.setContentsMargins(4, 12, 4, 4)
        vlay.setSpacing(18)

        # ── File Selection Card ─────────────────────────────────────
        file_card = QGroupBox("File Selection")
        file_grid = QGridLayout(file_card)
        file_grid.setVerticalSpacing(12)
        file_grid.setHorizontalSpacing(10)

        self.edit_input = QLineEdit()
        self.edit_input.setPlaceholderText("Select an image or video file...")
        btn_in = QPushButton("Browse…")
        btn_in.setFixedWidth(110)
        btn_in.clicked.connect(self._browse_input)
        file_grid.addWidget(QLabel("Input"), 0, 0)
        file_grid.addWidget(self.edit_input, 0, 1)
        file_grid.addWidget(btn_in, 0, 2)

        self.edit_output = QLineEdit()
        self.edit_output.setPlaceholderText("Save scrambled file to...")
        btn_out = QPushButton("Browse…")
        btn_out.setFixedWidth(110)
        btn_out.clicked.connect(self._browse_output)
        file_grid.addWidget(QLabel("Output"), 1, 0)
        file_grid.addWidget(self.edit_output, 1, 1)
        file_grid.addWidget(btn_out, 1, 2)
        file_grid.setColumnStretch(1, 1)
        vlay.addWidget(file_card)

        # ── Parameters Card ─────────────────────────────────────────
        param_card = QGroupBox("Parameters")
        param_grid = QGridLayout(param_card)
        param_grid.setVerticalSpacing(12)
        param_grid.setHorizontalSpacing(10)

        param_grid.addWidget(QLabel("Block Size"), 0, 0)
        bs_hbox = QHBoxLayout()
        self.slider_bs = QSlider(Qt.Orientation.Horizontal)
        self.slider_bs.setRange(3, 8)
        self.slider_bs.setValue(5)
        self.lbl_bs = QLabel("32")
        self.lbl_bs.setStyleSheet("font-weight: 600; color: #38bdf8; min-width: 28px;")
        self.slider_bs.valueChanged.connect(lambda v: self.lbl_bs.setText(str(1 << v)))
        bs_hbox.addWidget(self.slider_bs, 1)
        bs_hbox.addWidget(self.lbl_bs)
        param_grid.addLayout(bs_hbox, 0, 1)
        param_grid.addWidget(QLabel(" pixels"), 0, 2)

        self.btn_scramble = QPushButton("▶  Scramble & Save")
        self.btn_scramble.setObjectName("accentBtn")
        self.btn_scramble.setMinimumHeight(40)
        self.btn_scramble.clicked.connect(self._do_scramble)
        param_grid.addWidget(self.btn_scramble, 1, 0, 1, 3)

        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.hide()
        param_grid.addWidget(self.prog, 2, 0, 1, 3)

        self.edit_seed_out = QTextEdit()
        self.edit_seed_out.setReadOnly(True)
        self.edit_seed_out.setMaximumHeight(80)
        self.edit_seed_out.setPlaceholderText("Generated seed will appear here...")
        param_grid.addWidget(QLabel("Seed"), 3, 0, alignment=Qt.AlignmentFlag.AlignTop)
        param_grid.addWidget(self.edit_seed_out, 3, 1, 1, 2)
        param_grid.setColumnStretch(1, 1)
        vlay.addWidget(param_card)

        # ── Preview Card ────────────────────────────────────────────
        preview_card = QGroupBox("Preview")
        preview_vlay = QVBoxLayout(preview_card)
        preview_vlay.setSpacing(8)

        self.lbl_preview = QLabel()
        self.lbl_preview.setMinimumSize(400, 240)
        self.lbl_preview.setObjectName("previewLabel")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setText("No preview")
        preview_vlay.addWidget(self.lbl_preview, 1, Qt.AlignmentFlag.AlignCenter)
        vlay.addWidget(preview_card, 1)

    def _setup_lens_tab(self, tab):
        vlay = QVBoxLayout(tab)
        vlay.setContentsMargins(4, 12, 4, 4)
        vlay.setSpacing(18)

        # ── Seed Card ───────────────────────────────────────────────
        seed_card = QGroupBox("Seed")
        seed_grid = QGridLayout(seed_card)
        seed_grid.setVerticalSpacing(12)

        self.edit_seed_in = QTextEdit()
        self.edit_seed_in.setPlaceholderText("Paste your seed string here...")
        self.edit_seed_in.setMaximumHeight(90)
        self.edit_seed_in.textChanged.connect(self._validate_seed_input)
        seed_grid.addWidget(self.edit_seed_in, 0, 0)
        vlay.addWidget(seed_card)

        # ── Lens Controls Card ──────────────────────────────────────
        ctrl_card = QGroupBox("Lens Controls")
        ctrl_grid = QGridLayout(ctrl_card)
        ctrl_grid.setVerticalSpacing(14)
        ctrl_grid.setHorizontalSpacing(10)

        ctrl_grid.addWidget(QLabel("Preset"), 0, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("Custom (manual resize)", "custom")
        self.combo_preset.addItem("100%  — Original Size", 1.0)
        self.combo_preset.addItem("150%  — 1.5× Zoom", 1.5)
        self.combo_preset.addItem("200%  — 2× Zoom", 2.0)
        self.combo_preset.addItem("Fit Screen", "fit")
        ctrl_grid.addWidget(self.combo_preset, 0, 1, 1, 2)

        ctrl_grid.addWidget(QLabel("Scale"), 1, 0)
        hsize = QHBoxLayout()
        self.slider_lens_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_lens_size.setRange(100, 2500)
        self.slider_lens_size.setValue(1000)
        self.slider_lens_size.setEnabled(False)
        self.slider_lens_size.valueChanged.connect(self._on_lens_slider_changed)
        self.spin_lens_size = QDoubleSpinBox()
        self.spin_lens_size.setRange(10.0, 250.0)
        self.spin_lens_size.setDecimals(1)
        self.spin_lens_size.setSingleStep(0.1)
        self.spin_lens_size.setSuffix("%")
        self.spin_lens_size.setValue(100.0)
        self.spin_lens_size.setEnabled(False)
        self.spin_lens_size.setFixedWidth(90)
        self.spin_lens_size.valueChanged.connect(self._on_spinbox_changed)
        self.lbl_lens_size = QLabel("original")
        self.lbl_lens_size.setStyleSheet("color: #94a3b8; min-width: 60px;")
        hsize.addWidget(self.slider_lens_size, 1)
        hsize.addWidget(self.spin_lens_size)
        hsize.addWidget(self.lbl_lens_size)
        ctrl_grid.addLayout(hsize, 1, 1, 1, 2)

        # Auto-align toggle
        align_hbox = QHBoxLayout()
        self.btn_auto_align = QPushButton("🎯  Enable Auto Align")
        self.btn_auto_align.setCheckable(True)
        self.btn_auto_align.setMinimumHeight(36)
        self.btn_auto_align.clicked.connect(self._toggle_auto_align)
        self.lbl_auto_align = QLabel("Off")
        self.lbl_auto_align.setStyleSheet("color: #64748b; font-size: 13px;")
        align_hbox.addWidget(self.btn_auto_align)
        align_hbox.addWidget(self.lbl_auto_align)
        align_hbox.addStretch()
        ctrl_grid.addLayout(align_hbox, 2, 0, 1, 3)

        btn_hbox = QHBoxLayout()
        btn_hbox.setSpacing(10)
        self.btn_start = QPushButton("▶  Start Lens")
        self.btn_start.setObjectName("accentBtn")
        self.btn_start.setMinimumHeight(36)
        self.btn_stop = QPushButton("⏹  Stop Lens")
        self.btn_stop.setObjectName("dangerBtn")
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setEnabled(False)
        self.btn_save_preset = QPushButton("💾  Save Size")
        self.btn_save_preset.setMinimumHeight(36)
        self.btn_save_preset.setEnabled(False)
        self.btn_start.clicked.connect(self._start_lens)
        self.btn_stop.clicked.connect(self._stop_lens)
        self.btn_save_preset.clicked.connect(self._save_current_preset)
        btn_hbox.addWidget(self.btn_start)
        btn_hbox.addWidget(self.btn_stop)
        btn_hbox.addWidget(self.btn_save_preset)
        btn_hbox.addStretch()
        ctrl_grid.addLayout(btn_hbox, 3, 0, 1, 3)

        ctrl_grid.setColumnStretch(1, 1)
        vlay.addWidget(ctrl_card)

        # ── Status & Hints ──────────────────────────────────────────
        hint_card = QGroupBox("Status")
        hint_vlay = QVBoxLayout(hint_card)
        self.lbl_lens_status = QLabel("Enter a valid seed to start the decrypt lens.")
        self.lbl_lens_status.setObjectName("hintLabel")
        self.lbl_lens_status.setWordWrap(True)
        hint_vlay.addWidget(self.lbl_lens_status)

        hint_text = QLabel(
            "<b>Tips:</b> Drag the lens window to move. "
            "Right-click for options. "
            "Use <b>Ctrl+Shift+Arrows</b> to nudge 1px. "
            "Use <b>Ctrl+Shift++/-</b> to zoom ±0.1%. "
            "Double-click to close lens."
        )
        hint_text.setObjectName("hintLabel")
        hint_text.setWordWrap(True)
        hint_text.setTextFormat(Qt.TextFormat.RichText)
        hint_vlay.addWidget(hint_text)
        vlay.addWidget(hint_card)

        vlay.addStretch(1)

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Input", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;Videos (*.mp4 *.avi *.mkv *.mov);;All Files (*)")
        if path:
            self.edit_input.setText(path)
            base, ext = os.path.splitext(path)
            self.edit_output.setText(base + "_scrambled" + ext)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Output", "",
            "Images (*.png *.jpg *.bmp);;Videos (*.mp4 *.avi);;All Files (*)")
        if path:
            self.edit_output.setText(path)

    def _validate_seed_input(self):
        s = self.edit_seed_in.toPlainText().strip()
        seed = Seed.from_string(s)
        if seed:
            self.edit_seed_in.setStyleSheet(
                "border: 1px solid #10b981; border-radius: 6px; padding: 8px; background-color: #0f0f1a; color: #e2e8f0;"
            )
        else:
            self.edit_seed_in.setStyleSheet(
                "border: 1px solid #334155; border-radius: 6px; padding: 8px; background-color: #0f0f1a; color: #e2e8f0;"
            )

    def _do_scramble(self):
        in_path = self.edit_input.text()
        out_path = self.edit_output.text()
        if not in_path or not out_path:
            QMessageBox.warning(self, "Missing paths", "Please select input and output files.")
            return
        bs = 1 << self.slider_bs.value()
        seed_val = int(time.time_ns() % (2**64))

        is_video = any(in_path.lower().endswith(x) for x in ['.mp4', '.avi', '.mkv', '.mov'])
        self.prog.show()
        self.prog.setValue(0)
        self.btn_scramble.setEnabled(False)

        if not is_video:
            img = cv2.imread(in_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                QMessageBox.critical(self, "Error", "Failed to load image.")
                self.btn_scramble.setEnabled(True)
                self.prog.hide()
                return
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            h, w = img.shape[:2]
            seed = Seed(w, h, bs, seed_val)
            scrambled = scramble_image(img, seed)
            cv2.imwrite(out_path, scrambled)

            self.edit_seed_out.setPlainText(seed.to_string())
            self._show_preview(scrambled)
            self.prog.setValue(100)
            self.status_label.setText("Image scrambled successfully.")
            self.btn_scramble.setEnabled(True)
        else:
            cap = cv2.VideoCapture(in_path)
            if not cap.isOpened():
                QMessageBox.critical(self, "Error", "Failed to open video file.")
                self.btn_scramble.setEnabled(True)
                self.prog.hide()
                return
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            seed = Seed(w, h, bs, seed_val)
            self.edit_seed_out.setPlainText(seed.to_string())

            self.worker = VideoWorker(in_path, out_path, seed)
            self.worker.progress.connect(self.prog.setValue)
            self.worker.finished_ok.connect(self._on_video_done)
            self.worker.error.connect(self._on_video_error)
            self.worker.start()

    def _on_video_done(self):
        self.status_label.setText("Video scrambled successfully.")
        self.btn_scramble.setEnabled(True)
        self.prog.setValue(100)

    def _on_video_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.btn_scramble.setEnabled(True)
        self.prog.hide()

    def _show_preview(self, img_bgr):
        h, w = img_bgr.shape[:2]
        scale = min(400 / w, 240 / h)
        tw, th = max(1, round(w * scale)), max(1, round(h * scale))
        thumb = cv2.resize(img_bgr, (tw, th))
        rgb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888)
        self.lbl_preview.setPixmap(QPixmap.fromImage(qimg.copy()))
        self.lbl_preview.setText("")

    def _start_lens(self):
        try:
            s = self.edit_seed_in.toPlainText().strip()
            logger.info("_start_lens with seed string len=%d", len(s))
            seed = Seed.from_string(s)
            if not seed:
                QMessageBox.warning(self, "Invalid Seed", "The seed string is invalid.")
                logger.warning("_start_lens: invalid seed")
                return
            self.lens.set_seed(seed)
            preset = self.combo_preset.currentData()
            if isinstance(preset, (int, float)):
                self.lens.set_size_from_scale(preset)
            elif preset == "fit":
                self.lens.set_size_fit_screen()
            elif isinstance(preset, tuple) and len(preset) == 2:
                self.lens.resize(preset[0], preset[1])
            self.lens.start()
            self.slider_lens_size.setEnabled(True)
            self.spin_lens_size.setEnabled(True)
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_save_preset.setEnabled(True)
            self.lbl_lens_status.setText(
                "Lens is running. Drag to move, right-click for options, "
                "Ctrl+Shift+Arrows to nudge 1px, Ctrl+Shift++/- to zoom ±0.1%."
            )
            self.lbl_lens_status.setObjectName("okLabel")
            self.lbl_lens_status.setStyleSheet("color: #10b981;")
            self.status_label.setText("Lens active.")
            logger.info("_start_lens: lens started")
        except Exception:
            logger.exception("_start_lens exception")
            raise

    def _stop_lens(self):
        try:
            self.lens.stop()
            self.slider_lens_size.setEnabled(False)
            self.spin_lens_size.setEnabled(False)
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_save_preset.setEnabled(False)
            self.lbl_lens_status.setText("Lens stopped. Enter a valid seed to restart.")
            self.lbl_lens_status.setObjectName("hintLabel")
            self.lbl_lens_status.setStyleSheet("color: #64748b;")
            self.status_label.setText("Lens stopped.")
            logger.info("_stop_lens: lens stopped")
        except Exception:
            logger.exception("_stop_lens exception")

    def _toggle_auto_align(self):
        self._auto_align = self.btn_auto_align.isChecked()
        state = "On" if self._auto_align else "Off"
        color = "#10b981" if self._auto_align else "#64748b"
        self.lbl_auto_align.setText(state)
        self.lbl_auto_align.setStyleSheet(f"color: {color}; font-size: 13px;")
        self.status_label.setText(f"Auto-align {state.lower()}")
        logger.info("auto_align toggled: %s", state)

    def _on_native_message(self, msg):
        cmd = msg.get("cmd")
        logger.info("native_message: cmd=%s", cmd)
        if cmd == "align":
            rect = msg.get("rect", {})
            x = rect.get("x", 0)
            y = rect.get("y", 0)
            w = rect.get("width", 100)
            h = rect.get("height", 100)
            seed_str = self.edit_seed_in.toPlainText().strip()
            if not seed_str:
                self.status_label.setText("Auto-align: seed required")
                return
            seed = Seed.from_string(seed_str)
            if not seed:
                self.status_label.setText("Auto-align: invalid seed")
                return
            self.lens.set_seed(seed)
            self.lens.move(x, y)
            self.lens.resize(w, h)
            if not self.lens.is_visible():
                self._start_lens()
            else:
                self.status_label.setText("Lens aligned to target.")
            # Log alignment for debugging drift
            import ctypes
            from ctypes import wintypes
            r = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(self.lens._hwnd, ctypes.byref(r))
            debug = msg.get("debug", {})
            logger.info(
                "align: req=%dx%d+%d+%d act=%dx%d+%d+%d dpr=%s iframes=%s cssRect=%s screen=%s",
                w, h, x, y, r.right-r.left, r.bottom-r.top, r.left, r.top,
                debug.get("dpr"), debug.get("iframeDepth"),
                debug.get("cssRect"), (debug.get("screenLeft"), debug.get("screenTop"))
            )
        elif cmd == "set_seed":
            seed = msg.get("seed", "")
            self.edit_seed_in.setPlainText(seed)
            self._validate_seed_input()
            self.status_label.setText("Seed updated from browser.")
        elif cmd == "start_lens":
            self._start_lens()
        elif cmd == "stop_lens":
            self._stop_lens()
        elif cmd == "toggle_auto_align":
            enabled = msg.get("enabled", False)
            self.btn_auto_align.setChecked(enabled)
            self._toggle_auto_align()

    def _save_current_preset(self):
        if not self.lens.is_visible():
            QMessageBox.information(self, "Info", "Start the lens first to save its size.")
            return
        w, h = self.lens.width(), self.lens.height()
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name.strip():
            preset = {"name": name.strip(), "width": w, "height": h}
            self._custom_presets.append(preset)
            display = f"{preset['name']} ({w}×{h})"
            self.combo_preset.addItem(display, (w, h))
            self.combo_preset.setCurrentIndex(self.combo_preset.count() - 1)
            self._save_presets_to_file()

    def _load_presets(self):
        if not PRESETS_FILE.exists():
            return
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                self._custom_presets = json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load presets")
            self._custom_presets = []
        for p in self._custom_presets:
            name = p.get("name", "Unnamed")
            w, h = p.get("width", 0), p.get("height", 0)
            if w > 0 and h > 0:
                display = f"{name} ({w}×{h})"
                self.combo_preset.addItem(display, (w, h))

    def _save_presets_to_file(self):
        try:
            with open(PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._custom_presets, f, ensure_ascii=False, indent=2)
        except OSError:
            logger.exception("Failed to save presets")

    def _on_lens_slider_changed(self, value):
        if not self.lens.is_visible():
            return
        if not self.lens.seed:
            return
        scale = value / 1000.0
        self.spin_lens_size.blockSignals(True)
        self.spin_lens_size.setValue(round(scale * 100, 1))
        self.spin_lens_size.blockSignals(False)
        self.lens.set_size_from_scale(scale)
        logger.info("slider: set_size_from_scale scale=%.3f", scale)

    def _on_spinbox_changed(self, value):
        if not self.lens.is_visible():
            return
        if not self.lens.seed:
            return
        scale = value / 100.0
        slider_val = int(round(scale * 1000))
        self.slider_lens_size.blockSignals(True)
        self.slider_lens_size.setValue(slider_val)
        self.slider_lens_size.blockSignals(False)
        self.lens.set_size_from_scale(scale)
        logger.info("spinbox: set_size_from_scale scale=%.3f", scale)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.wait(2000)
        if self._native_server:
            self._native_server.stop()
            self._native_server.wait(2000)
        self.lens.close()
        event.accept()
