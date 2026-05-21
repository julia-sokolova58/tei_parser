#!/usr/bin/env python3

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import fitz


class ExtractTextApp:
    """Графический интерфейс для извлечения текстового слоя из нескольких PDF."""

    def __init__(self, root):
        self.root = root
        self.root.title("Извлечение текстового слоя из PDF (пакетная обработка)")
        self.root.geometry("750x600")
        self.root.resizable(True, True)

        self.pdf_dir = "pdf"
        self.default_output = "pdf_text"
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.default_output, exist_ok=True)

        self.selected_files = []
        self.output_dir = tk.StringVar(value=self.default_output)
        self.page_files = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="Готов к работе")

        self.create_widgets()
        self.refresh_file_list()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="PDF-файлы в папке 'pdf':").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.file_listbox = tk.Listbox(
            main_frame, selectmode=tk.MULTIPLE, height=8, width=70
        )
        self.file_listbox.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)

        scrollbar = ttk.Scrollbar(
            main_frame, orient="vertical", command=self.file_listbox.yview
        )
        scrollbar.grid(row=1, column=3, sticky="ns")
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        ttk.Button(
            main_frame, text="Обновить список", command=self.refresh_file_list
        ).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(
            main_frame, text="Выбрать все", command=self.select_all_files
        ).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(
            main_frame, text="Очистить выбор", command=self.clear_selection
        ).grid(row=2, column=2, padx=5, pady=5)

        ttk.Label(main_frame, text="Выходная папка:").grid(
            row=3, column=0, sticky="w", pady=5
        )
        ttk.Entry(main_frame, textvariable=self.output_dir, width=50).grid(
            row=3, column=1, sticky="ew", pady=5
        )
        ttk.Button(main_frame, text="Обзор…", command=self.browse_output).grid(
            row=3, column=2, padx=5
        )

        ttk.Checkbutton(
            main_frame,
            text="Сохранять постранично (отдельные файлы)",
            variable=self.page_files,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=5)

        ttk.Button(
            main_frame,
            text="Извлечь текст из выбранных файлов",
            command=self.run_extract,
        ).grid(row=5, column=0, columnspan=3, pady=10)

        ttk.Label(main_frame, text="Статус:").grid(row=6, column=0, sticky="w")
        self.status_label = ttk.Label(
            main_frame, textvariable=self.status_text, foreground="blue"
        )
        self.status_label.grid(row=6, column=1, columnspan=2, sticky="w")

        self.log_text = tk.Text(main_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=5)

        scrollbar_log = ttk.Scrollbar(
            main_frame, orient="vertical", command=self.log_text.yview
        )
        scrollbar_log.grid(row=7, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar_log.set)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)

    def refresh_file_list(self):
        try:
            files = [f for f in os.listdir(self.pdf_dir) if f.lower().endswith(".pdf")]
            self.file_listbox.delete(0, tk.END)
            for f in files:
                self.file_listbox.insert(tk.END, f)
            if files:
                self.status_text.set(f"Найдено {len(files)} PDF-файлов")
            else:
                self.status_text.set("PDF-файлы не найдены. Поместите файлы в папку 'pdf'")
            self.selected_files = []
        except Exception as e:
            self.status_text.set(f"Ошибка: {e}")

    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)

    def clear_selection(self):
        self.file_listbox.select_clear(0, tk.END)

    def browse_output(self):
        directory = filedialog.askdirectory(title="Выберите выходную папку")
        if directory:
            self.output_dir.set(directory)

    def run_extract(self):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("Ошибка", "Выберите хотя бы один PDF-файл")
            return

        self.selected_files = [self.file_listbox.get(i) for i in selected_indices]
        self.log_text.delete(1.0, tk.END)
        self._log(f"Выбрано файлов: {len(self.selected_files)}")
        self._log(f"{', '.join(self.selected_files)}")
        self._log("")

        thread = threading.Thread(target=self._extract_thread)
        thread.daemon = True
        thread.start()

    def _log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    def _update_status(self, message):
        self.status_text.set(message)
        self.root.update()

    def _extract_thread(self):
        try:
            output_dir = self.output_dir.get()
            page_files = self.page_files.get()
            total_files = len(self.selected_files)

            for idx, filename in enumerate(self.selected_files, 1):
                pdf_path = os.path.join(self.pdf_dir, filename)
                self._update_status(f"Обработка: {filename} ({idx}/{total_files})")
                self._log(f"--- {filename} ---")

                base_name = os.path.splitext(filename)[0]
                output_folder = os.path.join(output_dir, base_name)
                os.makedirs(output_folder, exist_ok=True)

                doc = fitz.open(pdf_path)
                total_pages = doc.page_count
                self._log(f"Страниц: {total_pages}")

                all_text = []
                for page_num in range(total_pages):
                    page = doc[page_num]
                    text = page.get_text()
                    all_text.append(text)

                    if page_files:
                        out_file = os.path.join(output_folder, f"{page_num + 1}.txt")
                        with open(out_file, "w", encoding="utf-8") as f:
                            f.write(text.strip())

                doc.close()

                full_text = "\n\n".join(all_text)
                out_full = os.path.join(output_dir, f"{base_name}.txt")
                with open(out_full, "w", encoding="utf-8") as f:
                    f.write(full_text)

                self._log(f"  Общий файл: {out_full}")
                self._log(f"  Постраничные файлы: {output_folder}")
                self._log("")

            self._update_status("Готово! Обработка завершена.")
            self._log("\n Все файлы обработаны.")
            messagebox.showinfo("Успех", f"Обработано {total_files} файлов.\nРезультаты в папке: {output_dir}")

        except Exception as e:
            self._update_status(f"Ошибка: {e}")
            self._log(f"\n Ошибка: {e}")
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ExtractTextApp(root)
    root.mainloop()