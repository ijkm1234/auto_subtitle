import threading
import time
import os

from PyQt6.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QHBoxLayout, QComboBox, QLabel, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QTimer
from loguru import logger

from service.audio_translate_service import AudioTranslateService
from model.event import TranslationEvent
from .subtitle_rect import SubtitleRect
from config import Config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.translate_service = AudioTranslateService()
        self.translate_service.register_callback(self.on_translate_event)
        self.is_translating = False
        self.setup_ui()
        font_size = self.config.get('subtitle.font_size', 24)
        screen_width, screen_height = self.get_real_screen_size()
        subtitle_x = screen_width // 2
        subtitle_y = screen_height // 100 * 85
        self.subtitle_rect=SubtitleRect(font_size,subtitle_x,subtitle_y)
        self.subtitle_data=SubTitleData()
        self.display_timer = QTimer(self)
        self.display_timer.timeout.connect(self.update_display)

    def setup_ui(self):
        # 创建中央widget和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建播放/暂停按钮
        self.play_button = QPushButton()
        self.play_button.setFixedSize(15, 15)  # 临时大小，稍后会根据窗口高度调整
        self.play_button.setIconSize(self.play_button.size())
        self.play_button.setIcon(QIcon("icon/play.png"))
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 50);
                border-radius: 5px;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 100);
                border-radius: 5px;
            }
        """)
        self.play_button.clicked.connect(self.toggle_translate)

        # 创建语言选择器
        self.source_lang_label = QLabel("源语言:")
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["auto","en", "zh", "ja", "ko", "fr", "de", "es", "ru"])
        self.source_lang_combo.setFixedHeight(20)
        self.source_lang_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 100);
                border: 1px solid rgba(0, 0, 0, 50);
                border-radius: 3px;
                padding: 2px;
                font-size: 10px;
            }
            QComboBox::drop-down {
                border: none;
                width: 15px;
            }
        """)
        
        self.target_lang_label = QLabel("目标语言:")
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["zh", "en"])
        self.target_lang_combo.setFixedHeight(20)
        self.target_lang_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 100);
                border: 1px solid rgba(0, 0, 0, 50);
                border-radius: 3px;
                padding: 2px;
                font-size: 10px;
            }
            QComboBox::drop-down {
                border: none;
                width: 15px;
            }
        """)

        # 加载当前配置
        self.load_language_config()
        
        # 连接信号
        self.source_lang_combo.currentTextChanged.connect(self.on_source_lang_changed)
        self.target_lang_combo.currentTextChanged.connect(self.on_target_lang_changed)

        # 将控件添加到布局
        layout.addWidget(self.play_button)
        layout.addStretch()
        layout.addWidget(self.source_lang_label)
        layout.addWidget(self.source_lang_combo)
        layout.addWidget(self.target_lang_label)
        layout.addWidget(self.target_lang_combo)

        screen_size = QApplication.primaryScreen().size()
        window_width = screen_size.width() // 5
        window_height = screen_size.height() // 10
        self.setGeometry((screen_size.width()-window_width)//2, (screen_size.height()-window_height)//2, window_width, window_height)
        
        # 调整按钮大小
        self.resizeEvent = self.on_window_resized

    def on_window_resized(self, event):
        # 根据窗口高度调整按钮大小
        button_size = int(self.height() * 0.75)
        self.play_button.setFixedSize(button_size, button_size)
        self.play_button.setIconSize(self.play_button.size())

    def start_translate(self):
        try:
            self.translate_service.start()
            self.is_translating = True
            self.play_button.setIcon(QIcon("icon/pause.png"))
            self.display_timer.start(200)
        except Exception as e:
            logger.exception(f"启动翻译失败: {e}")
            QMessageBox.critical(self, "启动翻译失败", str(e))

    def stop_translate(self):
        try:
            self.translate_service.stop()
            self.is_translating = False
            self.play_button.setIcon(QIcon("icon/play.png"))
            self.subtitle_rect.clean()
            self.subtitle_data.clean()
            self.display_timer.stop()
        except Exception as e:
            logger.exception(f"停止翻译失败: {e}")
            QMessageBox.critical(self, "停止翻译失败", str(e))

    def toggle_translate(self):
        if self.is_translating:
            self.stop_translate()
        else:
            self.start_translate()

    def on_translate_event(self, event: TranslationEvent):
        logger.debug('translate_event is {}'.format(event))
        self.subtitle_data.set(event.sentence_id,event.sentence)
        if event.is_sentence_ended:
            suspend_time = self.config.get('subtitle.suspend_time', 5)
            self.subtitle_data.delay_del(event.sentence_id, suspend_time)

    def update_display(self):
        texts=self.subtitle_data.get_list()
        if len(texts)>0:
            self.subtitle_rect.draw(texts)

    def get_real_screen_size(self):
        size=QApplication.primaryScreen().size()
        size=size*QApplication.primaryScreen().devicePixelRatio()
        return int(size.width()), int(size.height())

    def load_language_config(self):
        """加载语言配置并设置下拉框"""
        source_lang = self.config.get('translator.source_language', 'auto')
        target_lang = self.config.get('translator.target_language', 'zh')
        
        # 设置当前选中的语言
        source_index = self.source_lang_combo.findText(source_lang)
        if source_index >= 0:
            self.source_lang_combo.setCurrentIndex(source_index)
            
        target_index = self.target_lang_combo.findText(target_lang)
        if target_index >= 0:
            self.target_lang_combo.setCurrentIndex(target_index)

    def on_source_lang_changed(self, language):
        """源语言改变时更新配置"""
        self.config.update_config('translator.source_language', language)

    def on_target_lang_changed(self, language):
        """目标语言改变时更新配置"""
        self.config.update_config('translator.target_language', language)


class SubTitleData():
    def __init__(self):
        self.data={}
        self.lock=threading.Lock()

    def set(self,id,text):
        with self.lock:
            if id in self.data and self.data[id]==text:
                return False
            self.data[id]=text
            return True

    def get_list(self):
        with self.lock:
            sorted_keys = sorted(self.data.keys())
            return [self.data[key] for key in sorted_keys]

    def delay_del(self, id, delay_sec):
        def delayed_delete():
            with self.lock:
                if id in self.data:
                    del self.data[id]

        timer = threading.Timer(delay_sec, delayed_delete)
        timer.start()
    def clean(self):
        with self.lock:
            self.data.clear()
