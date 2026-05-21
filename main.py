import copy
import os
import re
import sys
import threading
import tkinter as tk
import xml.etree.ElementTree as ET
from tkinter import BooleanVar, filedialog, messagebox, scrolledtext

from cognate_finder import extract_cognate_block
from constants import MARKERS_DICT, STOP_WORDS
from cross_references import add_cross_references
from lemmas import extract_lemmas
from parse_cognates import parse_cognate_block
from parse_grammar import parse_notes
from parse_grammar_content import add_pos_and_morphemes, parse_grammar_content
from text_cleaners import (
    clean_html_entities,
    clean_text,
    remove_dangling_brackets,
    remove_duplicate_sentences,
    remove_page_headers,
)
from utils import transliterate_lemma


def load_files(folder, start_num=None, end_num=None):
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Папка '{folder}' не найдена")
    file_nums = []
    for fname in os.listdir(folder):
        m = re.match(r'^(\d+)\.txt$', fname)
        if m:
            file_nums.append(int(m.group(1)))
    file_nums.sort()
    if not file_nums:
        raise ValueError(f"В папке '{folder}' нет файлов с именами N.txt")
    if start_num is not None:
        file_nums = [n for n in file_nums if n >= start_num]
    if end_num is not None:
        file_nums = [n for n in file_nums if n <= end_num]
    if not file_nums:
        raise ValueError("Нет файлов в заданном диапазоне")
    print(f"[LOG] Загружено {len(file_nums)} страниц: {file_nums[0]}–{file_nums[-1]}")

    full_text = ""
    page_positions = []
    last_idx = len(file_nums) - 1

    for idx, num in enumerate(file_nums):
        path = os.path.join(folder, f"{num}.txt")
        with open(path, 'r', encoding='utf-8') as f:
            page_text = f.read()

        page_text = clean_html_entities(page_text)
        page_text = page_text.replace('£', 'č')
        page_text = remove_page_headers(page_text)
        page_text = clean_text(page_text)
        page_text = remove_dangling_brackets(page_text)

        if idx == last_idx:
            page_text = re.sub(r'\n?\s*[^\n.]*статей\.\s*$', '', page_text).strip()

        start_pos = len(full_text)
        if full_text and not full_text.endswith('\n'):
            full_text += '\n'
            start_pos += 1
        page_positions.append((start_pos, num))
        full_text += page_text

    print(f"[LOG] Общая длина текста: {len(full_text)} симв.")
    return full_text, page_positions


def split_into_entries(text, page_positions):
    lines = text.split('\n')
    candidates = []
    current_pos = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if (stripped.startswith('*') or stripped.startswith('•')) and ':' in stripped:
            header_part = stripped.split(':', 1)[0].strip()
            if header_part.startswith('*') or header_part.startswith('•'):
                header_part = header_part[1:].strip()

            if header_part and header_part.count(' ') <= 4:
                candidates.append((i, current_pos, header_part))
        current_pos += len(line) + 1

    valid_starts = []
    for line_idx, start_pos, header in candidates:
        lemmas = extract_lemmas('*' + header)
        if lemmas:
            valid_starts.append((start_pos, header, lemmas))

    entries = []
    for i, (start, header, lemmas) in enumerate(valid_starts):
        end = valid_starts[i + 1][0] if i + 1 < len(valid_starts) else len(text)
        entry_text = text[start:end].strip()

        start_page = None
        for pos, pnum in page_positions:
            if pos <= start:
                start_page = pnum
            else:
                break
        end_page = None
        for pos, pnum in page_positions:
            if pos <= end - 1:
                end_page = pnum
            else:
                break
        if start_page is None:
            start_page = page_positions[0][1] if page_positions else 1
        if end_page is None:
            end_page = start_page

        first_lemma = lemmas[0] if lemmas else "?"
        print(f"[LOG] Статья '{first_lemma}' → стр. {start_page}–{end_page}")
        entries.append((entry_text, start_page, end_page))

    print(f"[LOG] Всего статей: {len(entries)}")
    return entries


def parse_entry(entry_text):
    first_line_end = entry_text.find('\n')
    if first_line_end == -1:
        first_line = entry_text
        rest = ""
    else:
        first_line = entry_text[:first_line_end].strip()
        rest = entry_text[first_line_end + 1:].strip()
    if ':' not in first_line:
        raise ValueError(f"Нет двоеточия: {entry_text[:100]}")
    lemma_header = '*' + first_line.split(':', 1)[0].strip()
    after_colon = first_line.split(':', 1)[1].strip()
    if after_colon:
        rest = after_colon + '\n' + rest if rest else after_colon
    lemmas = extract_lemmas(lemma_header)
    cognate_block, notes = extract_cognate_block(rest)
    return lemmas, cognate_block, notes


def make_mixed_content(parent_elem, text, stop_words, only_first_ref=False):
    word_pattern = re.compile(
        r'\b[а-яёА-ЯЁa-zA-Z](?:[а-яёА-ЯЁa-zA-Z0-9.\-]*[а-яёА-ЯЁa-zA-Z0-9])?\.?\b',
        re.UNICODE
    )
    last_idx = 0
    found_ref = False
    for m in word_pattern.finditer(text):
        start, end = m.span()
        if start > last_idx:
            fragment = text[last_idx:start]
            if len(parent_elem) > 0:
                parent_elem[-1].tail = (parent_elem[-1].tail or '') + fragment
            else:
                parent_elem.text = (parent_elem.text or '') + fragment
        candidate = m.group()
        clean = candidate.rstrip('.')
        if only_first_ref and found_ref:
            if len(parent_elem) > 0:
                parent_elem[-1].tail = (parent_elem[-1].tail or '') + candidate
            else:
                parent_elem.text = (parent_elem.text or '') + candidate
        elif clean in stop_words or candidate in stop_words:
            if len(parent_elem) > 0:
                parent_elem[-1].tail = (parent_elem[-1].tail or '') + candidate
            else:
                parent_elem.text = (parent_elem.text or '') + candidate
        else:
            ref = ET.SubElement(parent_elem, 'ref')
            ref.text = candidate
            ref.tail = ''
            found_ref = True
        last_idx = end
    if last_idx < len(text):
        fragment = text[last_idx:]
        if len(parent_elem) > 0:
            parent_elem[-1].tail = (parent_elem[-1].tail or '') + fragment
        else:
            parent_elem.text = (parent_elem.text or '') + fragment


def _clean_all_texts(root):
    for entry_elem in root.findall('entry'):
        for note in entry_elem.findall('note'):
            if note.text:
                note.text = remove_duplicate_sentences(note.text)
                note.text = clean_html_entities(note.text)
                note.text = re.sub(r'\n', ' ', note.text)
                note.text = re.sub(r' +', ' ', note.text).strip()

        gramGrp = entry_elem.find('gramGrp')
        if gramGrp is not None:
            for gram in gramGrp.findall('gram'):
                if gram.text:
                    gram.text = remove_duplicate_sentences(gram.text)
                    gram.text = clean_html_entities(gram.text)
                    gram.text = re.sub(r'\n', ' ', gram.text)
                    gram.text = re.sub(r' +', ' ', gram.text).strip()

        for def_elem in entry_elem.findall('.//def'):
            if def_elem.text:
                def_elem.text = clean_html_entities(def_elem.text)
                def_elem.text = re.sub(r'\n', ' ', def_elem.text)
                def_elem.text = re.sub(r' +', ' ', def_elem.text).strip()

        for orth_elem in entry_elem.findall('.//orth'):
            if orth_elem.text:
                orth_elem.text = clean_html_entities(orth_elem.text)


def generate_xml(entries_data, output_file, entries_dir):
    root = ET.Element('entries')
    lemma_counter = {}

    for lemmas, cognate_items, parsed_notes, start_page, end_page in entries_data:
        first_lemma = lemmas[0].lstrip('*').strip()
        base_id = transliterate_lemma(first_lemma)
        cnt = lemma_counter.get(base_id, 0) + 1
        lemma_counter[base_id] = cnt
        xml_id = f"{base_id}-{cnt}" if cnt > 1 else base_id
        entry = ET.SubElement(root, 'entry', {'xml:id': xml_id})

        if start_page:
            pb = ET.SubElement(entry, 'pb', {'n': str(start_page)})
            if end_page != start_page:
                pb.attrib['end_page'] = str(end_page)

        for lemma in lemmas:
            form = ET.SubElement(entry, 'form', {'type': 'reconstructed', 'xml:lang': 'ocs'})
            orth = ET.SubElement(form, 'orth')
            orth.text = lemma.strip()
            lemma_elem = ET.SubElement(form, 'lemma')
            lemma_elem.text = lemma.strip()

        ety = ET.SubElement(entry, 'etym', {'type': 'cognates'})
        for item_data in cognate_items:
            lang_attrs = item_data.get('lang_attrs', {})
            orth_text = item_data.get('orth_text', '')
            lang_marker = ''
            rest_text = orth_text
            for marker in sorted(MARKERS_DICT.keys(), key=len, reverse=True):
                if orth_text.startswith(marker):
                    lang_marker = marker
                    rest_text = orth_text[len(marker):].lstrip()
                    break
            if not lang_marker:
                match = re.match(r'(\S+\.)\s', orth_text)
                if match:
                    lang_marker = match.group(1)
                    rest_text = orth_text[len(lang_marker):].lstrip()
            if not rest_text or not re.search(r'[a-zA-Zа-яёА-ЯЁ\-]', rest_text):
                continue

            item = ET.SubElement(ety, 'item')
            form = ET.SubElement(item, 'form')
            orth = ET.SubElement(form, 'orth', lang_attrs)
            if lang_marker:
                orth.text = lang_marker + ' '
            make_mixed_content(orth, rest_text, STOP_WORDS, only_first_ref=True)

            sense_text = item_data.get('sense_text', '').strip()
            sense_text = re.sub(
                r'^[\s\'\"\u2018\u2019\u201c\u201d]+|[\s\'\"\u2018\u2019\u201c\u201d.]+$',
                '',
                sense_text
            )
            if sense_text:
                sense = ET.SubElement(item, 'sense')
                def_el = ET.SubElement(sense, 'def')
                def_el.text = sense_text

            for bibl_text in item_data.get('bibliography', []):
                cit = ET.SubElement(item, 'cit', {'type': 'bibl'})
                ET.SubElement(cit, 'bibl').text = bibl_text

        grammar_text = parsed_notes.get('grammar')
        note_before = parsed_notes.get('note_before')
        note_after = parsed_notes.get('note_after')

        if note_before:
            note_before_el = ET.SubElement(entry, 'note')
            note_before_el.text = note_before
        if grammar_text:
            gramGrp = ET.SubElement(entry, 'gramGrp')
            gram_el = ET.SubElement(gramGrp, 'gram', {'type': 'derivation'})
            gram_el.text = grammar_text
        if note_after:
            note_after_el = ET.SubElement(entry, 'note')
            note_after_el.text = note_after

    lemma_to_id = {}
    for entry_elem in root.findall('entry'):
        xml_id = entry_elem.get('xml:id')
        if not xml_id:
            continue
        orth_elem = entry_elem.find("./form[@type='reconstructed']/orth")
        if orth_elem is not None and orth_elem.text:
            lemma_key = transliterate_lemma(orth_elem.text.strip())
            lemma_to_id[lemma_key] = xml_id

    add_cross_references(root, lemma_to_id)

    for entry_elem in root.findall('entry'):
        gramGrp = entry_elem.find('gramGrp')
        if gramGrp is not None:
            gram_el = gramGrp.find('gram')
            if gram_el is not None:
                parse_grammar_content(gram_el, lemma_to_id)
                add_pos_and_morphemes(gramGrp)

    _clean_all_texts(root)

    ET.indent(root, space="  ")
    xml_str = ET.tostring(root, encoding='unicode')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    print(f"[LOG] Общий XML сохранён: {output_file}")

    os.makedirs(entries_dir, exist_ok=True)
    for entry_elem in root.findall('entry'):
        xml_id = entry_elem.get('{http://www.w3.org/XML/1998/namespace}id') or entry_elem.get('xml:id')

        single_root = ET.Element('Entry')
        single_root.set('xml:id', xml_id)

        for child in entry_elem:
            single_root.append(copy.deepcopy(child))

        ET.indent(single_root, space="  ")
        single_str = ET.tostring(single_root, encoding='unicode')
        fpath = os.path.join(entries_dir, f"{xml_id}.xml")

        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(single_str)

    print(f"[LOG] Постатейные XML сохранены в: {entries_dir} ({len(root.findall('entry'))} шт.)")


def process(folder, output_file, start_num, end_num):
    full_text, page_positions = load_files(folder, start_num, end_num)
    entries_text = split_into_entries(full_text, page_positions)
    entries_data = []
    for entry_text, start_page, end_page in entries_text:
        lemmas, cognate_block, notes = parse_entry(entry_text)
        cognate_items, extra_notes = parse_cognate_block(cognate_block)
        full_notes = notes
        if extra_notes:
            full_notes = full_notes + '\n' + extra_notes if full_notes else extra_notes
        parsed_notes = parse_notes(full_notes)
        entries_data.append((lemmas, cognate_items, parsed_notes, start_page, end_page))

    base = os.path.splitext(output_file)[0]
    entries_dir = f"{base}_entries"
    generate_xml(entries_data, output_file, entries_dir)


class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        root.title("Парсер этимологического словаря")
        root.geometry("720x620")

        self.folder_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self.start_var = tk.StringVar(value="")
        self.end_var = tk.StringVar(value="")
        self.auto_var = BooleanVar(value=True)

        frm_folder = tk.Frame(root)
        frm_folder.pack(pady=5, padx=10, fill=tk.X)
        tk.Label(frm_folder, text="Папка с TXT-файлами (внутри pdf_text/):").pack(anchor=tk.W)
        self.entry_folder = tk.Entry(frm_folder, textvariable=self.folder_var, width=50)
        self.entry_folder.pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frm_folder, text="Обзор...", command=self.browse_folder).pack(side=tk.RIGHT, padx=5)

        chk = tk.Checkbutton(
            root,
            text="Автоматически формировать выходной путь",
            variable=self.auto_var,
            command=self.on_auto_toggle
        )
        chk.pack(anchor=tk.W, padx=10, pady=(5, 0))

        frm_out = tk.Frame(root)
        frm_out.pack(pady=5, padx=10, fill=tk.X)
        tk.Label(frm_out, text="Общий выходной XML-файл:").pack(anchor=tk.W)
        self.entry_out = tk.Entry(frm_out, textvariable=self.output_var, width=50)
        self.entry_out.pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(frm_out, text="Обзор...", command=self.browse_output).pack(side=tk.RIGHT, padx=5)

        frm_range = tk.Frame(root)
        frm_range.pack(pady=5, padx=10, fill=tk.X)
        tk.Label(frm_range, text="Диапазон страниц (пусто = все):").pack(anchor=tk.W)
        inner = tk.Frame(frm_range)
        inner.pack(anchor=tk.W)
        tk.Label(inner, text="Начальная:").pack(side=tk.LEFT)
        self.entry_start = tk.Entry(inner, textvariable=self.start_var, width=8)
        self.entry_start.pack(side=tk.LEFT, padx=5)
        tk.Label(inner, text="Конечная:").pack(side=tk.LEFT, padx=(10, 0))
        self.entry_end = tk.Entry(inner, textvariable=self.end_var, width=8)
        self.entry_end.pack(side=tk.LEFT, padx=5)

        self.btn_run = tk.Button(
            root,
            text="Запустить обработку",
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.start
        )
        self.btn_run.pack(pady=10)

        self.log_widget = scrolledtext.ScrolledText(root, height=20, wrap=tk.WORD)
        self.log_widget.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.redirect = RedirectText(self.log_widget)
        sys.stdout = self.redirect
        sys.stderr = self.redirect

    def _make_output_path(self, folder):
        if not folder:
            return ""
        volume_name = os.path.basename(folder.rstrip(os.sep))
        if not volume_name:
            volume_name = "result"
        return os.path.join("output", volume_name, f"{volume_name}.xml")

    def browse_folder(self):
        initial = "pdf_text" if os.path.isdir("pdf_text") else "."
        folder = filedialog.askdirectory(
            title="Выберите папку с TXT-файлами (pdf_text/имя_тома)",
            initialdir=initial
        )
        if folder:
            self.folder_var.set(folder)
            if self.auto_var.get():
                self.output_var.set(self._make_output_path(folder))

    def browse_output(self):
        file = filedialog.asksaveasfilename(
            title="Сохранить общий XML как",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.output_var.get()) or "."
        )
        if file:
            self.output_var.set(file)

    def on_auto_toggle(self):
        if self.auto_var.get() and self.folder_var.get():
            self.output_var.set(self._make_output_path(self.folder_var.get()))

    def start(self):
        folder = self.folder_var.get().strip()
        output = self.output_var.get().strip()
        start_str = self.start_var.get().strip()
        end_str = self.end_var.get().strip()

        if not folder:
            messagebox.showerror("Ошибка", "Выберите папку с TXT-файлами.")
            return
        if not output:
            messagebox.showerror("Ошибка", "Укажите путь к выходному файлу.")
            return

        start_num = None
        end_num = None
        try:
            if start_str:
                start_num = int(start_str)
            if end_str:
                end_num = int(end_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Номера страниц должны быть целыми числами.")
            return

        self.btn_run.config(state=tk.DISABLED, text="Идёт обработка...")
        self.log_widget.delete(1.0, tk.END)

        def worker():
            try:
                process(folder, output, start_num, end_num)
                self.root.after(0, lambda: messagebox.showinfo("Готово", "Обработка завершена успешно."))
            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Ошибка", str(e)))
            finally:
                self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text="Запустить обработку"))
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
