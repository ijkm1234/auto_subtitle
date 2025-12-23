import base64
import json
import os
import threading
import time
from typing import Callable

import websocket
from loguru import logger

from model.event import TranslationEvent
from translator.base import ITranslator
from config import Config


class QwenTranslator(ITranslator):
    def __init__(self, api_key: str = None, target_language: str = "zh", source_language: str = "auto"):
        """Initialize QwenTranslator with Qwen3 live translate flash realtime model
        
        Args:
            api_key: Dashscope API key. If None, will use environment variable or config
            target_language: Target language for translation (default: Chinese)
            source_language: Source language for input audio (default: English)
        """
        # 优先级：构造函数参数 > 配置文件 > 环境变量
        if api_key is None:
            raise RuntimeError('empty api_key')
        
        self.api_key = api_key
        self.target_language = target_language
        self.source_language = source_language
        self.callback = None
        self.is_running = False
        self.ws = None
        self.ws_thread = None
        self.startup_lock = threading.Lock()
        self.current_item_id = None
        self.current_sentence = ""
        self.sentence_id_counter = 0  # 自增的sentence_id计数器
        
        # WebSocket配置
        self.ws_url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-livetranslate-flash-realtime"
        
        # 会话配置 - 只输出文本
        self.session_config = {
            "modalities": ["text"],  # 只输出文本，不输出音频
            "input_audio_format": "pcm16",
            "translation": {
                "language": self.target_language
            }
        }
        if source_language!="auto":
            self.session_config["input_audio_transcription"] = {
                "language": self.source_language
            }

    def _connect_ws(self):
        """Establish WebSocket connection"""
        try:
            headers = [
                f"Authorization: Bearer {self.api_key}"
            ]
            
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            logger.info("Connecting to Qwen3 live translate service...")
            self.ws.run_forever()
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            self.is_running = False

    def _on_open(self, ws):
        """Handle WebSocket connection opened"""
        logger.info("WebSocket connection established")
        self.is_running = True
        
        # 发送会话配置
        session_update = {
            "event_id": f"event_{int(time.time() * 1000)}",
            "type": "session.update",
            "session": self.session_config
        }
        
        ws.send(json.dumps(session_update))
        logger.debug("Sent session.update event")

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            logger.debug(f"Received event: {data.get('type', 'unknown')}")
            
            event_type = data.get('type')
            
            if event_type == 'session.created':
                logger.info("Session created successfully")
                
            elif event_type == 'session.updated':
                logger.info("Session updated successfully")
                
            elif event_type == 'response.text.text':
                # 处理句子中的部分翻译结果（未完成）
                self._handle_text_partial_response(data)
                
            elif event_type == 'response.text.done':
                # 处理完整的文本翻译结果
                self._handle_text_response(data)
                
            elif event_type == 'error':
                logger.error(f"Server error: {data.get('error', {})}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _handle_text_partial_response(self, data):
        """Handle partial text translation response (sentence not complete)"""
        logger.debug(f"Partial text response: {data}")
        
        # 获取item_id和文本内容
        item_id = None
        text = ""

        if 'item_id' in data:
            item_id = data['item_id']
        if 'text' in data:
            text = data['text']
        if 'stash' in data:
            text+=data['stash']
        
        if item_id and text:
            # 如果item_id发生变化，递增sentence_id
            if self.current_item_id != item_id:
                self.sentence_id_counter += 1
                self.current_item_id = item_id
            
            self.current_sentence = text
            
            # 创建翻译事件（未完成状态）
            self._create_translation_event(
                sentence_id=self.sentence_id_counter,
                text=text,
                is_sentence_end=False
            )

    def _handle_text_response(self, data):
        """Handle complete text translation response"""
        logger.debug(f"Complete text response: {data}")
        
        # 获取item_id和文本内容
        item_id = None
        text = ""
        

        if 'item_id' in data:
            item_id = data['item_id']
        if 'text' in data:
            text = data['text']
        
        if item_id and text:
            # 如果item_id发生变化，递增sentence_id
            if self.current_item_id != item_id:
                self.sentence_id_counter += 1
                self.current_item_id = item_id
            
            self.current_sentence = text
            
            # 创建翻译事件（完成状态）
            self._create_translation_event(
                sentence_id=self.sentence_id_counter,
                text=text,
                is_sentence_end=True
            )

    def _create_translation_event(self, sentence_id: int, text: str, is_sentence_end: bool):
        """Create and trigger translation event"""
        if self.callback:
            event = TranslationEvent()
            event.sentence_id = sentence_id
            event.sentence = text
            event.is_sentence_ended = is_sentence_end
            event.create_time = time.time()
            self.callback(event)
            logger.debug(f"Translation event: {text}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
        self.is_running = False

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed"""
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.is_running = False

    def send_data(self, data: bytes):
        """Send audio data to the translation service
        
        Args:
            data: PCM16 audio data bytes
        """
        if not self.is_running:
            self.start()
            
        if self.ws and self.is_running:
            try:
                # Base64 encode audio data
                audio_base64 = base64.b64encode(data).decode('utf-8')
                
                # 创建音频输入事件
                audio_event = {
                    "event_id": f"event_{int(time.time() * 1000)}",
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }
                
                self.ws.send(json.dumps(audio_event))
                logger.debug(f"Sent audio data: {len(data)} bytes")
                
            except Exception as e:
                logger.error(f"Failed to send audio data: {e}")

    def close(self):
        """Close the translator and cleanup resources"""
        logger.info("Closing QwenTranslator...")
        self.is_running = False
        
        # 重置当前句子状态
        self.current_item_id = None
        self.current_sentence = ""
        self.sentence_id_counter = 0
        
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)

    def register_callback(self, cb: Callable[[TranslationEvent], None]):
        """Register callback function for translation events
        
        Args:
            cb: Callback function that receives TranslationEvent
        """
        self.callback = cb

    def start(self):
        """Start the translation service with locking mechanism"""
        with self.startup_lock:
            if not self.is_running:
                logger.info("Starting QwenTranslator service...")
                
                # 重置状态
                self.current_item_id = None
                self.current_sentence = ""
                self.sentence_id_counter = 0
                
                # 启动WebSocket连接线程
                self.ws_thread = threading.Thread(target=self._connect_ws, daemon=True)
                self.ws_thread.start()
                
                # 等待连接建立
                timeout = 10
                start_time = time.time()
                while not self.is_running and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                
                if self.is_running:
                    logger.info("QwenTranslator service started successfully")
                else:
                    logger.error("Failed to start QwenTranslator service")
                    raise RuntimeError("Failed to establish WebSocket connection")