from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from typing import Optional, Dict, Any, List
import time
import logging
import os
import sys
from pathlib import Path

from .element_finder import ElementFinder, ElementDescriptor

logger = logging.getLogger(__name__)


class BrowserController:
    """Контроллер для управления браузером с улучшенной обработкой ошибок для Windows"""
    
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.element_finder = None
        self.wait = None
        
    def _setup_chrome_options(self) -> Options:
        """Настройка опций Chrome для Windows"""
        options = Options()
        
        # КРИТИЧЕСКИ ВАЖНЫЕ опции для стабильности на Windows
        options.add_argument("--no-sandbox")  # Обязательно для Windows
        options.add_argument("--disable-dev-shm-usage")  # Обязательно для Windows
        options.add_argument("--disable-gpu")  # Помогает избежать проблем с видеокартой
        
        # Убираем признаки автоматизации
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Отключаем инфопанели и уведомления
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        
        # Отключаем расширения (могут мешать)
        options.add_argument("--disable-extensions")
        
        # Настройки для стабильности
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        # Отключаем сохранение паролей
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,  # Блокировать уведомления
        }
        options.add_experimental_option("prefs", prefs)
        
        # Устанавливаем размер окна если не headless
        if not self.config.HEADLESS:
            options.add_argument(f"--window-size={self.config.WINDOW_WIDTH},{self.config.WINDOW_HEIGHT}")
            options.add_argument("--start-maximized")
        else:
            options.add_argument("--headless=new")  # Новый headless режим
            
        # Устанавливаем язык
        options.add_argument("--lang=ru-RU")
        
        return options
    
    def _find_chrome_driver(self) -> Optional[str]:
        """Поиск ChromeDriver в системе"""
        possible_paths = [
            # Системные пути
            r"C:\Windows\chromedriver.exe",
            r"C:\Windows\System32\chromedriver.exe",
            
            # Папки Chrome
            r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe",
            
            # Путь к Python
            os.path.join(os.path.dirname(sys.executable), "chromedriver.exe"),
            os.path.join(os.path.dirname(sys.executable), "Scripts", "chromedriver.exe"),
            
            # Текущая директория
            "chromedriver.exe",
            
            # Домашняя директория пользователя
            str(Path.home() / "chromedriver.exe"),
            str(Path.home() / "Downloads" / "chromedriver.exe"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Найден ChromeDriver: {path}")
                return path
        
        logger.warning("ChromeDriver не найден в системе")
        return None
    
    def _try_webdriver_manager(self, options: Options) -> Optional[webdriver.Chrome]:
        """Попытка запуска с webdriver-manager"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            
            logger.info("Пробуем использовать webdriver-manager...")
            
            # Создаем сервис с автоматической установкой драйвера
            service = Service(
                ChromeDriverManager().install(),
                service_args=['--verbose']  # Добавляем логирование
            )
            
            # Запускаем драйвер
            driver = webdriver.Chrome(service=service, options=options)
            
            # Скрываем WebDriver
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Браузер запущен через webdriver-manager")
            return driver
            
        except ImportError:
            logger.warning("webdriver-manager не установлен")
            return None
        except Exception as e:
            logger.error(f"Ошибка webdriver-manager: {e}")
            return None
    
    def _try_system_chrome(self, options: Options) -> Optional[webdriver.Chrome]:
        """Попытка запуска с системным Chrome"""
        try:
            logger.info("Пробуем использовать системный Chrome...")
            
            # Пытаемся найти путь к Chrome
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    logger.info(f"Используем Chrome из: {path}")
                    break
            
            # Пытаемся найти ChromeDriver
            chromedriver_path = self._find_chrome_driver()
            
            if chromedriver_path:
                # Используем найденный ChromeDriver
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # Пытаемся без указания пути (будет искать в PATH)
                driver = webdriver.Chrome(options=options)
            
            # Скрываем WebDriver
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Браузер запущен через системный Chrome")
            return driver
            
        except Exception as e:
            logger.error(f"Ошибка системного Chrome: {e}")
            return None
    
    def _try_simple_chrome(self, options: Options) -> Optional[webdriver.Chrome]:
        """Самая простая попытка запуска с минимальными опциями"""
        try:
            logger.info("Пробуем простой запуск Chrome...")
            
            # Создаем минимальные опции
            simple_options = Options()
            simple_options.add_argument("--no-sandbox")
            simple_options.add_argument("--disable-dev-shm-usage")
            
            if self.config.HEADLESS:
                simple_options.add_argument("--headless")
            else:
                simple_options.add_argument("--start-maximized")
            
            # Пробуем запустить
            driver = webdriver.Chrome(options=simple_options)
            
            logger.info("Браузер запущен в простом режиме")
            return driver
            
        except Exception as e:
            logger.error(f"Ошибка простого запуска: {e}")
            return None
    
    def start(self) -> bool:
        """Запуск браузера с несколькими попытками"""
        logger.info("Запуск браузера...")
        
        # Настраиваем опции
        options = self._setup_chrome_options()
        
        # Пробуем разные методы запуска
        methods = [
            self._try_webdriver_manager,
            self._try_system_chrome,
            self._try_simple_chrome,
        ]
        
        for method in methods:
            try:
                logger.info(f"Пробуем метод: {method.__name__}")
                driver = method(options)
                
                if driver:
                    self.driver = driver
                    self.element_finder = ElementFinder(self.driver)
                    self.wait = WebDriverWait(self.driver, 10)
                    
                    # Даем браузеру время на инициализацию
                    time.sleep(2)
                    
                    logger.info("✅ Браузер успешно запущен")
                    return True
                    
            except Exception as e:
                logger.warning(f"Метод {method.__name__} не сработал: {e}")
                continue
        
        # Если все методы не сработали, пробуем последний шанс
        logger.info("Пробуем последний шанс с абсолютно минимальными опциями...")
        try:
            last_options = Options()
            last_options.add_argument("--no-sandbox")
            
            self.driver = webdriver.Chrome(options=last_options)
            self.element_finder = ElementFinder(self.driver)
            self.wait = WebDriverWait(self.driver, 10)
            
            logger.info("✅ Браузер запущен в минимальном режиме")
            return True
            
        except Exception as e:
            logger.error(f"❌ Все методы запуска браузера не сработали: {e}")
            
            # Даем советы пользователю
            self._print_troubleshooting_advice()
            return False
    
    def _print_troubleshooting_advice(self):
        """Печать советов по устранению неполадок"""
        print("\n" + "="*60)
        print("НЕ УДАЛОСЬ ЗАПУСТИТЬ БРАУЗЕР")
        print("="*60)
        print("\nВозможные решения:")
        print("1. Установите Google Chrome если он не установлен")
        print("2. Убедитесь что Chrome обновлен до последней версии")
        print("3. Установите ChromeDriver:")
        print("   - Скачайте с https://chromedriver.chromium.org/")
        print("   - Распакуйте chromedriver.exe в C:\\Windows\\")
        print("\n4. Установите зависимости:")
        print("   pip install --upgrade selenium webdriver-manager")
        print("\n5. Или попробуйте запустить в headless режиме:")
        print("   Измените config.py: HEADLESS = True")
        print("="*60)
    
    def stop(self):
        """Остановка браузера"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Браузер остановлен")
            except Exception as e:
                logger.error(f"Ошибка при остановке браузера: {e}")
        else:
            logger.info("Браузер не был запущен")
    
    def navigate_to(self, url: str) -> Dict[str, Any]:
        """Переход по URL"""
        try:
            # Добавляем протокол если отсутствует
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            logger.info(f"Переход на: {url}")
            
            # Пробуем несколько раз
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    self.driver.get(url)
                    
                    # Ждем загрузки страницы
                    time.sleep(1)  # Базовая задержка
                    
                    # Ждем готовности DOM
                    self.wait.until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                    
                    # Дополнительная пауза для полной загрузки
                    time.sleep(1)
                    
                    logger.info(f"Успешно перешли на: {self.driver.current_url}")
                    
                    return {
                        "success": True,
                        "url": self.driver.current_url,
                        "title": self.driver.title,
                        "message": f"Успешно перешли на {url}"
                    }
                    
                except Exception as e:
                    if attempt == max_attempts - 1:  # Последняя попытка
                        raise
                    logger.warning(f"Попытка {attempt + 1} не удалась: {e}, пробую снова...")
                    time.sleep(1)
            
        except Exception as e:
            logger.error(f"Ошибка при переходе на {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Не удалось перейти на {url}"
            }
    
    def get_page_state(self) -> Dict[str, Any]:
        """Получение текущего состояния страницы"""
        try:
            if not self.driver or not self.element_finder:
                return {
                    "url": "unknown",
                    "title": "Error: Browser not initialized",
                    "page_type": "error",
                    "elements": [],
                    "visible_text_preview": "Браузер не инициализирован",
                    "element_count": 0
                }
            
            return self.element_finder.get_page_state()
            
        except Exception as e:
            logger.error(f"Ошибка при получении состояния страницы: {e}")
            return {
                "url": "unknown",
                "title": "Error",
                "page_type": "error",
                "elements": [],
                "visible_text_preview": f"Error getting page state: {str(e)}",
                "element_count": 0
            }
    
    def click_element(self, element_description: str) -> Dict[str, Any]:
        """Клик по элементу на основе описания от ИИ"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            logger.info(f"Пытаюсь кликнуть на элемент: {element_description}")
            
            element = self.element_finder.find_element_by_description(element_description)
            
            if not element:
                logger.warning(f"Элемент не найден: {element_description}")
                return {
                    "success": False,
                    "error": "Element not found",
                    "message": f"Не удалось найти элемент: {element_description}"
                }
            
            # Прокручиваем к элементу
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
            time.sleep(0.5)
            
            # Даем время на рендеринг
            time.sleep(0.5)
            
            # Пробуем кликнуть несколько раз
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    # Пробуем обычный клик
                    element.click()
                    
                    # Небольшая пауза после клика
                    time.sleep(1)
                    
                    logger.info(f"Успешно кликнули на элемент: {element_description}")
                    
                    return {
                        "success": True,
                        "message": f"Успешно кликнули на элемент: {element_description}",
                        "element_found": True
                    }
                    
                except Exception as click_error:
                    if attempt == max_attempts - 1:
                        raise click_error
                    
                    # Пробуем JavaScript клик
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(1)
                        logger.info(f"Клик через JavaScript успешен: {element_description}")
                        return {
                            "success": True,
                            "message": f"Клик через JavaScript на элемент: {element_description}",
                            "element_found": True
                        }
                    except:
                        continue
            
        except Exception as e:
            logger.error(f"Ошибка при клике: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Ошибка при клике на элемент: {element_description}"
            }
    
    def type_text(self, element_description: str, text: str) -> Dict[str, Any]:
        """Ввод текста в элемент"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            logger.info(f"Ввожу текст '{text}' в элемент: {element_description}")
            
            element = self.element_finder.find_element_by_description(element_description)
            
            if not element:
                return {
                    "success": False,
                    "error": "Element not found",
                    "message": f"Не удалось найти элемент для ввода: {element_description}"
                }
            
            # Прокручиваем к элементу
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            
            # Кликаем и очищаем поле
            element.click()
            time.sleep(0.3)
            
            # Очищаем поле разными способами
            try:
                element.clear()
            except:
                try:
                    element.send_keys(Keys.CONTROL + "a")
                    element.send_keys(Keys.DELETE)
                except:
                    try:
                        element.send_keys(Keys.CONTROL + "a")
                        time.sleep(0.1)
                        element.send_keys(Keys.BACKSPACE)
                    except:
                        pass
            
            time.sleep(0.3)
            
            # Вводим текст посимвольно для надежности
            for char in text:
                element.send_keys(char)
                time.sleep(0.01)  # Минимальная задержка
            
            time.sleep(0.5)
            
            logger.info(f"Текст успешно введен")
            
            return {
                "success": True,
                "message": f"Успешно ввели текст '{text}' в элемент: {element_description}",
                "element_found": True
            }
            
        except Exception as e:
            logger.error(f"Ошибка при вводе текста: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Ошибка при вводе текста в элемент: {element_description}"
            }
    
    def press_key(self, key_name: str) -> Dict[str, Any]:
        """Нажатие клавиши"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            actions = ActionChains(self.driver)
            
            key_mapping = {
                "enter": Keys.ENTER,
                "escape": Keys.ESCAPE,
                "tab": Keys.TAB,
                "backspace": Keys.BACKSPACE,
                "space": Keys.SPACE,
                "arrow_up": Keys.ARROW_UP,
                "arrow_down": Keys.ARROW_DOWN,
                "arrow_left": Keys.ARROW_LEFT,
                "arrow_right": Keys.ARROW_RIGHT,
                "page_up": Keys.PAGE_UP,
                "page_down": Keys.PAGE_DOWN,
                "home": Keys.HOME,
                "end": Keys.END,
                "delete": Keys.DELETE,
                "f5": Keys.F5,
            }
            
            key = key_mapping.get(key_name.lower())
            if not key:
                return {
                    "success": False,
                    "error": "Unknown key",
                    "message": f"Неизвестная клавиша: {key_name}"
                }
            
            logger.info(f"Нажимаю клавишу: {key_name}")
            
            actions.send_keys(key).perform()
            time.sleep(0.5)
            
            return {
                "success": True,
                "message": f"Нажали клавишу {key_name}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при нажатии клавиши: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Ошибка при нажатии клавиши {key_name}"
            }
    
    def scroll(self, direction: str, amount: int = 300) -> Dict[str, Any]:
        """Прокрутка страницы"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            script = ""
            if direction.lower() == "down":
                script = f"window.scrollBy(0, {amount});"
            elif direction.lower() == "up":
                script = f"window.scrollBy(0, -{amount});"
            elif direction.lower() == "top":
                script = "window.scrollTo(0, 0);"
            elif direction.lower() == "bottom":
                script = "window.scrollTo(0, document.body.scrollHeight);"
            else:
                return {
                    "success": False,
                    "error": "Invalid direction",
                    "message": f"Неверное направление прокрутки: {direction}"
                }
            
            logger.info(f"Прокрутка: {direction}")
            
            self.driver.execute_script(script)
            time.sleep(0.5)
            
            return {
                "success": True,
                "message": f"Прокрутили страницу {direction}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при прокрутке: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Ошибка при прокрутке: {direction}"
            }
    
    def go_back(self) -> Dict[str, Any]:
        """Назад в истории"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            logger.info("Возврат на предыдущую страницу")
            
            self.driver.back()
            time.sleep(1.5)  # Даем больше времени на загрузку
            
            return {
                "success": True,
                "message": "Вернулись на предыдущую страницу",
                "current_url": self.driver.current_url
            }
        except Exception as e:
            logger.error(f"Ошибка при возврате назад: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при возврате на предыдущую страницу"
            }
    
    def refresh(self) -> Dict[str, Any]:
        """Обновление страницы"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            logger.info("Обновление страницы")
            
            self.driver.refresh()
            time.sleep(2)  # Даем время на перезагрузку
            
            return {
                "success": True,
                "message": "Обновили страницу",
                "current_url": self.driver.current_url
            }
        except Exception as e:
            logger.error(f"Ошибка при обновлении: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при обновлении страницы"
            }
    
    def take_screenshot(self, path: str = "screenshot.png") -> Dict[str, Any]:
        """Скриншот страницы"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            # Создаем папку если её нет
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            self.driver.save_screenshot(path)
            
            logger.info(f"Скриншот сохранен: {path}")
            
            return {
                "success": True,
                "message": f"Скриншот сохранен как {path}",
                "path": path
            }
        except Exception as e:
            logger.error(f"Ошибка при создании скриншота: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при создании скриншота"
            }
    
    def take_screenshot_base64(self) -> Dict[str, Any]:
        """Скриншот в формате base64"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            screenshot = self.driver.get_screenshot_as_base64()
            
            return {
                "success": True,
                "message": "Скриншот сделан",
                "data": screenshot,
                "format": "base64"
            }
        except Exception as e:
            logger.error(f"Ошибка при создании скриншота base64: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при создании скриншота"
            }
    
    def execute_javascript(self, script: str) -> Dict[str, Any]:
        """Выполнение JavaScript"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            logger.info(f"Выполняю JavaScript: {script[:50]}...")
            
            result = self.driver.execute_script(script)
            
            return {
                "success": True,
                "message": "JavaScript выполнен",
                "result": result
            }
        except Exception as e:
            logger.error(f"Ошибка при выполнении JavaScript: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка при выполнении JavaScript"
            }
    
    def wait_for_element(self, selector: str, timeout: int = 10) -> Dict[str, Any]:
        """Ожидание элемента"""
        try:
            if not self.driver:
                return {
                    "success": False,
                    "error": "Browser not initialized",
                    "message": "Браузер не инициализирован"
                }
            
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            return {
                "success": True,
                "message": f"Элемент {selector} найден",
                "element": element is not None
            }
        except Exception as e:
            logger.error(f"Ошибка при ожидании элемента: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Элемент {selector} не найден за {timeout} секунд"
            }
    
    def get_current_url(self) -> str:
        """Получение текущего URL"""
        if self.driver:
            return self.driver.current_url
        return ""
    
    def get_title(self) -> str:
        """Получение заголовка страницы"""
        if self.driver:
            return self.driver.title
        return ""
    
    def is_browser_alive(self) -> bool:
        """Проверка, жив ли браузер"""
        try:
            if self.driver:
                # Пробуем получить текущий URL
                _ = self.driver.current_url
                return True
        except:
            pass
        return False
    
    def restart_if_needed(self) -> bool:
        """Перезапуск браузера если он умер"""
        if not self.is_browser_alive():
            logger.warning("Браузер не отвечает, пробую перезапустить...")
            self.stop()
            time.sleep(2)
            return self.start()
        return True