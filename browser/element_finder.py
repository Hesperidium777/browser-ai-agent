from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ElementDescriptor:
    """Описание элемента для ИИ"""
    tag_name: str
    attributes: Dict[str, str]
    text: str
    visible_text: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    is_visible: bool
    is_interactable: bool
    xpath: str
    role: Optional[str] = None
    
    def to_ai_description(self) -> str:
        """Преобразование в описание для ИИ"""
        description = f"Элемент <{self.tag_name}>"
        
        if self.role:
            description += f" с ролью '{self.role}'"
        
        if self.attributes.get('id'):
            description += f" id='{self.attributes['id']}'"
        
        if self.attributes.get('class'):
            classes = ' '.join(self.attributes['class'].split()[:2])
            description += f" class='{classes}'"
        
        # Добавляем текст если он короткий
        display_text = self.text if self.text else self.visible_text
        if display_text and len(display_text) < 100:
            description += f" текст: '{display_text}'"
        
        if self.attributes.get('placeholder'):
            description += f" placeholder: '{self.attributes['placeholder']}'"
        
        if self.attributes.get('name'):
            description += f" name: '{self.attributes['name']}'"
        
        if self.attributes.get('type'):
            description += f" тип: {self.attributes['type']}"
        
        if self.attributes.get('aria-label'):
            description += f" aria-label: '{self.attributes['aria-label']}'"
        
        description += f" (видимый: {self.is_visible}, кликабельный: {self.is_interactable})"
        
        return description

class ElementFinder:
    """Улучшенный поиск и анализ элементов страницы"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def get_page_state(self) -> Dict[str, Any]:
        """Получение текущего состояния страницы"""
        try:
            url = self.driver.current_url
            title = self.driver.title
            
            # Получаем основные элементы
            elements = self._get_interactive_elements()
            
            # Получаем видимый текст страницы
            visible_text = self._get_visible_text()
            
            # Определяем тип страницы
            page_type = self._detect_page_type(url, title, elements)
            
            # Специальная обработка для Google
            if "google.com" in url:
                page_type = "search_engine"
                # Добавляем специальные элементы Google
                elements.extend(self._get_google_specific_elements())
            
            return {
                "url": url,
                "title": title,
                "page_type": page_type,
                "elements": [elem.to_ai_description() for elem in elements],
                "visible_text_preview": visible_text[:300] + "..." if len(visible_text) > 300 else visible_text,
                "element_count": len(elements),
                "is_search_page": "google.com" in url or "search" in url.lower() or "поиск" in visible_text.lower()
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении состояния страницы: {e}")
            return {
                "url": "unknown",
                "title": "Error",
                "page_type": "error",
                "elements": [],
                "visible_text_preview": f"Error getting page state: {str(e)}",
                "element_count": 0,
                "is_search_page": False
            }
    
    def _get_google_specific_elements(self) -> List[ElementDescriptor]:
        """Получение специальных элементов Google"""
        elements = []
        
        # Поисковая строка Google
        search_selectors = [
            "textarea[name='q']",
            "input[name='q']",
            "[aria-label='Поиск']",
            "[title='Поиск']",
            "input[type='text'][title='Поиск']",
            "input[aria-label='Найти']",
        ]
        
        for selector in search_selectors:
            try:
                found = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in found:
                    if elem.is_displayed():
                        descriptor = self._describe_element(elem)
                        descriptor.role = "search_box"
                        elements.append(descriptor)
                        break
            except:
                continue
        
        # Кнопка поиска Google
        button_selectors = [
            "input[value='Поиск в Google']",
            "input[type='submit'][value*='Поиск']",
            "[aria-label='Поиск в Google']",
            "button[type='submit']",
            "input[name='btnK']",
        ]
        
        for selector in button_selectors:
            try:
                found = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in found:
                    if elem.is_displayed():
                        descriptor = self._describe_element(elem)
                        descriptor.role = "search_button"
                        elements.append(descriptor)
                        break
            except:
                continue
        
        return elements
    
    def _get_interactive_elements(self) -> List[ElementDescriptor]:
        """Получение интерактивных элементов страницы"""
        interactive_selectors = [
            "a", "button", "input", "textarea", "select",
            "[role='button']", "[role='link']", "[role='menuitem']",
            "[onclick]", "[tabindex]", "[contenteditable='true']",
            "[type='submit']", "[type='button']",
        ]
        
        elements = []
        for selector in interactive_selectors:
            try:
                found = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in found[:5]:  # Ограничиваем количество
                    try:
                        if elem.is_displayed():
                            descriptor = self._describe_element(elem)
                            elements.append(descriptor)
                    except:
                        continue
            except:
                continue
        
        # Убираем дубликаты по xpath
        unique_elements = {}
        for elem in elements:
            unique_elements[elem.xpath] = elem
        
        return list(unique_elements.values())[:20]  # Ограничиваем количество
    
    def _describe_element(self, element: WebElement) -> ElementDescriptor:
        """Создание описания элемента"""
        try:
            tag_name = element.tag_name.lower()
            text = element.text.strip() if element.text else ""
            
            # Получаем атрибуты
            attributes = {}
            try:
                attrs = self.driver.execute_script(
                    "var items = {}; "
                    "for (index = 0; index < arguments[0].attributes.length; ++index) {"
                    "  items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value"
                    "}; "
                    "return items;", element
                )
                
                for key, value in attrs.items():
                    if key in ['id', 'class', 'href', 'src', 'type', 'placeholder', 
                              'aria-label', 'aria-describedby', 'name', 'value', 'title',
                              'role', 'autocomplete', 'maxlength']:
                        attributes[key] = value
            except:
                pass
            
            # Определяем роль элемента
            role = attributes.get('role')
            if not role:
                if tag_name in ['button', 'a']:
                    role = tag_name
                elif tag_name == 'input':
                    input_type = attributes.get('type', 'text')
                    role = f"input_{input_type}"
            
            # Проверяем кликабельность
            is_interactable = False
            try:
                is_interactable = element.is_enabled() and element.is_displayed()
            except:
                pass
            
            # Получаем позицию и размер
            location = {'x': 0, 'y': 0}
            size = {'width': 0, 'height': 0}
            try:
                location = element.location
                size = element.size
            except:
                pass
            
            # Получаем видимый текст
            visible_text = self._get_element_visible_text(element)
            
            # Генерируем XPath
            xpath = self._generate_simple_xpath(element)
            
            return ElementDescriptor(
                tag_name=tag_name,
                attributes=attributes,
                text=text,
                visible_text=visible_text,
                position=(location['x'], location['y']),
                size=(size['width'], size['height']),
                is_visible=element.is_displayed(),
                is_interactable=is_interactable,
                xpath=xpath,
                role=role
            )
            
        except Exception as e:
            logger.error(f"Ошибка при описании элемента: {e}")
            # Возвращаем минимальное описание
            return ElementDescriptor(
                tag_name="unknown",
                attributes={},
                text="",
                visible_text="",
                position=(0, 0),
                size=(0, 0),
                is_visible=False,
                is_interactable=False,
                xpath="//unknown"
            )
    
    def _get_element_visible_text(self, element: WebElement) -> str:
        """Получение видимого текста элемента"""
        try:
            # Используем JavaScript для получения только видимого текста
            script = """
            var element = arguments[0];
            var text = '';
            
            function getVisibleText(node) {
                if (node.nodeType === Node.TEXT_NODE) {
                    var parent = node.parentNode;
                    var style = window.getComputedStyle(parent);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        var trimmed = node.textContent.trim();
                        if (trimmed) {
                            text += ' ' + trimmed;
                        }
                    }
                } else {
                    for (var i = 0; i < node.childNodes.length; i++) {
                        getVisibleText(node.childNodes[i]);
                    }
                }
            }
            
            getVisibleText(element);
            return text.trim();
            """
            
            text = self.driver.execute_script(script, element)
            return text if text else ""
        except:
            return ""
    
    def _generate_simple_xpath(self, element: WebElement) -> str:
        """Генерация простого XPath для элемента"""
        try:
            # Пробуем использовать id если есть
            element_id = element.get_attribute('id')
            if element_id:
                return f"//*[@id='{element_id}']"
            
            # Пробуем использовать name если есть
            element_name = element.get_attribute('name')
            if element_name:
                return f"//*[@name='{element_name}']"
            
            # Генерируем путь по тегам
            script = """
            function getElementXPath(element) {
                if (element.id !== '')
                    return '//*[@id=\"' + element.id + '\"]';
                if (element === document.body)
                    return '/html/body';
                    
                var ix = 0;
                var siblings = element.parentNode.childNodes;
                
                for (var i = 0; i < siblings.length; i++) {
                    var sibling = siblings[i];
                    if (sibling === element)
                        return getElementXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                        ix++;
                }
            }
            return getElementXPath(arguments[0]);
            """
            
            return self.driver.execute_script(script, element)
        except:
            return "//unknown"
    
    def _get_visible_text(self) -> str:
        """Получение видимого текста страницы"""
        try:
            # Получаем весь текст body
            body = self.driver.find_element(By.TAG_NAME, "body")
            text = body.text.strip()
            
            # Очищаем текст от лишних пробелов
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return ' '.join(lines[:10])  # Ограничиваем количество строк
        except:
            return ""
    
    def _detect_page_type(self, url: str, title: str, elements: List[ElementDescriptor]) -> str:
        """Определение типа страницы"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        # Проверяем по URL
        if "google.com" in url_lower:
            return "search_engine"
        elif "login" in url_lower or "auth" in url_lower or "signin" in url_lower:
            return "login"
        elif "search" in url_lower or "поиск" in title_lower:
            return "search"
        elif "youtube.com" in url_lower:
            return "video"
        elif "amazon.com" in url_lower or "market" in url_lower:
            return "shopping"
        elif "news" in url_lower or "новости" in title_lower:
            return "news"
        
        # Проверяем по элементам
        element_texts = ' '.join([elem.text.lower() + ' ' + elem.visible_text.lower() 
                                 for elem in elements])
        
        if any(x in element_texts for x in ["поиск", "search", "найти"]):
            return "search"
        elif any(x in element_texts for x in ["логин", "пароль", "войти", "email"]):
            return "login"
        elif any(x in element_texts for x in ["корзина", "купить", "добавить в корзину"]):
            return "shopping"
        
        return "general"
    
    def find_element_by_description(self, description: str) -> Optional[WebElement]:
        """Поиск элемента по описанию от ИИ"""
        try:
            logger.info(f"Поиск элемента по описанию: {description}")
            
            # Сначала пробуем найти по специальным ролям
            if "поиск" in description.lower() or "search" in description.lower():
                # Ищем поисковую строку
                search_selectors = [
                    "textarea[name='q']",
                    "input[name='q']",
                    "[aria-label='Поиск']",
                    "[title='Поиск']",
                    "input[type='text'][title='Поиск']",
                    "[name='search']",
                    "[role='searchbox']",
                    "input[type='search']",
                ]
                
                for selector in search_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                logger.info(f"Найден элемент поиска: {selector}")
                                return elem
                    except:
                        continue
            
            elif "кнопка" in description.lower() or "button" in description.lower():
                # Ищем кнопки
                button_selectors = [
                    "button",
                    "input[type='submit']",
                    "input[type='button']",
                    "[role='button']",
                ]
                
                for selector in button_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                # Проверяем текст кнопки
                                elem_text = elem.text.lower()
                                desc_lower = description.lower()
                                if any(word in elem_text for word in ["поиск", "search", "найти", "искать"]):
                                    logger.info(f"Найденa кнопка поиска: {elem_text}")
                                    return elem
                                elif elem_text and len(elem_text) < 20:
                                    logger.info(f"Найденa кнопка: {elem_text}")
                                    return elem
                    except:
                        continue
            
            # Общий поиск по тексту
            text_match = re.search(r'текст:\s*[\'"]([^\'"]+)[\'"]', description)
            if text_match:
                target_text = text_match.group(1)
                try:
                    # Ищем по точному совпадению текста
                    elements = self.driver.find_elements(By.XPATH, 
                        f"//*[text()='{target_text}' or contains(text(), '{target_text}')]")
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            logger.info(f"Найден элемент по тексту: {target_text}")
                            return elem
                except:
                    pass
            
            # Поиск по атрибутам
            attr_patterns = [
                (r"id='([^']+)'", "id"),
                (r"placeholder='([^']+)'", "placeholder"),
                (r"name='([^']+)'", "name"),
            ]
            
            for pattern, attr in attr_patterns:
                match = re.search(pattern, description)
                if match:
                    value = match.group(1)
                    try:
                        elements = self.driver.find_elements(By.XPATH, f"//*[@{attr}='{value}']")
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                logger.info(f"Найден элемент по {attr}: {value}")
                                return elem
                    except:
                        continue
            
            # Если ничего не нашли, возвращаем первый интерактивный элемент
            interactive_elements = self._get_interactive_elements()
            for elem_desc in interactive_elements[:5]:
                try:
                    elem = self.driver.find_element(By.XPATH, elem_desc.xpath)
                    if elem.is_displayed() and elem.is_enabled():
                        logger.info(f"Возвращаю первый интерактивный элемент: {elem_desc.tag_name}")
                        return elem
                except:
                    continue
            
            logger.warning(f"Элемент не найден: {description}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске элемента: {e}")
            return None