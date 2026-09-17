"""One reviewed, display-only place lexicon for the native map and HTML UI."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile

from .l10n_tokens import validate_translation
from .paths import resource_path

REVIEW_FILE = resource_path('localization/reviewed_place_names.json')
BRIDGE_FILE = resource_path('localization/place_session.nut')
BRIDGE_ENTRY = 'scripts/!mods_preload/bbmod_place_session.nut'
DATA_ENTRY = 'ui/mods/bbmod_l10n/place_names.tsv'
JS_ENTRY = 'ui/mods/bbmod_l10n/place_names.js'
HEADER = 'BBMOD-PLACE-DISPLAY-1\n'
MODE = 'launcher_session'


def reviewed_places(catalog, policy):
    if not policy:
        return {}
    data = json.loads(REVIEW_FILE.read_text(encoding='utf-8'))
    expected = {catalog['entries'][key]['source'] for key in policy['name_keys']}
    if set(data['terms']) != expected or set(data['reviewed_ids']) != set(policy['name_keys']):
        raise ValueError('独立地名精修词库与当前目录不匹配')
    for source, target in data['terms'].items():
        if not target.strip() or validate_translation(source, target):
            raise ValueError('地名译文或变量无效：' + source)
    return data['terms']


def _variants(source, target):
    # The geographic corpus has at most one original random-choice group.
    pattern = r'\{([^{}]+)\}'
    a, b = list(re.finditer(pattern, source)), list(re.finditer(pattern, target))
    if not a and not b:
        return [(source, target)]
    if len(a) != 1 or len(b) != 1:
        raise ValueError('不支持的地名随机模板')
    left, right = a[0].group(1).split(' | '), b[0].group(1).split(' | ')
    if len(left) != len(right):
        raise ValueError('地名随机分支数量不一致')
    return [(source[:a[0].start()] + x.strip() + source[a[0].end():],
             target[:b[0].start()] + y.strip() + target[b[0].end():]) for x, y in zip(left, right)]


def build_display_data(catalog, policy, dictionary):
    reviewed = reviewed_places(catalog, policy)
    result = {}
    def add(source, target):
        source, target = source.strip(), target.strip()
        if not source or not target or any(c in source + target for c in '\t\r\n{}%'):
            raise ValueError('地名显示词库含未展开的模板或控制符：' + source)
        if source in result and result[source] != target:
            raise ValueError('相同英文地名有多个译名：' + source)
        result[source] = target
    for source, default in reviewed.items():
        if source == 'Ruins of ':
            continue
        target = dictionary.get(source, default)
        for english, chinese in _variants(source, target):
            token = next((name for name in ('randomname', 'randomnoble') if '%' + name + '%' in english), None)
            if token:
                pool = policy['owner_pools']['CharacterNames' if token == 'randomname' else 'KnightNames']
                for owner in pool:
                    translated_owner = dictionary.get(owner)
                    if not translated_owner or not re.search(r'[\u3400-\u9fff]', translated_owner):
                        raise ValueError('地名中的人物姓名尚未校对：' + owner)
                    add(english.replace('%' + token + '%', owner), chinese.replace('%' + token + '%', translated_owner))
            else:
                add(english, chinese)
    # Ruined towns keep the same canonical English name; pre-expand the visible
    # prefix so the map and prose use identical Chinese word order.
    ruin_suffix = dictionary.get('Ruins of ', reviewed['Ruins of ']).strip().rstrip('：:')
    for source, target in list(result.items()):
        if not source.startswith('Ruins of '):
            result.setdefault('Ruins of ' + source, target + ruin_suffix)
    raw = (HEADER + ''.join(source + '\t' + result[source] + '\n' for source in sorted(result))).encode('utf-8')
    return raw, result


def write_display_assets(archive, catalog, policy, dictionary):
    raw, names = build_display_data(catalog, policy, dictionary)
    digest = hashlib.sha256(raw).hexdigest()
    config = {'session': 'zh-CN:' + digest, 'names': names}
    archive.writestr(DATA_ENTRY, raw)
    archive.writestr(JS_ENTRY, 'window.BBMOD_PLACE_NAMES = ' + json.dumps(config, ensure_ascii=True) + ';\n')
    archive.write(BRIDGE_FILE, BRIDGE_ENTRY)
    return {'place_name_display': MODE, 'place_display_sha256': digest,
            'reviewed_place_entries': len(policy['name_keys']), 'expanded_place_names': len(names),
            'place_display_bridge_sha256': hashlib.sha256(BRIDGE_FILE.read_bytes()).hexdigest(),
            'place_name_save_policy': 'original_english_unchanged'}


def read_packaged_display(package):
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read('BBMOD_L10N.json'))
        if manifest.get('place_name_display') != MODE:
            raise ValueError('请先生成并应用新版独立汉化，再使用中文地名启动')
        if archive.getinfo(DATA_ENTRY).file_size > 4 * 1024 * 1024:
            raise ValueError('地名显示词库过大')
        raw = archive.read(DATA_ENTRY)
        if hashlib.sha256(raw).hexdigest() != manifest.get('place_display_sha256'):
            raise ValueError('汉化包中的地名词库校验失败，请重新生成')
        if not raw.startswith(HEADER.encode('ascii')) or b'\0' in raw:
            raise ValueError('地名显示词库格式无效')
        rows = raw.decode('utf-8')[len(HEADER):].splitlines()
        names = {}
        for row in rows:
            fields = row.split('\t')
            if len(fields) != 2 or not all(fields) or fields[0] in names:
                raise ValueError('地名显示词库存在空值或重复条目')
            names[fields[0]] = fields[1]
        if not names or not raw.endswith(b'\n'):
            raise ValueError('地名显示词库不完整')
        # A mismatched UI dictionary or bridge must fail before spawning the
        # game, rather than enabling Chinese labels on only one display path.
        if archive.getinfo(JS_ENTRY).file_size > 8 * 1024 * 1024:
            raise ValueError('界面地名词库过大')
        script = archive.read(JS_ENTRY).decode('utf-8')
        prefix = 'window.BBMOD_PLACE_NAMES = '
        if not script.startswith(prefix) or not script.endswith(';\n'):
            raise ValueError('界面地名词库格式无效')
        config = json.loads(script[len(prefix):-2])
        if config != {'session': 'zh-CN:' + manifest['place_display_sha256'], 'names': names}:
            raise ValueError('地图与对话的地名词库不一致，请重新生成汉化包')
        bridge = archive.read(BRIDGE_ENTRY)
        if (hashlib.sha256(bridge).hexdigest() != manifest.get('place_display_bridge_sha256')
                or bridge != BRIDGE_FILE.read_bytes()):
            raise ValueError('地名会话组件不匹配，请更新软件并重新生成汉化包')
        return raw
