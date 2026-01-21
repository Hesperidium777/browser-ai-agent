from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    """Состояние агента"""
    is_active: bool = False
    current_task: Optional[str] = None
    steps_completed: int = 0
    last_action: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class BaseAgent(ABC):
    """Базовый класс агента"""
    
    def __init__(self, name: str = "AI Agent"):
        self.name = name
        self.state = AgentState()
        self.logger = logging.getLogger(f"agent.{name}")
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Основной метод обработки"""
        pass
    
    @abstractmethod
    def decide_next_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Принятие решения о следующем действии"""
        pass
    
    def start(self):
        """Запуск агента"""
        self.state.is_active = True
        self.logger.info(f"Агент {self.name} запущен")
    
    def stop(self):
        """Остановка агента"""
        self.state.is_active = False
        self.logger.info(f"Агент {self.name} остановлен")
    
    def reset(self):
        """Сброс состояния агента"""
        self.state = AgentState()
        self.logger.info(f"Агент {self.name} сброшен")
    
    def log_action(self, action: Dict[str, Any], result: Dict[str, Any]):
        """Логирование действия"""
        self.state.last_action = {
            "action": action,
            "result": result,
            "timestamp": self._get_timestamp()
        }
        
        self.state.steps_completed += 1
        
        if not result.get("success"):
            self.state.errors.append(result.get("error", "Unknown error"))
            self.logger.warning(f"Действие неудачно: {result.get('message')}")
        else:
            self.logger.info(f"Действие успешно: {result.get('message')}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса агента"""
        return {
            "name": self.name,
            "is_active": self.state.is_active,
            "current_task": self.state.current_task,
            "steps_completed": self.state.steps_completed,
            "error_count": len(self.state.errors),
            "last_error": self.state.errors[-1] if self.state.errors else None
        }
    
    def _get_timestamp(self) -> str:
        """Получение временной метки"""
        from datetime import datetime
        return datetime.now().isoformat()