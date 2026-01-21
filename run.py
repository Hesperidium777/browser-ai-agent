#!/usr/bin/env python3
"""
Простой запуск AI Browser Agent
"""

import subprocess
import sys
import os

def check_and_install():
    """Проверка и установка зависимостей"""
    
    print("🔍 Проверяю зависимости...")
    
    # Проверяем Python
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Требуется Python 3.8 или выше")
        return False
    
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Список зависимостей
    dependencies = [
        "selenium",
        "requests", 
        "beautifulsoup4"
    ]
    
    # Проверяем каждую
    missing = []
    for dep in dependencies:
        try:
            __import__(dep.replace("-", "_"))
            print(f"✅ {dep}")
        except ImportError:
            missing.append(dep)
            print(f"❌ {dep}")
    
    # Устанавливаем недостающие
    if missing:
        print(f"\n📦 Устанавливаю недостающие зависимости...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ Зависимости установлены")
        except subprocess.CalledProcessError:
            print("❌ Не удалось установить зависимости")
            print("Попробуйте вручную: pip install " + " ".join(missing))
            return False
    
    return True

def check_ollama():
    """Проверка Ollama"""
    import requests
    
    print("\n🔍 Проверяю Ollama...")
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                print("✅ Ollama запущена")
                print("Доступные модели:")
                for model in models[:3]:  # Показываем первые 3
                    print(f"  - {model.get('name', 'unknown')}")
                return True
            else:
                print("⚠️ Ollama запущена, но нет моделей")
                print("Загрузите модель: ollama pull llama3.2:3b")
        else:
            print("❌ Ollama не отвечает")
    except:
        print("❌ Ollama не запущена")
        print("\nЧтобы запустить Ollama:")
        print("1. Скачайте с https://ollama.com/")
        print("2. Установите и запустите")
        print("3. В терминале выполните: ollama pull llama3.2:3b")
        print("4. Запустите: ollama serve")
    
    return False

def main():
    """Основная функция"""
    print("="*60)
    print("🚀 AI BROWSER AGENT - БЫСТРЫЙ ЗАПУСК")
    print("="*60)
    
    # Проверяем зависимости
    if not check_and_install():
        return
    
    # Проверяем Ollama (необязательно для теста)
    check_ollama()
    
    print("\n" + "="*60)
    print("🎯 ВАРИАНТЫ ЗАПУСКА:")
    print("1. Полная версия с AI (требуется Ollama)")
    print("2. Тестовая версия без AI")
    print("3. Простой тест браузера")
    print("="*60)
    
    choice = input("\nВыберите вариант (1-3): ").strip()
    
    if choice == "1":
        # Запуск полной версии
        print("\nЗапуск полной версии...")
        try:
            from main import main as main_full
            main_full()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("\nПопробуйте вариант 2 или 3")
    
    elif choice == "2":
        # Тестовая версия без AI
        print("\nЗапуск тестовой версии...")
        try:
            test_browser_without_ai()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    elif choice == "3":
        # Простой тест браузера
        print("\nЗапуск простого теста...")
        try:
            simple_browser_test()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    else:
        print("❌ Неверный выбор")

def test_browser_without_ai():
    """Тест браузера без AI"""
    from browser.controller import BrowserController
    from config import Config
    
    print("Тест браузера...")
    
    config = Config(HEADLESS=False)
    browser = BrowserController(config)
    
    if browser.start():
        print("✅ Браузер запущен")
        
        # Простой сценарий
        print("1. Открываю Google...")
        browser.navigate_to("https://www.google.com")
        time.sleep(2)
        
        print("2. Ищу информацию...")
        browser.type_text("поле поиска", "погода в Москве")
        time.sleep(1)
        browser.press_key("enter")
        time.sleep(3)
        
        print("3. Делаю скриншот...")
        browser.take_screenshot("test_result.png")
        
        print(f"✅ Тест завершен!")
        print(f"Страница: {browser.get_title()}")
        print(f"Скриншот: test_result.png")
        
        browser.stop()
    else:
        print("❌ Не удалось запустить браузер")

def simple_browser_test():
    """Самый простой тест браузера"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    print("Простой тест Chrome...")
    
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=options)
        
        print("✅ Chrome запущен")
        
        driver.get("https://www.google.com")
        print(f"Заголовок: {driver.title}")
        
        # Делаем скриншот
        driver.save_screenshot("simple_test.png")
        print("Скриншот: simple_test.png")
        
        driver.quit()
        print("✅ Тест пройден успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\nРешение проблем:")
        print("1. Установите Chrome: https://www.google.com/chrome/")
        print("2. Скачайте ChromeDriver: https://chromedriver.chromium.org/")
        print("3. Поместите chromedriver.exe в C:\\Windows\\")

if __name__ == "__main__":
    import time
    main()