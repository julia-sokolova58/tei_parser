from .utils import similarity, generate_new_id, update_entry_ids, rebuild_cross_references


def _get_manual_pages(manual_data, volume):
    if volume is not None and volume in manual_data:
        return manual_data[volume]
    if "all" in manual_data:
        return manual_data["all"]
    return {}


def replace_lemmas(root, id_to_entry, id_to_info, manual_data, volume=None, sim_threshold=0.6, offset=0):
    manual_pages = _get_manual_pages(manual_data, volume)
    if not manual_pages:
        raise ValueError(f"Для тома '{volume}' нет данных в Excel.")

    parsed_pages = {}
    for xml_id, (lemma, page) in id_to_info.items():
        if isinstance(page, int):
            corrected_page = page + offset
            parsed_pages.setdefault(corrected_page, []).append(xml_id)

    log = []
    old_to_new_id = {}
    new_id_to_info = {}
    id_counter = {}
    doubtful = []
    mismatch = []

    for corrected_page in sorted(parsed_pages.keys()):
        par_ids = parsed_pages.get(corrected_page, [])
        man_lemmas = manual_pages.get(corrected_page, [])
        if len(par_ids) != len(man_lemmas):
            prev_lemmas = manual_pages.get(corrected_page - 1, [])
            next_lemmas = manual_pages.get(corrected_page + 1, [])
            mismatch.append({
                'page': corrected_page,
                'parsed': [(oid, id_to_info[oid][0]) for oid in par_ids],
                'excel': man_lemmas,
                'prev_excel': prev_lemmas,
                'next_excel': next_lemmas
            })
            log.append(f"Стр. {corrected_page}: разное количество статей (парсинг {len(par_ids)}, Excel {len(man_lemmas)}) – требуется ручное сопоставление.")
            continue

        for old_id, new_lemma in zip(par_ids, man_lemmas):
            old_lemma, _ = id_to_info[old_id]
            sim = similarity(old_lemma, new_lemma)
            if sim < sim_threshold:
                doubtful.append({
                    'old_id': old_id,
                    'old_lemma': old_lemma,
                    'new_lemma': new_lemma,
                    'page': corrected_page,
                    'similarity': round(sim, 2)
                })
                log.append(f"Стр. {corrected_page}: '{old_lemma}' ~ '{new_lemma}' (сходство {sim:.2f}) – отложено для ручной проверки.")
            else:
                new_id = generate_new_id(new_lemma, id_counter)
                old_to_new_id[old_id] = new_id
                new_id_to_info[new_id] = (new_lemma, corrected_page)
                log.append(f"Стр. {corrected_page}: '{old_lemma}' → '{new_lemma}' (id={new_id})")

    for old_id, new_id in old_to_new_id.items():
        entry = id_to_entry[old_id]
        new_lemma = new_id_to_info[new_id][0]
        old_lemma = id_to_info[old_id][0]
        update_entry_ids(entry, old_id, new_id, new_lemma, old_lemma)

    return root, log, doubtful, mismatch


def apply_doubtful_decisions(root, id_to_entry, id_to_info, doubtful, decisions):
    log = []
    old_to_new_id = {}
    new_id_to_info = {}
    id_counter = {}

    for item in doubtful:
        old_id = item['old_id']
        if old_id not in decisions:
            continue
        action = decisions[old_id]
        if action[0] == 'keep':
            log.append(f"Оставлено без изменений: '{item['old_lemma']}' (стр. {item['page']})")
        else:
            new_lemma = action[1]
            new_id = generate_new_id(new_lemma, id_counter)
            old_to_new_id[old_id] = new_id
            new_id_to_info[new_id] = (new_lemma, item['page'])
            log.append(f"Ручная замена: '{item['old_lemma']}' → '{new_lemma}' (стр. {item['page']}, id={new_id})")

    for old_id, new_id in old_to_new_id.items():
        entry = id_to_entry[old_id]
        new_lemma = new_id_to_info[new_id][0]
        old_lemma = id_to_info[old_id][0]
        update_entry_ids(entry, old_id, new_id, new_lemma, old_lemma)

    rebuild_cross_references(root)
    return log


def apply_mismatch_decisions(root, id_to_entry, mismatch_list, lemma_decisions, page_decisions=None):
    log = []
    old_to_new_id = {}
    new_id_to_info = {}
    id_counter = {}

    for page_info in mismatch_list:
        page = page_info['page']
        for old_id, old_lemma in page_info['parsed']:
            if old_id not in lemma_decisions:
                log.append(f"ОШИБКА: нет решения для '{old_lemma}' (стр. {page})")
                continue
            new_lemma = lemma_decisions[old_id]
            new_page = page_decisions.get(old_id, page) if page_decisions else page

            new_id = generate_new_id(new_lemma, id_counter)
            old_to_new_id[old_id] = new_id
            new_id_to_info[new_id] = (new_lemma, new_page)
            log.append(f"Сопоставление стр. {page}→{new_page}: '{old_lemma}' → '{new_lemma}' (id={new_id})")

    for old_id, new_id in old_to_new_id.items():
        entry = id_to_entry[old_id]
        new_lemma = new_id_to_info[new_id][0]

        old_lemma = None
        for page_info in mismatch_list:
            for oid, ol in page_info['parsed']:
                if oid == old_id:
                    old_lemma = ol
                    break
            if old_lemma:
                break

        update_entry_ids(entry, old_id, new_id, new_lemma, old_lemma)

        new_page = new_id_to_info[new_id][1]
        pb = entry.find('pb')
        if pb is not None:
            pb.set('n', str(new_page))

    rebuild_cross_references(root)
    return log