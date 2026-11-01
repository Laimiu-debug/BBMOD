"""Display data shared by the website and the independently validated solver."""
from .localization import building_label, place_label, site_label, town_label, town_traits
from .loot import KINDS, camp_detail, item_label, item_rating
from .model import CAMP_PROFILE_LABEL, PROFILE_LABEL
from .trade import GOODS, goods_label, offer_reason, opportunities, prices, town_advice


def atlas_data(world):
    towns = []
    for town in world.settlements:
        towns.append(dict(index=town.index, name=town_label(world, town.index), xy=town.xy,
            traits=town_traits(town), produce=[goods_label(g) for g in dict.fromkeys(town.produce)],
            buildings=[building_label(b) for b in town.buildings if b],
            sites=[site_label(a) for a in town.attached], advice=town_advice(world, town.index),
            market=[dict(good=goods_label(g), buy=prices(town, g)[0], sell=prices(town, g)[1]) for g in GOODS]))
    camps, loot = [], []
    if world.campaign:
        for camp in world.campaign.camps:
            camps.append(dict(index=camp.index, name=place_label(camp.name), xy=camp.xy,
                              count=len(camp.items), detail=camp_detail(world, camp)))
            for item in camp.items:
                rating = item_rating(item)
                loot.append(dict(index=len(loot), camp=camp.index, name=item_label(item), kind=item.kind,
                    kind_label=KINDS[item.kind], score=rating.score if rating else None,
                    quality=rating.quality if rating else None, detail=camp_detail(world, camp, item)))
    return dict(schema=1, seed=world.seed, width=world.width, height=world.height, rows=world.rows,
        profile=PROFILE_LABEL, camp_profile=CAMP_PROFILE_LABEL, towns=towns, camps=camps, loot=loot,
        regions=[dict(name=place_label(r['name']), xy=r['xy']) for r in world.regions],
        player=world.campaign.player_xy if world.campaign else None,
        offers=[dict(good=goods_label(o.good), source=o.source, target=o.target, buy=o.buy, sell=o.sell,
                     profit=o.profit, roi=o.roi, reason=offer_reason(world, o)) for o in opportunities(world)])
