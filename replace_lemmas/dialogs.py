import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


class DoubtfulDialog(tk.Toplevel):
    def __init__(self, parent, doubtful_list):
        super().__init__(parent)
        self.title("Сомнительные леммы – ручная проверка")
        self.geometry("950x500")
        self.doubtful = doubtful_list
        self.decisions = {}
        self.result = False

        for item in self.doubtful:
            self.decisions[item['old_id']] = ('accept', item['new_lemma'])

        cols = ('page', 'old_lemma', 'new_lemma', 'sim', 'action')
        self.tree = ttk.Treeview(self, columns=cols, show='headings', selectmode='extended')
        self.tree.heading('page', text='Страница')
        self.tree.heading('old_lemma', text='Старая лемма')
        self.tree.heading('new_lemma', text='Новая лемма (Excel)')
        self.tree.heading('sim', text='Сходство')
        self.tree.heading('action', text='Действие')
        self.tree.column('page', width=60, anchor='center')
        self.tree.column('old_lemma', width=200)
        self.tree.column('new_lemma', width=200)
        self.tree.column('sim', width=70, anchor='center')
        self.tree.column('action', width=150)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for item in self.doubtful:
            self.tree.insert('', 'end', iid=item['old_id'],
                             values=(item['page'], item['old_lemma'], item['new_lemma'],
                                     item['similarity'], 'Принять'))

        frm_actions = tk.Frame(self)
        frm_actions.pack(fill=tk.X, padx=10, pady=(0,10))
        tk.Button(frm_actions, text="Принять выбранное", command=lambda: self.set_selected('accept')).pack(side=tk.LEFT, padx=5)
        tk.Button(frm_actions, text="Оставить выбранное", command=lambda: self.set_selected('keep')).pack(side=tk.LEFT, padx=5)
        tk.Button(frm_actions, text="Своя лемма для выбранного...", command=lambda: self.set_selected('custom')).pack(side=tk.LEFT, padx=5)

        frm_btns = tk.Frame(self)
        frm_btns.pack(pady=5)
        tk.Button(frm_btns, text="Применить все и закрыть", command=self.on_apply, bg="lightgreen").pack(side=tk.LEFT, padx=10)
        tk.Button(frm_btns, text="Отмена (ничего не менять)", command=self.destroy).pack(side=tk.LEFT, padx=10)

    def set_selected(self, action):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Не выбрано", "Выделите строки в таблице")
            return
        for rowid in selected:
            if action == 'accept':
                new_lemma = self.tree.set(rowid, 'new_lemma')
                self.decisions[rowid] = ('accept', new_lemma)
                self.tree.set(rowid, 'action', 'Принять')
            elif action == 'keep':
                self.decisions[rowid] = ('keep',)
                self.tree.set(rowid, 'action', 'Оставить')
            elif action == 'custom':
                old = self.tree.set(rowid, 'old_lemma')
                new = simpledialog.askstring("Своя лемма",
                                             f"Старая: {old}\nНовая из Excel: {self.tree.set(rowid, 'new_lemma')}\nВведите свою лемму:",
                                             parent=self)
                if new:
                    self.decisions[rowid] = ('custom', new)
                    self.tree.set(rowid, 'action', f"Своя: {new}")

    def on_apply(self):
        self.result = True
        self.destroy()


class MismatchDialog(tk.Toplevel):
    def __init__(self, parent, mismatch_list):
        super().__init__(parent)
        self.title("Сопоставление лемм (разное количество на странице)")
        self.geometry("1200x650")
        self.mismatch = mismatch_list
        self.lemma_decisions = {}
        self.page_decisions = {}
        self.result = False

        canvas = tk.Canvas(self, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.widgets = []
        for page_info in self.mismatch:
            page = page_info['page']
            parsed = page_info['parsed']
            excel = page_info['excel']
            prev_excel = page_info.get('prev_excel', [])
            next_excel = page_info.get('next_excel', [])

            frm_page = tk.LabelFrame(self.scrollable_frame,
                                     text=f"Страница {page} (Excel: {len(excel)} лемм, парсинг: {len(parsed)} статей)",
                                     padx=10, pady=10)
            frm_page.pack(fill=tk.X, padx=10, pady=5)

            header = tk.Frame(frm_page)
            header.pack(fill=tk.X, pady=2)
            tk.Label(header, text="Текущая лемма", width=20, anchor='w', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
            tk.Label(header, text="Новая лемма", width=20, anchor='w', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
            tk.Label(header, text="Источник", width=12, anchor='w', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
            tk.Label(header, text="Страница", width=6, font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)

            btn_frame = tk.Frame(frm_page)
            btn_frame.pack(fill=tk.X, pady=3)
            if prev_excel:
                tk.Button(btn_frame, text=f"← Вставить все с пред. стр. ({page-1})",
                         command=lambda p=page, pl=prev_excel: self.insert_all_neighbor(p, pl, 'prev')).pack(side=tk.LEFT, padx=5)
            if next_excel:
                tk.Button(btn_frame, text=f"Вставить все со след. стр. ({page+1}) →",
                         command=lambda p=page, nl=next_excel: self.insert_all_neighbor(p, nl, 'next')).pack(side=tk.LEFT, padx=5)

            for old_id, old_lemma in parsed:
                row = tk.Frame(frm_page)
                row.pack(fill=tk.X, pady=2)

                tk.Label(row, text=old_lemma, width=20, anchor='w', fg='gray').pack(side=tk.LEFT, padx=5)

                combo_var = tk.StringVar()
                combo = ttk.Combobox(row, textvariable=combo_var, state='readonly', width=20)
                all_options = [''] + excel
                if prev_excel:
                    all_options += [f"[пред. стр.] {l}" for l in prev_excel]
                if next_excel:
                    all_options += [f"[след. стр.] {l}" for l in next_excel]
                combo['values'] = all_options
                combo.pack(side=tk.LEFT, padx=5)

                source_var = tk.StringVar(value="—")
                tk.Label(row, textvariable=source_var, width=12, anchor='w', fg='blue').pack(side=tk.LEFT, padx=5)

                page_var = tk.StringVar(value=str(page))
                page_entry = tk.Entry(row, textvariable=page_var, width=6)
                page_entry.pack(side=tk.LEFT, padx=5)

                self.page_decisions[old_id] = page

                def update_source(event, sv=source_var, cv=combo_var, pe=prev_excel, ne=next_excel, ex=excel):
                    val = cv.get()
                    if val.startswith('[пред. стр.]'):
                        sv.set('пред. стр.')
                    elif val.startswith('[след. стр.]'):
                        sv.set('след. стр.')
                    elif val in ex:
                        sv.set('Excel')
                    elif val == '':
                        sv.set('—')
                    else:
                        sv.set('своя')

                combo.bind('<<ComboboxSelected>>', update_source)

                from .utils import similarity
                best_match = None
                best_sim = 0.0
                for el in excel:
                    sim = similarity(old_lemma, el)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = el
                if best_match and best_sim > 0.5:
                    combo_var.set(best_match)
                    source_var.set('Excel')
                    self.lemma_decisions[old_id] = best_match
                else:
                    for el in prev_excel + next_excel:
                        sim = similarity(old_lemma, el)
                        if sim > best_sim:
                            best_sim = sim
                            best_match = el
                    if best_match and best_sim > 0.5:
                        if best_match in prev_excel:
                            combo_var.set(f"[пред. стр.] {best_match}")
                            source_var.set('пред. стр.')
                        else:
                            combo_var.set(f"[след. стр.] {best_match}")
                            source_var.set('след. стр.')
                        self.lemma_decisions[old_id] = best_match
                    else:
                        combo_var.set('')

                def make_keep_cmd(oid, olemma, cv, sv):
                    def cmd():
                        cv.set(olemma)
                        sv.set('оставлена')
                        self.lemma_decisions[oid] = olemma
                    return cmd

                tk.Button(row, text="Оставить", command=make_keep_cmd(old_id, old_lemma, combo_var, source_var),
                         width=8).pack(side=tk.LEFT, padx=2)

                def make_custom_cmd(oid, olemma, cv, sv):
                    def cmd():
                        new = simpledialog.askstring("Своя лемма",
                                                     f"Введите свою лемму для замены '{olemma}':",
                                                     parent=self)
                        if new:
                            cv.set(new)
                            sv.set('своя')
                            self.lemma_decisions[oid] = new
                    return cmd

                tk.Button(row, text="Своя", command=make_custom_cmd(old_id, old_lemma, combo_var, source_var),
                         width=6).pack(side=tk.LEFT, padx=2)

                self.widgets.append((page, old_id, old_lemma, combo_var, source_var, page_var, excel, prev_excel, next_excel))

        frm_btns = tk.Frame(self)
        frm_btns.pack(pady=10)
        tk.Button(frm_btns, text="Применить всё и закрыть", command=self.on_apply, bg="lightgreen").pack(side=tk.LEFT, padx=10)
        tk.Button(frm_btns, text="Отмена (ничего не менять)", command=self.destroy).pack(side=tk.LEFT, padx=10)

    def insert_all_neighbor(self, page, neighbor_lemmas, direction):
        page_widgets = [(i, w) for i, w in enumerate(self.widgets) if w[0] == page]
        if len(page_widgets) == len(neighbor_lemmas):
            for (idx, (pg, oid, olemma, cv, sv, pv, ex, pe, ne)), new_lemma in zip(page_widgets, neighbor_lemmas):
                if direction == 'prev':
                    cv.set(f"[пред. стр.] {new_lemma}")
                    sv.set('пред. стр.')
                else:
                    cv.set(f"[след. стр.] {new_lemma}")
                    sv.set('след. стр.')
                self.lemma_decisions[oid] = new_lemma
                self.widgets[idx] = (pg, oid, olemma, cv, sv, pv, ex, pe, ne)
        else:
            messagebox.showwarning("Не совпадает",
                f"Количество лемм на странице {page} ({len(page_widgets)}) не совпадает с соседней ({len(neighbor_lemmas)}).")

    def on_apply(self):
        for page, old_id, old_lemma, combo_var, source_var, page_var, _, _, _ in self.widgets:
            new_lemma_raw = combo_var.get().strip()

            if not new_lemma_raw:
                messagebox.showwarning("Не выбрано",
                                       f"Для леммы '{old_lemma}' (стр. {page}) не выбрана замена.")
                return

            new_lemma = new_lemma_raw
            for prefix in ['[пред. стр.] ', '[след. стр.] ']:
                if new_lemma.startswith(prefix):
                    new_lemma = new_lemma[len(prefix):]
                    break

            self.lemma_decisions[old_id] = new_lemma

            try:
                new_page = int(page_var.get().strip())
                self.page_decisions[old_id] = new_page
            except ValueError:
                messagebox.showwarning("Ошибка", f"Некорректный номер страницы для леммы '{new_lemma}'")
                return

        self.result = True
        self.destroy()