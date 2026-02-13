import time

import dashscope
from dashscope.audio.asr import *
from typing import Callable

from loguru import logger

from model.event import TranslationEvent
from translator.base import ITranslator

class GummyTranslator(ITranslator):
    def __init__(self, api_key: str = None, target_language: str = "zh",source_language: str = "auto"):
        """Initialize GummyTranslator with dashscope configuration
        
        Args:
            api_key: Dashscope API key. If None, will use environment variable or config
            target_language: Target language for translation (default: Chinese)
        """
        if api_key is None:
            raise RuntimeError('empty api_key')
        else:
            dashscope.api_key = api_key
        
        self.target_language = target_language
        self.callback = None
        self.translator = None
        self.is_running = False

        # 创建回调实例
        self.recognition_callback = self.RecognitionCallback(self)
        self.translator = TranslationRecognizerRealtime(
            model="gummy-realtime-v1",
            format="pcm",
            sample_rate=16000,
            transcription_enabled=False,
            translation_enabled=True,
            source_language=source_language,
            translation_target_languages=[self.target_language],
            callback=self.recognition_callback,
        )
        
    class RecognitionCallback(TranslationRecognizerCallback):
        def __init__(self, parent):
            self.parent = parent
            
        def on_open(self) -> None:
            """Called when translation recognizer opens"""
            print("TranslationRecognizerCallback open.")
            # 不再创建音频流，由上游调用者管理

        def on_close(self) -> None:

            print("TranslationRecognizerCallback close.")
            self.parent.is_running = False
        def on_complete(self) -> None:
            print("TranslationRecognizerCallback complete.")
            self.parent.is_running = False
        def on_error(self, message) -> None:
            self.parent.is_running = False
            print(f"TranslationRecognizerCallback error {message}")

        def on_event(
            self, 
            request_id, 
            transcription_result: TranscriptionResult, 
            translation_result: TranslationResult, 
            usage, 
        ) -> None:
            """Handle translation and transcription results"""
            logger.debug(f'on_event: {request_id}, {usage}')
            
            # 处理翻译结果
            if translation_result is not None:
                english_translation = translation_result.get_translation(self.parent.target_language)
                if english_translation:
                    logger.debug(f'translate to english: {english_translation.text},id{english_translation.sentence_id}')
                    # 创建翻译事件并触发回调
                    if self.parent.callback:
                        event = TranslationEvent()
                        event.sentence_id = english_translation.sentence_id
                        event.sentence = english_translation.text
                        event.is_sentence_ended = english_translation.is_sentence_end
                        event.create_time=time.time()
                        self.parent.callback(event)
            
            # 处理转录结果
            if transcription_result is not None:
                print("sentence id:", transcription_result.sentence_id)
                print("transcription:", transcription_result.text)

    def send_data(self, data: bytes):
        if not self.is_running:
            self.start()
        if self.translator and self.is_running:
            logger.debug(f'data_len {len(data)},delay: {self.translator.get_last_package_delay()}')
            self.translator.send_audio_frame(data)

    def close(self):
        """Close the translator and cleanup resources"""
        self.is_running = False
        if self.translator:
            self.translator.stop()

    def register_callback(self, cb: Callable[[TranslationEvent], None]):
        """Register callback function for translation events
        
        Args:
            cb: Callback function that receives TranslationEvent
        """
        self.callback = cb

    def start(self):
        """Start the translation service"""
        if not self.is_running:
            self.is_running = True
            self.translator.start()
            print("翻译服务已启动，等待音频数据...")