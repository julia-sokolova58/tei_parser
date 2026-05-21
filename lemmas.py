import re


def extract_lemmas(header):
    header = header.lstrip('*•').strip()
    header = re.sub(r'\s*/\s*\**\s*', ',', header)
    parts = [p.strip() for p in header.split(',') if p.strip()]
    lemmas = []
    for part in parts:
        part = re.sub(r'^[<>:;"\'!?\s]+|[<>:;"\'!?\s]+$', '', part)
        part = part.lstrip('*•')
        part = part.strip()
        if part:
            lemmas.append(part)
    return lemmas