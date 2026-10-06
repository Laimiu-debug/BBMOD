"""Desktop application version; localization packages have their own version."""
import re

# Public releases always use MAJOR.MINOR.PATCH; see docs/versioning.md.
VERSION = '0.3.1'


def release_filename(version: str = VERSION) -> str:
    """One public naming rule; build runs never invent or increment a version."""
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        raise ValueError('桌面发布版本必须使用 主版本.功能版本.修复版本，例如 0.3.1。')
    if any(int(part) > 65535 for part in version.split('.')):
        raise ValueError('版本号超出 Windows 版本资源范围。')
    return f'BBMOD-{version}.exe'


def windows_version_info(version: str = VERSION) -> str:
    """PyInstaller VSVersionInfo; numeric fields carry the trailing pre-release number."""
    match = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]*?(\d+))?', version)
    if not match:
        raise ValueError(f'无法生成 Windows 版本信息：{version}')
    numbers = tuple(int(part or 0) for part in match.groups())
    flags = '0x2' if '-' in version else '0x0'
    strings = [('CompanyName', 'BBMOD'), ('FileDescription', 'BBMOD 战团整备所'), ('FileVersion', version),
               ('InternalName', 'BBMOD'), ('OriginalFilename', f'BBMOD-{version}.exe'),
               ('ProductName', 'BBMOD 战团整备所'), ('ProductVersion', version)]
    table = ',\n'.join(f"    StringStruct({key!r}, {value!r})" for key, value in strings)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={numbers}, prodvers={numbers}, mask=0x3f,
                    flags={flags}, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('080404B0', [
{table}
  ])]), VarFileInfo([VarStruct('Translation', [2052, 1200])])]
)
"""
