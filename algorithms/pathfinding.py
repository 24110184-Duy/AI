# algorithms/pathfinding.py

from collections import deque
import heapq
import math
import random
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


def ida_star(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    logs = [
        "IDA*: lap A* theo nguong f(n)=g(n)+h(n).",
        "Moi vong duyet DFS va cat nhanh khi f(n) vuot nguong hien tai.",
    ]
    threshold = manhattan(start, goal)
    all_visited = []
    threshold_samples = []
    max_frontier = 1

    def bounded_search(cur, goal_cost, bound, path, in_path, best_seen):
        nonlocal max_frontier
        f_score = goal_cost + manhattan(cur, goal)
        if f_score > bound:
            return f_score
        if goal_cost >= best_seen.get(cur, float("inf")):
            return float("inf")
        best_seen[cur] = goal_cost
        all_visited.append(cur)
        if cur == goal:
            return "FOUND"
        minimum_cutoff = float("inf")
        neighbors = []
        for nb in _neighbors(city_map, cur, blocked_cells):
            if nb in in_path:
                continue
            step_cost = city_map.get_tile_cost(*nb, risky_penalty=risky_penalty)
            next_cost = goal_cost + step_cost
            neighbors.append((next_cost + manhattan(nb, goal), next_cost, nb))
        neighbors.sort()
        max_frontier = max(max_frontier, len(neighbors))
        for _priority, next_cost, nb in neighbors:
            path.append(nb)
            in_path.add(nb)
            result = bounded_search(nb, next_cost, bound, path, in_path, best_seen)
            if result == "FOUND":
                return result
            if result < minimum_cutoff:
                minimum_cutoff = result
            in_path.remove(nb)
            path.pop()
        return minimum_cutoff

    path = [start]
    max_iterations = 80
    for iteration in range(max_iterations):
        path = [start]
        before = len(all_visited)
        result = bounded_search(start, 0, threshold, path, {start}, {})
        expanded = len(all_visited) - before
        if len(threshold_samples) < 6:
            threshold_samples.append(f"Vong {iteration + 1}: nguong f={_format_cost(threshold)}, mo rong {expanded} nut")
        if result == "FOUND":
            cost = path_cost(city_map, path, risky_penalty)
            logs.extend(threshold_samples)
            logs.append(f"Tim thay khi nguong f dat {_format_cost(threshold)}.")
            metrics = {"final_threshold": threshold, "iterations": iteration + 1, "max_frontier": max_frontier}
            return _make_result("IDA*", started_at, path[:], all_visited, cost, True, logs, "A* lap sau dan theo f(n).", metrics)
        if result == float("inf"):
            logs.extend(threshold_samples)
            return _make_result("IDA*", started_at, [], all_visited, 0, False, logs, "Khong co nguong f nao toi dich.")
        threshold = result
    logs.extend(threshold_samples)
    return _make_result("IDA*", started_at, [], all_visited, 0, False, logs, "Dung do qua nhieu vong tang nguong f.")


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


def _search_limit(city_map, multiplier=2):
    rows = len(city_map.grid)
    cols = len(city_map.grid[0]) if rows else 0
    return max(80, rows * cols * multiplier)


def _stable_rng(name, start, goal):
    seed = (
        sum(ord(ch) for ch in name) * 1009
        + start[0] * 917
        + start[1] * 613
        + goal[0] * 389
        + goal[1] * 211
    )
    return random.Random(seed)


def _local_path_score(city_map, path, goal, risky_penalty=0, distance_weight=3.0):
    if not path:
        return float("inf")
    return (
        path_cost(city_map, path, risky_penalty)
        + manhattan(path[-1], goal) * distance_weight
        + max(0, len(path) - 1) * 0.15
    )


def random_restart_hill_climbing_route(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    rng = _stable_rng("Random Restart Hill Climbing", start, goal)
    logs = [
        "Random Restart Hill Climbing route: restart nhieu lan va leo theo o lan can tot hon.",
        "Khong goi A*: diem = chi phi duong hien tai + khoang cach Manhattan toi dich.",
    ]
    visited = [start]
    best_partial = [start]
    best_partial_score = _local_path_score(city_map, best_partial, goal, risky_penalty)
    max_steps = _search_limit(city_map, 2)
    restart_count = 42

    for restart in range(restart_count):
        path = [start]
        seen = {start}
        sideways_left = 20 + restart % 9
        backtrack_left = 42
        noise = 0.75 + restart * 0.08
        current_score = _local_path_score(city_map, path, goal, risky_penalty)

        for _step in range(max_steps):
            cur = path[-1]
            if cur == goal:
                cost = path_cost(city_map, path, risky_penalty)
                logs.append(f"Restart {restart + 1}: toi dich voi chi phi {_format_cost(cost)}.")
                metrics = {"restarts": restart + 1, "best_score": current_score}
                return _make_result(
                    "Random Restart Hill Climbing",
                    started_at,
                    path,
                    visited,
                    cost,
                    True,
                    logs,
                    "Leo doi co restart da tim thay duong.",
                    metrics,
                )

            options = []
            for nb in _neighbors(city_map, cur, blocked_cells):
                if nb in seen:
                    continue
                next_path = path + [nb]
                score = _local_path_score(city_map, next_path, goal, risky_penalty)
                score += rng.random() * noise
                options.append((score, nb, next_path))
            if not options:
                if len(path) > 1 and backtrack_left > 0:
                    seen.remove(path.pop())
                    current_score = _local_path_score(city_map, path, goal, risky_penalty)
                    backtrack_left -= 1
                    continue
                break

            options.sort(key=lambda item: item[0])
            top_count = min(len(options), 1 + restart % 4)
            next_score, nb, next_path = options[0] if restart % 3 == 0 else rng.choice(options[:top_count])
            if next_score > current_score and sideways_left <= 0:
                if len(path) > 1 and backtrack_left > 0:
                    seen.remove(path.pop())
                    current_score = _local_path_score(city_map, path, goal, risky_penalty)
                    backtrack_left -= 1
                    sideways_left = 8
                    continue
                break
            if next_score > current_score:
                sideways_left -= 1

            path = next_path
            seen.add(nb)
            visited.append(nb)
            current_score = next_score
            if current_score < best_partial_score:
                best_partial_score = current_score
                best_partial = path[:]

        if restart in (0, 1, 3, 7, 15):
            logs.append(
                f"Restart {restart + 1}: gan nhat {best_partial[-1]}, h={manhattan(best_partial[-1], goal)}, "
                f"do dai={max(0, len(best_partial) - 1)}"
            )

    return _make_result(
        "Random Restart Hill Climbing",
        started_at,
        [],
        visited,
        0,
        False,
        logs,
        "Hill climbing ket o cuc bo, khong tim thay duong.",
        {"restarts": restart_count, "best_h": manhattan(best_partial[-1], goal)},
    )


def simulated_annealing_route(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    rng = _stable_rng("Simulated Annealing", start, goal)
    logs = [
        "Simulated Annealing route: chap nhan buoc te hon khi nhiet do con cao.",
        "Khong goi A*: trang thai la duong dang di, neighbor la o ke tiep.",
    ]
    visited = [start]
    max_steps = _search_limit(city_map, 2)
    restarts = 12
    best_partial = [start]
    best_score = _local_path_score(city_map, best_partial, goal, risky_penalty, distance_weight=4.0)

    for restart in range(restarts):
        path = [start]
        seen = {start}
        temperature = 42.0 + restart * 3.0
        current_score = _local_path_score(city_map, path, goal, risky_penalty, distance_weight=4.0)

        for step in range(max_steps):
            cur = path[-1]
            if cur == goal:
                cost = path_cost(city_map, path, risky_penalty)
                logs.append(f"Restart {restart + 1}: toi dich o buoc {step}, T={temperature:.2f}.")
                metrics = {"restarts": restart + 1, "temperature": temperature}
                return _make_result(
                    "Simulated Annealing",
                    started_at,
                    path,
                    visited,
                    cost,
                    True,
                    logs,
                    "Duong di duoc tim bang u mo phong.",
                    metrics,
                )

            neighbors = [nb for nb in _neighbors(city_map, cur, blocked_cells) if nb not in seen]
            if not neighbors:
                if len(path) <= 1:
                    break
                seen.remove(path.pop())
                current_score = _local_path_score(city_map, path, goal, risky_penalty, distance_weight=4.0)
                temperature *= 0.985
                continue

            rng.shuffle(neighbors)
            proposals = []
            for nb in neighbors[:4]:
                next_path = path + [nb]
                score = _local_path_score(city_map, next_path, goal, risky_penalty, distance_weight=4.0)
                proposals.append((score, nb, next_path))
            proposals.sort(key=lambda item: item[0])
            proposed_score, nb, next_path = proposals[0] if rng.random() > 0.2 else rng.choice(proposals)
            delta = proposed_score - current_score
            accept = delta <= 0 or rng.random() < math.exp(-delta / max(temperature, 0.001))
            if accept:
                path = next_path
                seen.add(nb)
                visited.append(nb)
                current_score = proposed_score
                if current_score < best_score:
                    best_score = current_score
                    best_partial = path[:]
            elif len(path) > 1 and rng.random() < 0.18:
                seen.remove(path.pop())
                current_score = _local_path_score(city_map, path, goal, risky_penalty, distance_weight=4.0)

            temperature *= 0.982
            if temperature < 0.08:
                temperature = 9.0

        if restart in (0, 1, 3, 7):
            logs.append(
                f"Restart {restart + 1}: best h={manhattan(best_partial[-1], goal)}, "
                f"do dai={max(0, len(best_partial) - 1)}"
            )

    return _make_result(
        "Simulated Annealing",
        started_at,
        [],
        visited,
        0,
        False,
        logs,
        "U mo phong khong tim thay duong trong gioi han buoc.",
        {"restarts": restarts, "best_h": manhattan(best_partial[-1], goal)},
    )


def local_beam_route(city_map, start, goal, risky_penalty=0, blocked_cells=None):
    started_at = time.perf_counter()
    logs = [
        "Local Beam Search route: giu nhieu duong ung vien tot cung luc.",
        "Khong goi A*: moi vong chi mo rong cac beam hien co va giu beam co diem thap.",
    ]
    visited = [start]
    beam_width = 14
    max_steps = _search_limit(city_map, 1)
    beams = [(0, [start])]
    best_path = [start]
    best_score = _local_path_score(city_map, best_path, goal, risky_penalty, distance_weight=2.2)

    for step in range(max_steps):
        candidates = []
        for cost_so_far, path in beams:
            cur = path[-1]
            for nb in _neighbors(city_map, cur, blocked_cells):
                if nb in path:
                    continue
                step_cost = city_map.get_tile_cost(*nb, risky_penalty=risky_penalty)
                next_cost = cost_so_far + step_cost
                next_path = path + [nb]
                visited.append(nb)
                if nb == goal:
                    cost = path_cost(city_map, next_path, risky_penalty)
                    logs.append(f"Beam step {step + 1}: gap dich, chi phi {_format_cost(cost)}.")
                    metrics = {"beam_width": beam_width, "steps": step + 1}
                    return _make_result(
                        "Local Beam Search",
                        started_at,
                        next_path,
                        visited,
                        cost,
                        True,
                        logs,
                        "Beam tot nhat da cham dich.",
                        metrics,
                    )
                score = next_cost + manhattan(nb, goal) * 2.2 + len(next_path) * 0.1
                candidates.append((score, next_cost, next_path))
                if score < best_score:
                    best_score = score
                    best_path = next_path[:]
        if not candidates:
            break
        candidates.sort(key=lambda item: item[0])
        beams = [(cost, path) for _score, cost, path in candidates[:beam_width]]
        if step in (0, 1, 3, 7, 15, 31):
            logs.append(
                f"Beam step {step + 1}: giu {len(beams)} beam, best h={manhattan(beams[0][1][-1], goal)}"
            )

    return _make_result(
        "Local Beam Search",
        started_at,
        [],
        visited,
        0,
        False,
        logs,
        "Beam search mat het ung vien truoc khi toi dich.",
        {"beam_width": beam_width, "best_h": manhattan(best_path[-1], goal)},
    )


PATH_ALGORITHM_FUNCS = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "A*": astar,
    "IDA*": ida_star,
    "Greedy": greedy,
    "IDS": ids,
    "Random Restart Hill Climbing": random_restart_hill_climbing_route,
    "Simulated Annealing": simulated_annealing_route,
    "Local Beam Search": local_beam_route,
}
