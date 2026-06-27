# core/city_map.py

from collections import deque
import math
import random

try:
    import pygame
except ModuleNotFoundError:
    pygame = None

from config import (
    ROWS, COLS, TILE_SIZE,
    ROAD, NORMAL_BUILDINGS, BUILDING_TILES, HOSPITAL, GAS_STATION, PARK,
    STATION, HYDRANT, FIRE, TRAFFIC, BLOCKED, RISKY, WALKABLE_TILES,
    TILE_COLORS, TILE_COST, GRID_COLOR, WHITE, BLACK, YELLOW, SHOW_LOT_MODELS,
)
from core.models import CityLot, FireIncident, TileVisual, TruckSpec


DISTRICT_BUILDINGS = {
    "downtown": ["building_4", "building_5", "building_6", "building_6"],
    "industrial": ["building_3", "building_4", "building_5", "building_6"],
    "residential": ["building_1", "building_1", "building_2", "building_3"],
    "civic": ["building_2", "building_4", "building_5"],
    "greenbelt": ["building_1", "building_2", "building_3"],
}

LOT_FOOTPRINTS = {
    "downtown": [(4, 4), (4, 3), (3, 4), (3, 3), (2, 4), (2, 3), (2, 2), (2, 1), (1, 2), (1, 1)],
    "industrial": [(4, 3), (4, 2), (3, 4), (3, 3), (3, 2), (2, 4), (2, 3), (2, 2), (2, 1), (1, 2), (1, 1)],
    "residential": [(3, 2), (2, 3), (2, 2), (2, 1), (1, 2), (1, 1)],
    "civic": [(4, 3), (3, 3), (3, 2), (2, 3), (2, 2), (2, 1), (1, 2), (1, 1)],
    "greenbelt": [(4, 2), (3, 2), (2, 2), (2, 1), (1, 2), (1, 1)],
}

HEIGHT_RANGES = {
    "downtown": (3, 6),
    "industrial": (1, 4),
    "residential": (1, 2),
    "civic": (2, 4),
    "greenbelt": (1, 1),
}

ROAD_LIKE_TILES = {ROAD, STATION, HYDRANT, TRAFFIC, BLOCKED, RISKY}


class CityMap:
    """
    Tabletop city generator:
    - Roads form a connected street network.
    - Space between roads is split into rectangular building lots: 2x1, 2x2,
      2x3, 3x4, 4x4...
    - grid remains tile-based for search algorithms.
    - lots/visuals store footprint metadata for large PNG assets.
    """

    def __init__(self, asset_loader=None, seed=None, station_count=3, fire_count=6, force_single_truck_fires=False):
        self.asset_loader = asset_loader
        self.seed = seed
        self.rng = random.Random(seed)
        self.station_count = max(1, min(3, int(station_count)))
        self.fire_count = max(1, int(fire_count))
        self.force_single_truck_fires = force_single_truck_fires
        self.grid = []
        self.visuals = []
        self.districts = []
        self.district_centers = {}
        self.road_rows = []
        self.road_cols = []
        self.road_cells = []
        self.lots = []
        self.lot_lookup = {}
        self.stations = []
        self.hydrants = []
        self.fires = []
        self.fire_lookup = {}
        self.selected_fire_index = 0
        self.generate()

    def generate(self):
        if self.seed is not None:
            self.rng.seed(self.seed)

        self.grid = [[ROAD for _ in range(COLS)] for _ in range(ROWS)]
        self.visuals = [[TileVisual(ROAD, ROAD, anchor=(r, c), district="road") for c in range(COLS)] for r in range(ROWS)]
        self.road_rows = []
        self.road_cols = []
        self.road_cells = []
        self.lots = []
        self.lot_lookup = {}
        self.stations = []
        self.hydrants = []
        self.fires = []
        self.fire_lookup = {}
        self.selected_fire_index = 0

        self._build_districts()
        self._build_tabletop_roads()
        self._build_city_lots()
        self._place_special_lots()
        self._place_stations_and_hydrants()
        self._place_road_conditions()
        self._place_fires()
        self._update_road_visuals()
        self._refresh_road_cells()

    def _build_districts(self):
        margin = 3
        centers = {
            "downtown": (self.rng.randint(7, ROWS - 8), self.rng.randint(9, COLS - 10)),
            "industrial": (self.rng.choice([4, ROWS - 5]), self.rng.choice([5, COLS - 6])),
            "residential": (self.rng.randint(4, ROWS - 5), self.rng.choice([4, COLS - 5])),
            "civic": (self.rng.randint(margin, ROWS - margin - 1), self.rng.randint(margin, COLS - margin - 1)),
            "greenbelt": (self.rng.choice([3, ROWS - 4]), self.rng.randint(4, COLS - 5)),
        }
        self.district_centers = centers
        self.districts = []
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                scored = []
                for name, center in centers.items():
                    dist = abs(r - center[0]) + abs(c - center[1])
                    scored.append((dist + self.rng.uniform(-2.0, 2.0), name))
                row.append(min(scored, key=lambda item: item[0])[1])
            self.districts.append(row)

    def _build_tabletop_roads(self):
        self.road_rows = self._make_road_lines(ROWS, min_gap=5, max_gap=8)
        self.road_cols = self._make_road_lines(COLS, min_gap=5, max_gap=9)

        for r in range(ROWS):
            for c in range(COLS):
                self.grid[r][c] = self._district_default_building(r, c)

        for r in self.road_rows:
            for c in range(COLS):
                self._set_road_tile(r, c, ROAD)
        for c in self.road_cols:
            for r in range(ROWS):
                self._set_road_tile(r, c, ROAD)

        self._add_city_entries()
        self._add_minor_streets()
        self._remove_double_wide_road_blobs()
        self._refresh_road_cells()

    def _make_road_lines(self, limit, min_gap, max_gap):
        lines = [0, limit - 1]
        pos = self.rng.randint(4, 5)
        while pos < limit - 2:
            lines.append(pos)
            pos += self.rng.randint(min_gap, max_gap)
        return sorted(set(lines))

    def _add_city_entries(self):
        entries = [
            (self.rng.randint(2, ROWS - 3), 0),
            (self.rng.randint(2, ROWS - 3), COLS - 1),
            (0, self.rng.randint(2, COLS - 3)),
            (ROWS - 1, self.rng.randint(2, COLS - 3)),
        ]
        for entry in entries:
            target = self._nearest_road(entry)
            if target:
                self._carve_manhattan_road(entry, target)

    def _add_minor_streets(self):
        for top, bottom in zip(self.road_rows, self.road_rows[1:]):
            height = bottom - top - 1
            if height < 6 or self.rng.random() > 0.18:
                continue
            r = self.rng.randint(top + 2, bottom - 2)
            c1 = self.rng.choice(self.road_cols[:-1])
            c2 = self.rng.choice([c for c in self.road_cols if c != c1])
            for c in range(min(c1, c2), max(c1, c2) + 1):
                self._set_road_tile(r, c, ROAD)
            self.road_rows.append(r)

        for left, right in zip(self.road_cols, self.road_cols[1:]):
            width = right - left - 1
            if width < 7 or self.rng.random() > 0.14:
                continue
            c = self.rng.randint(left + 2, right - 2)
            r1 = self.rng.choice(self.road_rows[:-1])
            r2 = self.rng.choice([r for r in self.road_rows if r != r1])
            for r in range(min(r1, r2), max(r1, r2) + 1):
                self._set_road_tile(r, c, ROAD)
            self.road_cols.append(c)

        self.road_rows = sorted(set(self.road_rows))
        self.road_cols = sorted(set(self.road_cols))

    def _carve_manhattan_road(self, start, goal):
        r, c = self._clamp_cell(start)
        gr, gc = self._clamp_cell(goal)
        self._set_road_tile(r, c, ROAD)
        if self.rng.random() < 0.5:
            while c != gc:
                c += 1 if gc > c else -1
                self._set_road_tile(r, c, ROAD)
            while r != gr:
                r += 1 if gr > r else -1
                self._set_road_tile(r, c, ROAD)
        else:
            while r != gr:
                r += 1 if gr > r else -1
                self._set_road_tile(r, c, ROAD)
            while c != gc:
                c += 1 if gc > c else -1
                self._set_road_tile(r, c, ROAD)

    def _build_city_lots(self):
        self.lots = []
        self.lot_lookup = {}
        lot_id = 1
        blocks = self._find_buildable_blocks()
        for top, left, height, width in blocks:
            occupied = [[False for _ in range(width)] for _ in range(height)]
            for rr in range(top, top + height):
                for cc in range(left, left + width):
                    if self.grid[rr][cc] in ROAD_LIKE_TILES:
                        occupied[rr - top][cc - left] = True
            for local_r in range(height):
                local_c = 0
                while local_c < width:
                    if occupied[local_r][local_c]:
                        local_c += 1
                        continue
                    row = top + local_r
                    col = left + local_c
                    district = self.districts[row][col]
                    footprint = self._choose_footprint(district, occupied, local_r, local_c, width, height)
                    tile = self._district_default_building(row, col)
                    lot_id = self._create_lot(lot_id, row, col, footprint, tile, district, occupied, top, left)
                    local_c += footprint[0]

    def _find_buildable_blocks(self):
        blocks = []
        seen = set()
        for r in range(ROWS):
            for c in range(COLS):
                if (r, c) in seen or self.grid[r][c] in ROAD_LIKE_TILES:
                    continue
                q = deque([(r, c)])
                seen.add((r, c))
                cells = []
                while q:
                    cur = q.popleft()
                    cells.append(cur)
                    for nr, nc in [(cur[0] - 1, cur[1]), (cur[0] + 1, cur[1]), (cur[0], cur[1] - 1), (cur[0], cur[1] + 1)]:
                        if not self.is_inside(nr, nc) or (nr, nc) in seen or self.grid[nr][nc] in ROAD_LIKE_TILES:
                            continue
                        seen.add((nr, nc))
                        q.append((nr, nc))
                rows = [cell[0] for cell in cells]
                cols = [cell[1] for cell in cells]
                top, bottom = min(rows), max(rows)
                left, right = min(cols), max(cols)
                blocks.append((top, left, bottom - top + 1, right - left + 1))
        blocks.sort()
        return blocks

    def _choose_footprint(self, district, occupied, local_r, local_c, block_w, block_h):
        choices = LOT_FOOTPRINTS.get(district, LOT_FOOTPRINTS["residential"])[:]
        scored = []
        for width, height in choices:
            if self._footprint_fits(occupied, local_r, local_c, width, height, block_w, block_h):
                remaining_w = block_w - (local_c + width)
                remaining_h = block_h - (local_r + height)
                score = width * height * 10
                if remaining_w == 1:
                    score -= 45
                if remaining_h == 1:
                    score -= 30
                if width == 1 and height == 1:
                    score -= 120
                elif width == 1 or height == 1:
                    score -= 12
                if district in ("downtown", "industrial") and width * height >= 9:
                    score += 25
                score += self.rng.random() * 3
                scored.append((score, width, height))
        if scored:
            _score, width, height = max(scored, key=lambda item: item[0])
            return width, height
        return 1, 1

    def _footprint_fits(self, occupied, local_r, local_c, width, height, block_w, block_h):
        if local_c + width > block_w or local_r + height > block_h:
            return False
        for rr in range(local_r, local_r + height):
            for cc in range(local_c, local_c + width):
                if occupied[rr][cc]:
                    return False
        return True

    def _create_lot(self, lot_id, row, col, footprint, tile, district, occupied, block_top, block_left):
        width, height = footprint
        if width == 1:
            for rr in range(row, row + height):
                for cc in range(col, col + width):
                    if not self.is_inside(rr, cc) or self.grid[rr][cc] in ROAD_LIKE_TILES:
                        continue
                    occupied[rr - block_top][cc - block_left] = True
                    self._set_filler_tile(rr, cc)
            return lot_id

        cells = []
        for rr in range(row, row + height):
            for cc in range(col, col + width):
                if not self.is_inside(rr, cc) or self.grid[rr][cc] in ROAD_LIKE_TILES:
                    continue
                cells.append((rr, cc))
                occupied[rr - block_top][cc - block_left] = True
        if not cells:
            return lot_id

        height_value = self._height_for_lot(tile, district, footprint)
        asset_key = self._choose_asset_key(tile, footprint)
        rotation = self.rng.choice([0, 90, 180, 270])
        lot = CityLot(lot_id, tile, (row, col), footprint, cells, district, height_value, asset_key, rotation)
        self.lots.append(lot)

        for cell in cells:
            rr, cc = cell
            self.lot_lookup[cell] = lot
            self.grid[rr][cc] = tile
            self.visuals[rr][cc] = TileVisual(
                tile=tile,
                asset_key=asset_key,
                rotation=rotation,
                variant=0,
                height=height_value,
                footprint=footprint,
                anchor=(row, col),
                lot_id=lot_id,
                district=district,
            )
        return lot_id + 1

    def _place_special_lots(self):
        self._retile_random_lot(HOSPITAL, preferred=("civic", "downtown"), min_area=4)
        self._retile_random_lot(GAS_STATION, preferred=("industrial",), min_area=3)
        for _ in range(3):
            self._retile_random_lot(PARK, preferred=("greenbelt", "residential"), min_area=2)

    def _retile_random_lot(self, tile, preferred, min_area=1):
        candidates = [
            lot for lot in self.lots
            if lot.district in preferred and len(lot.cells) >= min_area and self._lot_has_access(lot)
        ]
        if not candidates:
            candidates = [lot for lot in self.lots if len(lot.cells) >= min_area and self._lot_has_access(lot)]
        if not candidates:
            return
        lot = self.rng.choice(candidates)
        lot.tile = tile
        lot.asset_key = self._choose_asset_key(tile, lot.footprint)
        lot.height = 0 if tile == PARK else max(1, lot.height)
        for rr, cc in lot.cells:
            self.grid[rr][cc] = tile
            self.visuals[rr][cc].tile = tile
            self.visuals[rr][cc].asset_key = lot.asset_key
            self.visuals[rr][cc].height = lot.height

    def _place_stations_and_hydrants(self):
        road_cells = list(self._largest_walkable_component(tile_filter={ROAD}))
        if not road_cells:
            road_cells = self.road_cells[:]
        self.rng.shuffle(road_cells)
        chosen = []
        for cell in road_cells:
            if all(abs(cell[0] - other[0]) + abs(cell[1] - other[1]) >= 9 for other in chosen):
                chosen.append(cell)
            if len(chosen) == self.station_count:
                break
        while len(chosen) < self.station_count and road_cells:
            chosen.append(road_cells.pop())

        for idx, cell in enumerate(chosen[:self.station_count]):
            r, c = cell
            self._set_road_tile(r, c, STATION)
            easy_single_truck = self.station_count == 1
            speed = [3, 2, 2][idx]
            capacity = [180, 150, 140][idx] if easy_single_truck else [90, 150, 140][idx]
            water = capacity
            heavy = easy_single_truck or idx == 2
            self.stations.append(TruckSpec(f"T{idx + 1}", idx, cell, speed, water, capacity, heavy))

        for _ in range(4):
            cell = self._random_plain_road_cell()
            if cell:
                self._set_road_tile(cell[0], cell[1], HYDRANT)
                self.hydrants.append(cell)

    def _place_road_conditions(self):
        self._place_condition(TRAFFIC, count=14)
        self._place_condition(RISKY, count=7)
        placed = 0
        attempts = 0
        while placed < 5 and attempts < 150:
            attempts += 1
            cell = self._random_plain_road_cell()
            if not cell or not self._safe_to_block(cell):
                continue
            self._set_road_tile(cell[0], cell[1], BLOCKED)
            placed += 1

    def _place_condition(self, tile, count):
        placed = 0
        attempts = 0
        while placed < count and attempts < count * 12:
            attempts += 1
            cell = self._random_plain_road_cell()
            if not cell:
                break
            self._set_road_tile(cell[0], cell[1], tile)
            placed += 1

    def _place_fires(self):
        reachable_roads = set()
        for truck in self.stations:
            reachable_roads.update(self._reachable_from(truck.start))

        candidates = []
        for lot in self.lots:
            access = self._lot_access_options(lot, allowed_cells=reachable_roads)
            if access and lot.tile in BUILDING_TILES and lot.tile != PARK:
                candidates.append((lot, access))
        self.rng.shuffle(candidates)
        candidates.sort(key=lambda item: self._fire_candidate_weight(item[0]))

        count = self.fire_count
        placed = 0
        danger_tiles = {HOSPITAL: "hospital", GAS_STATION: "gas", PARK: "normal"}
        while placed < count and candidates:
            lot, access = candidates.pop()
            if lot.fire_id:
                continue
            fire_cell, target = self.rng.choice(access)
            danger = danger_tiles.get(lot.tile, "normal")
            severity = self.rng.choice([1, 1, 2, 2, 3, 3])
            if danger in ["hospital", "gas"]:
                severity = max(severity, 2)
            if lot.footprint[0] * lot.footprint[1] >= 9:
                severity = max(severity, 2)
            required = 1 if self.force_single_truck_fires else 2 if severity >= 3 or danger == "gas" else 1
            base_score = 100 + severity * 80 + (220 if danger == "gas" else 0) + (180 if danger == "hospital" else 0)
            incident = FireIncident(f"F{placed + 1}", fire_cell, target, severity, danger, required, base_score)
            lot.fire_id = incident.id
            self.fires.append(incident)
            self.fire_lookup[incident.id] = incident
            placed += 1

    def _fire_candidate_weight(self, lot):
        danger_weight = 5 if lot.tile == GAS_STATION else 4 if lot.tile == HOSPITAL else 0
        area = lot.footprint[0] * lot.footprint[1]
        size_weight = 2 if area >= 9 else 1 if area >= 6 else 0
        district_weight = 1 if lot.district in ("downtown", "industrial") else 0
        return danger_weight + size_weight + district_weight + self.rng.random()

    def _set_road_tile(self, row, col, tile):
        if not self.is_inside(row, col):
            return
        self.grid[row][col] = tile
        self.lot_lookup.pop((row, col), None)
        asset_key = self._choose_asset_key(tile, (1, 1))
        self.visuals[row][col] = TileVisual(
            tile=tile,
            asset_key=asset_key,
            rotation=0,
            variant=0,
            height=0,
            footprint=(1, 1),
            anchor=(row, col),
            lot_id=0,
            district="road",
        )

    def _set_filler_tile(self, row, col):
        tile = self._district_default_building(row, col)
        district = self.districts[row][col] if self.districts else "residential"
        self.grid[row][col] = tile
        self.lot_lookup.pop((row, col), None)
        self.visuals[row][col] = TileVisual(
            tile=tile,
            asset_key=self._choose_asset_key(tile, (1, 1)),
            rotation=0,
            variant=0,
            height=1,
            footprint=(1, 1),
            anchor=(row, col),
            lot_id=0,
            district=district,
        )

    def road_width_violations(self):
        violations = []
        for r in range(ROWS - 1):
            for c in range(COLS - 1):
                cells = [(r, c), (r + 1, c), (r, c + 1), (r + 1, c + 1)]
                if all(self.grid[rr][cc] in ROAD_LIKE_TILES for rr, cc in cells):
                    violations.append((r, c))
        return violations

    def _remove_double_wide_road_blobs(self):
        # Asset-friendly invariant: no 2x2 area may be entirely road-like.
        for _pass in range(200):
            violations = self.road_width_violations()
            if not violations:
                return
            changed = False
            for r, c in violations:
                candidates = [(r, c), (r + 1, c), (r, c + 1), (r + 1, c + 1)]
                candidates.sort(key=lambda cell: self._road_neighbor_count(*cell), reverse=True)
                for rr, cc in candidates:
                    if self.grid[rr][cc] not in ROAD_LIKE_TILES:
                        continue
                    old_tile = self.grid[rr][cc]
                    self.grid[rr][cc] = self._district_default_building(rr, cc)
                    if self._road_network_is_connected():
                        self._set_filler_tile(rr, cc)
                        changed = True
                        break
                    self.grid[rr][cc] = old_tile
                if changed:
                    break
            if not changed:
                # Last-resort fallback: prefer visual correctness for 2.5D roads.
                rr, cc = violations[0]
                self._set_filler_tile(rr, cc)

    def _road_neighbor_count(self, row, col):
        count = 0
        for nr, nc in [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]:
            if self.is_inside(nr, nc) and self.grid[nr][nc] in ROAD_LIKE_TILES:
                count += 1
        return count

    def _road_network_is_connected(self):
        road_cells = [(r, c) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] in ROAD_LIKE_TILES]
        if not road_cells:
            return True
        start = road_cells[0]
        q = deque([start])
        seen = {start}
        while q:
            cur = q.popleft()
            for nr, nc in [(cur[0] - 1, cur[1]), (cur[0] + 1, cur[1]), (cur[0], cur[1] - 1), (cur[0], cur[1] + 1)]:
                if not self.is_inside(nr, nc) or (nr, nc) in seen:
                    continue
                if self.grid[nr][nc] in ROAD_LIKE_TILES:
                    seen.add((nr, nc))
                    q.append((nr, nc))
        return len(seen) == len(road_cells)

    def _choose_asset_key(self, tile, footprint):
        if self.asset_loader:
            return self.asset_loader.choose_asset_key(tile, self.rng, footprint=footprint)
        return tile

    def _district_default_building(self, row, col):
        district = self.districts[row][col] if self.districts else "residential"
        return self.rng.choice(DISTRICT_BUILDINGS.get(district, NORMAL_BUILDINGS))

    def _height_for_lot(self, tile, district, footprint):
        if tile == PARK:
            return 0
        low, high = HEIGHT_RANGES.get(district, (1, 2))
        area = footprint[0] * footprint[1]
        bonus = 1 if area >= 9 and district in ("downtown", "industrial") else 0
        return self.rng.randint(low, high) + bonus

    def _lot_has_access(self, lot):
        return bool(self._lot_access_options(lot))

    def _lot_access_options(self, lot, allowed_cells=None):
        out = []
        for cell in lot.cells:
            row, col = cell
            for nr, nc in [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]:
                if allowed_cells is not None and (nr, nc) not in allowed_cells:
                    continue
                if self.is_inside(nr, nc) and self.grid[nr][nc] in WALKABLE_TILES:
                    out.append((cell, (nr, nc)))
        return out

    def _safe_to_block(self, cell):
        old = self.grid[cell[0]][cell[1]]
        if old != ROAD:
            return False
        self.grid[cell[0]][cell[1]] = BLOCKED
        stations_connected = self._stations_still_connected()
        self.grid[cell[0]][cell[1]] = old
        return stations_connected

    def _stations_still_connected(self):
        if not self.stations:
            return True
        reachable = self._reachable_from(self.stations[0].start)
        return all(truck.start in reachable for truck in self.stations)

    def _largest_walkable_component(self, tile_filter=None):
        allowed = tile_filter or WALKABLE_TILES
        cells = {(r, c) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] in allowed}
        if not cells:
            return set()
        largest = set()
        remaining = set(cells)
        while remaining:
            start = next(iter(remaining))
            q = deque([start])
            seen = {start}
            remaining.discard(start)
            while q:
                cur = q.popleft()
                for nb in self.get_neighbors(*cur):
                    if nb in cells and nb not in seen:
                        seen.add(nb)
                        remaining.discard(nb)
                        q.append(nb)
            if len(seen) > len(largest):
                largest = seen
        return largest

    def _reachable_from(self, start):
        if not self.is_walkable(*start):
            return set()
        q = deque([start])
        seen = {start}
        while q:
            cur = q.popleft()
            for nb in self.get_neighbors(*cur):
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        return seen

    def _update_road_visuals(self):
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] in ROAD_LIKE_TILES:
                    self.visuals[r][c].rotation = self._road_rotation(r, c)

    def _road_rotation(self, row, col):
        up = self.is_walkable(row - 1, col)
        down = self.is_walkable(row + 1, col)
        left = self.is_walkable(row, col - 1)
        right = self.is_walkable(row, col + 1)
        if left and right and not (up or down):
            return 0
        if up and down and not (left or right):
            return 90
        if down and right:
            return 0
        if down and left:
            return 90
        if up and left:
            return 180
        if up and right:
            return 270
        return 0

    def _refresh_road_cells(self):
        self.road_cells = [(r, c) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] == ROAD]

    def _random_plain_road_cell(self):
        cells = [(r, c) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] == ROAD]
        return self.rng.choice(cells) if cells else None

    def _nearest_road(self, cell):
        roads = [(r, c) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] == ROAD]
        if not roads:
            return None
        return min(roads, key=lambda p: abs(p[0] - cell[0]) + abs(p[1] - cell[1]))

    def _clamp_cell(self, cell):
        return max(0, min(ROWS - 1, cell[0])), max(0, min(COLS - 1, cell[1]))

    def get_building_cells(self, adjacent_road=False):
        out = []
        for lot in self.lots:
            if lot.tile not in BUILDING_TILES:
                continue
            if adjacent_road:
                out.extend(cell for cell, _target in self._lot_access_options(lot))
            else:
                out.extend(lot.cells)
        return out

    def get_access_road(self, building_cell, allowed_cells=None):
        lot = self.lot_lookup.get(building_cell)
        if lot:
            options = [
                target for cell, target in self._lot_access_options(lot, allowed_cells=allowed_cells)
                if cell == building_cell
            ]
            if options:
                return self.rng.choice(options)
        row, col = building_cell
        candidates = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
        valid = []
        for r, c in candidates:
            if allowed_cells is not None and (r, c) not in allowed_cells:
                continue
            if self.is_inside(r, c) and self.grid[r][c] in WALKABLE_TILES:
                valid.append((r, c))
        return self.rng.choice(valid) if valid else None

    def get_selected_fire(self):
        if not self.fires:
            return None
        self.selected_fire_index %= len(self.fires)
        return self.fires[self.selected_fire_index]

    def next_fire(self):
        if self.fires:
            self.selected_fire_index = (self.selected_fire_index + 1) % len(self.fires)

    def previous_fire(self):
        if self.fires:
            self.selected_fire_index = (self.selected_fire_index - 1) % len(self.fires)

    def is_inside(self, row, col):
        return 0 <= row < ROWS and 0 <= col < COLS

    def is_inside_inner(self, row, col):
        return 1 <= row < ROWS - 1 and 1 <= col < COLS - 1

    def is_walkable(self, row, col):
        return self.is_inside(row, col) and self.grid[row][col] in WALKABLE_TILES

    def get_neighbors(self, row, col, blocked_cells=None):
        blocked_cells = blocked_cells or set()
        out = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if (nr, nc) in blocked_cells:
                continue
            if self.is_walkable(nr, nc):
                out.append((nr, nc))
        return out

    def get_tile_cost(self, row, col, risky_penalty=0):
        tile = self.grid[row][col]
        cost = TILE_COST.get(tile, 1)
        if tile == RISKY:
            cost += risky_penalty
        return cost

    def draw(self, screen, selected_paths=None, extinguished_fires=None, draw_fire_effects=True):
        if pygame is None:
            raise RuntimeError("pygame is required to draw the map. Install with: python -m pip install pygame")
        for r in range(ROWS):
            for c in range(COLS):
                self.draw_base_tile(screen, r, c)
        self.draw_lots(screen)
        self.draw_road_symbols(screen)
        if draw_fire_effects:
            self.draw_fire_labels(screen, extinguished_fires)
            self.draw_selected_fire(screen)

    def draw_base_tile(self, screen, row, col):
        tile = self.grid[row][col]
        visual = self.visuals[row][col]
        x, y = col * TILE_SIZE, row * TILE_SIZE
        if tile in ROAD_LIKE_TILES:
            self._draw_road_tile(screen, row, col, tile, x, y)
            return
        color = TILE_COLORS.get(tile, (100, 100, 100))
        if visual.lot_id:
            color = self._lot_base_color(visual)
        pygame.draw.rect(screen, color, (x, y, TILE_SIZE, TILE_SIZE))
        # Road tiles intentionally avoid per-cell grid borders so streets read as continuous corridors.

    def _draw_road_tile(self, screen, row, col, tile, x, y):
        if tile == BLOCKED:
            pygame.draw.rect(screen, (18, 18, 22), (x, y, TILE_SIZE, TILE_SIZE))
            pygame.draw.rect(screen, (42, 42, 48), (x + 3, y + 3, TILE_SIZE - 6, TILE_SIZE - 6), border_radius=4)
            pygame.draw.rect(screen, GRID_COLOR, (x, y, TILE_SIZE, TILE_SIZE), 1)
            return

        up = self.is_walkable(row - 1, col)
        down = self.is_walkable(row + 1, col)
        left = self.is_walkable(row, col - 1)
        right = self.is_walkable(row, col + 1)
        asphalt = (76, 76, 82)
        asphalt_light = (90, 90, 96)
        curb = (42, 42, 48)
        lane_color = (205, 196, 118)

        pygame.draw.rect(screen, asphalt, (x, y, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(screen, asphalt_light, (x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4), 1)

        # Curbs only appear where road touches buildings/blocks. This keeps the road network cleaner.
        if not up:
            pygame.draw.line(screen, curb, (x, y), (x + TILE_SIZE, y), 2)
        if not down:
            pygame.draw.line(screen, curb, (x, y + TILE_SIZE - 1), (x + TILE_SIZE, y + TILE_SIZE - 1), 2)
        if not left:
            pygame.draw.line(screen, curb, (x, y), (x, y + TILE_SIZE), 2)
        if not right:
            pygame.draw.line(screen, curb, (x + TILE_SIZE - 1, y), (x + TILE_SIZE - 1, y + TILE_SIZE), 2)

        horizontal = left or right
        vertical = up or down
        intersection = horizontal and vertical
        if horizontal and not intersection and row % 2 == 0:
            pygame.draw.line(screen, lane_color, (x + 8, y + TILE_SIZE // 2), (x + 24, y + TILE_SIZE // 2), 1)
        if vertical and not intersection and col % 2 == 0:
            pygame.draw.line(screen, lane_color, (x + TILE_SIZE // 2, y + 8), (x + TILE_SIZE // 2, y + 24), 1)
        if intersection:
            pygame.draw.circle(screen, (96, 96, 102), (x + TILE_SIZE // 2, y + TILE_SIZE // 2), 2)

        if tile == TRAFFIC:
            pygame.draw.rect(screen, (210, 145, 42), (x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10), 1, border_radius=5)
        elif tile == RISKY:
            pygame.draw.rect(screen, (150, 100, 220), (x + 9, y + 9, TILE_SIZE - 18, TILE_SIZE - 18), 2, border_radius=4)
        elif tile == STATION:
            pygame.draw.rect(screen, TILE_COLORS.get(tile), (x + 7, y + 7, TILE_SIZE - 14, TILE_SIZE - 14), 2, border_radius=4)
        elif tile == HYDRANT:
            pygame.draw.rect(screen, (82, 82, 88), (x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8), 1, border_radius=4)

        pygame.draw.rect(screen, GRID_COLOR, (x, y, TILE_SIZE, TILE_SIZE), 1)

    def draw_lots(self, screen):
        for lot in sorted(self.lots, key=lambda item: (item.anchor[0] + item.footprint[1], item.anchor[1])):
            self.draw_lot(screen, lot)

    def draw_lot(self, screen, lot):
        row, col = lot.anchor
        width, height = lot.footprint
        x, y = col * TILE_SIZE, row * TILE_SIZE
        rect = pygame.Rect(x + 2, y + 2, width * TILE_SIZE - 4, height * TILE_SIZE - 4)
        image = self.asset_loader.get_for_footprint(lot.asset_key, lot.footprint) if SHOW_LOT_MODELS and self.asset_loader else None
        if image:
            screen.blit(image, (x, y))
            pygame.draw.rect(screen, (42, 42, 50), (x, y, width * TILE_SIZE, height * TILE_SIZE), 1)
            return
        self._draw_placeholder_lot(screen, lot, rect)

    def _draw_placeholder_lot(self, screen, lot, rect):
        base = TILE_COLORS.get(lot.tile, (80, 80, 96))
        if lot.tile == PARK:
            pygame.draw.rect(screen, base, rect, border_radius=5)
            rng = random.Random(lot.id * 7919)
            for _ in range(max(2, lot.footprint[0] * lot.footprint[1])):
                cx = rng.randint(rect.left + 6, rect.right - 6)
                cy = rng.randint(rect.top + 6, rect.bottom - 6)
                pygame.draw.circle(screen, (70, 170, 90), (cx, cy), 4)
            pygame.draw.rect(screen, (38, 90, 50), rect, 2, border_radius=5)
            return

        wall = tuple(min(255, max(0, value + lot.height * 5)) for value in base)
        roof = tuple(max(0, value - 20) for value in wall)
        pygame.draw.rect(screen, wall, rect, border_radius=4)
        roof_rect = rect.inflate(-8, -8)
        pygame.draw.rect(screen, roof, roof_rect, border_radius=3)
        if lot.district == "industrial" or lot.tile == GAS_STATION:
            chimney = pygame.Rect(rect.right - 13, rect.top + 5, 6, min(28, rect.height - 8))
            pygame.draw.rect(screen, (210, 90, 55), chimney, border_radius=2)
        if lot.footprint[0] >= 2 and lot.footprint[1] >= 2:
            for wx in range(rect.left + 10, rect.right - 8, 18):
                pygame.draw.rect(screen, (95, 130, 165), (wx, rect.top + 10, 8, 5), border_radius=1)
        pygame.draw.rect(screen, (28, 28, 36), rect, 2, border_radius=4)
        if lot.tile in (HOSPITAL, GAS_STATION):
            symbol = "H" if lot.tile == HOSPITAL else "G"
            font = pygame.font.SysFont("Arial", 18, bold=True)
            surf = font.render(symbol, True, WHITE)
            screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_road_symbols(self, screen):
        for r in range(ROWS):
            for c in range(COLS):
                tile = self.grid[r][c]
                if tile in ROAD_LIKE_TILES and tile != ROAD:
                    self.draw_symbol(screen, tile, c * TILE_SIZE, r * TILE_SIZE, r, c)

    def draw_symbol(self, screen, tile, x, y, row=None, col=None):
        if tile == HYDRANT:
            self.draw_hydrant_marker(screen, x, y, row, col)
            return
        if tile == TRAFFIC:
            self.draw_traffic_jam_marker(screen, x, y, row, col)
            return
        symbols = {
            STATION: "S",
            BLOCKED: "X",
            RISKY: "?",
            HOSPITAL: "H",
            GAS_STATION: "G",
            PARK: "P",
        }
        symbol = symbols.get(tile, "")
        if not symbol:
            return
        font = pygame.font.SysFont("Arial", 14, bold=True)
        text_color = BLACK if tile in [TRAFFIC, HYDRANT, RISKY] else WHITE
        surf = font.render(symbol, True, text_color)
        screen.blit(surf, surf.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2)))

    def draw_hydrant_marker(self, screen, x, y, row=None, col=None):
        cx = x + TILE_SIZE // 2
        cy = y + TILE_SIZE // 2
        if row is not None and col is not None:
            if not self.is_walkable(row, col - 1):
                cx = x + 8
            elif not self.is_walkable(row, col + 1):
                cx = x + TILE_SIZE - 8
            if not self.is_walkable(row - 1, col):
                cy = y + 8
            elif not self.is_walkable(row + 1, col):
                cy = y + TILE_SIZE - 8

        base = pygame.Rect(cx - 6, cy + 7, 12, 4)
        body = pygame.Rect(cx - 5, cy - 5, 10, 14)
        cap = pygame.Rect(cx - 4, cy - 10, 8, 6)
        pygame.draw.ellipse(screen, (20, 20, 24), base)
        pygame.draw.rect(screen, (180, 24, 28), body, border_radius=3)
        pygame.draw.rect(screen, (225, 38, 44), cap, border_radius=3)
        pygame.draw.circle(screen, (224, 42, 45), (cx, cy - 7), 5)
        pygame.draw.rect(screen, (124, 16, 22), (cx - 8, cy - 1, 16, 5), border_radius=2)
        pygame.draw.circle(screen, (245, 225, 120), (cx - 7, cy + 1), 2)
        pygame.draw.circle(screen, (245, 225, 120), (cx + 7, cy + 1), 2)
        pygame.draw.line(screen, (255, 122, 118), (cx - 3, cy - 4), (cx - 3, cy + 6), 2)
        pygame.draw.rect(screen, (72, 72, 78), (cx - 7, cy + 10, 14, 2), border_radius=1)

    def draw_traffic_jam_marker(self, screen, x, y, row=None, col=None):
        orientation = self.road_orientation(row, col)
        ticks = pygame.time.get_ticks()
        blink_on = (ticks // 360) % 2 == 0
        if orientation == "vertical":
            cars = [
                (x + 7, y + 3, 8, 13, (226, 52, 54), "down"),
                (x + 17, y + 10, 8, 13, (70, 148, 232), "up"),
                (x + 8, y + 19, 8, 10, (238, 202, 70), "down"),
            ]
        elif orientation == "intersection":
            cars = [
                (x + 3, y + 9, 13, 8, (226, 52, 54), "right"),
                (x + 16, y + 17, 13, 8, (70, 148, 232), "left"),
                (x + 11, y + 2, 8, 13, (238, 202, 70), "down"),
                (x + 20, y + 7, 8, 12, (92, 210, 150), "up"),
            ]
        else:
            cars = [
                (x + 2, y + 8, 13, 8, (226, 52, 54), "right"),
                (x + 12, y + 17, 13, 8, (70, 148, 232), "left"),
                (x + 20, y + 7, 10, 8, (238, 202, 70), "right"),
            ]
        for car in cars:
            self.draw_small_car(screen, *car, brake=blink_on)

    def road_orientation(self, row, col):
        if row is None or col is None:
            return "horizontal"
        horizontal = self.is_walkable(row, col - 1) or self.is_walkable(row, col + 1)
        vertical = self.is_walkable(row - 1, col) or self.is_walkable(row + 1, col)
        if horizontal and vertical:
            return "intersection"
        if vertical:
            return "vertical"
        return "horizontal"

    def draw_small_car(self, screen, x, y, width, height, color, direction, brake=False):
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (18, 18, 22), rect.move(1, 1), border_radius=3)
        pygame.draw.rect(screen, color, rect, border_radius=3)
        pygame.draw.rect(screen, (245, 245, 248), rect, 1, border_radius=3)
        if width >= height:
            windshield = pygame.Rect(rect.x + 4, rect.y + 2, max(3, rect.width - 8), 3)
            pygame.draw.rect(screen, (170, 220, 245), windshield, border_radius=1)
            if direction == "left":
                front_x = rect.left
                rear_x = rect.right - 2
            else:
                front_x = rect.right - 2
                rear_x = rect.left
            pygame.draw.circle(screen, (255, 245, 145), (front_x, rect.centery - 2), 1)
            pygame.draw.circle(screen, (255, 245, 145), (front_x, rect.centery + 2), 1)
            if brake:
                pygame.draw.circle(screen, (255, 54, 54), (rear_x, rect.centery - 2), 2)
                pygame.draw.circle(screen, (255, 54, 54), (rear_x, rect.centery + 2), 2)
        else:
            windshield = pygame.Rect(rect.x + 2, rect.y + 4, 3, max(3, rect.height - 8))
            pygame.draw.rect(screen, (170, 220, 245), windshield, border_radius=1)
            if direction == "up":
                front_y = rect.top
                rear_y = rect.bottom - 2
            else:
                front_y = rect.bottom - 2
                rear_y = rect.top
            pygame.draw.circle(screen, (255, 245, 145), (rect.centerx - 2, front_y), 1)
            pygame.draw.circle(screen, (255, 245, 145), (rect.centerx + 2, front_y), 1)
            if brake:
                pygame.draw.circle(screen, (255, 54, 54), (rect.centerx - 2, rear_y), 2)
                pygame.draw.circle(screen, (255, 54, 54), (rect.centerx + 2, rear_y), 2)

    def draw_fire_labels(self, screen, extinguished_fires=None):
        font = pygame.font.SysFont("Arial", 12, bold=True)
        fire_image = self.asset_loader.get(FIRE) if self.asset_loader else None
        extinguished_fires = extinguished_fires or set()
        ticks = pygame.time.get_ticks()
        for index, fire in enumerate(self.fires):
            r, c = fire.cell
            x, y = c * TILE_SIZE, r * TILE_SIZE
            if fire.id in extinguished_fires:
                self.draw_extinguished_fire_marker(screen, x, y, ticks, index)
            else:
                self.draw_active_fire_effect(screen, x, y, fire, fire_image, ticks, index)
            surf = font.render(fire.id, True, WHITE)
            bg = surf.get_rect(topleft=(x + 2, y + 2)).inflate(4, 2)
            pygame.draw.rect(screen, (10, 10, 14), bg, border_radius=3)
            screen.blit(surf, (x + 2, y + 2))

    def draw_active_fire_effect(self, screen, x, y, fire, fire_image, ticks, index):
        cx = x + TILE_SIZE // 2
        cy = y + TILE_SIZE // 2
        phase = ticks * 0.011 + index * 1.7 + fire.severity * 0.55
        pulse = 0.5 + 0.5 * math.sin(phase)
        flicker = 0.5 + 0.5 * math.sin(phase * 1.9 + 0.8)
        scale = 1.0 + fire.severity * 0.08 + pulse * 0.12

        glow = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2), pygame.SRCALPHA)
        glow_center = (TILE_SIZE, TILE_SIZE)
        pygame.draw.circle(glow, (255, 70, 24, int(58 + 42 * pulse)), glow_center, int(21 * scale))
        pygame.draw.circle(glow, (255, 165, 46, int(45 + 35 * flicker)), glow_center, int(15 * scale))
        screen.blit(glow, (x - TILE_SIZE // 2, y - TILE_SIZE // 2))

        if fire_image:
            size = int(TILE_SIZE * (0.9 + fire.severity * 0.05 + pulse * 0.08))
            image = pygame.transform.smoothscale(fire_image, (size, size))
            image.set_alpha(int(220 + 35 * flicker))
            screen.blit(image, image.get_rect(center=(cx, cy + 1)))

        flame_height = int(17 + fire.severity * 3 + pulse * 4)
        flame_width = int(10 + fire.severity * 2 + flicker * 3)
        outer = [
            (cx, cy - flame_height),
            (cx + flame_width, cy + 7),
            (cx + 3, cy + 13),
            (cx - flame_width, cy + 7),
        ]
        inner = [
            (cx + int(math.sin(phase) * 2), cy - flame_height // 2),
            (cx + flame_width // 2, cy + 7),
            (cx, cy + 11),
            (cx - flame_width // 2, cy + 7),
        ]
        core = [
            (cx - 1, cy - flame_height // 4),
            (cx + flame_width // 3, cy + 6),
            (cx - flame_width // 3, cy + 6),
        ]
        pygame.draw.polygon(screen, (220, 30, 24), outer)
        pygame.draw.polygon(screen, (255, 128, 28), inner)
        pygame.draw.polygon(screen, (255, 232, 92), core)

        ember_y = y + TILE_SIZE - 6
        for ember in range(3):
            offset = int(math.sin(phase * (1.4 + ember * 0.3) + ember) * 7)
            alpha = int(110 + 100 * ((pulse + ember * 0.23) % 1))
            color = (255, 95 + ember * 35, 35, alpha)
            ember_surface = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(ember_surface, color, (4, 4), 2)
            screen.blit(ember_surface, (cx + offset - 4, ember_y - ember * 5))

    def draw_extinguished_fire_marker(self, screen, x, y, ticks, index):
        cx = x + TILE_SIZE // 2
        cy = y + TILE_SIZE // 2
        phase = ticks * 0.006 + index * 1.3
        pulse = 0.5 + 0.5 * math.sin(phase)

        marker = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2), pygame.SRCALPHA)
        center = (TILE_SIZE, TILE_SIZE)
        pygame.draw.circle(marker, (44, 220, 142, int(70 + 35 * pulse)), center, 19)
        pygame.draw.circle(marker, (84, 238, 176, 190), center, 12)
        pygame.draw.circle(marker, (20, 78, 66, 230), center, 12, 2)
        pygame.draw.arc(marker, (160, 235, 255, 170), (18, 13, 28, 24), 0.2, 2.9, 2)
        pygame.draw.arc(marker, (160, 235, 255, 120), (14, 19, 36, 25), 3.3, 5.9, 2)
        screen.blit(marker, (x - TILE_SIZE // 2, y - TILE_SIZE // 2))

        check_points = [(cx - 8, cy), (cx - 3, cy + 6), (cx + 9, cy - 7)]
        pygame.draw.lines(screen, (220, 255, 238), False, check_points, 4)
        pygame.draw.lines(screen, (16, 110, 72), False, check_points, 2)

        for puff in range(2):
            drift = int(math.sin(phase * 1.5 + puff) * 3)
            puff_y = cy - 14 - puff * 7 - int(pulse * 2)
            pygame.draw.circle(screen, (150, 230, 235), (cx - 5 + puff * 10 + drift, puff_y), 3 + puff)

    def draw_selected_fire(self, screen):
        fire = self.get_selected_fire()
        if not fire:
            return
        r, c = fire.cell
        pygame.draw.rect(screen, YELLOW, (c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE), 3)
        tr, tc = fire.target
        pygame.draw.rect(screen, (80, 240, 130), (tc * TILE_SIZE + 4, tr * TILE_SIZE + 4, TILE_SIZE - 8, TILE_SIZE - 8), 2)

    def _lot_base_color(self, visual):
        color = TILE_COLORS.get(visual.tile, (72, 72, 86))
        if visual.district == "downtown":
            return tuple(min(255, value + 10) for value in color)
        if visual.district == "industrial":
            return tuple(max(0, value - 8) for value in color)
        if visual.district == "greenbelt":
            return tuple(max(0, min(255, value + 8 if i == 1 else value - 4)) for i, value in enumerate(color))
        return color
