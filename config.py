import os
from dataclasses import dataclass

@dataclass
class Config:
    """Конфигурация агента"""
    
    # Настройки Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "llama3.2:3b"
    
    # Настройки браузера
    BROWSER_TYPE: str = "chrome"
    HEADLESS: bool = False
    WINDOW_WIDTH: int = 1400
    WINDOW_HEIGHT: int = 900
    
    # Настройки агента
    MAX_STEPS: int = 8
    THINKING_DEPTH: str = "normal"
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Загрузка конфигурации из переменных окружения"""
        return cls(
            OLLAMA_BASE_URL=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            MODEL_NAME=os.getenv("MODEL_NAME", "llama3.2:3b"),
            HEADLESS=os.getenv("HEADLESS", "False").lower() == "true",
        )