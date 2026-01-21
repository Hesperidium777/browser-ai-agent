import json
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    content: str
    thinking: Optional[str] = None
    usage: Optional[Dict[str, int]] = None

class OllamaClient:
    """Клиент для работы с локальной Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()
        
    def generate(self, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                temperature: float = 0.1,
                max_tokens: int = 2000) -> LLMResponse:
        """Генерация ответа от модели"""
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Извлекаем thinking из сообщения если есть
            content = data["message"]["content"]
            thinking = None
            
            # Пытаемся найти reasoning в контенте
            if "დ" in content:  # Маркер reasoning для некоторых моделей
                parts = content.split("დ")
                if len(parts) > 1:
                    thinking = parts[0].strip()
                    content = parts[1].strip()
            
            return LLMResponse(
                content=content,
                thinking=thinking,
                usage=data.get("usage")
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к Ollama: {e}")
            raise

class StructuredLLMClient(OllamaClient):
    """Клиент для структурированных ответов"""
    
    def generate_structured(self,
                          prompt: str,
                          response_format: Dict[str, Any],
                          system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Генерация структурированного ответа"""
        
        format_description = json.dumps(response_format, indent=2)
        enhanced_prompt = f"""{prompt}

Ты должен ответить в формате JSON строго следующей структуры:
{format_description}

Твой ответ должен содержать только JSON, без дополнительных объяснений."""
        
        if system_prompt:
            enhanced_system = f"{system_prompt}\n\nТы всегда отвечаешь в формате JSON."
        else:
            enhanced_system = "Ты всегда отвечаешь в формате JSON."
        
        response = self.generate(
            prompt=enhanced_prompt,
            system_prompt=enhanced_system,
            temperature=0.1
        )
        
        # Извлекаем JSON из ответа
        content = response.content.strip()
        
        # Удаляем markdown кодовые блоки если есть
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Не удалось распарсить JSON: {content}")
            # Пытаемся извлечь JSON с помощью эвристик
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            raise