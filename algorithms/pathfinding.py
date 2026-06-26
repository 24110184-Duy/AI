# algorithms/pathfinding.py

from collections import deque
import heapq
import time

from config import RISKY, TRAFFIC
from utils.helpers import count_tile_on_path, manhattan, path_cost, reconstruct_path
from core.models import SearchResult


def _neighbors(city_map, cell, blocked_cells=None):
    row, col = cell
    return city_map.get_neighbors(row, col, blocked_cells=blocked_cells)


def _format_cost(value):
    return int(value) if float(value).is_integer() else round(value, 2)


def _make_result(name, started_at, path, visited, cost, success, logs, message, metrics=None):
    runtime_ms = (time.perf_counter() - started_at) * 1000
    metrics = dict(metrics or {})
    metrics.setdefault("path_length", max(0, len(path) - 1))
    metrics.setdefault("visited", len(visited))
    metrics.setdefault("cost", cost)
    metrics.setdefault("runtime_ms", runtime_ms)
    if success:
        logs.append(
            f"Thống kê: chi phí={_format_cost(cost)}, độ dài={max(0, len(path) - 1)}, "
            f"đã thăm={len(visited)}, thời gian={runtime_ms:.2f}ms"
        )
    else:
        logs.append(f"Thống kê: không có đường, đã thăm={len(visited)}, thời gian={runtime_ms:.2f}ms")
    return SearchResult(
        name,
        path,
        visited,
        cost,
        success,
        logs,
        message,
        runtime_ms=runtime_ms,
        metrics=metrics,
    )


def bfs(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    q = deque([start])
    parent = {start: None}
    visited = []
    logs = [
        "BFS: hàng đợi mở rộng theo từng lớp.",
        "Ưu tiên tìm kiếm: ít ô nhất, không tính chi phí đường.",
    ]
    max_frontier = 1
    while q:
        cur = q.popleft()
        visited.append(cur)
        if cur == goal:
            path = reconstruct_path(parent, start, goal)
            cost = path_cost(city_map, path, risky_penalty)
            logs.append(f"Đã tới đích sau {len(visited)} lần mở rộng.")
            if count_tile_on_path(city_map, path, TRAFFIC):
                logs.append("Tuyến BFS đi qua kẹt xe vì BFS bỏ qua trọng số.")
            metrics = {"max_frontier": max_frontier}
            return _make_result("BFS", started_at, path, visited, cost, True, logs, "Tuyến ít ô nhất.", metrics)
        for nb in _neighbors(city_map, cur, blocked_cells):
            if nb not in parent:
                parent[nb] = cur
                q.append(nb)
        max_frontier = max(max_frontier, len(q))
    return _make_result("BFS", started_at, [], visited, 0, False, logs, "Không tìm thấy đường.")


def dfs(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    stack = [start]
    parent = {start: None}
    seen = set()
    visited = []
    logs = [
        "DFS: ngăn xếp đi sâu trước.",
        "Ưu tiên tìm kiếm: độ sâu trước chất lượng.",
    ]
    max_frontier = 1
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        visited.append(cur)
        if cur == goal:
            path = reconstruct_path(parent, start, goal)
            cost = path_cost(city_map, path, risky_penalty)
            logs.append("Đã tới đích, nhưng DFS không đảm bảo tối ưu.")
            metrics = {"max_frontier": max_frontier}
            return _make_result("DFS", started_at, path, visited, cost, True, logs, "Tuyến đi sâu, không đảm bảo tối ưu.", metrics)
        for nb in reversed(_neighbors(city_map, cur, blocked_cells)):
            if nb not in seen and nb not in parent:
                parent[nb] = cur
                stack.append(nb)
        max_frontier = max(max_frontier, len(stack))
    return _make_result("DFS", started_at, [], visited, 0, False, logs, "Không tìm thấy đường.")


def ucs(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    pq = [(0, start)]
    parent = {start: None}
    best = {start: 0}
    closed = set()
    visited = []
    logs = [
        "UCS: ưu tiên = tổng chi phí g(n).",
        "Kẹt xe có chi phí cao nên UCS thường tránh nó.",
    ]
    max_frontier = 1
    sample = []
    while pq:
        cost, cur = heapq.heappop(pq)
        if cur in closed:
            continue
        closed.add(cur)
        visited.append(cur)
        if len(sample) < 4:
            sample.append(f"UCS mở rộng {cur}: g={_format_cost(cost)}")
        if cur == goal:
            path = reconstruct_path(parent, start, goal)
            logs.extend(sample)
            logs.append(f"Tìm được đường rẻ nhất với g={_format_cost(cost)}.")
            traffic_count = count_tile_on_path(city_map, path, TRAFFIC)
            if traffic_count:
                logs.append(f"Dùng {traffic_count} ô kẹt xe; không có đường vòng rẻ hơn.")
            metrics = {"goal_g": cost, "max_frontier": max_frontier}
            return _make_result("UCS", started_at, path, visited, path_cost(city_map, path, risky_penalty), True, logs, "Tuyến rẻ nhất có tính kẹt xe.", metrics)
        for nb in _neighbors(city_map, cur, blocked_cells):
            new_cost = cost + city_map.get_tile_cost(*nb, risky_penalty=risky_penalty)
            if nb not in best or new_cost < best[nb]:
                best[nb] = new_cost
                parent[nb] = cur
                heapq.heappush(pq, (new_cost, nb))
        max_frontier = max(max_frontier, len(pq))
    return _make_result("UCS", started_at, [], visited, 0, False, logs, "Không tìm thấy đường.")


def astar(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    pq = [(manhattan(start, goal), 0, start)]
    parent = {start: None}
    best = {start: 0}
    closed = set()
    visited = []
    logs = [
        "A*: ưu tiên f(n)=g(n)+h(n), h=Manhattan.",
        "g(n)=chi phí đã đi; h(n)=ước lượng ô còn lại.",
    ]
    max_frontier = 1
    sample = []
    while pq:
        _priority, cost, cur = heapq.heappop(pq)
        if cur in closed:
            continue
        closed.add(cur)
        visited.append(cur)
        if len(sample) < 4:
            h = manhattan(cur, goal)
            sample.append(f"A* mở rộng {cur}: g={_format_cost(cost)}, h={h}, f={_format_cost(cost + h)}")
        if cur == goal:
            path = reconstruct_path(parent, start, goal)
            logs.extend(sample)
            logs.append(f"Đã tới đích: g={_format_cost(cost)}, h=0, f={_format_cost(cost)}.")
            metrics = {"goal_g": cost, "goal_h": 0, "goal_f": cost, "max_frontier": max_frontier}
            return _make_result("A*", started_at, path, visited, path_cost(city_map, path, risky_penalty), True, logs, "Tuyến khẩn cấp cân bằng và nhanh.", metrics)
        for nb in _neighbors(city_map, cur, blocked_cells):
            new_cost = cost + city_map.get_tile_cost(*nb, risky_penalty=risky_penalty)
            if nb not in best or new_cost < best[nb]:
                best[nb] = new_cost
                parent[nb] = cur
                h = manhattan(nb, goal)
                heapq.heappush(pq, (new_cost + h, new_cost, nb))
        max_frontier = max(max_frontier, len(pq))
    return _make_result("A*", started_at, [], visited, 0, False, logs, "Không tìm thấy đường.")


def greedy(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    pq = [(manhattan(start, goal), start)]
    parent = {start: None}
    closed = set()
    visited = []
    logs = [
        "Tham lam: chỉ ưu tiên h(n).",
        "Tìm nhanh nhưng bỏ qua chi phí kẹt xe/rủi ro khi chọn.",
    ]
    max_frontier = 1
    sample = []
    while pq:
        h_value, cur = heapq.heappop(pq)
        if cur in closed:
            continue
        closed.add(cur)
        visited.append(cur)
        if len(sample) < 4:
            sample.append(f"Tham lam mở rộng {cur}: h={h_value}")
        if cur == goal:
            path = reconstruct_path(parent, start, goal)
            cost = path_cost(city_map, path, risky_penalty)
            logs.extend(sample)
            logs.append("Tới đích nhanh, nhưng tuyến có thể tốn kém.")
            if count_tile_on_path(city_map, path, TRAFFIC) or count_tile_on_path(city_map, path, RISKY):
                logs.append("Tuyến có ô chi phí cao vì g(n) bị bỏ qua.")
            metrics = {"goal_h": 0, "max_frontier": max_frontier}
            return _make_result("Greedy", started_at, path, visited, cost, True, logs, "Tuyến tìm nhanh theo ước lượng.", metrics)
        for nb in _neighbors(city_map, cur, blocked_cells):
            if nb not in parent:
                parent[nb] = cur
                heapq.heappush(pq, (manhattan(nb, goal), nb))
        max_frontier = max(max_frontier, len(pq))
    return _make_result("Greedy", started_at, [], visited, 0, False, logs, "Không tìm thấy đường.")


def _dls(city_map, cur, goal, limit, parent, visited, seen, blocked_cells=None):
    visited.append(cur)
    if cur == goal:
        return True
    if limit == 0:
        return False
    for nb in _neighbors(city_map, cur, blocked_cells):
        if nb not in seen:
            seen.add(nb)
            parent[nb] = cur
            if _dls(city_map, nb, goal, limit - 1, parent, visited, seen, blocked_cells):
                return True
            seen.remove(nb)
    return False


def ids(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    logs = [
        "IDS: DFS giới hạn độ sâu và tăng dần giới hạn.",
        "Cho thấy độ sâu tăng dần, vẫn giữ bộ nhớ thấp.",
    ]
    all_visited = []
    max_depth = 80
    depth_samples = []
    for depth in range(max_depth + 1):
        parent = {start: None}
        visited = []
        found = _dls(city_map, start, goal, depth, parent, visited, {start}, blocked_cells)
        all_visited.extend(visited)
        if depth in [0, 1, 2, 4, 8, 16] and len(depth_samples) < 5:
            depth_samples.append(f"Độ sâu {depth}: đã thăm {len(visited)} nút")
        if found:
            path = reconstruct_path(parent, start, goal)
            cost = path_cost(city_map, path, risky_penalty)
            logs.extend(depth_samples)
            logs.append(f"Tìm thấy ở giới hạn độ sâu {depth}.")
            metrics = {"depth_limit": depth}
            return _make_result("IDS", started_at, path, all_visited, cost, True, logs, "Tuyến sâu dần.", metrics)
    logs.extend(depth_samples)
    return _make_result("IDS", started_at, [], all_visited, 0, False, logs, "Không có đường trong giới hạn độ sâu.")


PATH_ALGORITHM_FUNCS = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "A*": astar,
    "Greedy": greedy,
    "IDS": ids,
}
