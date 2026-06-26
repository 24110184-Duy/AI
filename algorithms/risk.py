# algorithms/risk.py

from config import COLS, ROWS, RISKY, TRAFFIC


def _cells_with_tile(city_map, tile_name):
    return [(r, c) for r in range(ROWS) for c in range(COLS) if city_map.grid[r][c] == tile_name]


def _sample_cells(cells, limit=4):
    shown = cells[:limit]
    suffix = "" if len(cells) <= limit else f" +{len(cells) - limit} ô nữa"
    return f"{shown}{suffix}"


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
    "Minimax": minimax_policy,
    "Alpha-Beta Pruning": alpha_beta_policy,
    "Expectimax": expectimax_policy,
}
