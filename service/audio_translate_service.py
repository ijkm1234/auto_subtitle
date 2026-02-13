import sys
import threading
import time
import wave
from typing import Protocol, Callable

import numpy as np
import pyaudiowpatch as pyaudio
from loguru import logger

from model.event import TranslationEvent
from translator.base import ITranslator, create_translator

CHUNK_SIZE=9600

class AudioTranslateService:
    def __init__(self):
        self.stream = None
        self.audio_service = pyaudio.PyAudio()
        self.stopped = threading.Event()
        self.translator=None
        self.input_channels = 2
        self.input_rate = 48000
        self.callback=None
        self.continuous_silence_cnt = 0
        self.continuous_silence_cnt_threshold = 10

    def register_callback(self, cb: Callable[[TranslationEvent], None]):
        self.callback = cb

    def start(self):
        try:
            # Get default WASAPI info
            wasapi_info = self.audio_service.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            logger.warning("Looks like WASAPI is not available on the system. Exiting...")
            raise
        default_speakers = self.audio_service.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not default_speakers["isLoopbackDevice"]:
            for loopback in self.audio_service.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                logger.warning("Looks like WASAPI is not available on the system. Exiting...")
                return
        self.stopped.clear()
        self.translator = create_translator()
        if self.translator is None:
            logger.error("Failed to create translator instance")
            raise RuntimeError("Failed to create translator")
        self.translator.register_callback(self.callback)
        self.input_rate = default_speakers["defaultSampleRate"]
        self.input_channels = default_speakers["maxInputChannels"]
        self.stream = self.audio_service.open(
            format=pyaudio.paInt16,
            channels=self.input_channels,
            rate=int(self.input_rate),
            input=True,
            input_device_index=default_speakers["index"],
            stream_callback=self.translate,
            frames_per_buffer=CHUNK_SIZE,
        )

    def translate(self, data, frame_count, time_info, status):
        data = self.resample_audio(data, input_channels=self.input_channels, input_rate=self.input_rate)
        
        if self.is_silence(data):
            if self.continuous_silence_cnt<self.continuous_silence_cnt_threshold:
                self.continuous_silence_cnt+=1
        else:
            self.continuous_silence_cnt=0
        if self.continuous_silence_cnt<self.continuous_silence_cnt_threshold:
            self.translator.send_data(data)
        return (data, pyaudio.paContinue)

    def stop(self):
        self.stopped.set()
        if self.stream:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
        self.translator.close()
        logger.info('===stop===')

    def is_silence(self, data: bytes, threshold: float = 0.001) -> bool:
        """
        判断音频数据是否为静音
        
        Args:
            data: 音频数据字节
            threshold: 静音阈值 (0.0-1.0)，默认0.01
            
        Returns:
            bool: 如果音频为静音返回True，否则返回False
        """
        # 将字节数据转换为numpy数组
        audio_data = np.frombuffer(data, dtype=np.int16)
        
        # 计算音频数据的均方根 (RMS)
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        
        # 将RMS值归一化到0-1范围
        # int16的最大值为32767，所以除以32767进行归一化
        normalized_rms = rms / 32767.0
        
        # 如果归一化后的RMS值小于阈值，认为是静音
        return normalized_rms < threshold

    def resample_audio(self, data: bytes, input_channels: int, input_rate: int, output_rate: int = 16000) -> bytes:
        audio_data = np.frombuffer(data, dtype=np.int16)

        # Reshape based on channels
        if input_channels > 1:
            audio_data = audio_data.reshape(-1, input_channels)
            # Convert to mono by averaging channels
            audio_data = audio_data.mean(axis=1).astype(np.int16)

        # Calculate resampling ratio
        if input_rate != output_rate:
            # Calculate new length
            old_length = len(audio_data)
            new_length = int(old_length * output_rate / input_rate)

            # Create time indices for resampling
            old_indices = np.arange(old_length)
            new_indices = np.linspace(0, old_length - 1, new_length)

            # Linear interpolation for resampling
            resampled = np.interp(new_indices, old_indices, audio_data).astype(np.int16)
        else:
            resampled = audio_data

        return resampled.tobytes()