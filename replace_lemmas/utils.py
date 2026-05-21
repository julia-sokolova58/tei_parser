from difflib import SequenceMatcher


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def update_refs_in_entry(entry, old_lemma, new_lemma):
    old_clean = old_lemma.lstrip('*')
    new_clean = new_lemma.lstrip('*')

    for ref in entry.findall('.//ref'):
        if ref.text:
            ref.text = ref.text.replace('*' + old_clean, '*' + new_clean)
            ref.text = ref.text.replace(old_clean, new_clean)


def generate_new_id(new_lemma, id_counter):
    from utils import transliterate_lemma
    base = transliterate_lemma(new_lemma)
    cnt = id_counter.get(base, 0) + 1
    id_counter[base] = cnt
    return f"{base}-{cnt}" if cnt > 1 else base


def update_entry_ids(entry, old_id, new_id, new_lemma, old_lemma):
    entry.set('{http://www.w3.org/XML/1998/namespace}id', new_id)
    entry.set('xml:id', new_id)

    new_lemma_orth = new_lemma if new_lemma.startswith('*') else '*' + new_lemma
    new_lemma_clean = new_lemma.lstrip('*')

    orth = entry.find("./form[@type='reconstructed']/orth")
    if orth is not None:
        orth.text = new_lemma_orth

    lemma_elem = entry.find("./form[@type='reconstructed']/lemma")
    if lemma_elem is not None:
        lemma_elem.text = new_lemma_clean

    update_refs_in_entry(entry, old_lemma.lstrip('*'), new_lemma_clean)


def rebuild_cross_references(root):
    from utils import transliterate_lemma
    from cross_references import add_cross_references

    lemma_to_id = {}
    for entry in root.findall('entry'):
        xml_id = entry.get('xml:id')
        orth = entry.find("./form[@type='reconstructed']/orth")
        if orth is not None and orth.text:
            lemma_key = transliterate_lemma(orth.text.strip())
            lemma_to_id[lemma_key] = xml_id
    add_cross_references(root, lemma_to_id)