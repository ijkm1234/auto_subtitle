from typing import Callable, Optional
from loguru import logger
from model.event import  TranslationEvent

class ITranslator():
    def send_data(self, data: bytes):...
    def close(self):...
    def register_callback(self, cb :Callable[[TranslationEvent],None]):...

def create_translator() -> Optional[ITranslator]:
    """Factory function to create translator instance based on configuration
    
    Args:
        config_data: Configuration dictionary, if None will load from config.yaml
        
    Returns:
        ITranslator instance or None if creation fails
    """
    from config import Config

    config = Config()

    # Get translator configuration using Config's get method for nested access
    model_name = config.get('translator.model', 'gummy')  # Default to gummy for backward compatibility
    
    # Common parameters - use Config's get method for nested keys
    api_key = config.get('translator.api_key')  # Will be None if not set, letting each translator handle it
    target_language = config.get('translator.target_language', 'zh')
    source_language = config.get('translator.source_language', 'auto')
    
    try:
        if model_name == 'qwen':
            from translator.qwen_translator import QwenTranslator
            return QwenTranslator(
                api_key=api_key,
                target_language=target_language,
                source_language=source_language
            )
        elif model_name == 'gummy':
            from translator.gummy_translator import GummyTranslator
            return GummyTranslator(
                api_key=api_key,
                target_language=target_language,
                source_language=source_language
            )
        else:
            logger.warning(f"Unknown translator model: {model_name}, falling back to gummy")
            from translator.gummy_translator import GummyTranslator
            return GummyTranslator(
                api_key=api_key,
                target_language=target_language,
                source_language=source_language
            )
    except Exception as e:
        logger.error(f"Failed to create translator {model_name}: {e}")
        raise
