import re
import xml.etree.ElementTree as ET

from utils import transliterate_lemma


def add_cross_references(root, lemma_to_id):
    pat_direct = re.compile(
        r'((?:[Сс]р\.?(?:\s*(?:ещё|еще|далее))?|см\.?))\s+(\*[^\s,;.()]+)'
    )

    pat_inverse_pair = re.compile(
        r'(\*[^\s,.;()]+)\s*,?\s*([Сс]р\.?(?:\s*(?:ещё|еще|далее))?|см\.?)\s+(\*[^\s,.;()]+)'
    )

    pat_self_brackets = re.compile(
        r'(\*[^\s,.;()]+)\s*\(([Сс]р\.?|см\.?)\)'
    )

    pat_self_plain = re.compile(
        r'(\*[^\s,.;()]+)\s+([Сс]р\.?|см\.?)(?!\s*\*)'
    )

    combined = re.compile(
        r'(?:((?:[Сс]р\.?(?:\s*(?:ещё|еще|далее))?|см\.?))\s+(\*[^\s,;.()]+))|'
        r'(?:(\*[^\s,.;()]+)\s*,?\s*((?:[Сс]р\.?(?:\s*(?:ещё|еще|далее))?|см\.?))\s+(\*[^\s,.;()]+))|'
        r'(?:(\*[^\s,.;()]+)\s*\(((?:[Сс]р\.?|см\.?))\))|'
        r'(?:(\*[^\s,.;()]+)\s+((?:[Сс]р\.?|см\.?))(?!\s*\*))'
    )

    id_counter = {k: 1 for k in lemma_to_id}

    def get_or_create_target(plain_lemma):
        key = transliterate_lemma(plain_lemma)
        if key in lemma_to_id:
            return lemma_to_id[key]
        n = id_counter.get(key, 0) + 1
        id_counter[key] = n
        return f"{key}-{n}" if n > 1 else key

    def make_xr(marker, star_word):
        target = get_or_create_target(star_word.lstrip('*'))
        xr = ET.Element('xr', {'type': 'compare'})
        xr.text = marker + ' '
        ref = ET.SubElement(xr, 'ref', {'type': 'etymon', 'target': target})
        ref.text = star_word
        return xr

    for elem in root.iter():
        if elem.tag not in ('def', 'note'):
            continue

        content = []
        if elem.text:
            content.append(('text', elem.text))
        for child in elem:
            content.append(('elem', child))
            if child.tail:
                content.append(('text', child.tail))

        new_content = []
        for tp, val in content:
            if tp == 'elem':
                new_content.append(('elem', val))
                continue

            text = val
            last_idx = 0
            for m in combined.finditer(text):
                start, end = m.span()
                if start > last_idx:
                    new_content.append(('text', text[last_idx:start]))

                if m.group(1) is not None:
                    marker = m.group(1)
                    star = m.group(2)
                elif m.group(3) is not None:
                    marker = m.group(4)
                    star = m.group(5)
                elif m.group(6) is not None:
                    marker = m.group(7)
                    star = m.group(6)
                else:
                    marker = m.group(9)
                    star = m.group(8)

                new_content.append(('elem', make_xr(marker, star)))
                last_idx = end

            if last_idx < len(text):
                new_content.append(('text', text[last_idx:]))

        elem.clear()
        if not new_content:
            continue

        first_tp, first_val = new_content[0]
        if first_tp == 'text':
            elem.text = first_val
        else:
            elem.append(first_val)

        for i in range(1, len(new_content)):
            _, prev_val = new_content[i-1]
            curr_tp, curr_val = new_content[i]
            if curr_tp == 'text':
                if isinstance(prev_val, ET.Element):
                    prev_val.tail = (prev_val.tail or '') + curr_val
            else:
                elem.append(curr_val)