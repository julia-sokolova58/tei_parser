import re
import xml.etree.ElementTree as ET

from constants import MORPHEME_PREFIX_RE, MORPHEME_SUFFIX_RE, POS_MAP
from utils import transliterate_lemma


def parse_grammar_content(gram_el, lemma_to_id):
    text = gram_el.text or ""
    pattern = re.compile(r'\*\s*[a-zA-Zа-яёА-ЯЁ][a-zA-Zа-яёА-ЯЁ0-9()\[\]/\-]*')
    parts = []
    last_end = 0
    for m in pattern.finditer(text):
        start, end = m.span()
        if start > last_end:
            parts.append(('text', text[last_end:start]))
        raw_lemma = m.group()
        plain_lemma = raw_lemma.lstrip('*').strip()
        if not plain_lemma:
            parts.append(('text', raw_lemma))
            last_end = end
            continue
        key = transliterate_lemma(plain_lemma)
        if key in lemma_to_id:
            target = lemma_to_id[key]
        else:
            counter_dict = getattr(parse_grammar_content, '_id_counter', {})
            cnt = counter_dict.get(key, 0) + 1
            counter_dict[key] = cnt
            target = f"{key}-{cnt}" if cnt > 1 else key
            setattr(parse_grammar_content, '_id_counter', counter_dict)
        parts.append(('ref', raw_lemma, target))
        last_end = end
    if last_end < len(text):
        parts.append(('text', text[last_end:]))
    gram_el.text = ''
    prev = None
    for part in parts:
        if part[0] == 'text':
            if prev is None:
                gram_el.text = (gram_el.text or '') + part[1]
            else:
                prev.tail = (prev.tail or '') + part[1]
        elif part[0] == 'ref':
            ref_el = ET.SubElement(gram_el, 'ref', {'type': 'etymon', 'target': part[2]})
            ref_el.text = part[1]
            ref_el.tail = ''
            prev = ref_el


def add_pos_and_morphemes(gramGrp):
    gram_el = gramGrp.find('gram')
    if gram_el is None:
        return
    first_text = gram_el.text or ''
    pos_value = None
    if first_text.strip():
        first_word_match = re.match(r'(\S+)', first_text)
        if first_word_match:
            word = first_word_match.group(1).rstrip('.,;:').lower()
            if word in POS_MAP:
                pos_value = POS_MAP[word]
    if pos_value:
        pos_el = ET.Element('pos')
        pos_el.text = pos_value
        index = list(gramGrp).index(gram_el)
        gramGrp.insert(index, pos_el)
    suffix_re = re.compile(r'^-[a-zA-Zа-яёА-ЯЁ0-9]+(-[a-zA-Zа-яёА-ЯЁ0-9]+)?$')
    nodes = []
    if gram_el.text:
        nodes.append(('text', gram_el.text))
    for child in gram_el:
        nodes.append(('element', child))
        if child.tail:
            nodes.append(('text', child.tail))
    cleaned_nodes = []
    prev_elem_tail = ''
    for typ, content in nodes:
        if typ == 'text':
            if content == prev_elem_tail:
                prev_elem_tail = ''
                continue
            cleaned_nodes.append((typ, content))
            prev_elem_tail = ''
        else:
            cleaned_nodes.append((typ, content))
            prev_elem_tail = content.tail or ''
    nodes = cleaned_nodes
    new_nodes = []
    for typ, content in nodes:
        if typ == 'element':
            new_nodes.append((typ, content))
            continue
        tokens = re.split(r'(\s+)', content)
        for token in tokens:
            if not token or token.isspace():
                new_nodes.append(('text', token))
                continue
            leading = ''
            trailing = ''
            core = token
            while core and not re.match(r'[a-zA-Zа-яёА-ЯЁ0-9\-]', core[0]):
                leading += core[0]
                core = core[1:]
            while core and not re.match(r'[a-zA-Zа-яёА-ЯЁ0-9\-]', core[-1]):
                trailing = core[-1] + trailing
                core = core[:-1]
            if not core:
                new_nodes.append(('text', token))
                continue
            if leading:
                new_nodes.append(('text', leading))
            if suffix_re.search(core):
                m_elem = ET.Element('m', {'type': 'suffix'})
                ref = ET.SubElement(m_elem, 'ref')
                ref.text = core
                ref.tail = ''
                new_nodes.append(('element', m_elem))
            else:
                new_nodes.append(('text', core))
            if trailing:
                new_nodes.append(('text', trailing))
    gram_el.clear()
    gram_el.text = ''
    prev = None
    for typ, content in new_nodes:
        if typ == 'text':
            if prev is None:
                gram_el.text = (gram_el.text or '') + content
            else:
                prev.tail = (prev.tail or '') + content
        else:
            gram_el.append(content)
            prev = content