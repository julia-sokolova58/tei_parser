import re

from constants import GRAMMAR_KEYWORDS, NOTE_MARKERS
from utils import SOURCE_ABBREVS


def is_inside_open_construct(lines):
    combined = ' '.join(lines)
    depth = 0
    for ch in combined:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
    return depth != 0


def starts_with_note_marker(text):
    t = text.lstrip()
    for note_mark in NOTE_MARKERS:
        if re.match(r'^\s*' + note_mark, t, re.IGNORECASE):
            return True
    return False


def extract_cognate_block(text):
    lines = text.splitlines()
    current_part = []

    for i, line in enumerate(lines):
        current_part.append(line)
        stripped = line.strip()
        if not stripped:
            continue

        if is_inside_open_construct(current_part):
            continue

        ends_with_dot = bool(re.search(r'\.\s*$', stripped))
        has_note = starts_with_note_marker(stripped)

        if not ends_with_dot and not has_note:
            continue

        next_idx = i + 1
        while next_idx < len(lines) and not lines[next_idx].strip():
            next_idx += 1

        if next_idx >= len(lines):
            continue

        next_line = lines[next_idx].strip()
        if next_line and (next_line[0].isupper() or starts_with_note_marker(next_line)):
            cognate_lines = lines[:i + 1]
            note_lines = lines[i + 1:]
            return '\n'.join(cognate_lines).strip(), '\n'.join(note_lines).strip()

    cognate_block = text.strip()
    notes = ""

    cognate_block, notes = split_by_grammar(cognate_block)
    if notes:
        return cognate_block, notes

    cognate_block, notes = split_by_last_biblio(cognate_block)
    return cognate_block, notes


def split_by_grammar(text):
    pattern = r'(?:^|(?<=\. ))\s*(' + '|'.join(GRAMMAR_KEYWORDS) + r')'
    for m in re.finditer(pattern, text, re.IGNORECASE):
        start = m.start()
        end = text.find('.', m.end())
        if end == -1:
            end = len(text)
        else:
            end += 1

        candidate = text[start:end].strip()
        if '*' in candidate:
            grammar_start = start
            cognate = text[:grammar_start].strip()
            note = text[grammar_start:].strip()
            return cognate, note

    return text, ""


def split_by_last_biblio(text):
    if not SOURCE_ABBREVS:
        return text, ""

    alts = []
    for s in SOURCE_ABBREVS:
        escaped = re.escape(s)
        if s.endswith('.'):
            alts.append(escaped + r'(?![a-zA-Zа-яёА-ЯЁ0-9_])')
        else:
            alts.append(escaped + r'\b')

    biblio_re = re.compile(
        r'\(([^)]*\b(?:' + '|'.join(alts) + r')[^)]*)\)',
        re.IGNORECASE
    )

    last_match = None
    for m in biblio_re.finditer(text):
        last_match = m

    if last_match:
        end_pos = last_match.end()
        after = text[end_pos:]
        if re.match(r'\s*\.\s+[А-ЯЁA-Z]', after):
            dot_pos = after.find('.')
            cut = end_pos + dot_pos + 1
            return text[:cut].strip(), text[cut:].strip()

    for m in re.finditer(r'\)\s*\.?\s+[А-ЯЁA-Z]', text):
        end_pos = m.start() + 1
        after = text[end_pos:]
        if after.lstrip().startswith('.'):
            dot_pos = after.find('.')
            cut = end_pos + dot_pos + 1
        else:
            cut = end_pos
        return text[:cut].strip(), text[cut:].strip()

    return text, ""