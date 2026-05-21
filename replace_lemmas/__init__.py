from .core import replace_lemmas, apply_doubtful_decisions, apply_mismatch_decisions
from .file_utils import (
    parse_xml_entries, read_excel_manual, backup_files,
    restore_backup, save_xml_and_entries
)
from .dialogs import DoubtfulDialog, MismatchDialog
from .utils import similarity, update_refs_in_entry, generate_new_id, update_entry_ids, rebuild_cross_references
from .gui import main, ReplaceApp

__all__ = [
    'replace_lemmas',
    'apply_doubtful_decisions',
    'apply_mismatch_decisions',
    'parse_xml_entries',
    'read_excel_manual',
    'backup_files',
    'restore_backup',
    'save_xml_and_entries',
    'DoubtfulDialog',
    'MismatchDialog',
    'similarity',
    'update_refs_in_entry',
    'generate_new_id',
    'update_entry_ids',
    'rebuild_cross_references',
    'main',
    'ReplaceApp',
]