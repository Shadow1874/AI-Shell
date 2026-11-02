import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, filedialog

import customtkinter as ctk
import requests

from core.assistant import Assistant, DEFAULT_MODEL, get_local_models
from core.file_reader import build_file_context
from core.model_brand import get_model_brand

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_DIR = Path(__file__).resolve().parent
if os.name == "nt":
    _config_root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
else:
    _config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
APP_DATA_DIR = _config_root / "AssistantAI-Ollama"
SETTINGS_FILE = APP_DATA_DIR / "settings.json"
LEGACY_SETTINGS_FILE = APP_DIR / "settings.json"
DEFAULT_SETTINGS = {"num_ctx": 8192}
CONTEXT_OPTIONS = {
    "4K": 4096,
    "8K": 8192,
    "16K": 16384,
    "32K": 32768,
    "64K": 65536,
    "128K": 131072,
    "256K": 262144,
}


def load_settings():
    """Load per-user settings, migrating the old project-local file if present."""
    settings = DEFAULT_SETTINGS.copy()
    source = SETTINGS_FILE if SETTINGS_FILE.exists() else LEGACY_SETTINGS_FILE
    try:
        if source.exists():
            loaded = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                value = loaded.get("num_ctx")
                if isinstance(value, int) and not isinstance(value, bool):
                    settings["num_ctx"] = value
    except (OSError, json.JSONDecodeError):
        pass

    if settings["num_ctx"] not in CONTEXT_OPTIONS.values():
        settings["num_ctx"] = DEFAULT_SETTINGS["num_ctx"]

    # Best-effort migration: do not prevent startup if the profile directory
    # cannot be created (for example, on a read-only account).
    if source == LEGACY_SETTINGS_FILE and source.exists() and not SETTINGS_FILE.exists():
        try:
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(
                json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass
    return settings


def save_settings(settings):
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class AssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local AI Assistant")
        self.geometry("1160x850")
        self.minsize(850, 680)

        self.assistant = Assistant()
        self.events = queue.Queue()
        self.is_generating = False
        self.is_loading_models = False
        self.settings = load_settings()
        self.selected_files = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_settings()
        self._build_chat()
        self._build_controls()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._process_events)
        self.after(150, self.refresh_models)

        self._append_message(
            "Ассистент",
            "Привет! Выбери установленную модель Ollama. Размер контекста "
            "можно менять в панели выше. Без интернет-поиска "
            "чат работает локально.",
        )

    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 7))
        header.grid_columnconfigure(1, weight=1)
        self.brand_title_label = ctk.CTkLabel(
            header, text="Local AI Assistant",
            font=ctk.CTkFont(size=23, weight="bold")
        )
        self.brand_title_label.grid(row=0, column=0, sticky="w", padx=18, pady=(12, 2))
        self.brand_subtitle_label = ctk.CTkLabel(
            header, text="Локальные модели Ollama",
            text_color="gray"
        )
        self.brand_subtitle_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        model_area = ctk.CTkFrame(header, fg_color="transparent")
        model_area.grid(row=0, column=1, rowspan=2, sticky="e", padx=14, pady=12)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.model_menu = ctk.CTkComboBox(
            model_area, variable=self.model_var,
            values=[DEFAULT_MODEL], width=270, state="readonly",
            command=self._on_model_selected,
        )
        self.model_menu.pack(side="left", padx=(0, 8))
        self.refresh_button = ctk.CTkButton(
            model_area, text="Обновить", width=100, command=self.refresh_models
        )
        self.refresh_button.pack(side="left")
        self._update_branding(DEFAULT_MODEL)

    def _on_model_selected(self, selected_model: str):
        """Update app and chat branding as soon as another model is selected."""
        self._update_branding(selected_model)
        if hasattr(self, "status_label"):
            brand = self.current_brand
            self.status_label.configure(
                text=f"Выбрана модель {selected_model} · {brand.company}"
            )

    def _update_branding(self, model_name: str | None = None):
        selected = (model_name if model_name is not None else self.model_var.get()).strip()
        self.current_brand = get_model_brand(selected)
        app_title = self.current_brand.app_title
        self.title(app_title)
        self.brand_title_label.configure(text=app_title)
        if selected:
            subtitle = (
                f"Модель: {selected} · семейство: {self.current_brand.display_name}"
                f" · разработчик: {self.current_brand.company}"
            )
        else:
            subtitle = "Локальные модели Ollama"
        self.brand_subtitle_label.configure(text=subtitle)

    def _build_settings(self):
        panel = ctk.CTkFrame(self, corner_radius=12)
        panel.grid(row=1, column=0, sticky="ew", padx=16, pady=7)
        panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Размер контекста",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=14, pady=10)

        self.context_var = tk.StringVar(value=self._context_label(self.settings["num_ctx"]))
        self.context_menu = ctk.CTkComboBox(
            panel, variable=self.context_var, values=list(CONTEXT_OPTIONS),
            state="readonly", width=150
        )
        self.context_menu.grid(row=0, column=1, sticky="w", padx=12, pady=10)

        self.apply_button = ctk.CTkButton(
            panel, text="Применить", command=self.apply_settings, width=120
        )
        self.apply_button.grid(row=0, column=2, sticky="e", padx=14, pady=10)

        self.settings_note = ctk.CTkLabel(
            panel,
            text="Контекст применяется к следующим запросам. Большие значения требуют больше оперативной и видеопамяти.",
            text_color="gray", font=ctk.CTkFont(size=11), wraplength=1000, justify="left"
        )
        self.settings_note.grid(row=1, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 10))

    def _context_label(self, value):
        for label, number in CONTEXT_OPTIONS.items():
            if number == value:
                return label
        return "8K"

    @staticmethod
    def _gpu_label(value):
        return "Авто" if value == 99 else ("0 (CPU)" if value == 0 else str(value))

    def _build_chat(self):
        self.chat = ctk.CTkTextbox(
            self, corner_radius=12, wrap="word",
            font=ctk.CTkFont(size=14), activate_scrollbars=True
        )
        self.chat.grid(row=2, column=0, sticky="nsew", padx=16, pady=7)
        self.chat.configure(state="disabled")

    def _build_controls(self):
        controls = ctk.CTkFrame(self, corner_radius=12)
        controls.grid(row=3, column=0, sticky="ew", padx=16, pady=(7, 16))
        controls.grid_columnconfigure(0, weight=1)
        self.message_entry = ctk.CTkEntry(
            controls, placeholder_text="Напиши сообщение и нажми Enter...", height=42
        )
        self.message_entry.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 8))
        self.message_entry.bind("<Return>", self._on_enter)

        self.thinking_var = tk.BooleanVar(value=False)
        self.web_var = tk.BooleanVar(value=False)
        self.coding_var = tk.BooleanVar(value=False)
        self.thinking_checkbox = ctk.CTkCheckBox(
            controls, text="Режим раздумья (XHIGH)", variable=self.thinking_var
        )
        self.thinking_checkbox.grid(row=1, column=0, sticky="w", padx=14, pady=7)
        self.web_checkbox = ctk.CTkCheckBox(
            controls, text="Интернет-поиск", variable=self.web_var
        )
        self.web_checkbox.grid(row=1, column=1, sticky="w", padx=14, pady=7)
        self.coding_checkbox = ctk.CTkCheckBox(
            controls, text="Режим кодинга", variable=self.coding_var
        )
        self.coding_checkbox.grid(row=2, column=0, sticky="w", padx=14, pady=(3, 8))

        self.attach_button = ctk.CTkButton(
            controls, text="Добавить файлы", width=130, height=34,
            fg_color="transparent", border_width=1, command=self.attach_files
        )
        self.attach_button.grid(row=2, column=1, sticky="w", padx=12, pady=(0, 8))
        self.files_label = ctk.CTkLabel(
            controls, text="Файлы не выбраны", text_color="gray", anchor="w"
        )
        self.files_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 5))
        self.remove_files_button = ctk.CTkButton(
            controls, text="Убрать файлы", width=110, height=28,
            fg_color="transparent", border_width=1, command=self.remove_files
        )
        self.remove_files_button.grid(row=3, column=2, sticky="e", padx=12, pady=(0, 5))

        self.send_button = ctk.CTkButton(
            controls, text="Отправить", width=130, height=36, command=self.send_message
        )
        self.send_button.grid(row=1, column=2, sticky="e", padx=12, pady=7)
        self.clear_button = ctk.CTkButton(
            controls, text="Очистить чат", width=130, height=34,
            fg_color="transparent", border_width=1, command=self.clear_chat
        )
        self.clear_button.grid(row=2, column=2, sticky="e", padx=12, pady=(0, 8))
        self.status_label = ctk.CTkLabel(controls, text="Подключение к Ollama...", text_color="gray")
        self.status_label.grid(row=4, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 10))

    def attach_files(self):
        filetypes = [
            ("Поддерживаемые документы", "*.pdf *.docx *.txt *.md *.py *.cpp *.h *.hpp *.js *.ts *.html *.css *.json *.xml *.yaml *.yml *.toml *.ini *.log *.sql *.csv *.xlsx"),
            ("PDF", "*.pdf"),
            ("Word DOCX", "*.docx"),
            ("Excel XLSX и CSV", "*.xlsx *.csv"),
            ("Текст и исходный код", "*.txt *.md *.py *.cpp *.h *.hpp *.js *.ts *.html *.css *.json *.xml *.yaml *.yml *.toml *.ini *.log *.sql"),
            ("Все файлы", "*.*"),
        ]
        paths = filedialog.askopenfilenames(title="Выбери файлы для анализа", filetypes=filetypes)
        if not paths:
            return
        known = set(self.selected_files)
        for path in paths:
            if path not in known:
                self.selected_files.append(path)
                known.add(path)
        names = [Path(path).name for path in self.selected_files]
        preview = ", ".join(names[:3])
        if len(names) > 3:
            preview += f" и ещё {len(names) - 3}"
        self.files_label.configure(text=f"Выбрано файлов: {len(names)} · {preview}")
        self.status_label.configure(text="Файлы выбраны локально. Они будут прочитаны при отправке запроса.")

    def remove_files(self):
        self.selected_files.clear()
        self.files_label.configure(text="Файлы не выбраны")

    def apply_settings(self):
        if self.is_generating:
            messagebox.showinfo("Запрос выполняется", "Дождись завершения генерации перед изменением контекста.")
            return

        context = CONTEXT_OPTIONS.get(self.context_var.get())
        if context is None:
            messagebox.showwarning("Контекст", "Выбери размер контекста из списка.")
            return

        new_settings = {"num_ctx": context}
        try:
            save_settings(new_settings)
        except OSError as error:
            messagebox.showerror(
                "Не удалось сохранить настройки",
                f"Путь: {SETTINGS_FILE}\nПричина: {error}",
            )
            return

        self.settings = new_settings
        messagebox.showinfo(
            "Настройки сохранены",
            f"Размер контекста: {context:,} токенов.\n\n"
            "Новое значение будет использоваться при следующих запросах. "
            "При необходимости Ollama перезагрузит модель."
        )
        self.status_label.configure(
            text=f"Настройки сохранены · контекст {self._context_label(context)}"
        )

    def refresh_models(self):
        if self.is_loading_models:
            return
        self.is_loading_models = True
        self.refresh_button.configure(state="disabled", text="Загрузка...")
        threading.Thread(target=self._load_models_worker, daemon=True).start()

    def _load_models_worker(self):
        try:
            self.events.put(("models", get_local_models()))
        except requests.exceptions.ConnectionError:
            self.events.put(("models_error", "Не удалось подключиться к Ollama. Запусти Ollama."))
        except requests.exceptions.RequestException as error:
            self.events.put(("models_error", f"Не удалось получить список моделей: {error}"))
        finally:
            self.events.put(("models_done", None))

    def _append_message(self, author: str, text: str):
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{author}:\n{text}\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _append_stream_chunk(self, chunk: str):
        self.chat.configure(state="normal")
        self.chat.insert("end", chunk)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def send_message(self):
        if self.is_generating:
            return
        question = self.message_entry.get().strip()
        if not question:
            return
        selected_model = self.model_var.get().strip()
        if not selected_model:
            messagebox.showwarning("Модель не выбрана", "Сначала выбери модель Ollama.")
            return
        try:
            self.assistant.set_model(selected_model)
        except ValueError as error:
            messagebox.showwarning("Модель не выбрана", str(error))
            return

        self._update_branding(selected_model)
        self.message_entry.delete(0, "end")
        self._append_message("Вы", question)
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{self.current_brand.assistant_name} ({selected_model}):\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

        self.is_generating = True
        for widget in (self.send_button, self.clear_button, self.message_entry,
                       self.model_menu, self.refresh_button, self.apply_button):
            widget.configure(state="disabled")

        thinking, web_search, coding_mode = self.thinking_var.get(), self.web_var.get(), self.coding_var.get()
        self.status_label.configure(text=f"{selected_model} · подготовка запроса...")
        settings = self.settings.copy()
        selected_files = self.selected_files.copy()
        threading.Thread(
            target=self._generate_answer,
            args=(question, thinking, web_search, coding_mode, selected_model, settings, selected_files),
            daemon=True,
        ).start()

    def _generate_answer(self, question, thinking, web_search, coding_mode, model, settings, selected_files):
        try:
            file_context = ""
            if selected_files:
                self.events.put(("status", "Чтение выбранных файлов..."))
                file_context = build_file_context(
                    selected_files, max_chars=int(settings["num_ctx"] * 2.5)
                )
            for chunk in self.assistant.ask(
                question=question, thinking=thinking, web_search=web_search,
                coding_mode=coding_mode, model=model,
                num_ctx=settings["num_ctx"],
                file_context=file_context,
            ):
                self.events.put(("chunk", chunk))
        except Exception as error:
            self.events.put(("chunk", f"\n[Ошибка] {error}"))
        finally:
            self.events.put(("done", None))

    def _process_events(self):
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "chunk":
                    self._append_stream_chunk(payload)
                elif event == "status":
                    self.status_label.configure(text=payload)
                elif event == "models":
                    models = payload or []
                    current = self.model_var.get()
                    if models:
                        self.model_menu.configure(values=models)
                        selected = current if current in models else (DEFAULT_MODEL if DEFAULT_MODEL in models else models[0])
                        self.model_var.set(selected)
                        self._update_branding(selected)
                        self.status_label.configure(text=f"Найдено моделей: {len(models)}")
                    else:
                        self.model_menu.configure(values=[])
                        self.status_label.configure(
                            text="Моделей не найдено · установи модель командой: ollama pull <имя>"
                        )
                elif event == "models_error":
                    self.status_label.configure(text=payload)
                elif event == "models_done":
                    self.is_loading_models = False
                    self.refresh_button.configure(state="normal", text="Обновить")
                elif event == "done":
                    self.chat.configure(state="normal")
                    self.chat.insert("end", "\n\n")
                    self.chat.see("end")
                    self.chat.configure(state="disabled")
                    self.is_generating = False
                    for widget in (self.send_button, self.clear_button, self.message_entry,
                                   self.model_menu, self.refresh_button, self.apply_button):
                        widget.configure(state="normal")
                    self.model_menu.configure(state="readonly")
                    self.message_entry.focus_set()
                    self.status_label.configure(text="Готово · локальная модель Ollama")
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def clear_chat(self):
        if self.is_generating:
            return
        self.assistant.clear_history()
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self.status_label.configure(text="История диалога очищена")

    def _on_enter(self, _event):
        self.send_message()
        return "break"

    def _on_close(self):
        self.destroy()


if __name__ == "__main__":
    app = AssistantApp()
    app.mainloop()
