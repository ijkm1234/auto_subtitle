import os
import yaml
import threading
import time
from typing import Dict, Any


class Config:
    _instance = None
    _lock = threading.Lock()
    _last_modified = 0
    _config_data: Dict[str, Any] = {}
    _timer = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Config, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.config_file = os.path.join(os.getcwd(), '.config.yaml')
                    self._load_config()
                    self._start_periodic_reload()
                    self._initialized = True

    def _load_config(self):
        """从.config.yaml文件加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading config file: {e}")
                self._config_data = {}
        else:
            # 如果配置文件不存在，初始化为空字典
            self._config_data = {}

    def _periodic_reload(self):
        """定期重新加载配置文件"""
        current_time = time.time()
        if os.path.exists(self.config_file):
            file_modified = os.path.getmtime(self.config_file)
            if file_modified > self._last_modified:
                self._load_config()
                self._last_modified = file_modified
        else:
            # 如果文件不存在，清空配置
            self._config_data = {}

        # 设置下一次检查
        self._timer = threading.Timer(30.0, self._periodic_reload)
        self._timer.daemon = True
        self._timer.start()

    def _start_periodic_reload(self):
        """启动定期重新加载"""
        self._timer = threading.Timer(30.0, self._periodic_reload)
        self._timer.daemon = True
        self._timer.start()

    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self._config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config_data.copy()

    def reload(self):
        """手动重新加载配置文件"""
        self._load_config()

    def update_config(self, key: str, value: Any) -> bool:
        """更新配置文件中的设置
        
        Args:
            key: 配置的键，支持点分隔符（如 'translator.source_language'）
            value: 要设置的值
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            # 读取当前配置
            config_data = self._config_data.copy()
            
            # 更新配置值
            keys = key.split('.')
            current = config_data
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
            
            # 写回配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            # 更新内存中的配置
            self._config_data = config_data
            
            print(f'Updated config: {key} = {value}')
            return True
            
        except Exception as e:
            print(f'Failed to update config: {e}')
            return False

    def __del__(self):
        if self._timer:
            self._timer.cancel()