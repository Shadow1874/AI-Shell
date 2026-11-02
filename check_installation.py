"""Check Python dependencies and the local Ollama installation."""

from __future__ import annotations

import importlib.util
import sys


OLLAMA_BASE_URL = "http://localhost:11434"
REQUIRED_MODULES = {
    "customtkinter": "customtkinter",
    "requests": "requests",
    "ddgs": "ddgs",
    "pypdf": "pypdf",
    "python-docx": "docx",
    "openpyxl": "openpyxl",
}


def main() -> int:
    print("AssistantAI Ollama — проверка установки")
    print("=" * 45)

    checks_ok = True
    print(f"Python: {sys.version.split()[0]}", end="")
    if sys.version_info < (3, 10):
        print(" [ОШИБКА: требуется Python 3.10 или новее]")
        checks_ok = False
    else:
        print(" [OK]")

    try:
        import tkinter  # noqa: F401
        print("Tkinter: доступен [OK]")
    except ImportError:
        print("Tkinter: не найден [ОШИБКА]. Установи Python с компонентом Tcl/Tk.")
        checks_ok = False

    print("\nPython-зависимости:")
    for package_name, module_name in REQUIRED_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            print(f"  [ОШИБКА] {package_name}: не установлен")
            checks_ok = False
        else:
            print(f"  [OK] {package_name}")

    print("\nПодключение к Ollama:")
    if importlib.util.find_spec("requests") is None:
        print("  [ПРОПУСК] Нельзя проверить Ollama: сначала установи зависимости из requirements.txt.")
    else:
        import requests

        try:
            version_response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=5)
            version_response.raise_for_status()
            version_data = version_response.json()
            print(f"  [OK] Сервер доступен, версия: {version_data.get('version', 'не указана')}")

            tags_response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
            tags_response.raise_for_status()
            models_data = tags_response.json()
            models = sorted(
                item.get("name", "")
                for item in models_data.get("models", [])
                if item.get("name")
            )
            if models:
                print("  Установленные модели:")
                for model in models:
                    print(f"    - {model}")
            else:
                print("  [ВНИМАНИЕ] Модели не найдены. Загрузи модель командой: ollama pull <имя-модели>")
                checks_ok = False
        except requests.exceptions.ConnectionError:
            print("  [ОШИБКА] Не удалось подключиться к http://localhost:11434.")
            print("  Запусти Ollama и повтори проверку. При необходимости выполни: ollama serve")
            checks_ok = False
        except requests.exceptions.Timeout:
            print("  [ОШИБКА] Ollama не ответила за отведённое время.")
            checks_ok = False
        except (requests.exceptions.RequestException, ValueError) as error:
            print(f"  [ОШИБКА] Не удалось проверить Ollama: {error}")
            checks_ok = False

    print("\nИтог:")
    if checks_ok:
        print("Проверка пройдена. Можно запускать приложение: python main.py")
        return 0
    print("Есть проблемы. Исправь сообщения выше и запусти проверку повторно.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
