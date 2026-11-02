
from pathlib import Path
import csv

TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".pyw", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".log", ".sql", ".sh", ".bat", ".cmd",
    ".ps1", ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".java",
    ".kt", ".go", ".rs", ".php", ".rb", ".swift", ".r", ".ipynb",
}
MAX_FILE_CHARS = 45_000


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "cp866", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_file_text(filename: str) -> str:
    path = Path(filename)
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        text = _read_text(path)
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"[Страница {i}]\n{page_text}")
        text = "\n\n".join(pages)
    elif suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table_index, table in enumerate(doc.tables, 1):
            parts.append(f"[Таблица {table_index}]")
            for row in table.rows:
                parts.append(" | ".join(cell.text.replace("\n", " ") for cell in row.cells))
        text = "\n".join(parts)
    elif suffix == ".xlsx":
        from openpyxl import load_workbook
        workbook = load_workbook(str(path), read_only=True, data_only=True)
        parts = []
        for sheet in workbook.worksheets:
            parts.append(f"[Лист: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                values = ["" if value is None else str(value) for value in row]
                if any(values):
                    parts.append(" | ".join(values))
        workbook.close()
        text = "\n".join(parts)
    elif suffix == ".csv":
        raw = _read_text(path)
        try:
            dialect = csv.Sniffer().sniff(raw[:4096], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = csv.reader(raw.splitlines(), dialect)
        text = "\n".join(" | ".join(row) for row in rows)
    else:
        raise ValueError(f"Формат {suffix or '(без расширения)'} не поддерживается.")

    text = text.strip()
    if not text:
        return "[Текст не найден. Возможно, PDF состоит из сканов или документ пуст.]"
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + "\n\n[Файл обрезан: достигнут лимит извлечения текста. Для больших документов понадобится RAG/разбиение на фрагменты.]"
    return text


def build_file_context(paths: list[str], max_chars: int = 24_000) -> str:

    blocks = []
    remaining = max(1_000, int(max_chars))
    for filename in paths:
        path = Path(filename)
        try:
            content = extract_file_text(filename)
        except ImportError as error:
            missing = str(error).split("No module named")[-1].strip(" '\"")
            blocks.append(f"\n[Файл: {path.name}] Не установлен пакет для чтения этого формата ({missing}). Установи зависимости из requirements.txt.")
            continue
        except Exception as error:
            blocks.append(f"\n[Файл: {path.name}] Ошибка чтения: {error}")
            continue
        if remaining <= 0:
            blocks.append("\n[Остальные файлы пропущены: достигнут общий лимит контекста файлов.]")
            break
        content = content[:remaining]
        remaining -= len(content)
        blocks.append(f"\n===== НАЧАЛО ФАЙЛА: {path.name} =====\n{content}\n===== КОНЕЦ ФАЙЛА: {path.name} =====")
    return "\n\n".join(blocks)
