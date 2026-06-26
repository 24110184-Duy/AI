# utils/helpers.py

from config import TILE_SIZE


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(parent, start, goal):
    if goal != start and goal not in parent:
        return []
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path if path and path[0] == start else []


def path_cost(city_map, path, risky_penalty=0):
    if not path:
        return 0
    total = 0
    for row, col in path[1:]:
        total += city_map.get_tile_cost(row, col, risky_penalty=risky_penalty)
    return total


def count_tile_on_path(city_map, path, tile_name):
    return sum(1 for row, col in path if city_map.grid[row][col] == tile_name)


def cell_to_center(cell):
    row, col = cell
    return col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2


def clamp(value, low, high):
    return max(low, min(high, value))
