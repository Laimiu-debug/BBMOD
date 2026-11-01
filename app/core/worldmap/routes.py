"""Terrain-aware land routes. Travel time is a stated baseline estimate."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import math

from .model import SPEED_MULT, WorldMap, adjacent
from .localization import town_label


@dataclass(frozen=True)
class Route:
    stops: tuple[int, ...]
    tiles: tuple[tuple[int, int], ...]
    hours: float
    road_steps: int
    legs: tuple[dict, ...]


class RoutePlanner:
    def __init__(self, world: WorldMap):
        self.world = world
        self._graph = None
        self._searches = {}

    def _build_graph(self):
        world = self.world
        graph = [[] for _ in range(world.width*world.height)]
        for y, row in enumerate(world.rows):
            for x, tile in enumerate(row):
                if not SPEED_MULT[tile[0]]:
                    continue
                for direction in range(6):
                    nx, ny = adjacent(x, y, direction)
                    if not world.contains((nx, ny)):
                        continue
                    other = world.rows[ny][nx]
                    if not SPEED_MULT[other[0]]:
                        continue
                    road = bool(tile[4] & (1 << direction) and other[4] & (1 << ((direction+3) % 6)))
                    dx = (nx-x)*180
                    dy = (ny-y)*120+((nx & 1)-(x & 1))*60
                    seconds = math.hypot(dx, dy)/75 * (.5/SPEED_MULT[tile[0]]+.5/SPEED_MULT[other[0]])/(1.5 if road else 1)
                    graph[y*world.width+x].append((ny*world.width+nx, seconds, road))
        self._graph = graph

    def _search(self, source: int, road_only: bool):
        key = source, road_only
        if key in self._searches:
            return self._searches[key]
        if self._graph is None:
            self._build_graph()
        world = self.world
        start = world.settlements[source].xy
        start_id = start[1]*world.width+start[0]
        costs = [math.inf]*len(self._graph)
        previous = [-1]*len(self._graph)
        roads = [False]*len(self._graph)
        costs[start_id] = 0
        queue = [(0., start_id)]
        while queue:
            cost, current = heapq.heappop(queue)
            if cost != costs[current]:
                continue
            for target, seconds, road in self._graph[current]:
                if road_only and not road:
                    continue
                next_cost = cost+seconds
                if next_cost+1e-9 < costs[target]:
                    costs[target], previous[target], roads[target] = next_cost, current, road
                    heapq.heappush(queue, (next_cost, target))
        self._searches[key] = costs, previous, roads
        return costs, previous, roads

    def plan(self, stops: list[int] | tuple[int, ...], *, road_only=False) -> Route:
        world = self.world
        if any(type(i) is not int or not 0 <= i < len(world.settlements) for i in stops):
            raise ValueError('路线包含无效城镇。')
        tiles, legs, hours, road_steps = [], [], 0., 0
        for source, target in zip(stops, stops[1:]):
            if source == target:
                continue
            costs, previous, roads = self._search(source, road_only)
            destination = world.settlements[target].xy
            current = destination[1]*world.width+destination[0]
            if not math.isfinite(costs[current]):
                raise ValueError(f'{town_label(world, source)} → {town_label(world, target)} 没有可通行的'+('连续道路。' if road_only else '陆路。'))
            leg_hours = costs[current]*24/105
            path, road_count = [], 0
            while current >= 0:
                path.append((current % world.width, current//world.width))
                road_count += int(roads[current])
                current = previous[current]
            path.reverse()
            tiles.extend(path if not tiles else path[1:])
            legs.append(dict(source=source, target=target, hours=leg_hours, steps=len(path)-1, road_steps=road_count))
            hours += leg_hours
            road_steps += road_count
        return Route(tuple(stops), tuple(tiles), hours, road_steps, tuple(legs))
