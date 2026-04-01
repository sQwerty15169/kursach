import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog


APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "notes.json"
LOG_FILE = APP_DIR / "app.log"
CONFIG_FILE = APP_DIR / "config.json"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


@dataclass
class Note:
    title: str
    content: str
    created_at: str
    updated_at: str


class NotesRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[Note]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [Note(**item) for item in raw]
        except Exception as exc:
            logging.exception("Ошибка чтения заметок: %s", exc)
            return []

    def save(self, notes: list[Note]) -> None:
        serialized = [asdict(note) for note in notes]
        self.path.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ConfigRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_theme(self) -> str:
        if not self.path.exists():
            return "light"
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get("theme", "light")
        except Exception:
            return "light"

    def save_theme(self, theme: str) -> None:
        self.path.write_text(
            json.dumps({"theme": theme}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class NotesApp:
    THEMES = {
        "light": {"bg": "#f4f6f8", "fg": "#1c1f23", "box": "#ffffff", "accent": "#0057b8"},
        "dark": {"bg": "#1b1f24", "fg": "#f1f5f9", "box": "#2a3038", "accent": "#4aa3ff"},
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Курсовой проект: Менеджер заметок")
        self.root.geometry("920x560")

        self.repo = NotesRepository(DATA_FILE)
        self.config = ConfigRepository(CONFIG_FILE)
        self.notes = self.repo.load()
        self.filtered_indexes: list[int] = list(range(len(self.notes)))
        self.current_index: int | None = None
        self.theme_name = self.config.load_theme()

        self._build_ui()
        self.apply_theme()
        self.refresh_list()
        logging.info("Приложение запущено")

    def _build_ui(self) -> None:
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=8, pady=8)

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(toolbar, textvariable=self.search_var, width=36)
        search_entry.pack(side=tk.LEFT, padx=(0, 8))
        search_entry.bind("<KeyRelease>", lambda _e: self.search_notes())

        tk.Button(toolbar, text="Новая", command=self.create_note).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Сохранить", command=self.save_current_note).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Удалить", command=self.delete_note).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Сменить тему", command=self.toggle_theme).pack(side=tk.LEFT, padx=4)

        self.main = tk.Frame(self.root)
        self.main.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.listbox = tk.Listbox(self.main, width=34)
        self.listbox.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_note)

        editor = tk.Frame(self.main)
        editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(editor, textvariable=self.title_var, font=("Segoe UI", 12, "bold"))
        self.title_entry.pack(fill=tk.X, pady=(0, 8))

        self.meta_label = tk.Label(editor, text="", anchor="w")
        self.meta_label.pack(fill=tk.X, pady=(0, 8))

        self.text = tk.Text(editor, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True)

    def apply_theme(self) -> None:
        theme = self.THEMES.get(self.theme_name, self.THEMES["light"])
        self.root.configure(bg=theme["bg"])
        for widget in [self.main, self.listbox.master, self.title_entry.master]:
            widget.configure(bg=theme["bg"])
        self.listbox.configure(
            bg=theme["box"],
            fg=theme["fg"],
            selectbackground=theme["accent"],
            selectforeground="#ffffff",
        )
        self.title_entry.configure(bg=theme["box"], fg=theme["fg"], insertbackground=theme["fg"])
        self.text.configure(bg=theme["box"], fg=theme["fg"], insertbackground=theme["fg"])
        self.meta_label.configure(bg=theme["bg"], fg=theme["fg"])

    def refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for idx in self.filtered_indexes:
            note = self.notes[idx]
            self.listbox.insert(tk.END, note.title or "(без названия)")

    def search_notes(self) -> None:
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_indexes = list(range(len(self.notes)))
        else:
            self.filtered_indexes = [
                i for i, note in enumerate(self.notes)
                if query in note.title.lower() or query in note.content.lower()
            ]
        self.current_index = None
        self.clear_editor()
        self.refresh_list()

    def create_note(self) -> None:
        title = simpledialog.askstring("Новая заметка", "Введите заголовок:")
        if title is None:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note = Note(title=title.strip(), content="", created_at=now, updated_at=now)
        self.notes.append(note)
        self.repo.save(self.notes)
        logging.info("Добавлена заметка: %s", note.title)
        self.search_notes()

    def on_select_note(self, _event=None) -> None:
        if not self.listbox.curselection():
            return
        visible_index = self.listbox.curselection()[0]
        self.current_index = self.filtered_indexes[visible_index]
        note = self.notes[self.current_index]
        self.title_var.set(note.title)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", note.content)
        self.meta_label.config(
            text=f"Создано: {note.created_at}    Обновлено: {note.updated_at}"
        )

    def save_current_note(self) -> None:
        if self.current_index is None:
            messagebox.showwarning("Внимание", "Сначала выберите заметку в списке.")
            return
        note = self.notes[self.current_index]
        note.title = self.title_var.get().strip() or "(без названия)"
        note.content = self.text.get("1.0", tk.END).rstrip()
        note.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.repo.save(self.notes)
        self.meta_label.config(
            text=f"Создано: {note.created_at}    Обновлено: {note.updated_at}"
        )
        self.search_notes()
        logging.info("Сохранена заметка: %s", note.title)
        messagebox.showinfo("Готово", "Изменения сохранены.")

    def delete_note(self) -> None:
        if self.current_index is None:
            messagebox.showwarning("Внимание", "Выберите заметку для удаления.")
            return
        title = self.notes[self.current_index].title
        if not messagebox.askyesno("Подтверждение", f"Удалить заметку «{title}»?"):
            return
        del self.notes[self.current_index]
        self.repo.save(self.notes)
        logging.info("Удалена заметка: %s", title)
        self.current_index = None
        self.search_notes()

    def toggle_theme(self) -> None:
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.config.save_theme(self.theme_name)
        self.apply_theme()
        logging.info("Тема переключена на: %s", self.theme_name)

    def clear_editor(self) -> None:
        self.title_var.set("")
        self.text.delete("1.0", tk.END)
        self.meta_label.config(text="")


def main() -> None:
    root = tk.Tk()
    app = NotesApp(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
