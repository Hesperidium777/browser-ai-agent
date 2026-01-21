from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .base_agent import BaseAgent, AgentState
from models.llm_client import StructuredLLMClient

@dataclass
class PlanStep:
    """Шаг плана"""
    step_number: int
    action: str
    description: str
    expected_outcome: str
    is_completed: bool = False

class PlanningAgent(BaseAgent):
    """Агент планирования для разбивки сложных задач"""
    
    def __init__(self, llm_client: StructuredLLMClient):
        super().__init__(name="PlanningAgent")
        self.llm = llm_client
        self.current_plan: List[PlanStep] = []
        self.current_step_index: int = 0
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка входных данных и создание плана"""
        
        task = input_data.get("task", "")
        current_state = input_data.get("current_state", {})
        
        if not task:
            return {
                "success": False,
                "error": "No task provided",
                "message": "Задача не предоставлена"
            }
        
        # Создаем план
        plan = self.create_plan(task, current_state)
        
        if not plan:
            return {
                "success": False,
                "error": "Failed to create plan",
                "message": "Не удалось создать план"
            }
        
        self.current_plan = plan
        self.current_step_index = 0
        self.state.current_task = task
        
        return {
            "success": True,
            "plan": [step.__dict__ for step in plan],
            "message": f"План создан, шагов: {len(plan)}"
        }
    
    def create_plan(self, task: str, current_state: Dict[str, Any]) -> List[PlanStep]:
        """Создание плана выполнения задачи"""
        
        prompt = f"""
Создай пошаговый план для выполнения следующей задачи в веб-браузере.

Задача: {task}

Текущее состояние:
URL: {current_state.get('url', 'неизвестен')}
Заголовок страницы: {current_state.get('title', 'неизвестен')}
Тип страницы: {current_state.get('page_type', 'general')}

Инструкции по созданию плана:
1. Разбей задачу на конкретные шаги
2. Каждый шаг должен быть выполнимым действием (клик, ввод текста, навигация и т.д.)
3. Учитывай текущее состояние страницы
4. Предусмотри возможные ошибки и альтернативные пути
5. План должен быть адаптивным - если шаг не удастся, нужно иметь запасной вариант

Создай план в формате JSON с шагами. Каждый шаг должен содержать:
- step_number: номер шага
- action: тип действия (navigate, click, type, etc.)
- description: описание что делать
- expected_outcome: что должно произойти после шага
        """
        
        try:
            response_format = {
                "plan_name": "string",
                "steps": [
                    {
                        "step_number": "integer",
                        "action": "string",
                        "description": "string", 
                        "expected_outcome": "string"
                    }
                ]
            }
            
            result = self.llm.generate_structured(
                prompt=prompt,
                response_format=response_format,
                system_prompt="Ты эксперт по планированию веб-автоматизации."
            )
            
            steps = []
            for step_data in result.get("steps", []):
                step = PlanStep(
                    step_number=step_data.get("step_number", 0),
                    action=step_data.get("action", ""),
                    description=step_data.get("description", ""),
                    expected_outcome=step_data.get("expected_outcome", "")
                )
                steps.append(step)
            
            return steps
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании плана: {e}")
            # Возвращаем простой план по умолчанию
            return self._create_default_plan(task)
    
    def _create_default_plan(self, task: str) -> List[PlanStep]:
        """Создание плана по умолчанию"""
        steps = [
            PlanStep(
                step_number=1,
                action="navigate",
                description="Открыть поисковую систему",
                expected_outcome="Страница поиска открыта"
            ),
            PlanStep(
                step_number=2,
                action="type",
                description="Ввести запрос связанный с задачей",
                expected_outcome="Заполнено поле поиска"
            ),
            PlanStep(
                step_number=3,
                action="press_key",
                description="Нажать Enter для поиска",
                expected_outcome="Результаты поиска отображены"
            ),
            PlanStep(
                step_number=4,
                action="click",
                description="Кликнуть на релевантный результат",
                expected_outcome="Переход на нужную страницу"
            ),
            PlanStep(
                step_number=5,
                action="analyze",
                description="Проанализировать открывшуюся страницу",
                expected_outcome="Определены дальнейшие действия"
            )
        ]
        return steps
    
    def get_next_step(self) -> Optional[PlanStep]:
        """Получение следующего шага"""
        if self.current_step_index < len(self.current_plan):
            return self.current_plan[self.current_step_index]
        return None
    
    def complete_current_step(self):
        """Отметка текущего шага как выполненного"""
        if self.current_step_index < len(self.current_plan):
            self.current_plan[self.current_step_index].is_completed = True
            self.current_step_index += 1
    
    def adjust_plan(self, feedback: Dict[str, Any]):
        """Корректировка плана на основе обратной связи"""
        
        if not feedback.get("needs_adjustment"):
            return
        
        # Если план нужно скорректировать, перепланируем оставшиеся шаги
        remaining_steps = self.current_plan[self.current_step_index:]
        
        if remaining_steps:
            # Анализируем почему текущий подход не работает
            analysis = feedback.get("analysis", "")
            
            # Создаем новый план для оставшейся части
            new_steps = self._replan_remaining(analysis, remaining_steps)
            
            # Заменяем оставшиеся шаги
            self.current_plan = self.current_plan[:self.current_step_index] + new_steps
    
    def _replan_remaining(self, analysis: str, old_steps: List[PlanStep]) -> List[PlanStep]:
        """Перепланирование оставшихся шагов"""
        # Простая эвристика: добавляем шаг анализа и пробуем альтернативный подход
        new_steps = [
            PlanStep(
                step_number=self.current_step_index + 1,
                action="analyze",
                description="Проанализировать причину неудачи и найти альтернативный путь",
                expected_outcome="Определен новый подход"
            )
        ]
        
        # Модифицируем старые шаги с учетом анализа
        for i, step in enumerate(old_steps, start=2):
            new_step = PlanStep(
                step_number=self.current_step_index + i,
                action=step.action,
                description=f"Альтернативный подход: {step.description}",
                expected_outcome=step.expected_outcome
            )
            new_steps.append(new_step)
        
        return new_steps
    
    def decide_next_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Принятие решения о следующем действии"""
        
        next_step = self.get_next_step()
        
        if not next_step:
            return {
                "action": "complete",
                "description": "Задача завершена",
                "parameters": {}
            }
        
        return {
            "action": next_step.action,
            "description": next_step.description,
            "parameters": {"step_info": next_step.__dict__}
        }