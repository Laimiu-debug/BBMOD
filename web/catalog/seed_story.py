"""Deterministic, fact-backed seed stories and hero motifs for public cards."""
import hashlib

from app.core.seedgen.brother_rating import rate_brother
from app.core.seedgen.config_emitter import ATTRIBUTES
from app.core.seedgen.presentation import brothers, metric, named_count
from .cover_art import artwork


def _variant(identity, choices):
    return choices[int(hashlib.sha256(identity.encode('utf-8')).hexdigest()[:8], 16) % len(choices)]


def _hero(brother, rating, identity):
    if not rating or rating.rank == 0:
        return None
    if rating.title == '神射':
        return 'huang-zhong'
    if rating.title == '统领':
        return 'guan-yu' if rating.rank >= 2 else None
    if rating.title == '盾卫' and rating.rank >= 3:
        return 'zhang-fei'
    if rating.rank == 4:
        return 'lu-bu'
    if rating.rank == 3:
        muscular = brother.projected.get('Hitpoints', 0) >= 100 or bool(
            {'trait.huge', 'trait.strong', 'trait.drunkard'} & set(brother.traits))
        return 'zhang-fei' if muscular else 'guan-yu'
    if rating.rank == 2:
        return _variant(identity, ('yan-liang', 'wen-chou'))
    return None


HEADLINES = {
    'lu-bu': ('这副底子，有几分吕布之姿', '帐下添一员无双猛将'),
    'guan-yu': ('关二爷般的沉稳，先看这副底子', '长刀未出鞘，已有大将风'),
    'zhang-fei': ('张飞式猛将，前排先立住一人', '一身虎胆，等你带他上阵'),
    'huang-zhong': ('黄忠式神射，远程有了盼头', '弓还没拉满，底子先亮出来'),
    'yan-liang': ('河北猛将的底子，值得练一练', '颜良式的好苗子，就在这支战团'),
    'wen-chou': ('文丑式猛将，养成路线有着落', '河北有猛将，你的战团也有苗子'),
    'trade-port': ('让港口，把下一程商路串起来', '帆影连着城镇，跑商多些选择'),
    'named-loot': ('先翻红装账本，再决定往哪儿走', '宝物记在册，远征有了念想'),
    'mercenary-camp': ('篝火刚点起，远征等你落笔', '兄弟已在营中，故事从这里开始'),
}


def seed_story(result):
    identity = result.origin + '|' + result.seed
    people = brothers(result)
    roster = []
    for brother in people:
        rating = rate_brother(brother)
        hero = _hero(brother, rating, identity + f'|{brother.index}')
        stars_complete = len(brother.stars) == len(ATTRIBUTES)
        roster.append({'index': brother.index, 'role': brother.role,
                       'rating': rating.label if rating else '资料不足，暂不分档',
                       'rank': rating.rank if rating else -1,
                       'evidence': rating.evidence if rating else '',
                       'hero': artwork(hero) if hero else None,
                       'stars': sum(brother.stars.values()) if stars_complete else None,
                       'star_positions': '、'.join(f'{ATTRIBUTES[key]}{brother.stars[key]}星'
                           for key in ATTRIBUTES if brother.stars.get(key, 0)),
                       'brother': brother})
    # Only genuine qualifying profiles can receive a hero illustration.
    candidates = [row for row in roster if row['hero']]
    featured = max(candidates, key=lambda row: (row['rank'], -row['index'])) if candidates else None
    ports, named = metric(result, 'SettlementInfo:', 'Port'), named_count(result)
    if featured:
        key = featured['hero']['key']
        lead = f"兄弟{featured['index']}评为{featured['rating']}，11级潜力：{featured['evidence']}。"
    elif named is not None and named >= 10:
        key, lead = 'named-loot', '这一局，先把寻宝路线写进远征计划。'
    elif ports is not None and ports >= 6:
        key, lead = 'trade-port', '不妨从港口出发，把沿海城镇慢慢连成自己的商路。'
    else:
        key, lead = 'mercenary-camp', '先挑兄弟，再定去路；一份开局，能写出许多种远征。'
    facts = []
    nine = sum(row['stars'] == 9 for row in roster)
    if nine:
        facts.append(f'{nine}名兄弟总计9星，星位分配也别忘了看')
    if ports is not None:
        facts.append(f'记录有{ports}座港口')
    if named is not None:
        facts.append(f'初始营地记录{named}件红装，能否取得还要看路线与守军')
    if not people and ports is None and named is None:
        facts.append('现有记录尚未包含可解析的人物、港口或红装详情，可先核对完整档案')
    headline = _variant(identity, HEADLINES[key])
    if not featured and nine:
        headline = '九星在身，先看看星位落在何处'
    return {'headline': headline, 'intro': lead, 'facts': facts,
            'cover': artwork(key), 'featured': featured, 'brothers': roster,
            'has_hero': bool(featured), 'motif_label': featured['hero']['title'] if featured else artwork(key)['title']}
