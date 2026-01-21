import os
import sys
import time
import json
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ai_browser.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Добавляем путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from browser.controller import BrowserController
from config import Config

class SimpleAIBrowserAgent:
    """AI агент для браузера с улучшенной логикой поиска"""
    
    def __init__(self):
        self.config = Config(
            HEADLESS=False,
            WINDOW_WIDTH=1400,
            WINDOW_HEIGHT=900,
            MODEL_NAME="llama3.2:3b"
        )
        self.browser = None
        self.current_task = ""
        self.task_history = []
        self.consecutive_errors = 0
        
    def initialize(self) -> bool:
        """Инициализация системы"""
        print("\n" + "="*60)
        print("🤖 AI BROWSER AGENT - Улучшенная версия")
        print("="*60)
        
        print("🚀 Инициализация системы...")
        
        # Запускаем браузер
        self.browser = BrowserController(self.config)
        
        if not self.browser.start():
            print("❌ Не удалось запустить браузер")
            print("\nВозможные решения:")
            print("1. Установите Google Chrome")
            print("2. Скачайте ChromeDriver с https://chromedriver.chromium.org/")
            print("3. Поместите chromedriver.exe в C:\\Windows\\")
            print("4. Перезапустите программу")
            return False
        
        print("✅ Браузер успешно запущен")
        print(f"📊 Используется модель: {self.config.MODEL_NAME}")
        
        # Открываем Google
        print("🌐 Открываю Google...")
        result = self.browser.navigate_to("https://www.google.com")
        
        if result["success"]:
            print(f"✅ Загружена страница: {result.get('title', 'Без названия')}")
            print(f"🔗 URL: {result.get('url', 'Неизвестно')}")
        else:
            print(f"⚠️ Не удалось загрузить Google: {result.get('message')}")
            # Пробуем альтернативный URL
            result = self.browser.navigate_to("https://www.google.com/search?q=test")
            if result["success"]:
                print(f"✅ Загружена альтернативная страница Google")
        
        return True
    
    def ask_ollama(self, prompt: str) -> str:
        """Запрос к Ollama с обработкой ошибок"""
        try:
            import requests
            
            print("🤔 Запрашиваю решение у AI...")
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.config.MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 500,
                        "stop": ["\n```", "```json", "```"]
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "Нет ответа")
                print(f"💡 AI ответил: {ai_response[:100]}...")
                return ai_response
            else:
                error_msg = f"Ошибка AI: {response.status_code}"
                print(f"❌ {error_msg}")
                return error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = "Ошибка: Ollama не запущена. Запустите: ollama serve"
            print(f"❌ {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Ошибка подключения к AI: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Извлечение JSON из ответа AI"""
        response = response.strip()
        
        # Удаляем markdown блоки если есть
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        # Ищем JSON в тексте
        json_patterns = [
            r'\{[^{}]*\}',  # Простой JSON
            r'\{.*\}',      # Сложный JSON
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for json_str in matches:
                try:
                    # Исправляем распространенные ошибки
                    json_str = json_str.replace("'", '"')
                    json_str = re.sub(r'(\w+):\s*"', r'"\1": "', json_str)
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    
                    data = json.loads(json_str)
                    
                    # Проверяем минимальную структуру
                    if isinstance(data, dict) and "action" in data:
                        if "description" not in data:
                            data["description"] = data["action"]
                        if "parameters" not in data:
                            data["parameters"] = {}
                        return data
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"Ошибка парсинга JSON: {e}, строка: {json_str[:100]}")
                    continue
                except Exception as e:
                    logger.debug(f"Ошибка обработки JSON: {e}")
                    continue
        
        return None
    
    def analyze_page(self) -> Dict[str, Any]:
        """Анализ текущей страницы"""
        if not self.browser or not self.browser.driver:
            return {"error": "Браузер не инициализирован"}
        
        try:
            state = self.browser.get_page_state()
            
            # Определяем основные элементы для AI
            important_elements = []
            elements = state.get("elements", [])
            
            # Добавляем до 7 элементов для контекста
            for i, elem_desc in enumerate(elements[:7]):
                if i < 3 or "поиск" in elem_desc.lower() or "search" in elem_desc.lower():
                    important_elements.append(f"{i+1}. {elem_desc}")
            
            analysis = {
                "url": state.get("url", "unknown"),
                "title": state.get("title", "Без названия"),
                "page_type": state.get("page_type", "general"),
                "is_search_page": state.get("is_search_page", False),
                "elements_count": state.get("element_count", 0),
                "important_elements": important_elements,
                "text_preview": state.get("visible_text_preview", "")[:200] + "...",
                "has_search_box": any("поиск" in elem.lower() or "search" in elem.lower() 
                                     for elem in elements[:5]),
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Ошибка анализа страницы: {e}")
            return {"error": str(e)}
    
    def decide_action(self, task: str, page_analysis: dict) -> Dict[str, Any]:
        """Принятие решения о следующем действии"""
        
        # Формируем промпт для AI
        prompt = f"""
Ты - AI помощник, который управляет браузером. Текущая задача: {task}

ТЕКУЩАЯ СТРАНИЦА:
- URL: {page_analysis.get('url', 'unknown')}
- Заголовок: {page_analysis.get('title', 'Без названия')}
- Тип: {page_analysis.get('page_type', 'general')}
- Это поисковая страница: {page_analysis.get('is_search_page', False)}
- Есть поле поиска: {page_analysis.get('has_search_box', False)}
- Краткий текст: {page_analysis.get('text_preview', 'Нет текста')}

ДОСТУПНЫЕ ЭЛЕМЕНТЫ:
{chr(10).join(page_analysis.get('important_elements', ['Нет элементов']))}

ИНСТРУКЦИИ:
1. Если на странице Google - используй поле поиска
2. Введи поисковый запрос и нажми Enter
3. Запрос должен быть кратким и точным
4. Не добавляй слова "Найди" или "Поищи" в запрос

ФОРМАТ ОТВЕТА (только JSON):
{{
  "action": "тип_действия",
  "description": "что сделать",
  "parameters": {{
    "query": "поисковый запрос"
  }}
}}

ВОЗМОЖНЫЕ ДЕЙСТВИЯ:
- "google_search": поиск на Google
- "click": кликнуть на элемент
- "scroll": прокрутить страницу
- "back": вернуться назад
- "complete": задача выполнена

Пример для задачи "погода в Москве":
{{
  "action": "google_search",
  "description": "Искать погоду в Москве на Google",
  "parameters": {{"query": "погода в Москве сегодня"}}
}}

Что нужно сделать?
"""
        
        ai_response = self.ask_ollama(prompt)
        
        # Пытаемся извлечь JSON
        action_data = self.extract_json_from_response(ai_response)
        
        if action_data:
            print(f"✅ AI предложил: {action_data.get('description')}")
            return action_data
        
        # Если не удалось получить JSON от AI, используем логику по умолчанию
        print("⚠️ AI не дал четкого ответа, использую логику по умолчанию")
        return self._get_smart_action(task, page_analysis)
    
    def _get_smart_action(self, task: str, page_analysis: dict) -> Dict[str, Any]:
        """Умное действие по умолчанию на основе анализа"""
        
        # Очищаем запрос от лишних слов
        clean_query = self._clean_search_query(task)
        
        # Если на Google или есть поле поиска
        if page_analysis.get("is_search_page", False) or page_analysis.get("has_search_box", False):
            return {
                "action": "google_search",
                "description": f"Искать '{clean_query}' на Google",
                "parameters": {"query": clean_query}
            }
        
        # Если не на поисковой странице
        return {
            "action": "navigate",
            "description": f"Перейти на Google для поиска '{clean_query}'",
            "parameters": {"url": f"https://www.google.com/search?q={clean_query}"}
        }
    
    def _clean_search_query(self, query: str) -> str:
        """Очистка поискового запроса"""
        # Убираем команды поиска
        stop_words = ["найди", "поищи", "найти", "ищи", "узнай", "посмотри"]
        
        words = query.lower().split()
        cleaned_words = []
        
        for word in words:
            if word not in stop_words:
                cleaned_words.append(word)
        
        cleaned_query = " ".join(cleaned_words).strip()
        
        # Если запрос стал пустым, возвращаем оригинал
        if not cleaned_query:
            return query
        
        return cleaned_query
    
    def execute_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение действия"""
        action_type = action_data.get("action", "")
        params = action_data.get("parameters", {})
        description = action_data.get("description", "Действие")
        
        print(f"⚡ Выполняю: {description}")
        
        try:
            if action_type == "google_search":
                query = params.get("query", self.current_task)
                return self._perform_google_search(query)
            
            elif action_type == "click":
                element_desc = params.get("element", "элемент")
                return self.browser.click_element(element_desc)
            
            elif action_type == "type":
                element_desc = params.get("element", "поле")
                text = params.get("text", "")
                return self.browser.type_text(element_desc, text)
            
            elif action_type == "navigate":
                url = params.get("url", "")
                if not url.startswith("http"):
                    url = f"https://www.google.com/search?q={url}"
                return self.browser.navigate_to(url)
            
            elif action_type == "scroll":
                direction = params.get("direction", "down")
                return self.browser.scroll(direction)
            
            elif action_type == "back":
                return self.browser.go_back()
            
            elif action_type == "refresh":
                return self.browser.refresh()
            
            elif action_type == "complete":
                return {"success": True, "message": "Задача выполнена"}
            
            else:
                # Если неизвестное действие, пробуем поиск
                print(f"⚠️ Неизвестное действие '{action_type}', пробую поиск...")
                return self._perform_google_search(self.current_task)
                
        except Exception as e:
            error_msg = f"Ошибка выполнения: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": str(e), "message": error_msg}
    
    def _perform_google_search(self, query: str) -> Dict[str, Any]:
        """Выполнение поиска на Google"""
        print(f"🔍 Выполняю поиск: '{query}'")
        
        # Шаг 1: Убедимся что на Google
        current_url = self.browser.get_current_url()
        if "google.com" not in current_url.lower():
            print("📍 Перехожу на Google...")
            result = self.browser.navigate_to("https://www.google.com")
            if not result["success"]:
                return result
            time.sleep(2)
        
        # Шаг 2: Очищаем поисковую строку
        print("🧹 Очищаю поисковую строку...")
        self._clear_google_search_box()
        time.sleep(0.5)
        
        # Шаг 3: Вводим запрос
        print("⌨️  Ввожу запрос...")
        result = self.browser.type_text("поле поиска", query)
        if not result["success"]:
            return result
        time.sleep(0.5)
        
        # Шаг 4: Нажимаем Enter
        print("⏎ Нажимаю Enter для поиска...")
        result = self.browser.press_key("enter")
        if result["success"]:
            print("⏳ Жду загрузки результатов...")
            time.sleep(3)
        
        return result
    
    def _clear_google_search_box(self):
        """Очистка поисковой строки Google (прямой доступ)"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            
            # Пробуем разные селекторы
            selectors = [
                "textarea[name='q']",
                "input[name='q']",
                "[aria-label='Поиск']",
                "[title='Поиск']",
                "[name='search']",
            ]
            
            for selector in selectors:
                try:
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            element.clear()
                            return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            logger.warning(f"Не удалось очистить поисковую строку: {e}")
            return False
    
    def run_task(self, task: str, max_steps: int = 6):
        """Выполнение задачи"""
        print(f"\n📋 ЗАДАЧА: {task}")
        print("="*60)
        
        self.current_task = task
        self.task_history = []
        self.consecutive_errors = 0
        step = 1
        
        while step <= max_steps:
            print(f"\n🌀 Шаг {step}/{max_steps}")
            
            # Проверяем состояние браузера
            if not self.browser.is_browser_alive():
                print("⚠️ Браузер не отвечает, перезапускаю...")
                self.browser.restart_if_needed()
                time.sleep(2)
                self.browser.navigate_to("https://www.google.com")
                time.sleep(2)
            
            # Анализируем страницу
            page_analysis = self.analyze_page()
            if "error" in page_analysis:
                print(f"❌ Ошибка анализа: {page_analysis['error']}")
                self.consecutive_errors += 1
                if self.consecutive_errors >= 2:
                    print("🔄 Пробую альтернативный подход...")
                    self._force_google_search(task)
                    self.consecutive_errors = 0
                continue
            
            print(f"📄 Страница: {page_analysis.get('title', 'Без названия')}")
            
            # Принимаем решение
            action_data = self.decide_action(task, page_analysis)
            
            # Выполняем действие
            result = self.execute_action(action_data)
            
            # Записываем в историю
            self.task_history.append({
                "step": step,
                "action": action_data,
                "result": result,
                "page_state": page_analysis,
                "timestamp": datetime.now().isoformat()
            })
            
            # Обрабатываем результат
            if result.get("success", False):
                print(f"✅ Успех: {result.get('message', 'Действие выполнено')}")
                self.consecutive_errors = 0
                
                # Проверяем завершение
                if action_data.get("action") == "complete":
                    print("\n🎉 ЗАДАЧА УСПЕШНО ВЫПОЛНЕНА!")
                    break
            else:
                self.consecutive_errors += 1
                error_msg = result.get('message', result.get('error', 'Неизвестная ошибка'))
                print(f"❌ Ошибка: {error_msg}")
                
                # Если много ошибок подряд
                if self.consecutive_errors >= 2:
                    print("🔄 Использую принудительный поиск...")
                    self._force_google_search(task)
                    self.consecutive_errors = 0
            
            step += 1
            time.sleep(1.5)  # Пауза между шагами
        
        # Вывод результатов
        self._show_task_results()
    
    def _force_google_search(self, task: str):
        """Принудительный поиск на Google (обход AI)"""
        print("🔧 Использую принудительный поиск...")
        
        clean_query = self._clean_search_query(task)
        search_url = f"https://www.google.com/search?q={clean_query}"
        
        result = self.browser.navigate_to(search_url)
        if result["success"]:
            print(f"✅ Перешел на: {result.get('url', 'Google')}")
            time.sleep(3)
        else:
            print(f"❌ Не удалось выполнить поиск: {result.get('message')}")
    
    def _show_task_results(self):
        """Показ результатов выполнения задачи"""
        print("\n" + "="*60)
        print("📊 ИТОГИ ВЫПОЛНЕНИЯ")
        print("="*60)
        
        if not self.browser:
            print("Браузер не доступен")
            return
        
        current_url = self.browser.get_current_url()
        current_title = self.browser.get_title()
        
        print(f"📍 Текущий URL: {current_url}")
        print(f"📰 Заголовок страницы: {current_title}")
        print(f"📈 Выполнено шагов: {len(self.task_history)}")
        
        # Статистика успешности
        successful = sum(1 for step in self.task_history if step["result"].get("success"))
        print(f"✅ Успешных шагов: {successful}/{len(self.task_history)}")
        
        # Последнее действие
        if self.task_history:
            last_action = self.task_history[-1]["action"]
            print(f"🔄 Последнее действие: {last_action.get('description', 'Неизвестно')}")
        
        # Сохранение результатов
        self._save_results()
    
    def _save_results(self):
        """Сохранение результатов задачи"""
        try:
            # Создаем папки если их нет
            os.makedirs("screenshots", exist_ok=True)
            os.makedirs("history", exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Скриншот
            screenshot_path = f"screenshots/task_{timestamp}.png"
            screenshot_result = self.browser.take_screenshot(screenshot_path)
            if screenshot_result.get("success"):
                print(f"📸 Скриншот сохранен: {screenshot_path}")
            
            # История
            history_data = {
                "task": self.current_task,
                "start_time": self.task_history[0]["timestamp"] if self.task_history else "",
                "end_time": datetime.now().isoformat(),
                "total_steps": len(self.task_history),
                "final_url": self.browser.get_current_url(),
                "final_title": self.browser.get_title(),
                "successful_steps": sum(1 for step in self.task_history if step["result"].get("success")),
                "history": self.task_history
            }
            
            history_file = f"history/task_{timestamp}.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            print(f"📝 История сохранена: {history_file}")
            
        except Exception as e:
            print(f"⚠️ Не удалось сохранить результаты: {e}")
    
    def interactive_mode(self):
        """Интерактивный режим работы"""
        if not self.initialize():
            return
        
        print("\n" + "="*60)
        print("🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ")
        print("="*60)
        print("Доступные команды:")
        print("- Любой текст: выполнить задачу")
        print("- 'скриншот': сделать скриншот")
        print("- 'url': показать текущий URL")
        print("- 'статус': показать статус")
        print("- 'очистить': очистить историю")
        print("- 'выход': завершить работу")
        print("="*60)
        print("Примеры задач:")
        print("- погода в Москве")
        print("- рецепт пиццы")
        print("- курс доллара к рублю")
        print("- новости сегодня")
        print("- магазин электроники")
        print("="*60)
        
        while True:
            try:
                print("\n" + "-"*60)
                user_input = input("🎯 Введите задачу или команду: ").strip()
                
                if not user_input:
                    continue
                
                # Проверка команд
                if user_input.lower() in ['выход', 'exit', 'quit']:
                    print("Завершение работы...")
                    break
                
                elif user_input.lower() == 'скриншот':
                    timestamp = datetime.now().strftime("%H%M%S")
                    path = f"screenshots/manual_{timestamp}.png"
                    result = self.browser.take_screenshot(path)
                    if result["success"]:
                        print(f"✅ Скриншот сохранен: {path}")
                    else:
                        print(f"❌ Ошибка: {result.get('message')}")
                    continue
                
                elif user_input.lower() == 'url':
                    url = self.browser.get_current_url()
                    title = self.browser.get_title()
                    print(f"📍 Текущий URL: {url}")
                    print(f"📰 Заголовок: {title}")
                    continue
                
                elif user_input.lower() == 'статус':
                    alive = self.browser.is_browser_alive()
                    print(f"🟢 Браузер: {'работает' if alive else 'не отвечает'}")
                    print(f"📊 История задач: {len(self.task_history)}")
                    continue
                
                elif user_input.lower() == 'очистить':
                    self.task_history = []
                    print("✅ История очищена")
                    continue
                
                # Выполнение задачи
                print(f"\n🚀 Начинаю выполнение задачи: {user_input}")
                self.run_task(user_input)
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Прервано пользователем")
                break
            except Exception as e:
                print(f"\n❌ Критическая ошибка: {e}")
                import traceback
                traceback.print_exc()
        
        # Завершение работы
        print("\n" + "="*60)
        print("👋 ЗАВЕРШЕНИЕ РАБОТЫ")
        print("="*60)
        
        if self.browser:
            self.browser.stop()
            print("✅ Браузер закрыт")
        
        print(f"📊 Всего выполнено задач: {len(self.task_history)}")
        print("До свидания!")

def check_ollama_connection():
    """Проверка подключения к Ollama"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                print("✅ Ollama подключена")
                print(f"📦 Доступные модели: {', '.join(m.get('name', '?') for m in models[:3])}")
                return True
            else:
                print("⚠️ Ollama запущена, но нет моделей")
                print("   Загрузите модель: ollama pull llama3.2:3b")
                return False
        else:
            print("❌ Ollama не отвечает")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Ollama не запущена")
        print("\nЧтобы использовать AI:")
        print("1. Скачайте Ollama с https://ollama.com/")
        print("2. Установите и запустите")
        print("3. В терминале выполните: ollama pull llama3.2:3b")
        print("4. Запустите: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки Ollama: {e}")
        return False

def check_dependencies():
    """Проверка зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    dependencies = {
        "selenium": "Selenium (для управления браузером)",
        "requests": "Requests (для HTTP запросов)",
    }
    
    missing = []
    
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {description}")
        except ImportError:
            missing.append(module)
            print(f"❌ {description}")
    
    if missing:
        print(f"\n⚠️ Отсутствуют: {', '.join(missing)}")
        print(f"Установите: pip install {' '.join(missing)}")
        return False
    
    return True

def main():
    """Точка входа в программу"""
    print("="*60)
    print("🤖 AI BROWSER AGENT v2.1")
    print("="*60)
    
    # Проверяем зависимости
    if not check_dependencies():
        print("\n❌ Не удалось проверить зависимости")
        return
    
    # Проверяем Ollama (предупреждение, но не ошибка)
    has_ollama = check_ollama_connection()
    if not has_ollama:
        print("\n⚠️ AI функции будут ограничены")
        print("Программа продолжит работу с базовым поиском")
    
    print("\n" + "="*60)
    print("🚀 ЗАПУСК ПРОГРАММЫ")
    print("="*60)
    
    # Создаем и запускаем агента
    agent = SimpleAIBrowserAgent()
    
    try:
        agent.interactive_mode()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()