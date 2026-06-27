# algorithms/priority.py

import math
import random


def plan_label(order):
    return " -> ".join(order) if order else "(không có)"


def short_plan(order, max_chars=34):
    text = plan_label(order)
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def add_log(logs, line, max_lines=18):
    if len(logs) < max_lines:
        logs.append(line)


def fire_value(fire):
    danger_bonus = 3 if fire.danger_zone == "gas" else 2 if fire.danger_zone == "hospital" else 0
    return fire.severity * 4 + danger_bonus * 5


def order_cost(planner, order_ids, start_cell):
    if not order_ids:
        return 0
    cur = start_cell
    total = 0
    for position, fid in enumerate(order_ids):
        fire = planner.map.fire_lookup[fid]
        res = planner.route_cost(cur, fire.target)
        if not res.success:
            total += 9999
            continue
        urgency_bonus = fire_value(fire) * (0.35 + 0.05 * max(0, len(order_ids) - position))
        total += res.cost - urgency_bonus
        cur = fire.target
    return total


def initial_order_by_urgency(planner):
    fires = planner.map.fires[:]
    fires.sort(key=lambda f: (-fire_value(f), f.id))
    return [f.id for f in fires]


def neighbors(order):
    out = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            new = order[:]
            new[i], new[j] = new[j], new[i]
            out.append(new)
    return out


def simple_hill(planner):
    logs = ["Leo đồi đơn giản: nhận thứ tự tốt hơn đầu tiên."]
    order = initial_order_by_urgency(planner)
    start = planner.primary_start()
    current = order_cost(planner, order, start)
    add_log(logs, f"Kế hoạch hiện tại: {short_plan(order)} | chi phí {int(current)}")
    improved = True
    while improved:
        improved = False
        for nb in neighbors(order):
            c = order_cost(planner, nb, start)
            if c < current:
                add_log(logs, f"Kế hoạch lân cận: {short_plan(nb)} | chi phí {int(c)}")
                add_log(logs, f"Nhận bước tốt đầu tiên: {int(current)} -> {int(c)}")
                order, current = nb, c
                improved = True
                break
    add_log(logs, f"Thứ tự cuối: {plan_label(order)}")
    return order, logs


def best_hill(planner):
    logs = ["Leo đồi tốt nhất: so mọi hoán đổi và chọn bước tốt nhất."]
    order = initial_order_by_urgency(planner)
    start = planner.primary_start()
    current = order_cost(planner, order, start)
    add_log(logs, f"Kế hoạch hiện tại: {short_plan(order)} | chi phí {int(current)}")
    while True:
        best_order, best_cost = order, current
        checked = 0
        for nb in neighbors(order):
            checked += 1
            c = order_cost(planner, nb, start)
            if c < best_cost:
                best_order, best_cost = nb, c
        add_log(logs, f"Đã kiểm {checked} lân cận; chi phí tốt nhất {int(best_cost)}")
        if best_cost < current:
            add_log(logs, f"Lân cận tốt nhất: {short_plan(best_order)}")
            add_log(logs, f"Nhận hoán đổi tốt nhất: {int(current)} -> {int(best_cost)}")
            order, current = best_order, best_cost
        else:
            break
    add_log(logs, f"Thứ tự cuối: {plan_label(order)}")
    return order, logs


def stochastic_hill(planner):
    logs = ["Leo đồi ngẫu nhiên: chọn ngẫu nhiên một lân cận tốt hơn."]
    order = [f.id for f in planner.map.fires]
    random.shuffle(order)
    start = planner.primary_start()
    current = order_cost(planner, order, start)
    add_log(logs, f"Kế hoạch hiện tại: {short_plan(order)} | chi phí {int(current)}")
    for step in range(70):
        better = []
        for nb in neighbors(order):
            c = order_cost(planner, nb, start)
            if c < current:
                better.append((c, nb))
        if not better:
            break
        current, order = random.choice(better)
        add_log(logs, f"Bước {step}: chọn tốt hơn {short_plan(order)} | chi phí {int(current)}")
    add_log(logs, f"Thứ tự cuối: {plan_label(order)}")
    return order, logs


def random_restart(planner):
    logs = ["Khởi động lại ngẫu nhiên: lặp leo đồi từ nhiều thứ tự khác nhau."]
    start = planner.primary_start()
    best_order = None
    best_cost = float("inf")
    ids = [f.id for f in planner.map.fires]
    for k in range(14):
        order = ids[:]
        random.shuffle(order)
        current = order_cost(planner, order, start)
        improved = True
        while improved:
            improved = False
            for nb in neighbors(order):
                c = order_cost(planner, nb, start)
                if c < current:
                    order, current = nb, c
                    improved = True
                    break
        add_log(logs, f"Lần khởi động {k + 1}: {short_plan(order)} | chi phí {int(current)}")
        if current < best_cost:
            best_order, best_cost = order, current
            add_log(logs, f"Tốt nhất toàn cục mới: {int(best_cost)}")
    add_log(logs, f"Thứ tự cuối: {plan_label(best_order)}")
    return best_order, logs


def simulated_annealing(planner):
    logs = ["Ủ mô phỏng: có thể nhận thứ tự tệ hơn khi nhiệt độ còn cao."]
    order = [f.id for f in planner.map.fires]
    random.shuffle(order)
    start = planner.primary_start()
    current = order_cost(planner, order, start)
    best_order, best_cost = order[:], current
    temp = 55.0
    add_log(logs, f"Kế hoạch hiện tại: {short_plan(order)} | chi phí {int(current)}")
    for step in range(240):
        if len(order) < 2:
            break
        i, j = random.sample(range(len(order)), 2)
        nb = order[:]
        nb[i], nb[j] = nb[j], nb[i]
        c = order_cost(planner, nb, start)
        delta = c - current
        accept = delta < 0 or random.random() < math.exp(-delta / max(temp, 0.001))
        if accept:
            if delta > 0:
                add_log(logs, f"T={temp:.1f}: nhận bước tệ hơn {int(current)} -> {int(c)}")
            elif step < 8:
                add_log(logs, f"T={temp:.1f}: nhận bước tốt hơn {int(current)} -> {int(c)}")
            order, current = nb, c
            if current < best_cost:
                best_order, best_cost = order[:], current
        elif step < 8:
            add_log(logs, f"T={temp:.1f}: bỏ lân cận chi phí {int(c)}")
        temp *= 0.965
        if temp < 0.1:
            temp = 8.0
    add_log(logs, f"Thứ tự cuối sau ủ: {plan_label(best_order)}")
    add_log(logs, f"Chi phí cuối sau ủ={int(best_cost)}")
    return best_order, logs


def local_beam(planner):
    logs = ["Tìm kiếm chùm cục bộ: giữ nhiều thứ tự tốt cùng lúc."]
    ids = [f.id for f in planner.map.fires]
    start = planner.primary_start()
    beams = []
    for _ in range(4):
        order = ids[:]
        random.shuffle(order)
        beams.append(order)
    for step in range(45):
        cand = []
        for beam in beams:
            cand.append(beam)
            cand.extend(neighbors(beam))
        unique = []
        seen = set()
        for candidate in cand:
            key = tuple(candidate)
            if key not in seen:
                seen.add(key)
                unique.append(candidate)
        unique.sort(key=lambda o: order_cost(planner, o, start))
        beams = unique[:4]
        if step in [0, 1, 5, 10, 20, 35]:
            summary = " | ".join(f"{short_plan(b, 18)}:{int(order_cost(planner, b, start))}" for b in beams[:3])
            add_log(logs, f"Bước chùm {step}: {summary}")
    add_log(logs, f"Thứ tự cuối: {plan_label(beams[0])}")
    return beams[0], logs


PRIORITY_ALGORITHM_FUNCS = {
    "Simple Hill Climbing": simple_hill,
    "Best Hill Climbing": best_hill,
    "Stochastic Hill Climbing": stochastic_hill,
    "Random Restart Hill Climbing": random_restart,
    "Simulated Annealing": simulated_annealing,
    "Local Beam Search": local_beam,
}
