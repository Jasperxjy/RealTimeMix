#!/usr/bin/env python3
"""Main application window."""
import os
import time
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QSlider,
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QComboBox,
    QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import cv2
import numpy as np
from seed import Seed
from scrambler import scramble_image, descramble_image, scramble_video
from lens_window import LensWindow

logger = logging.getLogger(__name__)


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
        self.setWindowTitle("RealTimeMix - Pixel Scrambler")
        self.resize(900, 650)
        self.lens = LensWindow()
        self.lens.on_close = self._stop_lens
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        vlay = QVBoxLayout(central)

        tabs = QTabWidget()
        self.tab_encrypt = QWidget()
        self.tab_lens = QWidget()
        self._setup_encrypt_tab(self.tab_encrypt)
        self._setup_lens_tab(self.tab_lens)
        tabs.addTab(self.tab_encrypt, "Encrypt")
        tabs.addTab(self.tab_lens, "Decrypt Lens")
        vlay.addWidget(tabs)

        self.status_label = QLabel("Ready")
        vlay.addWidget(self.status_label)

    def _setup_encrypt_tab(self, tab):
        grid = QGridLayout(tab)
        r = 0

        grid.addWidget(QLabel("Input:"), r, 0)
        self.edit_input = QLineEdit()
        self.edit_input.setPlaceholderText("Image or video...")
        grid.addWidget(self.edit_input, r, 1)
        btn_in = QPushButton("Browse...")
        btn_in.clicked.connect(self._browse_input)
        grid.addWidget(btn_in, r, 2)
        r += 1

        grid.addWidget(QLabel("Output:"), r, 0)
        self.edit_output = QLineEdit()
        self.edit_output.setPlaceholderText("Save scrambled file to...")
        grid.addWidget(self.edit_output, r, 1)
        btn_out = QPushButton("Browse...")
        btn_out.clicked.connect(self._browse_output)
        grid.addWidget(btn_out, r, 2)
        r += 1

        grid.addWidget(QLabel("Block Size:"), r, 0)
        hbox = QHBoxLayout()
        self.slider_bs = QSlider(Qt.Orientation.Horizontal)
        self.slider_bs.setRange(3, 8)  # 8..256
        self.slider_bs.setValue(5)     # 32
        self.lbl_bs = QLabel("32")
        self.slider_bs.valueChanged.connect(lambda v: self.lbl_bs.setText(str(1 << v)))
        hbox.addWidget(self.slider_bs)
        hbox.addWidget(self.lbl_bs)
        grid.addLayout(hbox, r, 1, 1, 2)
        r += 1

        self.btn_scramble = QPushButton("Scramble & Save")
        self.btn_scramble.setStyleSheet("font-weight: bold; padding: 8px;")
        self.btn_scramble.clicked.connect(self._do_scramble)
        grid.addWidget(self.btn_scramble, r, 0, 1, 3)
        r += 1

        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.hide()
        grid.addWidget(self.prog, r, 0, 1, 3)
        r += 1

        grid.addWidget(QLabel("Seed:"), r, 0)
        self.edit_seed_out = QTextEdit()
        self.edit_seed_out.setReadOnly(True)
        self.edit_seed_out.setMaximumHeight(70)
        grid.addWidget(self.edit_seed_out, r, 1, 1, 2)
        r += 1

        grid.addWidget(QLabel("Preview:"), r, 0)
        self.lbl_preview = QLabel()
        self.lbl_preview.setMinimumSize(360, 200)
        self.lbl_preview.setStyleSheet("background-color: #1e1e1e;")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.lbl_preview, r, 1, 1, 2)

        grid.setColumnStretch(1, 1)

    def _setup_lens_tab(self, tab):
        grid = QGridLayout(tab)
        r = 0

        grid.addWidget(QLabel("Seed:"), r, 0)
        self.edit_seed_in = QTextEdit()
        self.edit_seed_in.setPlaceholderText("Paste seed here...")
        self.edit_seed_in.setMaximumHeight(70)
        self.edit_seed_in.textChanged.connect(self._validate_seed_input)
        grid.addWidget(self.edit_seed_in, r, 1, 1, 2)
        r += 1

        grid.addWidget(QLabel("Preset:"), r, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("Custom (manual resize)", "custom")
        self.combo_preset.addItem("100% Original", 1.0)
        self.combo_preset.addItem("150% Zoom", 1.5)
        self.combo_preset.addItem("200% Zoom", 2.0)
        self.combo_preset.addItem("Fit Screen", "fit")
        grid.addWidget(self.combo_preset, r, 1, 1, 2)
        r += 1

        grid.addWidget(QLabel("Size:"), r, 0)
        self.slider_lens_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_lens_size.setRange(10, 250)
        self.slider_lens_size.setValue(100)
        self.slider_lens_size.setEnabled(False)
        self.slider_lens_size.valueChanged.connect(self._on_lens_slider_changed)
        self.lbl_lens_size = QLabel("100% original")
        hsize = QHBoxLayout()
        hsize.addWidget(self.slider_lens_size)
        hsize.addWidget(self.lbl_lens_size)
        grid.addLayout(hsize, r, 1, 1, 2)
        r += 1

        hbtn = QHBoxLayout()
        self.btn_start = QPushButton("Start Lens")
        self.btn_stop = QPushButton("Stop Lens")
        self.btn_save_preset = QPushButton("Save current size")
        self.btn_stop.setEnabled(False)
        self.btn_save_preset.setEnabled(False)
        self.btn_start.clicked.connect(self._start_lens)
        self.btn_stop.clicked.connect(self._stop_lens)
        self.btn_save_preset.clicked.connect(self._save_current_preset)
        hbtn.addWidget(self.btn_start)
        hbtn.addWidget(self.btn_stop)
        hbtn.addWidget(self.btn_save_preset)
        hbtn.addStretch()
        grid.addLayout(hbtn, r, 0, 1, 3)
        r += 1

        self.lbl_lens_status = QLabel("Enter a valid seed to start.")
        self.lbl_lens_status.setStyleSheet("color: #888;")
        grid.addWidget(self.lbl_lens_status, r, 0, 1, 3)
        grid.setRowStretch(r, 1)

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
            self.edit_seed_in.setStyleSheet("border: 1px solid #0a0;")
        else:
            self.edit_seed_in.setStyleSheet("border: 1px solid #aaa;")

    def _do_scramble(self):
        in_path = self.edit_input.text()
        out_path = self.edit_output.text()
        if not in_path or not out_path:
            QMessageBox.warning(self, "Missing paths", "Select input and output files.")
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
            self.status_label.setText("Image scrambled.")
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
        self.status_label.setText("Video scrambled.")
        self.btn_scramble.setEnabled(True)
        self.prog.setValue(100)

    def _on_video_error(self, msg):
        QMessageBox.critical(self, "Error", msg)
        self.btn_scramble.setEnabled(True)
        self.prog.hide()

    def _show_preview(self, img_bgr):
        h, w = img_bgr.shape[:2]
        scale = min(360 / w, 200 / h)
        tw, th = max(1, round(w * scale)), max(1, round(h * scale))
        thumb = cv2.resize(img_bgr, (tw, th))
        rgb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888)
        self.lbl_preview.setPixmap(QPixmap.fromImage(qimg.copy()))

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
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_save_preset.setEnabled(True)
            self.lbl_lens_status.setText("Lens running. Drag to move, right-click for options.")
            self.lbl_lens_status.setStyleSheet("color: #0a0;")
            self.status_label.setText("Lens active.")
            logger.info("_start_lens: lens started")
        except Exception:
            logger.exception("_start_lens exception")
            raise

    def _stop_lens(self):
        try:
            self.lens.stop()
            self.slider_lens_size.setEnabled(False)
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_save_preset.setEnabled(False)
            self.lbl_lens_status.setText("Lens stopped.")
            self.lbl_lens_status.setStyleSheet("color: #888;")
            self.status_label.setText("Lens stopped.")
            logger.info("_stop_lens: lens stopped")
        except Exception:
            logger.exception("_stop_lens exception")

    def _save_current_preset(self):
        if not self.lens.is_visible():
            QMessageBox.information(self, "Info", "Start the lens first to save its size.")
            return
        w, h = self.lens.width(), self.lens.height()
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name.strip():
            display = f"{name.strip()} ({w}×{h})"
            self.combo_preset.addItem(display, (w, h))
            self.combo_preset.setCurrentIndex(self.combo_preset.count() - 1)

    def _on_lens_slider_changed(self, value):
        logger.info("slider value=%d", value)
        if not self.lens.is_visible():
            logger.info("slider: lens not visible")
            return
        if not self.lens.seed:
            logger.info("slider: no seed")
            return
        scale = value / 100.0
        logger.info("slider: set_size_from_scale scale=%.2f", scale)
        self.lens.set_size_from_scale(scale)
        self.lbl_lens_size.setText(f"{value}% original")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.wait(2000)
        self.lens.close()
        event.accept()
