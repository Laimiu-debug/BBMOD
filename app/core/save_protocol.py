"""Shared campaign manifests and bounded, opaque Battle Brothers save validation."""
import hashlib
import json

from .profile_protocol import HASH, file_name, text, validate_manifest as validate_profile

MAX_SAVE_BYTES = 100 * 1024**2
DLCS = ('Lindwurm', 'Beasts & Exploration', 'Warriors of the North', 'Blazing Deserts', 'Of Flesh and Faith')


def save_name(value):
    if not isinstance(value, str) or not value.lower().endswith('.sav'):
        raise ValueError('请选择战役存档 .sav 文件。')
    return file_name(value[:-4] + '.zip')[:-4] + '.sav'


def inspect_save(stream):
    """Check the container header and bytes, without executing or unpacking a save."""
    stream.seek(0)
    header = stream.read(7)
    # BB's resource saves (for example MSU update caches) have revision zero.
    if len(header) != 7 or header[:3] != b'\xbb\x00\x02' or int.from_bytes(header[3:7], 'little') == 0:
        raise ValueError('这不是可分享的战役存档，或存档格式不受支持。')
    digest, size = hashlib.sha256(header), len(header)
    while block := stream.read(128 * 1024):
        size += len(block)
        if size > MAX_SAVE_BYTES:
            raise ValueError('单个存档最大 100 MB。')
        digest.update(block)
    if size < 256:
        raise ValueError('战役存档不完整。')
    stream.seek(0)
    return {'sha256': digest.hexdigest(), 'size': size}


def validate_manifest(value):
    result = validate_profile(value, allow_empty=True)
    if not result['game_version']:
        raise ValueError('分享存档必须记录游戏版本。')
    dlcs = value.get('dlcs')
    if (not isinstance(dlcs, list) or any(not isinstance(dlc, str) or dlc not in DLCS for dlc in dlcs)
            or len(set(dlcs)) != len(dlcs)):
        raise ValueError('存档 DLC 清单无效。')
    save = value.get('save')
    if (not isinstance(save, dict) or not isinstance(save.get('sha256'), str)
            or not HASH.fullmatch(save['sha256']) or type(save.get('size')) is not int
            or not 256 <= save['size'] <= MAX_SAVE_BYTES):
        raise ValueError('存档大小或校验信息无效。')
    result['dlcs'] = sorted(dlcs)
    result['save'] = {'file_name': save_name(save.get('file_name')), 'sha256': save['sha256'], 'size': save['size']}
    return result


def profile_manifest(manifest):
    return validate_profile(manifest, allow_empty=True)


def manifest_key(manifest):
    return hashlib.sha256(json.dumps(validate_manifest(manifest), ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
