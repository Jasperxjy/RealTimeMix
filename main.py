#!/usr/bin/env python3
import sys
import os
import ctypes
import logging

logging.basicConfig(
    filename='rtm_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    force=True
)

# Win32 lens needs physical pixels. Set process-wide DPI awareness before
# any window creation (Qt or Win32).
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RealTimeMix")
    app.setOrganizationName("RealTimeMix")

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
