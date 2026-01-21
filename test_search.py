#!/usr/bin/env python3
"""
Тестовый скрипт для проверки поиска на Google
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time

def test_google_search():
    """Тест поиска на Google"""
    print("🔍 Тест поиска на Google")
    print("-" * 40)
    
    # Настройка Chrome
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Запуск браузера
    driver = webdriver.Chrome(options=options)
    
    try:
        # 1. Переходим на Google
        print("1. Перехожу на Google...")
        driver.get("https://www.google.com")
        time.sleep(2)
        print(f"   Заголовок: {driver.title}")
        
        # 2. Ищем поисковую строку
        print("2. Ищу поисковую строку...")
        
        # Пробуем разные селекторы
        search_selectors = [
            "textarea[name='q']",
            "input[name='q']",
            "[aria-label='Поиск']",
            "[title='Поиск']",
        ]
        
        search_element = None
        for selector in search_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        search_element = element
                        print(f"   ✅ Найден: {selector}")
                        break
                if search_element:
                    break
            except:
                continue
        
        if not search_element:
            print("   ❌ Поисковая строка не найдена")
            return False
        
        # 3. Вводим текст
        print("3. Ввожу текст 'рецепт пиццы'...")
        search_element.click()
        search_element.clear()
        search_element.send_keys("рецепт пиццы")
        time.sleep(1)
        
        # 4. Ищем кнопку поиска
        print("4. Ищу кнопку поиска...")
        
        button_selectors = [
            "input[name='btnK']",
            "input[value='Поиск в Google']",
            "button[type='submit']",
        ]
        
        for selector in button_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed():
                        print(f"   ✅ Найдена кнопка: {selector}")
                        button.click()
                        break
                break
            except:
                continue
        else:
            # Если не нашли кнопку, нажимаем Enter
            print("   ⚠️ Кнопка не найдена, нажимаю Enter...")
            search_element.send_keys(Keys.RETURN)
        
        # 5. Ждем результаты
        print("5. Жду результаты...")
        time.sleep(3)
        print(f"   Новый заголовок: {driver.title}")
        
        # 6. Проверяем результаты
        results = driver.find_elements(By.CSS_SELECTOR, "h3")
        print(f"   Найдено результатов: {len(results)}")
        
        if len(results) > 0:
            print(f"   Первый результат: {results[0].text[:50]}...")
        
        # 7. Делаем скриншот
        print("6. Делаю скриншот...")
        driver.save_screenshot("test_search_result.png")
        print("   ✅ Скриншот сохранен: test_search_result.png")
        
        print("\n" + "="*40)
        print("✅ ТЕСТ УСПЕШНО ПРОЙДЕН!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        driver.quit()
        print("Браузер закрыт")

if __name__ == "__main__":
    test_google_search()