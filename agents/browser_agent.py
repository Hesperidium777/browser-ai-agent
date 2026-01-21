from typing import Dict, Any, Optional, List
import json
import time
from .base_agent import BaseAgent
from models.llm_client import StructuredLLMClient
from memory.context_manager import ContextManager
from memory.episodic_memory import EpisodicMemory
from patterns.reflection_pattern import ReflectionPattern
from tools.action_tools import ActionTools, Action

class BrowserAgent(BaseAgent):
    """Основной AI агент для управления браузером"""
    
    def __init__(self, 
                 llm_client: StructuredLLMClient,
                 browser_controller,
                 config):
        
        super().__init__(name="BrowserAI")
        
        self.llm = llm_client
        self.browser = browser_controller
        self.config = config
        
        # Инициализация компонентов
        self.context_manager = ContextManager()
        self.episodic_memory = EpisodicMemory()
        self.reflection_pattern = ReflectionPattern(llm_client)
        
        # Состояние выполнения
        self.max_steps = config.MAX_STEPS
        self.current_step = 0
        self.is_task_complete = False
        self.needs_human_input = False
        self.human_input_queue = []
        
        # Системные промпты
        self._setup_system_prompts()
    
    def _setup_system_prompts(self):
        """Настройка системных промптов"""
        
        system_prompt = """
Ты - автономный AI агент для управления веб-браузером. Твоя задача - выполнять сложные многошаговые задачи в веб-браузере.

Инструкции:
1. Ты работаешь полностью автономно, пока задача не будет выполнена или не потребуется ввод пользователя
2. Ты сам определяешь, что делать дальше на основе текущего состояния страницы
3. Ты не используешь заранее заготовленные селекторы или шаги
4. Ты анализируешь страницу и находишь элементы по их описанию
5. Ты учишься на своих действиях и корректируешь поведение

Доступные действия:
- navigate: Перейти по URL
- click: Кликнуть на элемент (опиши элемент)
- type: Ввести текст в поле (опиши поле и текст)
- press_key: Нажать клавишу (enter, escape, tab и т.д.)
- scroll: Прокрутить страницу (up, down, top, bottom)
- go_back: Вернуться на предыдущую страницу
- refresh: Обновить страницу
- wait: Подождать
- analyze: Проанализировать ситуацию (без действия в браузере)
- complete: Задача завершена
- ask_human: Запросить помощь у пользователя

Формат ответа (ВСЕГДА отвечай в этом формате JSON):
{
  "action": "тип_действия",
  "description": "Человекочитаемое описание действия",
  "parameters": {
    "параметр1": "значение1",
    "параметр2": "значение2"
  },
  "confidence": 0.95,
  "reasoning": "Твои рассуждения о выборе этого действия"
}

Примеры:
{
  "action": "click",
  "description": "Кликнуть на кнопку 'Поиск'",
  "parameters": {
    "element_description": "кнопка с текстом 'Поиск'"
  },
  "confidence": 0.9,
  "reasoning": "Нужно начать поиск по запросу"
}

{
  "action": "type",
  "description": "Ввести поисковый запрос",
  "parameters": {
    "element_description": "поле поиска",
    "text": "Python программирование"
  },
  "confidence": 0.95,
  "reasoning": "Для поиска информации нужно ввести запрос в поле поиска"
}
        """
        
        self.context_manager.add_system_context(system_prompt)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Основной метод обработки - запуск выполнения задачи"""
        
        task = input_data.get("task", "")
        initial_url = input_data.get("initial_url", "https://www.google.com")
        
        if not task:
            return {
                "success": False,
                "error": "No task provided",
                "message": "Задача не предоставлена"
            }
        
        # Начинаем новую задачу
        self.context_manager.start_new_task(
            task_description=task,
            goal=input_data.get("goal", ""),
            constraints=input_data.get("constraints", [])
        )
        
        # Переходим на начальный URL если указан
        if initial_url:
            self.browser.navigate_to(initial_url)
            time.sleep(2)
        
        # Основной цикл выполнения
        return self._execute_task_loop(task)
    
    def _execute_task_loop(self, task: str) -> Dict[str, Any]:
        """Цикл выполнения задачи"""
        
        self.start()
        self.is_task_complete = False
        self.current_step = 0
        
        final_result = None
        
        try:
            while (not self.is_task_complete and 
                   self.current_step < self.max_steps and
                   not self.needs_human_input):
                
                self.current_step += 1
                
                # Получаем текущее состояние
                current_state = self.browser.get_page_state()
                
                # Получаем полный контекст
                context = self.context_manager.get_full_context(current_state)
                
                # Получаем совет из памяти
                memory_advice = self.episodic_memory.get_advice(current_state)
                if memory_advice:
                    context += "\n\n" + memory_advice
                
                # Принимаем решение о следующем действии
                action_decision = self.decide_next_action({
                    "task": task,
                    "current_state": current_state,
                    "context": context,
                    "step": self.current_step
                })
                
                if not action_decision:
                    break
                
                # Выполняем действие
                action_result = self._execute_action(action_decision)
                
                # Обновляем контекст
                self.context_manager.add_action(
                    action_type=action_decision.get("action", "unknown"),
                    action_description=action_decision.get("description", ""),
                    result=action_result,
                    page_state=current_state
                )
                
                # Проверяем, завершена ли задача
                if action_decision.get("action") == "complete":
                    self.is_task_complete = True
                    final_result = {
                        "success": True,
                        "message": "Задача успешно выполнена",
                        "steps": self.current_step,
                        "final_state": self.browser.get_page_state()
                    }
                    break
                
                # Проверяем, нужен ли ввод пользователя
                if action_decision.get("action") == "ask_human":
                    self.needs_human_input = True
                    final_result = {
                        "success": False,
                        "message": "Требуется ввод пользователя",
                        "question": action_decision.get("parameters", {}).get("question"),
                        "current_step": self.current_step
                    }
                    break
                
                # Проводим рефлексию если нужно
                if (self.config.ENABLE_REFLECTION and 
                    self.current_step % 5 == 0):
                    
                    self._perform_reflection(task)
                
                # Небольшая пауза между действиями
                time.sleep(1)
            
            # Если достигли лимита шагов
            if not self.is_task_complete and not self.needs_human_input:
                final_result = {
                    "success": False,
                    "message": f"Достигнут лимит шагов ({self.max_steps})",
                    "steps": self.current_step,
                    "current_state": self.browser.get_page_state()
                }
            
        except Exception as e:
            final_result = {
                "success": False,
                "error": str(e),
                "message": "Ошибка при выполнении задачи",
                "steps": self.current_step
            }
        
        finally:
            self.stop()
            
            # Сохраняем эпизод в память
            if self.context_manager.action_history:
                actions = []
                for record in self.context_manager.action_history:
                    actions.append({
                        "action_type": record.action_type,
                        "action_description": record.action_description,
                        "result": record.result
                    })
                
                current_state = self.browser.get_page_state()
                success = final_result.get("success", False) if final_result else False
                
                self.episodic_memory.add_episode(
                    url=current_state.get("url"),
                    title=current_state.get("title"),
                    page_type=current_state.get("page_type"),
                    actions=actions,
                    success=success
                )
        
        return final_result or {
            "success": False,
            "message": "Неизвестная ошибка"
        }
    
    def decide_next_action(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Принятие решения о следующем действии"""
        
        task = context.get("task", "")
        current_state = context.get("current_state", {})
        full_context = context.get("context", "")
        
        # Формируем промпт для LLM
        prompt = f"""
На основе следующего контекста, реши какое действие выполнить следующим.

КОНТЕКСТ:
{full_context}

Задача: {task}

Твой ответ должен быть в формате JSON как описано в системном промпте.
Думай шаг за шагом, но в ответе давай только JSON.
        """
        
        try:
            # Получаем ответ от LLM
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=self.context_manager.get_system_context(),
                temperature=0.1,
                max_tokens=1000
            )
            
            # Парсим действие
            action_data = self._parse_llm_response(response.content)
            
            if not action_data:
                # Если не удалось распарсить, возвращаем действие анализа
                return {
                    "action": "analyze",
                    "description": "Проанализировать текущую ситуацию",
                    "parameters": {},
                    "confidence": 1.0,
                    "reasoning": "Не удалось распознать следующее действие"
                }
            
            return action_data
            
        except Exception as e:
            self.logger.error(f"Ошибка при принятии решения: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Парсинг ответа LLM"""
        
        # Пытаемся извлечь JSON
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if not json_match:
            return None
        
        try:
            action_data = json.loads(json_match.group())
            
            # Проверяем обязательные поля
            if "action" not in action_data or "description" not in action_data:
                return None
            
            # Добавляем параметры если их нет
            if "parameters" not in action_data:
                action_data["parameters"] = {}
            
            # Добавляем уверенность если её нет
            if "confidence" not in action_data:
                action_data["confidence"] = 0.8
            
            return action_data
            
        except json.JSONDecodeError:
            # Пробуем альтернативный парсинг через ActionTools
            action = ActionTools.parse_action_from_llm(response)
            
            if action:
                return {
                    "action": action.type,
                    "description": action.description,
                    "parameters": action.parameters,
                    "confidence": action.confidence,
                    "reasoning": "Определено на основе текстового анализа"
                }
            
            return None
    
    def _execute_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение действия"""
        
        action_type = action_data.get("action")
        parameters = action_data.get("parameters", {})
        
        # Специальные действия
        if action_type == "analyze":
            return {
                "success": True,
                "message": "Проведен анализ ситуации"
            }
        
        elif action_type == "complete":
            return {
                "success": True,
                "message": "Задача помечена как завершенная"
            }
        
        elif action_type == "ask_human":
            question = parameters.get("question", "Требуется помощь пользователя")
            return {
                "success": True,
                "message": "Запрошена помощь пользователя",
                "question": question
            }
        
        elif action_type == "wait":
            wait_time = parameters.get("seconds", 2)
            time.sleep(wait_time)
            return {
                "success": True,
                "message": f"Подождали {wait_time} секунд"
            }
        
        # Действия браузера
        action = Action(
            type=action_type,
            description=action_data.get("description", ""),
            parameters=parameters,
            confidence=action_data.get("confidence", 1.0)
        )
        
        return ActionTools.execute_action(self.browser, action)
    
    def _perform_reflection(self, task: str):
        """Проведение рефлексии"""
        
        if not self.config.ENABLE_REFLECTION:
            return
        
        # Получаем текущее состояние
        current_state = self.browser.get_page_state()
        
        # Получаем историю действий
        recent_actions = self.context_manager.get_recent_actions(10)
        
        # Анализируем неудачи
        reflection = self.reflection_pattern.analyze_failure(
            action_history=recent_actions,
            current_state=current_state,
            task_description=task
        )
        
        if reflection.needs_correction and reflection.correction_plan:
            self.logger.info(f"Рефлексия: требуется коррекция - {reflection.correction_plan[:100]}...")
            
            # Добавляем анализ в контекст
            self.context_manager.add_system_context(
                f"Урок из рефлексии: {reflection.learned_lesson or 'Требуется изменить подход'}"
            )
    
    def provide_human_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка ввода от пользователя"""
        
        if not self.needs_human_input:
            return {
                "success": False,
                "message": "Ввод пользователя не требуется"
            }
        
        answer = input_data.get("answer", "")
        instruction = input_data.get("instruction", "")
        
        if instruction == "continue":
            # Продолжаем выполнение
            self.needs_human_input = False
            return {
                "success": True,
                "message": "Продолжаем выполнение задачи"
            }
        
        elif answer:
            # Используем ответ пользователя
            self.needs_human_input = False
            
            # Добавляем ответ в контекст
            self.context_manager.add_system_context(
                f"Пользователь предоставил информацию: {answer}"
            )
            
            return {
                "success": True,
                "message": "Получен ответ пользователя, продолжаем выполнение"
            }
        
        return {
            "success": False,
            "message": "Неверный ввод пользователя"
        }
    
    def get_current_status(self) -> Dict[str, Any]:
        """Получение текущего статуса"""
        base_status = super().get_status()
        
        current_state = self.browser.get_page_state()
        
        status = {
            **base_status,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "is_task_complete": self.is_task_complete,
            "needs_human_input": self.needs_human_input,
            "current_url": current_state.get("url"),
            "current_title": current_state.get("title"),
            "task_context": self.context_manager.get_task_context() if self.context_manager.current_task else ""
        }
        
        return status