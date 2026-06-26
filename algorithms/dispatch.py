# algorithms/dispatch.py

import random


def add_log(logs, line, max_lines=28):
    if len(logs) < max_lines:
        logs.append(line)


def truck_can_handle(truck, fire):
    needed_water = fire.severity * 35
    if truck.capacity < needed_water:
        return False
    if fire.severity >= 3 and truck.water < 80:
        return False
    if fire.danger_zone == "gas" and not truck.heavy and truck.water < 100:
        return False
    return True


def truck_reject_reason(planner, truck, fire):
    needed_water = fire.severity * 35
    if truck.capacity < needed_water:
        return f"bình {truck.capacity} nhỏ hơn lượng nước cần {needed_water}"
    if fire.severity >= 3 and truck.water < 80:
        return f"không đủ nước cho mức nguy hiểm {fire.severity}"
    if fire.danger_zone == "gas" and not truck.heavy and truck.water < 100:
        return "cháy trạm xăng cần xe nặng hoặc ít nhất 100 nước"
    route = planner.route_cost(truck.start, fire.target)
    if not route.success:
        return "không có đường tới"
    return ""


def compatibility_score(planner, truck, fire):
    if not truck_can_handle(truck, fire):
        return 99999
    route = planner.route_cost(truck.start, fire.target)
    if not route.success:
        return 99999
    water_penalty = max(0, fire.severity * 35 - truck.capacity) * 3
    speed_bonus = -truck.speed * 4
    heavy_bonus = -12 if fire.severity >= 3 and truck.heavy else 0
    danger_bonus = -8 if fire.danger_zone in ["gas", "hospital"] and truck.speed >= 3 else 0
    return route.cost + water_penalty + speed_bonus + heavy_bonus + danger_bonus


def make_domains(planner):
    domains = {}
    logs = []
    for fire in planner.map.fires:
        all_trucks = [truck.id for truck in planner.map.stations]
        add_log(logs, f"Miền ban đầu({fire.id}) = {all_trucks}")
        valid = []
        for truck in planner.map.stations:
            reason = truck_reject_reason(planner, truck, fire)
            if reason:
                add_log(logs, f"Loại {truck.id} khỏi {fire.id} vì {reason}.")
            elif compatibility_score(planner, truck, fire) < 99999:
                valid.append(truck.id)
        domains[fire.id] = valid
        add_log(logs, f"Miền cuối({fire.id}) = {valid}")
    return domains, logs


def finish_assignment(planner, fire_order, domains, logs):
    # Assign required number of trucks for each fire. Trucks can receive several sequential fires.
    truck_load = {t.id: 0 for t in planner.map.stations}
    assignment = {fid: [] for fid in fire_order}
    for fid in fire_order:
        fire = planner.map.fire_lookup[fid]
        candidates = domains.get(fid, [])[:]
        candidates.sort(key=lambda tid: truck_load[tid] + compatibility_score(planner, planner.truck_by_id(tid), fire) * 0.05)
        chosen = []
        for tid in candidates:
            if len(chosen) >= fire.required_units:
                break
            chosen.append(tid)
            truck_load[tid] += 1
        assignment[fid] = chosen
        if len(chosen) < fire.required_units:
            add_log(logs, f"{fid} thiếu xe: cần {fire.required_units}, có {len(chosen)}")
        else:
            add_log(logs, f"{fid} <- {chosen}")
    return assignment, logs


def backtracking(planner, fire_order):
    domains, logs = make_domains(planner)
    logs.insert(0, "Quay lui: thử đệ quy các lựa chọn xe cho từng đám cháy.")
    best = {"score": 999999, "assign": None}
    partial = {}

    def rec(i, cost):
        if cost >= best["score"]:
            return
        if i == len(fire_order):
            best["score"] = cost
            best["assign"] = {k: v[:] for k, v in partial.items()}
            add_log(logs, f"Phân công tốt hơn, chi phí={int(cost)}")
            return
        fid = fire_order[i]
        fire = planner.map.fire_lookup[fid]
        choices = domains.get(fid, [])
        if not choices:
            return
        # choose one or two trucks combinations
        combos = []
        for a in choices:
            combos.append([a])
        if fire.required_units >= 2:
            for idx, a in enumerate(choices):
                for b in choices[idx+1:]:
                    combos.append([a, b])
        for combo in combos:
            if len(combo) < fire.required_units:
                continue
            c = sum(compatibility_score(planner, planner.truck_by_id(t), fire) for t in combo)
            partial[fid] = combo
            rec(i + 1, cost + c)
            partial.pop(fid, None)

    rec(0, 0)
    if best["assign"] is None:
        assignment, logs = finish_assignment(planner, fire_order, domains, logs)
        return assignment, logs
    return best["assign"], logs


def forward_checking(planner, fire_order):
    domains, logs = make_domains(planner)
    logs.insert(0, "Kiểm tra trước: gán xe rồi kiểm tra các đám cháy tiếp theo còn lựa chọn hợp lệ.")
    assignment = {}
    for idx, fid in enumerate(fire_order):
        fire = planner.map.fire_lookup[fid]
        domains[fid].sort(key=lambda tid: compatibility_score(planner, planner.truck_by_id(tid), fire))
        chosen = domains[fid][:fire.required_units]
        assignment[fid] = chosen
        add_log(logs, f"Gán {fid} <- {chosen}")
        for future in fire_order[idx+1:]:
            if not domains.get(future):
                add_log(logs, f"Kiểm tra trước lỗi: {future} không còn xe hợp lệ.")
    return assignment, logs


def ac3(planner, fire_order):
    domains, logs = make_domains(planner)
    logs.insert(0, "AC3: cắt bớt miền xe không hợp lệ bằng ràng buộc.")
    for fid in list(domains.keys()):
        fire = planner.map.fire_lookup[fid]
        before = domains[fid][:]
        domains[fid] = [tid for tid in domains[fid] if truck_can_handle(planner.truck_by_id(tid), fire)]
        removed = sorted(set(before) - set(domains[fid]))
        if removed:
            add_log(logs, f"Loại {removed} khỏi {fid}: ràng buộc nước/xe nặng.")
        if fire.danger_zone == "hospital":
            before = domains[fid][:]
            domains[fid] = [tid for tid in domains[fid] if planner.truck_by_id(tid).speed >= 2]
            removed = sorted(set(before) - set(domains[fid]))
            if removed:
                add_log(logs, f"Loại {removed} khỏi {fid}: khu bệnh viện cần xe đủ nhanh.")
    return finish_assignment(planner, fire_order, domains, logs)


def min_conflicts(planner, fire_order):
    domains, logs = make_domains(planner)
    logs.insert(0, "Giảm xung đột: bắt đầu ngẫu nhiên rồi sửa phân công nhiều xung đột.")
    assignment = {}
    for fid in fire_order:
        fire = planner.map.fire_lookup[fid]
        choices = domains.get(fid, [])[:]
        random.shuffle(choices)
        assignment[fid] = choices[:fire.required_units]
    def conflict_count(assign):
        conflicts = 0
        for fid, tids in assign.items():
            fire = planner.map.fire_lookup[fid]
            if len(tids) < fire.required_units:
                conflicts += 5
            for tid in tids:
                if not truck_can_handle(planner.truck_by_id(tid), fire):
                    conflicts += 3
        return conflicts
    best = {k: v[:] for k, v in assignment.items()}
    best_conf = conflict_count(best)
    for step in range(90):
        if best_conf == 0:
            break
        fid = random.choice(fire_order)
        fire = planner.map.fire_lookup[fid]
        choices = domains.get(fid, [])[:]
        choices.sort(key=lambda tid: compatibility_score(planner, planner.truck_by_id(tid), fire))
        assignment[fid] = choices[:fire.required_units]
        conf = conflict_count(assignment)
        if conf <= best_conf:
            best_conf = conf
            best = {k: v[:] for k, v in assignment.items()}
            add_log(logs, f"Bước sửa {step}: xung đột={conf}")
    return best, logs


DISPATCH_ALGORITHM_FUNCS = {
    "Backtracking Search": backtracking,
    "Forward Checking": forward_checking,
    "AC3 Search": ac3,
    "Min Conflicts": min_conflicts,
}
