import pytest

from core.gamelog import LogRow
from core.seedgen.config_emitter import attribute_condition, render_bro_row, score_condition
from core.seedgen.log_watcher import SeedLogParser, SeedResult
from core.seedgen.presentation import Brother, brothers, format_collection, format_seed, highlights, metric
from core.seedgen.brother_rating import PROFILES, TIERS, rate_brother


@pytest.mark.parametrize('title,keys,levels', PROFILES)
def test_each_ability_profile_has_enforced_tier_boundaries(title, keys, levels):
    for rank, thresholds in enumerate(levels, 1):
        brother = Brother(1, '', projected=dict(zip(keys, thresholds)))
        rating = rate_brother(brother)
        assert rating.rank == rank and rating.title == title
        assert TIERS[rank] in rating.label
        for key in keys:
            reduced = Brother(1, '', projected={**brother.projected, key: brother.projected[key] - 1})
            assert rate_brother(reduced).rank < rank


def test_nine_stars_do_not_replace_combat_attributes_or_missing_evidence():
    brother = Brother(1, '', projected={'MeleeSkill': 75, 'MeleeDefense': 10,
        'Hitpoints': 70, 'Stamina': 90, 'Bravery': 40},
        stars={'MeleeSkill': 3, 'MeleeDefense': 3, 'Stamina': 3})
    assert rate_brother(brother).rank == 0
    assert rate_brother(Brother(1, '', projected={'MeleeSkill': 110})) is None


def test_seed_description_contains_themed_rating_evidence_and_star_positions():
    seed = SeedResult('THEMEDSEED', 1, done=True, lines=[
        'CharInfo: 0 Melee:0.9 Hitpoints:60(95)0 Bravery:40(55)0 Stamina:80(115)3 '
        'MeleeSkill:60(95)3 RangedSkill:40(70)0 MeleeDefense:5(35)3 '
        'RangedDefense:0(30)0 Initiative:100(140)0',
        'Trait: trait.determined',
    ])
    detail = format_seed(seed)
    assert '总计9星；疲劳上限3星、近战命中3星、近战防御3星' in detail
    assert '关张档 · 猛将' in detail and '依据：近战命中95、近战防御35' in detail
    assert '坚定（毅然）' in detail and '不能同时把全部属性点满' in detail
    brief = format_seed(seed, 'danmaku')
    assert '1名9星兄弟' in brief and '关张档 · 猛将' in brief


def result():
    return SeedResult("AbCdEfGhIj", 42, origin="scenario.militia", done=True, lines=[
        "TeamInfo: 0.83 Melee:3",
        "CharInfo: 0 Melee:0.9 Hitpoints:65(100)1 MeleeSkill:60(95)3 MeleeDefense:5(30)1",
        "CharInfo: 1 Melee:0.8 MeleeSkill:60(90)2 MeleeDefense:8(38)2",
        "CharInfo: 2 Polearm:0.8 MeleeSkill:60(90)2 MeleeDefense:2(22)0",
        "SettlementInfo: Settlements:22 CityPort:2 Port:7[2,1,1,2,1]",
        "NamedInfo: Helmet:4 Armor:2 Shield:3 Sum:12(2)",
        "ItemInfo(Armor): armor.named_coat Armor:250",
    ])


def test_attribute_parse_uses_projected_values_and_named_summary():
    seed = result()
    parsed = brothers(seed)
    assert parsed[0].initial["MeleeSkill"] == 60
    assert parsed[0].projected["MeleeSkill"] == 95
    assert parsed[0].stars["MeleeSkill"] == 3
    text = format_seed(seed, "danmaku")
    assert text.startswith("缺大哥？AbCdEfGhIj 农民团，7座港口")
    assert "3个预估11级90+近战大哥" in text and "共12件红装" in text and "2件红甲" in text
    assert "金鹅" not in text and "北港" not in text
    assert "生命 65→100（1星）" in format_seed(seed)


def test_unknown_data_is_not_invented_or_confused_with_zero():
    seed = SeedResult("UNKNOWNSEED", 3, lines=["SettlementInfo: CityPort:2"])
    assert metric(seed, "SettlementInfo:", "Port") is None
    assert highlights(seed) == []
    text = format_seed(seed, "danmaku", "卡大货了？", "自填路线\n先到港口")
    assert "0件" not in text and "0座" not in text and "\n" not in text
    assert text.startswith("卡大货了？UNKNOWNSEED")
    assert text.endswith("自填路线 先到港口")
    zero = SeedResult("ZEROSEED00", 4, lines=["TeamInfo: 0 Melee:0", "SettlementInfo: Port:0", "NamedInfo: Sum:0(0)"])
    assert zero.team_score == 0 and "0座港口" in highlights(zero)


def test_parser_preserves_actual_origin_and_negative_or_integer_scores():
    parser = SeedLogParser()
    records, _ = parser.feed([LogRow("info", "", "SQ", text) for text in (
        "Seed: AbCdEfGhIj LoopIdx:4 BroOutputType:0 MapOutputType:0 Origin:scenario.militia",
        "TeamInfo: -0.02 Melee:1", "CRLF")])
    assert records[0].origin == "scenario.militia" and records[0].team_score == -0.02
    assert records[0].bro_output_type == 0 and records[0].map_output_type == 0


def test_danmaku_is_one_line_per_seed_and_codes_keep_case():
    seed = result()
    text = format_collection([seed, SeedResult("abCDEfGHIJ", 2)], "danmaku", "不加开场白", {})
    assert len(text.splitlines()) == 2
    assert text.startswith("AbCdEfGhIj ")
    assert format_seed(seed, "seed") == "AbCdEfGhIj"


def test_attribute_condition_wire_order_and_score_pair_layout():
    condition = attribute_condition(3, {"MeleeSkill": 90, "MeleeDefense": 25})
    assert render_bro_row(condition) == "[BroOutput.RoleAttr, 3, -100, -100, -100, 90, -100, 25, -100, -100],"
    assert score_condition("AnyRoleScore", .8, 3, "RoleMelee").args == [.8, 3]
    assert score_condition("RoleScore", .8, 3, "RoleMelee").args == [.8, 3, "RoleMelee"]
    with pytest.raises(ValueError):
        attribute_condition(3, {})
