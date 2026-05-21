import re

from constants import DERIVATION_KEYWORDS, MORPHEME_INDICATORS, POS_KEYWORDS


def _find_sent_start(text, pos):
    depth = 0
    for i in range(pos - 1, -1, -1):
        ch = text[i]
        if ch == ')':
            depth += 1
        elif ch == '(':
            depth -= 1
        elif ch == '.' and depth == 0:
            j = i + 1
            while j < len(text) and text[j] in (' ', '\n', '\t', '\r'):
                j += 1
            if j < len(text) and text[j].isupper():
                return j
    return 0


def _find_sent_end(text, pos):
    depth = 0
    for i in range(pos, len(text)):
        ch = text[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == '.' and depth == 0:
            j = i + 1
            while j < len(text) and text[j] in (' ', '\n', '\t', '\r'):
                j += 1
            if j < len(text) and text[j].isupper():
                return i + 1
            elif j >= len(text):
                return i + 1
    return len(text)


def _last_word_before_dot(sentence):
    s = sentence.strip()
    if s.endswith('.'):
        s = s[:-1]
    parts = s.split()
    return parts[-1] if parts else ''


def _is_morpheme_ending(sentence):
    last = _last_word_before_dot(sentence)
    last = last.rstrip(')')
    return last in MORPHEME_INDICATORS


def _find_grammar_with_keywords(text, keywords):
    if not text or not keywords:
        return None, None, None
    pattern = re.compile(r'(?:^|(?<=\s))(' + '|'.join(keywords) + r')', re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        return None, None, None
    for match in matches:
        sent_start = _find_sent_start(text, match.start())
        sent_end = _find_sent_end(text, match.end())
        candidate = text[sent_start:sent_end].strip()
        if not re.search(r'\*\s*[a-zA-Zа-яёА-ЯЁ]', candidate):
            continue
        while sent_end < len(text):
            next_start = sent_end
            while next_start < len(text) and text[next_start] in (' ', '\n', '\t', '\r'):
                next_start += 1
            if next_start >= len(text):
                break
            next_end = _find_sent_end(text, next_start)
            if next_end == next_start:
                break
            extension = text[next_start:next_end].strip()
            if not extension:
                break
            if _is_morpheme_ending(candidate):
                candidate = candidate + ' ' + extension
                sent_end = next_end
            else:
                break
        before = text[:sent_start].strip()
        after = text[sent_end:].strip()
        return candidate, before, after
    return None, None, None


def extract_grammar_sentence(text):
    if not text:
        return None, "", ""
    grammar, before, after = _find_grammar_with_keywords(text, POS_KEYWORDS)
    if grammar is not None:
        return grammar, before, after
    grammar, before, after = _find_grammar_with_keywords(text, DERIVATION_KEYWORDS)
    if grammar is not None:
        return grammar, before, after
    return None, text, ""


def parse_notes(notes_text):
    if not notes_text or not notes_text.strip():
        return {'grammar': None, 'note_before': None, 'note_after': None}
    grammar, before, after = extract_grammar_sentence(notes_text)
    return {
        'grammar': grammar,
        'note_before': before if before else None,
        'note_after': after if after else None,
    }