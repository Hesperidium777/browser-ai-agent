from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re

@dataclass
class ReflectionResult:
    """Результат рефлексии"""
    needs_correction: bool
    correction_plan: Optional[str] = None
    learned_lesson: Optional[str] = None
    confidence_score: float = 1.0

class ReflectionPattern:
    """Паттерн рефлексии для самоанализа и коррекции"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def analyze_failure(self, 
                       action_history: List[Dict[str, Any]],
                       current_state: Dict[str, Any],
                       task_description: str) -> ReflectionResult:
        """Анализ неудачных действий и предложение корректировок"""
        
        # Собираем информацию о последних неудачах
        recent_failures = []
        for action in action_history[-5:]:
            result = action.get('result', {})
            if not result.get('success', False):
                recent_failures.append({
                    "action": action.get('action_description'),
                    "error": result.get('error', 'unknown'),
                    "message": result.get('message', '')
                })
        
        if not recent_failures:
            return ReflectionResult(needs_correction=False)
        
        # Анализируем с помощью LLM
        prompt = f"""
Проанализируй последние неудачные действия и предложи план корректировки.

Задача: {task_description}

Текущее состояние страницы:
URL: {current_state.get('url')}
Заголовок: {current_state.get('title')}
Тип страницы: {current_state.get('page_type')}

Последние неудачи:
{self._format_failures(recent_failures)}

Доступные элементы на странице:
{chr(10).join(current_state.get('elements', ['Нет элементов'])[:10])}

Проанализируй:
1. Почему действия не удались?
2. Что агент неправильно понял о странице?
3. Какой должна быть правильная последовательность действий?
4. Какой конкретный следующий шаг нужно предпринять?

Предложи конкретный план корректировки.
        """
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="Ты эксперт по анализу ошибок веб-автоматизации.",
                temperature=0.3
            )
            
            # Анализируем ответ
            analysis = response.content
            
            # Определяем, нужна ли коррекция
            needs_correction = self._detect_correction_needed(analysis)
            
            # Извлекаем предложение по коррекции
            correction_plan = self._extract_correction_plan(analysis)
            
            # Извлекаем выученный урок
            learned_lesson = self._extract_lesson(analysis)
            
            # Оцениваем уверенность
            confidence = self._calculate_confidence(analysis, len(recent_failures))
            
            return ReflectionResult(
                needs_correction=needs_correction,
                correction_plan=correction_plan,
                learned_lesson=learned_lesson,
                confidence_score=confidence
            )
            
        except Exception as e:
            print(f"Ошибка при анализе неудач: {e}")
            return ReflectionResult(needs_correction=False)
    
    def reflect_on_progress(self,
                          task_description: str,
                          action_history: List[Dict[str, Any]],
                          current_state: Dict[str, Any]) -> str:
        """Рефлексия о прогрессе выполнения задачи"""
        
        prompt = f"""
Проведи рефлексию о прогрессе выполнения задачи.

Задача: {task_description}

Выполненные действия (последние 10):
{self._format_action_history(action_history[-10:])}

Текущее состояние:
URL: {current_state.get('url')}
Заголовок: {current_state.get('title')}

Проанализируй:
1. Насколько хорошо продвигается задача?
2. Какие стратегии работают хорошо?
3. Какие ошибки повторяются?
4. Что нужно изменить в подходе?

Дай краткий анализ и рекомендации.
        """
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt="Ты эксперт по стратегическому планированию веб-автоматизации.",
                temperature=0.2
            )
            
            return response.content
            
        except Exception as e:
            return f"Не удалось провести рефлексию: {str(e)}"
    
    def _format_failures(self, failures: List[Dict[str, Any]]) -> str:
        """Форматирование информации о неудачах"""
        if not failures:
            return "Нет неудачных действий"
        
        formatted = []
        for i, failure in enumerate(failures, 1):
            formatted.append(f"{i}. Действие: {failure.get('action')}")
            formatted.append(f"   Ошибка: {failure.get('error')}")
            formatted.append(f"   Сообщение: {failure.get('message')}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _format_action_history(self, actions: List[Dict[str, Any]]) -> str:
        """Форматирование истории действий"""
        if not actions:
            return "История действий пуста"
        
        formatted = []
        for action in actions:
            result = action.get('result', {})
            status = "✓" if result.get('success') else "✗"
            formatted.append(f"{status} {action.get('action_description', '')}")
        
        return "\n".join(formatted)
    
    def _detect_correction_needed(self, analysis: str) -> bool:
        """Определение, нужна ли коррекция на основе анализа"""
        correction_keywords = [
            "нужно", "следует", "рекомендуется", "необходимо",
            "исправьте", "попробуйте", "измените", "скорректируйте",
            "ошибка", "неправильно", "неверно"
        ]
        
        analysis_lower = analysis.lower()
        for keyword in correction_keywords:
            if keyword in analysis_lower:
                return True
        
        return False
    
    def _extract_correction_plan(self, analysis: str) -> Optional[str]:
        """Извлечение плана коррекции"""
        # Ищем секции с планом или рекомендациями
        patterns = [
            r"План[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Рекомендации[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Следующий шаг[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Корректировка[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Если не нашли структурированный план, берем последний абзац
        paragraphs = analysis.strip().split('\n\n')
        if paragraphs:
            return paragraphs[-1].strip()
        
        return None
    
    def _extract_lesson(self, analysis: str) -> Optional[str]:
        """Извлечение выученного урока"""
        patterns = [
            r"Урок[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Вывод[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)",
            r"Learned[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _calculate_confidence(self, analysis: str, failure_count: int) -> float:
        """Расчет уровня уверенности в анализе"""
        # Базовый уровень уверенности
        confidence = 1.0
        
        # Уменьшаем уверенность при большом количестве неудач
        if failure_count > 3:
            confidence *= 0.7
        
        # Анализируем тон ответа
        uncertainty_words = ["возможно", "может быть", "вероятно", "скорее всего"]
        certainty_words = ["точно", "определенно", "несомненно", "очевидно"]
        
        analysis_lower = analysis.lower()
        
        for word in uncertainty_words:
            if word in analysis_lower:
                confidence *= 0.9
        
        for word in certainty_words:
            if word in analysis_lower:
                confidence *= 1.1
        
        # Ограничиваем от 0.1 до 1.0
        return max(0.1, min(1.0, confidence))