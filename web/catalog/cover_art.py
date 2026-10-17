"""Curated theme artwork, selected from recorded facts rather than remote prompts."""
from django.templatetags.static import static


ART = {
    'lu-bu': ('吕布之姿', '双翎冠与方天画戟的吕布主题插画'),
    'guan-yu': ('关二爷的底子', '绿袍长髯、手持偃月刀的关羽主题插画'),
    'zhang-fei': ('张飞式猛将', '浓须铁甲、手持蛇矛的张飞主题插画'),
    'huang-zhong': ('黄忠式神射', '白须老将张弓搭箭的黄忠主题插画'),
    'yan-liang': ('河北猛将·颜良', '持长刀的河北猛将颜良主题插画'),
    'wen-chou': ('河北猛将·文丑', '重甲持矛的河北猛将文丑主题插画'),
    'trade-port': ('四海通商', '帆船与商队汇聚在中世纪海港的主题插画'),
    'named-loot': ('红装寻宝', '营地中陈列传奇武器与甲胄的主题插画'),
    'mercenary-camp': ('远征将启', '篝火边整备待发的雇佣兵战团主题插画'),
    'armoury': ('淬火军械', '锻炉边修整武器与甲胄的主题插画'),
    'chronicle': ('远征手札', '烛光下的地图、手札与羽毛笔主题插画'),
}


def artwork(key):
    title, alt = ART[key]
    return {'key': key, 'title': title, 'alt': alt,
            'url': static(f'covers/v1/{key}.webp'), 'source': 'generated'}


def mod_artwork(metadata, uploaded_url=''):
    if uploaded_url:
        return {'key': '', 'title': '作者封面', 'alt': str(metadata.get('title', 'MOD')) + ' 展示图',
                'url': uploaded_url, 'source': 'author'}
    title = ' '.join(str(metadata.get(field, '')) for field in ('title', 'english_name', 'summary')).casefold()
    heroes = (
        ('lu-bu', ('吕布', '吕奉先', 'lu bu', 'lü bu')),
        ('zhang-fei', ('张飞', '张翼德', 'zhang fei')),
        ('guan-yu', ('关羽', '关二爷', '关云长', 'guan yu')),
        ('huang-zhong', ('黄忠', 'huang zhong')),
        ('yan-liang', ('颜良', 'yan liang')),
        ('wen-chou', ('文丑', 'wen chou')),
    )
    for key, names in heroes:
        if any(name in title for name in names):
            return artwork(key)
    for key, words in (
        ('trade-port', ('港口', '商路', '商队', '贸易', 'caravan', 'trade')),
        ('named-loot', ('红装', '宝藏', '传奇装备', 'named item', 'treasure')),
        ('armoury', ('武器', '盔甲', '装备', '锻造', 'weapon', 'armor', 'armour')),
    ):
        if any(word in title for word in words):
            return artwork(key)
    return artwork({'战斗与平衡': 'armoury', '装备与外观': 'armoury',
                    '起源与事件': 'mercenary-camp', '汉化': 'chronicle',
                    '基础功能': 'chronicle', '框架': 'chronicle'}.get(metadata.get('category'), 'mercenary-camp'))
