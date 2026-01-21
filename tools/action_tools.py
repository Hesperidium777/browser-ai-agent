from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re

@dataclass
class Action:
    """Действие агента"""
    type: str
    description: str
    parameters: Dict[str, Any]
    confidence: float = 1.0

class ActionTools:
    """Инструменты для разбора и выполнения действий"""
    
    # Маппинг действий на методы браузера
    ACTION_MAPPING = {
        "navigate": "navigate_to",
        "click": "click_element",
        "type": "type_text",
        "press_key": "press_key",
        "scroll": "scroll",
        "go_back": "go_back",
        "refresh": "refresh",
        "screenshot": "take_screenshot",
        "execute_js": "execute_javascript",
        "wait": "wait"
    }
    
    @staticmethod
    def parse_action_from_llm(response: str) -> Optional[Action]:
        """Парсинг действия из ответа LLM"""
        
        # Очищаем ответ от лишних символов
        response = response.strip()
        
        # Убираем markdown кодовые блоки если есть
        if response.startswith("```"):
            lines = response.split('\n')
            if len(lines) > 1:
                response = '\n'.join(lines[1:-1])
        
        # Пытаемся найти структурированный ответ
        action_match = re.search(r'"action"\s*:\s*"([^"]+)"', response)
        params_match = re.search(r'"parameters"\s*:\s*({[^}]+})', response)
        
        if action_match and params_match:
            try:
                import json
                action_type = action_match.group(1)
                parameters = json.loads(params_match.group(1))
                
                # Извлекаем описание
                desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', response)
                description = desc_match.group(1) if desc_match else action_type
                
                # Извлекаем уверенность
                conf_match = re.search(r'"confidence"\s*:\s*(\d+\.?\d*)', response)
                confidence = float(conf_match.group(1)) if conf_match else 1.0
                
                return Action(
                    type=action_type,
                    description=description,
                    parameters=parameters,
                    confidence=confidence
                )
            except:
                pass
        
        # Если не нашли JSON, пробуем извлечь из текста
        return ActionTools._extract_action_from_text(response)
    
    @staticmethod
    def _extract_action_from_text(text: str) -> Optional[Action]:
        """Извлечение действия из текстового описания"""
        
        text_lower = text.lower()
        
        # Определяем тип действия по ключевым словам
        if any(word in text_lower for word in ["перейди", "открой", "navigate", "go to", "open"]):
            return ActionTools._parse_navigation_action(text)
        
        elif any(word in text_lower for word in ["нажми", "кликни", "click", "tap"]):
            return ActionTools._parse_click_action(text)
        
        elif any(word in text_lower for word in ["введи", "напиши", "type", "enter", "input"]):
            return ActionTools._parse_type_action(text)
        
        elif any(word in text_lower for word in ["нажми клавишу", "press", "key"]):
            return ActionTools._parse_key_action(text)
        
        elif any(word in text_lower for word in ["прокрути", "scroll"]):
            return ActionTools._parse_scroll_action(text)
        
        elif any(word in text_lower for word in ["назад", "go back", "back"]):
            return Action(
                type="go_back",
                description="Вернуться на предыдущую страницу",
                parameters={}
            )
        
        elif any(word in text_lower for word in ["обнови", "refresh", "reload"]):
            return Action(
                type="refresh",
                description="Обновить страницу",
                parameters={}
            )
        
        return None
    
    @staticmethod
    def _parse_navigation_action(text: str) -> Action:
        """Парсинг действия навигации"""
        # Ищем URL в тексте
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+)'
        match = re.search(url_pattern, text)
        
        if match:
            url = match.group(0)
            return Action(
                type="navigate",
                description=f"Перейти на {url}",
                parameters={"url": url}
            )
        
        # Ищем домен
        domain_pattern = r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,})'
        match = re.search(domain_pattern, text)
        
        if match:
            domain = match.group(0)
            if not domain.startswith(('http://', 'https://')):
                domain = 'https://' + domain
            return Action(
                type="navigate",
                description=f"Перейти на {domain}",
                parameters={"url": domain}
            )
        
        # По умолчанию
        return Action(
            type="navigate",
            description="Перейти на главную страницу Google",
            parameters={"url": "https://www.google.com"}
        )
    
    @staticmethod
    def _parse_click_action(text: str) -> Action:
        """Парсинг действия клика"""
        # Извлекаем описание элемента
        element_desc = text
        
        # Убираем ключевые слова
        keywords = ["нажми на", "кликни по", "click on", "click the", "tap on"]
        for keyword in keywords:
            if keyword in element_desc.lower():
                element_desc = element_desc.lower().split(keyword)[-1].strip()
        
        # Убираем кавычки если есть
        element_desc = element_desc.strip('"\'')
        
        return Action(
            type="click",
            description=f"Кликнуть на {element_desc}",
            parameters={"element_description": element_desc}
        )
    
    @staticmethod
    def _parse_type_action(text: str) -> Action:
        """Парсинг действия ввода текста"""
        # Ищем текст для ввода
        text_match = re.search(r'["\']([^"\']+)["\']', text)
        input_text = text_match.group(1) if text_match else ""
        
        # Ищем описание поля
        field_desc = text
        
        # Убираем ключевые слова
        keywords = ["введи", "напиши", "type", "enter", "input"]
        for keyword in keywords:
            if keyword in field_desc.lower():
                parts = field_desc.lower().split(keyword)
                if len(parts) > 1:
                    field_desc = parts[-1].strip()
        
        # Убираем текст для ввода из описания
        if text_match and text_match.group() in field_desc:
            field_desc = field_desc.replace(text_match.group(), "").strip()
        
        # Убираем предлоги
        prepositions = ["в", "в поле", "в input", "в textarea", "into", "in the"]
        for prep in prepositions:
            if field_desc.lower().startswith(prep):
                field_desc = field_desc[len(prep):].strip()
        
        return Action(
            type="type",
            description=f"Ввести '{input_text}' в {field_desc}",
            parameters={
                "element_description": field_desc,
                "text": input_text
            }
        )
    
    @staticmethod
    def _parse_key_action(text: str) -> Action:
        """Парсинг действия нажатия клавиши"""
        key_mapping = {
            "enter": "enter",
            "escape": "escape",
            "tab": "tab",
            "backspace": "backspace",
            "space": "space",
            "стрелка вверх": "arrow_up",
            "стрелка вниз": "arrow_down",
            "стрелка влево": "arrow_left",
            "стрелка вправо": "arrow_right"
        }
        
        text_lower = text.lower()
        
        for key_name, key_code in key_mapping.items():
            if key_name in text_lower:
                return Action(
                    type="press_key",
                    description=f"Нажать клавишу {key_name}",
                    parameters={"key_name": key_code}
                )
        
        # По умолчанию Enter
        return Action(
            type="press_key",
            description="Нажать клавишу Enter",
            parameters={"key_name": "enter"}
        )
    
    @staticmethod
    def _parse_scroll_action(text: str) -> Action:
        """Парсинг действия прокрутки"""
        text_lower = text.lower()
        
        direction = "down"
        if "вверх" in text_lower or "up" in text_lower:
            direction = "up"
        elif "вниз" in text_lower or "down" in text_lower:
            direction = "down"
        elif "начало" in text_lower or "top" in text_lower:
            direction = "top"
        elif "конец" in text_lower or "bottom" in text_lower:
            direction = "bottom"
        
        return Action(
            type="scroll",
            description=f"Прокрутить страницу {direction}",
            parameters={"direction": direction}
        )
    
    @staticmethod
    def execute_action(browser, action: Action) -> Dict[str, Any]:
        """Выполнение действия через браузер"""
        
        method_name = ActionTools.ACTION_MAPPING.get(action.type)
        if not method_name:
            return {
                "success": False,
                "error": f"Unknown action type: {action.type}",
                "message": f"Неизвестный тип действия: {action.type}"
            }
        
        try:
            method = getattr(browser, method_name)
            
            if action.parameters:
                result = method(**action.parameters)
            else:
                result = method()
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Ошибка при выполнении действия: {action.type}"
            }