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


RISK_ALGORITHM_FUNCS = {
    "And-Or Search": and_or_policy,
    "Belief State Search": belief_state_policy,
}
