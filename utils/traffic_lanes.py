# utils/traffic_lanes.py

from config import ROUTE_LANE_COUNT, TILE_SIZE


def direction_between(a, b):
    if not a or not b:
        return 0, 0
    dr = b[0] - a[0]
    dc = b[1] - a[1]
    if abs(dr) > abs(dc):
        return 1 if dr > 0 else -1, 0
    if dc:
        return 0, 1 if dc > 0 else -1
    return 0, 0


def right_lane_normal(direction):
    dr, dc = direction
    dx, dy = dc, dr
    return -dy, dx


def lane_slot_offset(slot_index, lane_count=ROUTE_LANE_COUNT):
    lane_count = max(1, int(lane_count or 1))
    if lane_count == 1:
        return 0
    slot_index = max(0, min(lane_count - 1, int(slot_index)))
    max_offset = TILE_SIZE // 2 - 6
    return -max_offset + (2 * max_offset * slot_index / (lane_count - 1))


def distributed_lane_slot(index, count, lane_count=ROUTE_LANE_COUNT):
    lane_count = max(1, int(lane_count or 1))
    count = max(1, int(count or 1))
    if lane_count == 1:
        return 0
    if count == 1:
        return lane_count // 2
    if count >= lane_count:
        return max(0, min(lane_count - 1, int(index)))
    first = 1 if lane_count >= 6 else 0
    last = lane_count - 2 if lane_count >= 6 else lane_count - 1
    return int(round(first + max(0, index) * (last - first) / max(1, count - 1)))


def lane_center_for_direction(cell, direction, slot_index=0, lane_count=ROUTE_LANE_COUNT):
    row, col = cell
    nx, ny = right_lane_normal(direction)
    offset = lane_slot_offset(slot_index, lane_count)
    return (
        col * TILE_SIZE + TILE_SIZE // 2 + nx * offset,
        row * TILE_SIZE + TILE_SIZE // 2 + ny * offset,
    )


def lane_center_between(cell, other_cell, slot_index=0, lane_count=ROUTE_LANE_COUNT):
    return lane_center_for_direction(cell, direction_between(cell, other_cell), slot_index, lane_count)


def lane_segment_points(path, slot_index=0, lane_count=ROUTE_LANE_COUNT):
    segments = []
    for index in range(len(path) - 1):
        start = path[index]
        end = path[index + 1]
        direction = direction_between(start, end)
        if direction == (0, 0):
            continue
        segments.append((
            lane_center_for_direction(start, direction, slot_index, lane_count),
            lane_center_for_direction(end, direction, slot_index, lane_count),
        ))
    return segments


def lane_path_waypoints(path, slot_index=0, lane_count=ROUTE_LANE_COUNT):
    waypoints = []
    for index in range(len(path) - 1):
        start = path[index]
        end = path[index + 1]
        direction = direction_between(start, end)
        if direction == (0, 0):
            continue
        start_point = lane_center_for_direction(start, direction, slot_index, lane_count)
        end_point = lane_center_for_direction(end, direction, slot_index, lane_count)
        if not waypoints:
            waypoints.append((start_point, index))
        elif point_distance(waypoints[-1][0], start_point) > 0.5:
            waypoints.append((start_point, index))
        waypoints.append((end_point, index + 1))
    return waypoints


def point_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
