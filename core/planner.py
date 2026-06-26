# core/planner.py

import time
import itertools

from config import (
    PASS_RATIO, TRAFFIC, RISKY, ALGORITHM_LABELS,
    ROUTE_ALGORITHMS, PRIORITY_ALGORITHMS, DISPATCH_ALGORITHMS, RISK_ALGORITHMS,
    ON_TIME_BONUS, LATE_TURN_PENALTY, GAS_LATE_PENALTY, HOSPITAL_LATE_PENALTY,
    TRAVEL_COST_SCORE_PENALTY, COMPUTATION_NODE_SCORE_DIVISOR,
    TRAFFIC_TILE_SCORE_PENALTY, RISKY_TILE_SCORE_PENALTY_AND_OR,
    RISKY_TILE_SCORE_PENALTY_BELIEF, MISSING_FIRE_SCORE_PENALTY,
)
from core.models import ComboChoice, PlanReport, TruckPlan
from algorithms.pathfinding import PATH_ALGORITHM_FUNCS, astar
from algorithms.priority import PRIORITY_ALGORITHM_FUNCS
from algorithms.dispatch import DISPATCH_ALGORITHM_FUNCS
from algorithms.risk import RISK_ALGORITHM_FUNCS
from utils.helpers import count_tile_on_path


class CrisisPlanner:
    def __init__(self, city_map):
        self.map = city_map
        self.path_cache = {}
        self.current_route_ai = "A*"
        self.current_risky_penalty = 0

    def reset_cache(self):
        self.path_cache = {}

    def truck_by_id(self, truck_id):
        for truck in self.map.stations:
            if truck.id == truck_id:
                return truck
        raise KeyError(f"Unknown truck id {truck_id}")

    def primary_start(self):
        return self.map.stations[0].start if self.map.stations else (0, 0)

    def route_cost(self, start, goal, blocked_cells=None):
        blocked_key = tuple(sorted(blocked_cells or ()))
        key = (self.current_route_ai, self.current_risky_penalty, blocked_key, start, goal)
        if key in self.path_cache:
            return self.path_cache[key]
        func = PATH_ALGORITHM_FUNCS.get(self.current_route_ai, astar)
        result = func(self.map, start, goal, self.current_risky_penalty, set(blocked_key))
        self.path_cache[key] = result
        return result

    def build_plan(self, choice, planning_seconds_used=0, benchmark_score=0, pass_score=0, timed_out=False):
        self.reset_cache()
        self.current_route_ai = choice.route_ai
        risk_func = RISK_ALGORITHM_FUNCS[choice.risk_ai]
        risky_penalty, risk_logs = risk_func(self)
        self.current_risky_penalty = risky_penalty

        priority_func = PRIORITY_ALGORITHM_FUNCS[choice.priority_ai]
        fire_order, priority_logs = priority_func(self)

        dispatch_func = DISPATCH_ALGORITHM_FUNCS[choice.dispatch_ai]
        fire_to_trucks, dispatch_logs = dispatch_func(self, fire_order)

        report = PlanReport(choice=choice)
        report.benchmark_score = benchmark_score
        report.pass_score = pass_score
        report.total_fires = len(self.map.fires)
        report.fire_order = fire_order
        report.fire_to_trucks = fire_to_trucks
        report.dispatch_logs = dispatch_logs[:16]
        report.priority_logs = priority_logs[:16]
        report.risk_logs = risk_logs[:16]
        report.planning_penalty = int(planning_seconds_used // 6) * 5
        report.timed_out = timed_out
        if timed_out:
            report.planning_penalty += max(500, int(benchmark_score * 0.75), pass_score + 250)

        truck_plans = {}
        for truck in self.map.stations:
            truck_plans[truck.id] = TruckPlan(truck_id=truck.id, start=truck.start)

        # Build truck task sequences based on fire order.
        for fid in fire_order:
            for tid in fire_to_trucks.get(fid, []):
                if tid in truck_plans:
                    truck_plans[tid].assigned_fires.append(fid)

        route_label = ALGORITHM_LABELS.get(choice.route_ai, choice.route_ai)
        route_logs = [f"AI đường đi: {route_label}", f"Phạt rủi ro mỗi ô '?': {self.current_risky_penalty}"]
        computation_nodes = 0
        total_cost = 0
        extinguished = set()
        route_explanation_added = False

        for tid, plan in truck_plans.items():
            cur = plan.start
            elapsed = 0
            full_path = [cur]
            truck = self.truck_by_id(tid)
            water_left = truck.water
            for fid in plan.assigned_fires:
                fire = self.map.fire_lookup[fid]
                # Refill if needed and hydrant exists.
                needed_water = fire.severity * 35
                if truck.capacity < needed_water:
                    plan.success = False
                    if len(route_logs) < 18:
                        route_logs.append(f"{tid} không đủ bình cho {fid}: cần {needed_water}, bình {truck.capacity}.")
                    continue
                if water_left < needed_water and self.map.hydrants:
                    hydrant = min(self.map.hydrants, key=lambda h: abs(h[0] - cur[0]) + abs(h[1] - cur[1]))
                    segment = self.route_cost(cur, hydrant)
                    computation_nodes += segment.visited_count
                    if segment.success:
                        plan.path_segments.append(("NƯỚC", "Trụ nước", segment.path))
                        full_path.extend(segment.path[1:])
                        plan.travel_cost += segment.cost
                        total_cost += segment.cost
                        elapsed += segment.cost / max(1, truck.speed)
                        cur = hydrant
                        water_left = truck.capacity
                        route_logs.append(f"{tid} nạp nước trước khi đến {fid}.")
                    else:
                        plan.success = False
                        if len(route_logs) < 18:
                            route_logs.append(f"{tid} không tới được trụ nước trước {fid}.")
                        continue
                elif water_left < needed_water:
                    plan.success = False
                    if len(route_logs) < 18:
                        route_logs.append(f"{tid} thiếu nước cho {fid} và không có trụ W để nạp.")
                    continue
                segment = self.route_cost(cur, fire.target)
                computation_nodes += segment.visited_count
                report.route_visited.extend(segment.visited)
                if not segment.success:
                    plan.success = False
                    route_logs.append(f"{tid} không tới được {fid}.")
                    continue
                if not route_explanation_added:
                    route_logs.extend(segment.logs[:7])
                    route_explanation_added = True
                plan.path_segments.append(("CHÁY", fid, segment.path))
                full_path.extend(segment.path[1:])
                plan.travel_cost += segment.cost
                total_cost += segment.cost
                plan.traffic_tiles += count_tile_on_path(self.map, segment.path, TRAFFIC)
                plan.risky_tiles += count_tile_on_path(self.map, segment.path, RISKY)
                risky_on_segment = [cell for cell in segment.path if self.map.grid[cell[0]][cell[1]] == RISKY]
                if choice.risk_ai == "And-Or Search" and risky_on_segment:
                    backup = self.route_cost(cur, fire.target, blocked_cells=set(risky_on_segment))
                    computation_nodes += backup.visited_count
                    report.route_visited.extend(backup.visited)
                    if backup.success and backup.path != segment.path:
                        report.backup_paths.append(backup.path)
                        if len(route_logs) < 18:
                            route_logs.append(
                                f"AND-OR dự phòng cho {tid}->{fid}: chặn {risky_on_segment[0]}, chi phí {int(backup.cost)}"
                            )
                    elif len(route_logs) < 18:
                        route_logs.append(f"Cảnh báo AND-OR: không tìm được tuyến dự phòng cho {tid}->{fid}.")
                elapsed += segment.cost / max(1, truck.speed)
                arrival_turn = int(elapsed // 7) + 1
                plan.arrival_times[fid] = arrival_turn
                cur = fire.target
                water_left -= needed_water
                extinguished.add(fid)
                if len(route_logs) < 18:
                    route_logs.append(
                        f"{tid} -> {fid}: chi phí {int(segment.cost)}, nút {segment.visited_count}, "
                        f"{segment.runtime_ms:.2f}ms, lượt {arrival_turn}"
                    )
            plan.full_path = full_path
            truck_plans[tid] = plan

        route_logs.insert(2, f"Tổng chi phí di chuyển: {int(total_cost)} | Số nút đã tính: {computation_nodes}")
        report.truck_plans = truck_plans
        report.route_logs = route_logs[:18]
        report.computation_nodes = computation_nodes
        report.total_travel_cost = total_cost
        report.extinguished_count = len(extinguished)
        report.route_path_preview = self._first_nonempty_path(truck_plans)

        score = self.calculate_score(report)
        report.score = score
        report.win = report.extinguished_count == report.total_fires and score >= pass_score and not timed_out
        if timed_out:
            report.fail_reason = "Hết thời gian lập kế hoạch, điểm bị phạt mạnh."
        elif report.extinguished_count < report.total_fires:
            report.fail_reason = f"Chỉ dập được {report.extinguished_count}/{report.total_fires} đám cháy."
        elif score < pass_score:
            report.fail_reason = f"Điểm {score} thấp hơn điểm qua màn {pass_score}."
        else:
            report.fail_reason = "Nhiệm vụ hoàn thành."
        return report

    def _first_nonempty_path(self, truck_plans):
        for plan in truck_plans.values():
            if len(plan.full_path) > 1:
                return plan.full_path
        return []

    def calculate_score(self, report):
        score = 0
        handled_fires = set()
        for plan in report.truck_plans.values():
            for fid in plan.assigned_fires:
                if fid not in handled_fires and fid in plan.arrival_times:
                    fire = self.map.fire_lookup[fid]
                    handled_fires.add(fid)
                    score += fire.base_score
                    arrival = plan.arrival_times[fid]
                    if arrival <= fire.deadline:
                        score += ON_TIME_BONUS
                    else:
                        score -= (arrival - fire.deadline) * LATE_TURN_PENALTY
                    if fire.danger_zone == "gas" and arrival > fire.deadline:
                        score -= GAS_LATE_PENALTY
                    if fire.danger_zone == "hospital" and arrival > fire.deadline:
                        score -= HOSPITAL_LATE_PENALTY
        score -= int(report.total_travel_cost * TRAVEL_COST_SCORE_PENALTY)
        score -= int(report.computation_nodes / COMPUTATION_NODE_SCORE_DIVISOR)
        score -= report.planning_penalty
        for plan in report.truck_plans.values():
            score -= plan.traffic_tiles * TRAFFIC_TILE_SCORE_PENALTY
            risky_penalty = RISKY_TILE_SCORE_PENALTY_AND_OR if report.choice.risk_ai == "And-Or Search" else RISKY_TILE_SCORE_PENALTY_BELIEF
            score -= plan.risky_tiles * risky_penalty
        missing = report.total_fires - len(handled_fires)
        score -= missing * MISSING_FIRE_SCORE_PENALTY
        return max(0, int(score))

    def estimate_benchmark(self):
        # Benchmark only uses algorithms currently allowed in config.
        candidate_dispatch = DISPATCH_ALGORITHMS[:]
        candidate_priority = PRIORITY_ALGORITHMS[:]
        candidate_route = ROUTE_ALGORITHMS[:]
        candidate_risk = RISK_ALGORITHMS[:]
        best_report = None
        tested = 0
        start = time.perf_counter()
        for d, p, r, risk in itertools.product(candidate_dispatch, candidate_priority, candidate_route, candidate_risk):
            choice = ComboChoice(d, p, r, risk)
            report = self.build_plan(choice, planning_seconds_used=0, benchmark_score=0, pass_score=0)
            tested += 1
            if best_report is None or report.score > best_report.score:
                best_report = report
        elapsed = time.perf_counter() - start
        benchmark = best_report.score if best_report else 0
        pass_score = int(benchmark * PASS_RATIO)
        return benchmark, pass_score, best_report, tested, elapsed

    def compare_current_map(self, limit=8):
        combos = [
            ComboChoice(d, p, r, risk)
            for d, p, r, risk in itertools.product(
                DISPATCH_ALGORITHMS,
                PRIORITY_ALGORITHMS,
                ROUTE_ALGORITHMS,
                RISK_ALGORITHMS,
            )
        ]
        reports = [self.build_plan(c, 0, 0, 0) for c in combos[:limit]]
        reports.sort(key=lambda r: r.score, reverse=True)
        return reports
