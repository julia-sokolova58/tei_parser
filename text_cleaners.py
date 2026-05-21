import re


def clean_html_entities(text):
    if not text:
        return text
    text = text.replace('&gt;', '>')
    text = text.replace('&lt;', '<')
    text = text.replace('&amp;', '&')
    return text


def remove_duplicate_sentences(text):
    if not text:
        return text

    fragments = re.split(r'(?<=[.!?;])\s+', text)

    seen = set()
    unique = []
    for f in fragments:
        norm = re.sub(r'\s+', ' ', f.strip()).lower()
        if len(norm) < 20:
            unique.append(f)
        elif norm not in seen:
            seen.add(norm)
            unique.append(f)

    return ' '.join(unique).strip()


def clean_text(text):
    text = re.sub(r'\b\d+\s+\*[^*\s]+\b', '', text)
    text = re.sub(r'(?:^|(?<=\s))\w+\([^)]*\)\s+\d+\s*', '', text, flags=re.MULTILINE)
    return text


def remove_page_headers(text):
    lines = text.split('\n')
    cleaned = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('*') and ':' not in stripped:
            has_number_next = (i + 1 < len(lines) and re.fullmatch(r'\s*\d+\s*', lines[i + 1]))
            has_number_prev = (i > 0 and cleaned and re.fullmatch(r'\s*\d+\s*', cleaned[-1]))

            if has_number_next:
                i += 2
                continue
            elif has_number_prev:
                if cleaned and re.fullmatch(r'\s*\d+\s*', cleaned[-1]):
                    cleaned.pop()
                i += 1
                continue
            else:
                cleaned.append(line)
                i += 1
                continue

        if re.fullmatch(r'\s*\d+\s*', stripped):
            if i + 1 < len(lines) and not lines[i + 1].strip().startswith('*'):
                i += 1
                continue
            elif i > 0 and cleaned and not cleaned[-1].strip().startswith('*'):
                i += 1
                continue
            else:
                cleaned.append(line)
                i += 1
                continue

        cleaned.append(line)
        i += 1
    return '\n'.join(cleaned)


def remove_dangling_brackets(text, max_distance=500):
    result = []
    depth = 0
    open_positions = []
    for i, ch in enumerate(text):
        if ch == '(':
            open_positions.append(len(result))
            depth += 1
            result.append(ch)
        elif ch == ')' and depth > 0:
            open_positions.pop()
            depth -= 1
            result.append(ch)
        else:
            result.append(ch)
        while open_positions and (i - open_positions[0]) > max_distance:
            result[open_positions[0]] = ''
            open_positions.pop(0)
            depth -= 1
    return ''.join(result)
