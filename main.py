#!/usr/bin/env python3
import sys
import os
import ctypes
import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = os.environ.get("RTM_LOG_FILE", "rtm_debug.log")
LOG_LEVEL = getattr(logging, os.environ.get("RTM_LOG_LEVEL", "DEBUG").upper(), logging.DEBUG)

handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.basicConfig(level=LOG_LEVEL, handlers=[handler], force=True)

# Win32 lens needs physical pixels. Set process-wide DPI awareness before
# any window creation (Qt or Win32).
ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

from PyQt6.QtWidgets import QApplication  # noqa: E402
from main_window import MainWindow  # noqa: E402

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RealTimeMix")
    app.setOrganizationName("RealTimeMix")

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
