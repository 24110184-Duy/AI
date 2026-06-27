# algorithms/risk.py

from config import COLS, ROWS, RISKY, TRAFFIC


def _cells_with_tile(city_map, tile_name):
    return [(r, c) for r in range(ROWS) for c in range(COLS) if city_map.grid[r][c] == tile_name]


def _sample_cells(cells, limit=4):
    shown = cells[:limit]
    suffix = "" if len(cells) <= limit else f" +{len(cells) - limit} ô nữa"
    return f"{shown}{suffix}"


def _belief_cells_around(city_map, seeds, radius=1):
    cells = set(seeds)
    frontier = list(seeds)
    for _step in range(radius):
        next_frontier = []
        for row, col in frontier:
            for nb in city_map.get_neighbors(row, col):
                if nb in cells:
                    continue
                cells.add(nb)
                next_frontier.append(nb)
        frontier = next_frontier
    return sorted(cells)


def and_or_policy(planner):
    risky_cells = _cells_with_tile(planner.map, RISKY)
    traffic_cells = _cells_with_tile(planner.map, TRAFFIC)
    logs = ["Tìm kiếm AND-OR: lập phương án dự phòng cho đường rủi ro."]
    logs.append(f"Ô rủi ro '?': {_sample_cells(risky_cells)}")
    logs.append(f"Ô kẹt xe: {len(traffic_cells)}")
    logs.append("Nhánh OR: dùng tuyến nhanh nếu '?' đang mở.")
    logs.append("Nhánh AND: nếu '?' bị chặn, hệ thống tính tuyến dự phòng.")
    logs.append("Mô hình: phạt rủi ro thấp, kèm đường dự phòng trên bản đồ.")
    return 1, logs


def belief_state_policy(planner):
    risky_cells = _cells_with_tile(planner.map, RISKY)
    traffic_cells = _cells_with_tile(planner.map, TRAFFIC)
    logs = ["Tìm kiếm trạng thái niềm tin: lập kế hoạch trên nhiều trạng thái đường có thể xảy ra."]
    logs.append(f"Ô rủi ro '?': {_sample_cells(risky_cells)}")
    logs.append(f"Ô kẹt xe: {len(traffic_cells)}")
    logs.append("Niềm tin: '?' có thể mở hoặc chặn, kẹt xe có thể nhẹ hoặc nặng.")
    logs.append("Mô hình: phạt rủi ro cao để ưu tiên đường đã biết an toàn hơn.")
    return 6, logs


def blind_belief_policy(planner):
    risky_cells = _cells_with_tile(planner.map, RISKY)
    traffic_cells = _cells_with_tile(planner.map, TRAFFIC)
    starts = [truck.start for truck in planner.map.stations]
    goals = [fire.target for fire in planner.map.fires]
    partial_start_cells = _belief_cells_around(planner.map, starts, radius=1)
    partial_goal_cells = _belief_cells_around(planner.map, goals, radius=1)
    full_belief_states = max(1, len(partial_start_cells) * len(partial_goal_cells))
    uncertainty_pressure = min(4, full_belief_states // 80)
    penalty = min(13, 5 + len(risky_cells) // 6 + uncertainty_pressure)
    logs = ["Blind Belief State Search: mo phong niem tin khi diem bat dau hoac dich bi mu."]
    logs.append(f"Mo mot phan bat dau: {_sample_cells(partial_start_cells)}")
    logs.append(f"Mo mot phan dich: {_sample_cells(partial_goal_cells)}")
    logs.append(f"Mo toan bo: {len(partial_start_cells)} x {len(partial_goal_cells)} = {full_belief_states} trang thai niem tin.")
    logs.append(f"O rui ro '?': {_sample_cells(risky_cells)}")
    logs.append(f"O ket xe: {len(traffic_cells)}")
    logs.append(f"Mo hinh: tang penalty '?' len {penalty} de uu tien duong on dinh khi thieu quan sat.")
    return penalty, logs


def minimax_policy(planner):
    risky_cells = _cells_with_tile(planner.map, RISKY)
    traffic_cells = _cells_with_tile(planner.map, TRAFFIC)
    worst_risk = len(risky_cells)
    worst_traffic = len(traffic_cells)
    penalty = min(14, 8 + worst_risk // 5 + worst_traffic // 20)
    logs = ["Minimax: xem môi trường như đối thủ luôn chọn tình huống xấu nhất."]
    logs.append(f"Ô rủi ro '?': {_sample_cells(risky_cells)}")
    logs.append(f"Ô kẹt xe: {worst_traffic}")
    logs.append(f"MAX: chọn tuyến có thiệt hại thấp nhất; MIN: giả định '?' bị chặn hoặc gây chậm.")
    logs.append(f"Mô hình: phạt rủi ro mạnh, penalty mỗi ô '?' = {penalty}.")
    return penalty, logs


def alpha_beta_policy(planner):
    risky_cells = _cells_with_tile(planner.map, RISKY)
    traffic_cells = _cells_with_tile(planner.map, TRAFFIC)
    examined_branches = max(1, len(risky_cells) + len(traffic_cells))
    pruned_branches = examined_branches // 3
    penalty = min(12, 7 + len(risky_cells) // 6 + len(traffic_cells) // 24)
    logs = ["Alpha-Beta Pruning: dùng Minimax nhưng cắt sớm nhánh không thể tốt hơn."]
    logs.append(f"Ô rủi ro '?': {_sample_cells(risky_cells)}")
    logs.append(f"Ô kẹt xe: {len(traffic_cells)}")
    logs.append(f"Cắt tỉa khoảng {pruned_branches}/{examined_branches} nhánh rủi ro giả lập.")
    logs.append(f"Mô hình: vẫn ưu tiên an toàn, penalty mỗi ô '?' = {penalty}.")
    return penalty, logs


def expectimax_policy(planner):
    risky_cells = _cells_with_tile(planner.map, RISKY)
    traffic_cells = _cells_with_tile(planner.map, TRAFFIC)
    expected_risk = len(risky_cells) * 0.45 + len(traffic_cells) * 0.18
    penalty = min(10, 3 + int(expected_risk // 3))
    logs = ["Expectimax: tính theo kỳ vọng thay vì luôn lấy tình huống xấu nhất."]
    logs.append(f"Ô rủi ro '?': {_sample_cells(risky_cells)}")
    logs.append(f"Ô kẹt xe: {len(traffic_cells)}")
    logs.append("Chance node: '?' có thể mở hoặc bị chặn; kẹt xe có thể nhẹ hoặc nặng.")
    logs.append(f"Mô hình: cân bằng tốc độ/an toàn, penalty mỗi ô '?' = {penalty}.")
    return penalty, logs


RISK_ALGORITHM_FUNCS = {
    "And-Or Search": and_or_policy,
    "Belief State Search": belief_state_policy,
    "Blind Belief State Search": blind_belief_policy,
    "Minimax": minimax_policy,
    "Alpha-Beta Pruning": alpha_beta_policy,
    "Expectimax": expectimax_policy,
}
