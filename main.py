import sys
import time
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from view.main_window import MainWindow
from loguru import logger

if __name__ == '__main__':
    log_dir = './logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log")
    logger.add(log_file, rotation="00:00", retention="7 days", encoding="utf-8", level="INFO")
    app = QApplication(sys.argv)
    app.setApplicationName('Auto Subtitle')
    icon_path='icon/icon.ico'
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    main_window=MainWindow()
    main_window.show()
    main_window.raise_()
    app.exec()