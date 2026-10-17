"""Графический интерфейс на Tkinter."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Union

from crypto_utils import (
    generate_salt, derive_key, hash_master_password, CryptoManager
)
from database import Database
from password_generator import generate_password, password_strength
from export_import import export_to_json, import_from_json
from exporters import export_to_excel, export_to_pdf


class PasswordManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Менеджер паролей")
        self.root.geometry("950x600") # Чуть шире для новых кнопок

        self.db = Database()
        self.crypto = None

        self._build_login_frame()
        self._build_main_frame()

        if not self.db.is_initialized():
            self.show_setup()
        else:
            self.show_login()

    # ---------- Экраны входа ----------
    def _build_login_frame(self):
        self.login_frame = ttk.Frame(self.root, padding=40)

        ttk.Label(self.login_frame, text="Менеджер паролей",
                  font=("Segoe UI", 18, "bold")).pack(pady=10)

        self.login_label = ttk.Label(self.login_frame, text="Мастер-пароль:")
        self.login_label.pack(anchor="w", pady=(20, 4))

        self.login_entry = ttk.Entry(self.login_frame, show="*", width=40)
        self.login_entry.pack(pady=4)
        self.login_entry.bind("<Return>", lambda e: self._login_action())

        self.login_btn = ttk.Button(self.login_frame, text="Войти",
                                    command=self._login_action)
        self.login_btn.pack(pady=10)
        
        self.login_extra_frame = ttk.Frame(self.login_frame)
        self.login_extra_frame.pack(pady=5)

        self.forgot_btn = ttk.Button(self.login_extra_frame, text="Забыли пароль? (Справка)",
                                     command=self._forgot_password)

        self.login_hint = ttk.Label(self.login_frame, text="", foreground="red")
        self.login_hint.pack(pady=10)

    def show_setup(self):
        self.login_frame.pack(expand=True)
        self.login_label.config(text="Придумайте мастер-пароль:")
        self.login_btn.config(text="Создать хранилище", command=self._create_vault)
        self.forgot_btn.pack_forget()

    def show_login(self):
        self.login_frame.pack(expand=True)
        self.login_label.config(text="Мастер-пароль:")
        self.login_btn.config(text="Войти", command=self._login_action)
        self.forgot_btn.pack(side="top", pady=2)
        self.login_entry.focus_set()

    def _forgot_password(self):
        messagebox.showinfo("Забыли пароль? (Справка)", 
            "К сожалению, восстановить мастер-пароль невозможно.\n\n"
            "База данных зашифрована надежным алгоритмом (AES). Без ключа "
            "расшифровать данные нельзя — это гарантирует безопасность.\n\n"
            "Если у вас есть резервная копия (Экспорт JSON) и вы помните "
            "пароль от неё — вы можете удалить файл vault.db и импортировать данные заново.")

    def _create_vault(self):
        pwd = self.login_entry.get()
        if len(pwd) < 6:
            self.login_hint.config(text="Пароль должен быть ≥ 6 символов")
            return
            
        salt = generate_salt()
        master_hash = hash_master_password(pwd, salt)
        key = derive_key(pwd, salt)
        crypto = CryptoManager(key)
        check_token = crypto.encrypt("VAULT_OK")
        self.db.save_meta(salt, master_hash, check_token)
        
        messagebox.showinfo("Готово", "Хранилище создано. Запомните мастер-пароль!")
        self.login_entry.delete(0, tk.END)
        self.login_hint.config(text="")
        self.show_login()

    def _login_action(self):
        pwd = self.login_entry.get()
        meta = self.db.get_meta()
        if not meta:
            messagebox.showerror("Ошибка", "Хранилище не инициализировано")
            return

        key = derive_key(pwd, meta["salt"])
        crypto = CryptoManager(key)
        try:
            token = crypto.decrypt(meta["check_token"])
        except Exception:
            self.login_hint.config(text="Неверный мастер-пароль")
            return

        if token != "VAULT_OK":
            self.login_hint.config(text="Неверный мастер-пароль")
            return

        self.crypto = crypto
        self.login_hint.config(text="")
        self.login_entry.delete(0, tk.END)
        self.login_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.refresh_list()

    # ---------- Основной экран ----------
    def _build_main_frame(self):
        self.main_frame = ttk.Frame(self.root, padding=10)

        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill="x", pady=(0, 8))

        ttk.Button(toolbar, text="+ Новая запись", command=self._new_entry).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Изменить", command=self._edit_entry).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Удалить выбранные", command=self._delete_selected).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Удалить всё", command=self._delete_all).pack(side="left", padx=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        
        # Кнопки экспорта
        ttk.Button(toolbar, text="Экспорт JSON", command=self._export_json).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Экспорт Excel", command=self._export_excel).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Экспорт PDF", command=self._export_pdf).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Импорт JSON", command=self._import).pack(side="left", padx=2)
        
        ttk.Button(toolbar, text="Выйти", command=self._logout).pack(side="right", padx=2)

        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(search_frame, text="Поиск:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=6)

        columns = ("title", "username", "strength", "updated")
        # selectmode="extended" позволяет выделять несколько строк (Shift + клик или Ctrl + клик)
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        
        # Список для хранения ID выбранных записей
        self.selected_ids = set()
        for col, text, w in [
            ("title", "Название", 220),
            ("username", "Логин", 180),
            ("strength", "Надёжность", 130),
            ("updated", "Обновлено", 160),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self._edit_entry())
        self._id_map = {}

    def _logout(self):
        if not messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            return
        self.crypto = None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._id_map.clear()
        self.search_var.set("") 
        self.main_frame.pack_forget()
        self.login_entry.delete(0, tk.END)
        self.show_login()

    def _get_decrypted_entries(self) -> list:
        """Возвращает список расшифрованных записей для экспорта."""
        result = []
        for e in self.db.get_all_entries():
            try:
                title = self.crypto.decrypt(e["title"])
                username = self.crypto.decrypt(e["username"])
                password = self.crypto.decrypt(e["password"])
                notes = self.crypto.decrypt(e["notes"]) if e["notes"] else ""
            except Exception:
                continue # Пропускаем битые записи

            raw_date = e["updated_at"]
            date_str = raw_date
            if raw_date and len(raw_date) >= 16:
                date_str = f"{raw_date[8:10]}.{raw_date[5:7]}.{raw_date[0:4]} {raw_date[11:16]}"

            result.append({
                "title": title, "username": username, "password": password, 
                "notes": notes, "strength": password_strength(password), "date": date_str
            })
        return result

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._id_map.clear()

        query = self.search_var.get().lower().strip()
        for e in self.db.get_all_entries():
            try:
                title = self.crypto.decrypt(e["title"])
                username = self.crypto.decrypt(e["username"])
                password = self.crypto.decrypt(e["password"])
            except Exception:
                title, username, password = "<ошибка>", "", ""

            if query and query not in title.lower() and query not in username.lower():
                continue

            raw_date = e["updated_at"]
            formatted_date = raw_date
            if raw_date and len(raw_date) >= 16:
                formatted_date = f"{raw_date[8:10]}.{raw_date[5:7]}.{raw_date[0:4]} {raw_date[11:16]}"

            iid = self.tree.insert("", "end", values=(
                title, username, password_strength(password), formatted_date
            ))
            self._id_map[iid] = e["id"]

    def _new_entry(self):
        EntryDialog(self.root, self.crypto, self.db, on_save=self.refresh_list)

    def _edit_entry(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Инфо", "Выберите запись")
            return
        entry_id = self._id_map[sel[0]]
        record = self.db.get_entry(entry_id)
        EntryDialog(self.root, self.crypto, self.db, record=record, on_save=self.refresh_list)

    def _on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        entry_id = self._id_map.get(item)
        if not entry_id:
            return

        # Если запись уже выбрана - убираем её из списка и снимаем подсветку
        if entry_id in self.selected_ids:
            self.selected_ids.remove(entry_id)
            self.tree.item(item, tags=())
        # Если не выбрана - добавляем и красим в серый цвет
        else:
            self.selected_ids.add(entry_id)
            self.tree.item(item, tags=("selected",))
        
        # Применяем стиль для серого фона
        self.tree.tag_configure("selected", background="#e0e0e0")

    def _select_all(self):
        # Выделяем все записи
        self.selected_ids.clear()
        for item in self.tree.get_children():
            self.selected_ids.add(self._id_map[item])
            self.tree.item(item, tags=("selected",))

    # ---------- Удаление ----------
    def _delete_selected(self):
        if not self.selected_ids:
            messagebox.showinfo("Инфо", "Выберите записи для удаления (кликните по ним мышкой)")
            return
        
        count = len(self.selected_ids)
        if not messagebox.askyesno("Удаление", f"Удалить выбранные записи ({count} шт.)?"):
            return
            
        for entry_id in self.selected_ids:
            self.db.delete_entry(entry_id)
        
        self.selected_ids.clear()
        self.refresh_list()

    def _delete_all(self):
        if not messagebox.askyesno("Удаление всего", "Вы уверены, что хотите удалить ВСЕ записи?\nЭто действие нельзя отменить."):
            return
        
        # Удаляем все записи из БД
        entries = self.db.get_all_entries()
        for e in entries:
            self.db.delete_entry(e["id"])
        self.refresh_list()

    # ---------- Экспорт / Импорт ----------
    def _export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")], title="Экспорт базы"
        )
        if not path: return
        n = export_to_json(self.db, path)
        messagebox.showinfo("Экспорт", f"Экспортировано записей: {n}")

    def _export_excel(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Экспорт в Excel"
        )
        if not path: return
        try:
            entries = self._get_decrypted_entries()
            export_to_excel(entries, path)
            messagebox.showinfo("Экспорт", "Успешно экспортировано в Excel!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")

    def _export_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], title="Экспорт в PDF"
        )
        if not path: return
        try:
            entries = self._get_decrypted_entries()
            export_to_pdf(entries, path)
            messagebox.showinfo("Экспорт", "Успешно экспортировано в PDF!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], title="Импорт базы")
        if not path: return
        try:
            n = import_from_json(self.db, self.crypto, path)
            messagebox.showinfo("Импорт", f"Импортировано записей: {n}")
            self.refresh_list()
        except Exception as exc:
            messagebox.showerror("Ошибка импорта", str(exc))


class EntryDialog(tk.Toplevel):
    def __init__(self, parent, crypto: CryptoManager, db: Database,
                 record: Union[dict, None] = None, on_save=None):
        super().__init__(parent)
        self.crypto = crypto
        self.db = db
        self.record = record
        self.on_save = on_save

        self.title("Редактирование" if record else "Новая запись")
        self.geometry("520x480")
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 10, "pady": 4}

        ttk.Label(self, text="Название:").pack(anchor="w", **pad)
        self.title_e = ttk.Entry(self)
        self.title_e.pack(fill="x", **pad)

        ttk.Label(self, text="Логин:").pack(anchor="w", **pad)
        self.user_e = ttk.Entry(self)
        self.user_e.pack(fill="x", **pad)

        ttk.Label(self, text="Пароль:").pack(anchor="w", **pad)
        pwd_frame = ttk.Frame(self)
        pwd_frame.pack(fill="x", **pad)
        self.pwd_e = ttk.Entry(pwd_frame, show="*")
        self.pwd_e.pack(side="left", fill="x", expand=True)
        ttk.Button(pwd_frame, text="👁", width=3, command=self._toggle_pwd).pack(side="left", padx=2)
        ttk.Button(pwd_frame, text="🎲 Сгенерировать", command=self._generate_pwd).pack(side="left", padx=2)

        self.show_pwd = False
        self.strength_label = ttk.Label(self, text="", foreground="gray")
        self.strength_label.pack(anchor="w", padx=10)
        self.pwd_e.bind("<KeyRelease>", self._update_strength)

        ttk.Label(self, text="Заметки:").pack(anchor="w", **pad)
        self.notes_t = tk.Text(self, height=8, wrap="word")
        self.notes_t.pack(fill="both", expand=True, **pad)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)
        ttk.Button(btn_frame, text="Сохранить", command=self._save).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Отмена", command=self.destroy).pack(side="right")

        if record:
            self._load_record(record)

    def _load_record(self, rec):
        try:
            self.title_e.insert(0, self.crypto.decrypt(rec["title"]))
            self.user_e.insert(0, self.crypto.decrypt(rec["username"]))
            self.pwd_e.insert(0, self.crypto.decrypt(rec["password"]))
            if rec.get("notes"):
                self.notes_t.insert("1.0", self.crypto.decrypt(rec["notes"]))
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось расшифровать запись: {exc}")
            self.destroy()

    def _toggle_pwd(self):
        self.show_pwd = not self.show_pwd
        self.pwd_e.config(show="" if self.show_pwd else "*")

    def _generate_pwd(self):
        pwd = generate_password(20)
        self.pwd_e.delete(0, tk.END)
        self.pwd_e.insert(0, pwd)
        self.show_pwd = True
        self.pwd_e.config(show="")
        self._update_strength()

    def _update_strength(self, event=None):
        s = password_strength(self.pwd_e.get())
        colors = {"Очень слабый": "red", "Слабый": "orange", "Средний": "#b58900", "Сильный": "green", "Очень сильный": "darkgreen"}
        self.strength_label.config(text=f"Надёжность: {s}", foreground=colors.get(s, "gray"))

    def _save(self):
        title = self.title_e.get().strip()
        username = self.user_e.get().strip()
        password = self.pwd_e.get()
        notes = self.notes_t.get("1.0", "end").rstrip("\n")

        if not title:
            messagebox.showwarning("Внимание", "Введите название")
            return
        if not password:
            messagebox.showwarning("Внимание", "Введите пароль")
            return

        t = self.crypto.encrypt(title)
        u = self.crypto.encrypt(username)
        p = self.crypto.encrypt(password)
        n = self.crypto.encrypt(notes) if notes else b""

        if self.record:
            self.db.update_entry(self.record["id"], t, u, p, n)
        else:
            self.db.add_entry(t, u, p, n)

        if self.on_save:
            self.on_save()
        self.destroy()