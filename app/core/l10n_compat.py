"""Compatibility assets; never read translations or scripts from other language packs.

The public Modding Script Hooks runtime is already distributed with seedgen.
Reuse its four runtime files unchanged, not its old replacement ui/main.html.
"""
from __future__ import annotations

import hashlib
import re
import zipfile

from .paths import resource_path

HOOKS_ARCHIVE_SHA256 = '0461ea3f457a798e6af2082ecbe6e058f5917e70f4487a1298160161b0a8d38c'
HOOKS_FILES = (
    'scripts/!mods_preload/!!redirect.nut',
    'scripts/!mods_preload/~~finalize.nut',
    'scripts/root_state.cnut',
    'ui/mod_hooks.js',
)
# These screens can be translated by runtime.js without replacing game logic.
# In particular, SR Alternative Standard owns this file and its three buttons.
DISPLAY_ONLY_FILES = frozenset({
    'ui/screens/world/modules/world_town_screen/world_town_screen_hire_dialog_module.js',
})
HOOKS_CREDIT = '''Modding Script Hooks 21.1
Author: Adam Milazzo (AdamMil01)
Source: https://www.nexusmods.com/battlebrothers/mods/42
Local source: BBMOD's pre-existing seedgen/payload/mod_hooks.zip.
The four runtime files are included byte-for-byte. The old ui/main.html is NOT used.
This is a general mod framework, separate from BBMOD's independently authored Chinese translations.
No files were extracted from Fox localization.
Permissions checked on the author's page on 2026-09-16:
Redistribution with author credit and modification are permitted.
Use in paid mods/files is not permitted. Donation Points require permission.
'''


def override_keys(names) -> set[str]:
    """The game resolves source and compiled Squirrel files to the same script."""
    return {re.sub(r'\.(?:c?nut)$', '.squirrel', n.replace('\\', '/').lower())
            for n in names if n.lower().endswith(('.cnut', '.nut', '.js', '.html'))}


def hooks_assets() -> dict[str, bytes]:
    source = resource_path('seedgen/payload/mod_hooks.zip')
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HOOKS_ARCHIVE_SHA256:
        raise ValueError('随附的 MOD 加载框架校验失败，请重新安装 BBMOD。')
    with zipfile.ZipFile(source) as archive:
        return {name: archive.read(name) for name in HOOKS_FILES}


def write_hooks(archive: zipfile.ZipFile) -> dict:
    assets = hooks_assets()
    for name, raw in assets.items():
        archive.writestr(name, raw)
    archive.writestr('BBMOD_FRAMEWORK_CREDITS.txt', HOOKS_CREDIT)
    return {
        'bundled_framework': {'id': 'mod_hooks', 'version': '21.1',
                              'source_archive_sha256': HOOKS_ARCHIVE_SHA256,
                              'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in assets.items()}},
        'external_hooks_required': False,
        'display_only_translation_files': sorted(DISPLAY_ONLY_FILES),
    }
