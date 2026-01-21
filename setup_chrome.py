#!/usr/bin/env python3
"""
Скрипт для автоматической настройки Chrome и ChromeDriver на Windows
"""

import os
import sys
import subprocess
import requests
import zipfile
import io
import stat
from pathlib import Path

def check_chrome_installed():
    """Проверка установлен ли Chrome"""
    print("🔍 Проверяю установлен ли Google Chrome...")
    
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, "--version"], 
                                      capture_output=True, 
                                      text=True, 
                                      shell=True)
                if result.returncode == 0:
                    print(f"✅ Chrome установлен: {result.stdout.strip()}")
                    return True, path
            except:
                pass
    
    print("❌ Chrome не найден")
    return False, None

def download_chrome():
    """Скачивание установщика Chrome"""
    print("\n📥 Скачиваю установщик Chrome...")
    
    # URL для скачивания Chrome
    chrome_url = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
    
    try:
        response = requests.get(chrome_url, stream=True)
        response.raise_for_status()
        
        installer_path = "chrome_installer.exe"
        with open(installer_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Установщик скачан: {installer_path}")
        return installer_path
        
    except Exception as e:
        print(f"❌ Ошибка скачивания Chrome: {e}")
        return None

def install_chrome(installer_path):
    """Установка Chrome"""
    print("\n⚙️ Устанавливаю Chrome...")
    
    try:
        # Запускаем установщик
        process = subprocess.run([installer_path], 
                               shell=True, 
                               capture_output=True, 
                               text=True)
        
        if process.returncode == 0:
            print("✅ Chrome успешно установлен")
            return True
        else:
            print(f"❌ Ошибка установки: {process.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при запуске установщика: {e}")
        return False

def check_chromedriver():
    """Проверка установлен ли ChromeDriver"""
    print("\n🔍 Проверяю ChromeDriver...")
    
    possible_paths = [
        r"C:\Windows\chromedriver.exe",
        r"C:\Windows\System32\chromedriver.exe",
        "chromedriver.exe",
        str(Path.home() / "chromedriver.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ ChromeDriver найден: {path}")
            return True, path
    
    print("❌ ChromeDriver не найден")
    return False, None

def get_chrome_version():
    """Получение версии Chrome"""
    try:
        chrome_installed, chrome_path = check_chrome_installed()
        if chrome_installed and chrome_path:
            result = subprocess.run([chrome_path, "--version"], 
                                  capture_output=True, 
                                  text=True, 
                                  shell=True)
            if result.returncode == 0:
                version_text = result.stdout.strip()
                # Извлекаем версию (например: Google Chrome 121.0.6167.160)
                import re
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', version_text)
                if match:
                    return match.group(1)
    except:
        pass
    return None

def download_chromedriver():
    """Скачивание ChromeDriver"""
    print("\n📥 Скачиваю ChromeDriver...")
    
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("❌ Не удалось определить версию Chrome")
        return None
    
    # Извлекаем основную версию
    major_version = chrome_version.split('.')[0]
    print(f"Версия Chrome: {chrome_version} (основная: {major_version})")
    
    try:
        # Получаем точную версию ChromeDriver
        version_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        response = requests.get(version_url)
        response.raise_for_status()
        
        exact_version = response.text.strip()
        print(f"Версия ChromeDriver: {exact_version}")
        
        # Скачиваем ChromeDriver
        download_url = f"https://chromedriver.storage.googleapis.com/{exact_version}/chromedriver_win32.zip"
        print(f"Скачиваю: {download_url}")
        
        response = requests.get(download_url)
        response.raise_for_status()
        
        # Распаковываем
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            zip_file.extractall(".")
        
        chromedriver_path = "chromedriver.exe"
        
        # Делаем файл исполняемым
        os.chmod(chromedriver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        
        print(f"✅ ChromeDriver скачан: {chromedriver_path}")
        
        # Копируем в системные папки
        system_paths = [
            r"C:\Windows\chromedriver.exe",
            r"C:\Windows\System32\chromedriver.exe",
        ]
        
        for system_path in system_paths:
            try:
                import shutil
                shutil.copy2(chromedriver_path, system_path)
                print(f"✅ Скопирован в: {system_path}")
            except Exception as e:
                print(f"⚠️ Не удалось скопировать в {system_path}: {e}")
        
        return chromedriver_path
        
    except Exception as e:
        print(f"❌ Ошибка скачивания ChromeDriver: {e}")
        return None

def install_selenium():
    """Установка Selenium и зависимостей"""
    print("\n📦 Устанавливаю Python зависимости...")
    
    try:
        # Обновляем pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True)
        
        # Устанавливаем Selenium и webdriver-manager
        dependencies = [
            "selenium==4.21.0",
            "webdriver-manager==4.0.2",
            "requests",
            "beautifulsoup4",
        ]
        
        for dep in dependencies:
            print(f"Устанавливаю {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                          check=True)
        
        print("✅ Все зависимости установлены")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def test_setup():
    """Тестирование установки"""
    print("\n🧪 Тестирую установку...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.google.com")
        
        print(f"✅ Тест пройден! Браузер запущен: {driver.title}")
        
        driver.quit()
        return True
        
    except Exception as e:
        print(f"❌ Тест не пройден: {e}")
        return False

def main():
    """Основная функция"""
    print("=" * 60)
    print("🛠️  НАСТРОЙКА BROWSER AI AGENT НА WINDOWS")
    print("=" * 60)
    
    # 1. Проверяем Chrome
    chrome_installed, chrome_path = check_chrome_installed()
    
    if not chrome_installed:
        print("\nChrome не установлен. Хотите установить? (y/n)")
        choice = input().lower()
        if choice == 'y':
            installer = download_chrome()
            if installer:
                if install_chrome(installer):
                    # Удаляем установщик
                    os.remove(installer)
                    chrome_installed, chrome_path = check_chrome_installed()
                else:
                    print("Не удалось установить Chrome")
                    return
        else:
            print("Chrome необходим для работы программы")
            return
    
    # 2. Проверяем ChromeDriver
    chromedriver_installed, chromedriver_path = check_chromedriver()
    
    if not chromedriver_installed:
        print("\nChromeDriver не найден. Хотите скачать? (y/n)")
        choice = input().lower()
        if choice == 'y':
            download_chromedriver()
        else:
            print("ChromeDriver необходим для работы программы")
            return
    
    # 3. Устанавливаем Python зависимости
    print("\nХотите установить Python зависимости? (y/n)")
    choice = input().lower()
    if choice == 'y':
        install_selenium()
    
    # 4. Тестируем
    print("\nХотите протестировать установку? (y/n)")
    choice = input().lower()
    if choice == 'y':
        test_setup()
    
    print("\n" + "=" * 60)
    print("✅ НАСТРОЙКА ЗАВЕРШЕНА")
    print("=" * 60)
    print("\nТеперь можно запустить программу:")
    print("python main.py")

if __name__ == "__main__":
    main()