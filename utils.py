import re

from constants import MODIFIERS

MODIFIERS_SET = {m.rstrip('.') for m in MODIFIERS}


def load_source_abbreviations(filepath='sources.txt'):
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


SOURCE_ABBREVS = load_source_abbreviations()


def is_bibliography(content, sources=SOURCE_ABBREVS):
    if not content:
        return False
    if re.search(r'\d', content):
        return True
    if re.search(r'там\s*же', content, re.IGNORECASE):
        return True
    for abbr in sources:
        if abbr in content:
            return True
    return False


def extract_bracketed_bibliography(text, sources=SOURCE_ABBREVS):
    cleaned = []
    bibliography = []
    i = 0
    length = len(text)
    while i < length:
        if text[i] == '(':
            depth = 1
            j = i + 1
            while j < length and depth > 0:
                if text[j] == '(':
                    depth += 1
                elif text[j] == ')':
                    depth -= 1
                j += 1
            if depth == 0:
                full_bracket = text[i:j]
                content = full_bracket[1:-1].strip()
                if is_bibliography(content, sources):
                    bibliography.append(full_bracket)
                else:
                    cleaned.append(full_bracket)
                i = j
                continue
        cleaned.append(text[i])
        i += 1
    cleaned_text = ''.join(cleaned)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = re.sub(r'^\s*[,;]\s*', '', cleaned_text)
    cleaned_text = re.sub(r'\s*[,;]\s*$', '', cleaned_text)
    cleaned_text = re.sub(r',\s*$', '', cleaned_text)
    return cleaned_text, bibliography


def transliterate_lemma(lemma):
    replacements = {
        'ě': 'e', 'č': 'c', 'š': 's', 'ž': 'z', 'ř': 'r',
        'ь': '', 'ъ': '', 'ę': 'e', 'ǫ': 'o',
        'ĭ': 'i', 'ŭ': 'u', 'ā': 'a', 'ē': 'e', 'ī': 'i',
        'ō': 'o', 'ū': 'u', 'ă': 'a', 'ĕ': 'e', 'ŏ': 'o',
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    result = ''
    for ch in lemma:
        result += replacements.get(ch.lower(), ch)
    result = re.sub(r'[^a-zA-Z0-9_-]', '', result)
    return result.strip('_') or 'lemma'