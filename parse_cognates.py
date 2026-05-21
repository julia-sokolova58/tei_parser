import re

from constants import LANG_NAME_MAP, MARKERS_DICT, MARKER_PATTERN
from utils import extract_bracketed_bibliography


def normalize_whitespace(text):
    return re.sub(r'\s+', ' ', text).strip()


def mask_brackets(text):
    result = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '(':
            if depth == 0:
                start = i
            depth += 1
        elif ch == ')':
            if depth > 0:
                depth -= 1
                if depth == 0:
                    result.append(' ' * (i - start + 1))
                    start = -1
                    continue
        if depth == 0:
            result.append(ch)
    return ''.join(result)


def get_lang_name(code, typ):
    key = (code, typ)
    return LANG_NAME_MAP.get(key)


def split_orth_sense(text):
    match = re.search(r"[\u2018\u2019']", text)
    if not match:
        return text.strip(), ""
    idx = match.start()
    orth = text[:idx].strip()
    sense = text[idx+1:].strip()
    sense = re.sub(r"[\u2018\u2019']", "", sense).strip()
    return orth, sense


def refine_segment(segment_text, code, typ, initial_bibl=None):
    norm = normalize_whitespace(segment_text)
    depth = 0
    for ch in norm:
        if ch == '(':
            depth += 1
        elif ch == ')' and depth > 0:
            depth -= 1
    if depth != 0:
        raw_text, bibl = extract_bracketed_bibliography(norm)
        final_bibl = initial_bibl if initial_bibl is not None else bibl
        orth_text, sense_text = split_orth_sense(raw_text)
        return [{
            'lang_attrs': build_lang_attrs(code, typ),
            'orth_text': orth_text,
            'sense_text': sense_text,
            'bibliography': final_bibl
        }]

    masked = mask_brackets(norm)
    matches = list(MARKER_PATTERN.finditer(masked))
    if not matches:
        raw_text, bibl = extract_bracketed_bibliography(norm)
        final_bibl = initial_bibl if initial_bibl is not None else bibl
        orth_text, sense_text = split_orth_sense(raw_text)
        return [{
            'lang_attrs': build_lang_attrs(code, typ),
            'orth_text': orth_text,
            'sense_text': sense_text,
            'bibliography': final_bibl
        }]

    sub_items = []
    last_pos = 0
    local_code = code
    local_type = typ
    first_start, _ = matches[0].span()
    if first_start > 0:
        initial_text = norm[:first_start].strip()
        if initial_text:
            lang_name = get_lang_name(local_code, local_type)
            if lang_name and not initial_text.startswith(lang_name):
                initial_text = lang_name + ' ' + initial_text
            raw_text, bibl = extract_bracketed_bibliography(initial_text)
            orth_text, sense_text = split_orth_sense(raw_text)
            sub_items.append({
                'lang_attrs': build_lang_attrs(local_code, local_type),
                'orth_text': orth_text,
                'sense_text': sense_text,
                'bibliography': bibl
            })
        last_pos = first_start

    for i, match in enumerate(matches):
        start, end = match.span()
        marker = match.group()
        lang_info = MARKERS_DICT[marker]
        new_code, new_type = lang_info.split(':') if ':' in lang_info else (lang_info, 'standard')
        if new_code == '__':
            if local_code is None:
                continue
            new_code = local_code
        else:
            local_code = new_code
            local_type = new_type
        next_start = matches[i+1].start() if i+1 < len(matches) else len(norm)
        segment_content = norm[start:next_start].strip()
        if segment_content:
            raw_text, bibl = extract_bracketed_bibliography(segment_content)
            orth_text, sense_text = split_orth_sense(raw_text)
            sub_items.append({
                'lang_attrs': build_lang_attrs(local_code, local_type),
                'orth_text': orth_text,
                'sense_text': sense_text,
                'bibliography': bibl
            })
    if initial_bibl and sub_items:
        sub_items[-1]['bibliography'].extend(initial_bibl)
    return sub_items


def parse_cognate_block(cognate_text):
    norm = normalize_whitespace(cognate_text).strip()
    if not norm:
        return [], ""
    masked = mask_brackets(norm)
    matches = list(MARKER_PATTERN.finditer(masked))
    if not matches:
        return [], norm

    items = []
    last_lang_code = None
    last_pos = 0
    prev_code = None
    prev_type = None

    for i, match in enumerate(matches):
        start, end = match.span()
        marker = match.group()
        lang_info = MARKERS_DICT[marker]
        code, typ = lang_info.split(':') if ':' in lang_info else (lang_info, 'standard')
        if code == '__':
            if last_lang_code is None:
                continue
            code = last_lang_code
        else:
            last_lang_code = code

        if i > 0:
            seg_start = last_pos
            seg_end = start
            segment = norm[seg_start:seg_end].strip()
            segment = re.sub(r'[,;]+\s*$', '', segment)
            if segment:
                if prev_code is not None:
                    raw_text, bibl = extract_bracketed_bibliography(segment)
                    refined = refine_segment(raw_text, prev_code, prev_type, initial_bibl=bibl)
                    items.extend(refined)

        prev_code = code
        prev_type = typ
        last_pos = start

    extra_notes = ""
    if last_pos < len(norm):
        segment = norm[last_pos:].strip()
        segment = re.sub(r'[,;]+\s*$', '', segment)
        if segment:
            tail_masked = mask_brackets(segment)
            tail_matches = list(MARKER_PATTERN.finditer(tail_masked))
            if tail_matches:
                tail_text = segment
                first_start = tail_matches[0].start()
                if first_start > 0 and items:
                    pre_text = tail_text[:first_start].strip()
                    if pre_text:
                        items[-1]['orth_text'] += ' ' + pre_text
                for j, tm in enumerate(tail_matches):
                    t_start, t_end = tm.span()
                    marker = tm.group()
                    lang_info = MARKERS_DICT[marker]
                    code, typ = lang_info.split(':') if ':' in lang_info else (lang_info, 'standard')
                    if code == '__':
                        code = prev_code if prev_code else 'unknown'
                    next_t_start = tail_matches[j+1].start() if j+1 < len(tail_matches) else len(tail_text)
                    seg_content = tail_text[t_start:next_t_start].strip()
                    if seg_content:
                        raw_text, bibl = extract_bracketed_bibliography(seg_content)
                        orth_text, sense_text = split_orth_sense(raw_text)
                        if orth_text.startswith(marker):
                            rest = orth_text[len(marker):].strip()
                        else:
                            rest = orth_text.strip()
                        if rest and re.search(r'[a-zA-Zа-яёА-ЯЁ]', rest):
                            items.append({
                                'lang_attrs': build_lang_attrs(code, typ),
                                'orth_text': orth_text,
                                'sense_text': sense_text,
                                'bibliography': bibl
                            })
            else:
                if prev_code is not None:
                    raw_text, bibl = extract_bracketed_bibliography(segment)
                    refined = refine_segment(raw_text, prev_code, prev_type, initial_bibl=bibl)
                    items.extend(refined)
                else:
                    raw_text, bibl = extract_bracketed_bibliography(segment)
                    if raw_text.strip():
                        items.append({
                            'lang_attrs': build_lang_attrs('unknown', 'standard'),
                            'orth_text': raw_text.strip(),
                            'sense_text': '',
                            'bibliography': bibl
                        })

    note_markers = [
        r'Производное', r'Прилаг\.', r'Гл\.', r'Сложение', r'Сложное',
        r'Бессуф\.', r'Сущ-ное', r'Имя', r'Именное', r'Старое\s+сложение',
        r'Соотносительно', r'Значительная\s+древность', r'Очевидно',
        r'См\.', r'Ср\.', r'Древность', r'Итератив', r'Глагол,\s*производный',
        r'Продолжения', r'Форма', r'Значение'
    ]
    note_pattern = r'(?:(?:' + '|'.join(note_markers) + r')\b)'
    extracted_note = ""

    filtered_items = []
    for it in items:
        orth_text = it.get('orth_text', '')
        marked = False
        for marker in sorted(MARKERS_DICT.keys(), key=len, reverse=True):
            if orth_text.startswith(marker):
                rest = orth_text[len(marker):].strip()
                if rest and re.search(r'[a-zA-Zа-яёА-ЯЁ]', rest):
                    filtered_items.append(it)
                marked = True
                break
        if not marked:
            if orth_text.strip():
                filtered_items.append(it)
    items = filtered_items

    if items:
        last = items[-1]
        combined = (last.get('orth_text', '') + ' ' + last.get('sense_text', '')).strip()
        if re.match(r'^(Ср\.|см\.)\s', combined):
            pass
        elif re.search(note_pattern, combined):
            extracted_note = combined
            items.pop()
    return items, extracted_note.strip()


def build_lang_attrs(code, typ):
    attrs = {'xml:lang': code}
    if typ and typ != 'standard':
        attrs['type'] = typ
    return attrs