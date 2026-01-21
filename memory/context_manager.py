from typing import List, Dict, Any, Deque, Optional
from collections import deque
import json
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ActionRecord:
    """Запись о выполненном действии"""
    timestamp: str
    action_type: str
    action_description: str
    result: Dict[str, Any]
    page_state: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_text(self) -> str:
        """Преобразование в текстовое описание"""
        result_status = "успешно" if self.result.get("success") else "ошибка"
        result_msg = self.result.get("message", "")
        
        return f"[{self.timestamp}] {self.action_type}: {self.action_description} - {result_status} ({result_msg})"

@dataclass
class TaskContext:
    """Контекст задачи"""
    task_description: str
    start_time: str
    current_step: int = 0
    goal: str = ""
    constraints: List[str] = None
    progress: str = ""
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []

class ContextManager:
    """Менеджер контекста для агента"""
    
    def __init__(self, max_history: int = 100, max_tokens: int = 4000):
        self.action_history: Deque[ActionRecord] = deque(maxlen=max_history)
        self.current_task: Optional[TaskContext] = None
        self.max_tokens = max_tokens
        self.system_context = []
        
    def start_new_task(self, task_description: str, goal: str = "", constraints: List[str] = None) -> TaskContext:
        """Начало новой задачи"""
        self.current_task = TaskContext(
            task_description=task_description,
            start_time=datetime.now().isoformat(),
            goal=goal,
            constraints=constraints or []
        )
        self.action_history.clear()
        return self.current_task
    
    def add_action(self, 
                   action_type: str, 
                   action_description: str, 
                   result: Dict[str, Any],
                   page_state: Dict[str, Any]) -> ActionRecord:
        """Добавление записи о действии"""
        record = ActionRecord(
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            action_description=action_description,
            result=result,
            page_state=page_state
        )
        
        self.action_history.append(record)
        
        if self.current_task:
            self.current_task.current_step += 1
            
            # Обновляем прогресс на основе последних действий
            if result.get("success"):
                self.current_task.progress = f"Шаг {self.current_task.current_step} выполнен: {action_description}"
            else:
                self.current_task.progress = f"Шаг {self.current_task.current_step} не удался: {action_description}"
        
        return record
    
    def get_recent_actions(self, count: int = 10) -> List[ActionRecord]:
        """Получение последних действий"""
        return list(self.action_history)[-count:]
    
    def get_action_summary(self) -> str:
        """Получение сводки действий"""
        if not self.action_history:
            return "История действий пуста"
        
        summary = []
        for record in list(self.action_history)[-5:]:  # Последние 5 действий
            summary.append(record.to_text())
        
        return "\n".join(summary)
    
    def get_task_context(self) -> str:
        """Получение контекста задачи в текстовом виде"""
        if not self.current_task:
            return "Нет активной задачи"
        
        context = f"""
Задача: {self.current_task.task_description}
Цель: {self.current_task.goal}
Текущий шаг: {self.current_task.current_step}
Прогресс: {self.current_task.progress}
Ограничения: {', '.join(self.current_task.constraints)}
        """.strip()
        
        return context
    
    def get_full_context(self, current_page_state: Dict[str, Any]) -> str:
        """Получение полного контекста для ИИ"""
        context_parts = []
        
        # Контекст задачи
        if self.current_task:
            context_parts.append("=== ТЕКУЩАЯ ЗАДАЧА ===")
            context_parts.append(self.get_task_context())
            context_parts.append("")
        
        # История действий
        context_parts.append("=== ИСТОРИЯ ДЕЙСТВИЙ ===")
        context_parts.append(self.get_action_summary())
        context_parts.append("")
        
        # Текущее состояние страницы
        context_parts.append("=== ТЕКУЩАЯ СТРАНИЦА ===")
        context_parts.append(f"URL: {current_page_state.get('url', 'unknown')}")
        context_parts.append(f"Заголовок: {current_page_state.get('title', 'unknown')}")
        context_parts.append(f"Тип страницы: {current_page_state.get('page_type', 'general')}")
        context_parts.append("")
        
        # Видимый текст
        context_parts.append("=== ВИДИМЫЙ ТЕКСТ ===")
        context_parts.append(current_page_state.get('visible_text_preview', 'Нет текста'))
        context_parts.append("")
        
        # Доступные элементы
        context_parts.append("=== ДОСТУПНЫЕ ЭЛЕМЕНТЫ ===")
        elements = current_page_state.get('elements', [])
        if elements:
            for i, elem in enumerate(elements[:15], 1):  # Ограничиваем количество
                context_parts.append(f"{i}. {elem}")
            
            if len(elements) > 15:
                context_parts.append(f"... и еще {len(elements) - 15} элементов")
        else:
            context_parts.append("Элементы не найдены")
        
        return "\n".join(context_parts)
    
    def add_system_context(self, context: str):
        """Добавление системного контекста"""
        self.system_context.append(context)
    
    def get_system_context(self) -> str:
        """Получение системного контекста"""
        return "\n".join(self.system_context)
    
    def save_context(self, filepath: str):
        """Сохранение контекста в файл"""
        data = {
            "current_task": asdict(self.current_task) if self.current_task else None,
            "action_history": [record.to_dict() for record in self.action_history],
            "system_context": self.system_context
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_context(self, filepath: str):
        """Загрузка контекста из файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data["current_task"]:
                self.current_task = TaskContext(**data["current_task"])
            
            self.action_history = deque(
                [ActionRecord(**record) for record in data["action_history"]],
                maxlen=self.action_history.maxlen
            )
            
            self.system_context = data["system_context"]
            
        except Exception as e:
            print(f"Ошибка при загрузке контекста: {e}")