# core/game.py

import math
import random
import time
import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, FULLSCREEN, MAP_WIDTH, MAP_HEIGHT, PANEL_X,
    PANEL_CONTENT_WIDTH,
    STATE_MENU, STATE_PLANNING, STATE_EXECUTING, STATE_RESULT,
    STATION, HYDRANT, FIRE, TRAFFIC, BLOCKED, RISKY,
    WHITE, BLACK, DARK_BG, PANEL_BG, CARD_BG, TEXT_MUTED, SUCCESS, WARNING, DANGER, CYAN, YELLOW,
    STATION_COLOR, HYDRANT_COLOR, FIRE_COLOR, HOSPITAL_COLOR, GAS_COLOR, TRAFFIC_COLOR, BLOCKED_COLOR, RISKY_COLOR,
    ROUTE_ALGORITHMS, PRIORITY_ALGORITHMS, DISPATCH_ALGORITHMS, RISK_ALGORITHMS,
    ALGORITHM_INFO, ALGORITHM_LABELS, ALGORITHM_DETAILS,
    PLANNING_SECONDS, STAR_2_RATIO, STAR_3_RATIO, PERFECT_RATIO,
    ON_TIME_BONUS, LATE_TURN_PENALTY, GAS_LATE_PENALTY, HOSPITAL_LATE_PENALTY,
    TRAVEL_COST_SCORE_PENALTY, TRAFFIC_TILE_SCORE_PENALTY,
    RISKY_TILE_SCORE_PENALTY_AND_OR, RISKY_TILE_SCORE_PENALTY_BELIEF,
    TILE_SIZE, VISITED_COLOR, ALT_PATH_COLOR,
    ROUTE_LINE_OUTLINE_WIDTH, ROUTE_LINE_WIDTH,
    ROUTE_DASH_LENGTH, ROUTE_GAP_LENGTH, ROUTE_LANE_COUNT, TRUCK_COLORS,
)
from utils.asset_loader import AssetLoader
from core.city_map import CityMap
from core.planner import CrisisPlanner
from core.models import ComboChoice
from core.entities import AnimatedTruck
from ui.button import Button
from ui.dropdown import Dropdown
from ui.slider import Slider
from ui.panel import Panel
from utils.traffic_lanes import direction_between, distributed_lane_slot, lane_center_for_direction


class Game:
    def __init__(self):
        pygame.init()
        self.fullscreen = FULLSCREEN
        self.screen = self.set_display_mode()
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = STATE_MENU

        self.asset_loader = AssetLoader()
        self.city_map = None
        self.planner = None
        self.benchmark_score = 0
        self.pass_score = 0
        self.best_report = None
        self.benchmark_info = ""

        self.report = None
        self.compare_reports = []
        self.trucks = []
        self.execution_started_at = None
        self.planning_started_at = time.perf_counter()
        self.execution_done = False
        self.reviewing_result = False
        self.map_zoom = 1.0
        self.map_camera_x = 0.0
        self.map_camera_y = 0.0
        self.map_min_zoom = 1.0
        self.map_max_zoom = 3.0
        self.background_cars = self.create_background_cars()
        self.visited_visible = 0
        self.path_visible = 0
        self.visible_logs = []
        self.animation_speed = 3
        self.show_visited_nodes = False
        self.show_legend = True
        self.show_details_modal = False
        self.show_truck_modal = False
        self.details_scroll = 0
        self.truck_colors = [tuple(color) for color in TRUCK_COLORS[:3]]
        self.truck_slider_drag = None
        self.truck_slider_rects = {}
        self.truck_slider_hit_rects = {}
        self.truck_input_rects = {}
        self.truck_edit_key = None
        self.truck_edit_text = ""
        self.truck_edit_select_all = False
        self.truck_specs_dirty = False
        self.selected_fire = None
        self.fire_info_rect = None

        self.title_font = self.load_font(["segoeuisemibold", "tahoma", "arial"], 34, bold=True)
        self.font = self.load_font(["tahoma", "segoeui", "arial"], 21)
        self.small_font = self.load_font(["consolas", "tahoma", "segoeui"], 16)
        self.tiny_font = self.load_font(["consolas", "tahoma", "segoeui"], 14)
        self.panel = Panel(self.screen, self.font, self.small_font, self.title_font)

        self.menu_buttons = []
        self.plan_buttons = []
        self.result_buttons = []
        self.result_modal_buttons = []
        self.result_modal_rect = None
        self.dispatch_dropdown = None
        self.priority_dropdown = None
        self.route_dropdown = None
        self.risk_dropdown = None
        self.speed_slider = None
        self.route_nodes_button = None
        self.legend_button = None
        self.truck_menu_button = None
        self.details_button = None
        self.details_close_button = None
        self.truck_close_button = None

        self.create_menu_ui()
        self.new_crisis()
        self.create_planning_ui()
        self.create_result_ui()

    def load_font(self, names, size, bold=False):
        for name in names:
            path = pygame.font.match_font(name, bold=bold)
            if path:
                return pygame.font.Font(path, size)
            path = pygame.font.match_font(name)
            if path:
                return pygame.font.Font(path, size)
        return pygame.font.SysFont(names[0], size, bold=bold)

    def set_display_mode(self):
        flags = 0
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
            if hasattr(pygame, "SCALED"):
                flags |= pygame.SCALED
        try:
            return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except pygame.error:
            self.fullscreen = False
            return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.screen = self.set_display_mode()
        self.panel.screen = self.screen

    def create_background_cars(self):
        rng = random.Random(20260626)
        colors = [
            (225, 38, 58),
            (245, 125, 40),
            (235, 215, 65),
            (90, 210, 255),
            (82, 220, 132),
            (210, 210, 218),
        ]
        cars = []
        for index in range(22):
            orientation = "h" if index % 2 == 0 else "v"
            cars.append({
                "orientation": orientation,
                "lane": rng.randrange(6),
                "speed": rng.uniform(24, 62),
                "phase": rng.random(),
                "color": rng.choice(colors),
                "size": rng.choice([0.75, 0.9, 1.05]),
                "reverse": rng.random() < 0.5,
            })
        return cars

    def draw_dynamic_background(self, rect, dark_overlay=0):
        old_clip = self.screen.get_clip()
        self.screen.set_clip(rect)
        pygame.draw.rect(self.screen, (12, 13, 18), rect)

        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        self.draw_background_roads(surface, rect.size)
        self.draw_background_cars(surface, rect.size)
        self.screen.blit(surface, rect.topleft)

        if dark_overlay:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, dark_overlay))
            self.screen.blit(overlay, rect.topleft)
        self.screen.set_clip(old_clip)

    def draw_background_roads(self, surface, size):
        width, height = size
        road_color = (42, 44, 52, 185)
        edge_color = (68, 70, 80, 110)
        lane_color = (214, 204, 122, 90)

        h_lanes = [int(height * ratio) for ratio in (0.22, 0.47, 0.72)]
        v_lanes = [int(width * ratio) for ratio in (0.18, 0.42, 0.70, 0.88)]

        for y in h_lanes:
            pygame.draw.rect(surface, road_color, (0, y - 18, width, 36))
            pygame.draw.line(surface, edge_color, (0, y - 18), (width, y - 18), 1)
            pygame.draw.line(surface, edge_color, (0, y + 18), (width, y + 18), 1)
            for x in range(-40, width + 40, 58):
                pygame.draw.line(surface, lane_color, (x, y), (x + 24, y), 2)

        for x in v_lanes:
            pygame.draw.rect(surface, road_color, (x - 18, 0, 36, height))
            pygame.draw.line(surface, edge_color, (x - 18, 0), (x - 18, height), 1)
            pygame.draw.line(surface, edge_color, (x + 18, 0), (x + 18, height), 1)
            for y in range(-40, height + 40, 58):
                pygame.draw.line(surface, lane_color, (x, y), (x, y + 24), 2)

        for x in v_lanes:
            for y in h_lanes:
                pygame.draw.rect(surface, (52, 54, 62, 160), (x - 20, y - 20, 40, 40), border_radius=5)

    def draw_background_cars(self, surface, size):
        width, height = size
        ticks = pygame.time.get_ticks() / 1000.0
        h_lanes = [int(height * ratio) for ratio in (0.22, 0.47, 0.72)]
        v_lanes = [int(width * ratio) for ratio in (0.18, 0.42, 0.70, 0.88)]

        for car in self.background_cars:
            speed = car["speed"]
            phase = car["phase"]
            color = car["color"]
            scale = car["size"]
            if car["orientation"] == "h":
                y = h_lanes[car["lane"] % len(h_lanes)] + (-8 if car["lane"] % 2 == 0 else 8)
                travel = width + 70
                x = ((ticks * speed + phase * travel) % travel) - 35
                if car["reverse"]:
                    x = width - x
                self.draw_background_car(surface, x, y, color, scale, horizontal=True)
            else:
                x = v_lanes[car["lane"] % len(v_lanes)] + (-8 if car["lane"] % 2 == 0 else 8)
                travel = height + 70
                y = ((ticks * speed + phase * travel) % travel) - 35
                if car["reverse"]:
                    y = height - y
                self.draw_background_car(surface, x, y, color, scale, horizontal=False)

    def draw_background_car(self, surface, x, y, color, scale=1.0, horizontal=True):
        length = int(22 * scale)
        width = int(11 * scale)
        if horizontal:
            rect = pygame.Rect(0, 0, length, width)
        else:
            rect = pygame.Rect(0, 0, width, length)
        rect.center = (int(x), int(y))
        pygame.draw.rect(surface, (0, 0, 0, 85), rect.move(2, 2), border_radius=4)
        pygame.draw.rect(surface, (*color, 210), rect, border_radius=4)
        pygame.draw.rect(surface, (245, 245, 250, 120), rect, 1, border_radius=4)
        if horizontal:
            pygame.draw.rect(surface, (165, 220, 245, 170), (rect.x + 5, rect.y + 2, max(4, rect.w - 10), 3), border_radius=1)
        else:
            pygame.draw.rect(surface, (165, 220, 245, 170), (rect.x + 2, rect.y + 5, 3, max(4, rect.h - 10)), border_radius=1)

    def create_menu_ui(self):
        cx = SCREEN_WIDTH // 2
        self.menu_buttons = [
            Button((cx - 145, 405, 290, 54), "BẮT ĐẦU", self.font, self.start_crisis, icon="play"),
            Button((cx - 145, 475, 290, 54), "THOÁT", self.font, self.quit_game, icon="close"),
        ]

    def create_planning_ui(self):
        x = PANEL_X + 22
        self.dispatch_dropdown = Dropdown((x, 184, 342, 34), DISPATCH_ALGORITHMS, self.small_font, "Điều xe", display_labels=ALGORITHM_LABELS)
        self.priority_dropdown = Dropdown((x, 254, 342, 34), PRIORITY_ALGORITHMS, self.small_font, "Ưu tiên", display_labels=ALGORITHM_LABELS)
        self.route_dropdown = Dropdown((x, 324, 342, 34), ROUTE_ALGORITHMS, self.small_font, "Đường đi", display_labels=ALGORITHM_LABELS)
        self.risk_dropdown = Dropdown((x, 394, 342, 34), RISK_ALGORITHMS, self.small_font, "Rủi ro", display_labels=ALGORITHM_LABELS)

        # Sensible default combo.
        self.dispatch_dropdown.set_selected("AC3 Search")
        self.priority_dropdown.set_selected("Simulated Annealing")
        self.route_dropdown.set_selected("A*")
        self.risk_dropdown.set_selected("Belief State Search")

        self.speed_slider = Slider((x, 570, 342, 24), 1, 12, 3, self.small_font, "Tốc độ mô phỏng", self.set_speed)
        self.details_button = Button((x, 598, 78, 24), "AI", self.small_font, self.open_details_modal, icon="info")
        self.legend_button = Button((x + 88, 598, 78, 24), "KÝ HIỆU", self.small_font, self.toggle_legend, icon="legend")
        self.route_nodes_button = Button((x + 176, 598, 78, 24), "LAN", self.small_font, self.toggle_visited_nodes, icon="nodes")
        self.truck_menu_button = Button((x + 264, 598, 78, 24), "XE", self.small_font, self.open_truck_modal, icon="truck")

        self.plan_buttons = [
            Button((x, 625, 165, 38), "CHẠY", self.font, self.execute_plan, icon="play"),
            Button((x + 177, 625, 165, 38), "SO SÁNH", self.font, self.compare_combos, icon="compare"),
            Button((x, 674, 165, 38), "THỬ LẠI", self.font, self.retry_map, icon="retry"),
            Button((x + 177, 674, 165, 38), "MENU", self.font, self.to_menu, icon="menu"),
        ]

    def create_result_ui(self):
        x = PANEL_X + 22
        self.result_buttons = [
            Button((x, 650, 165, 38), "THỬ LẠI", self.font, self.retry_map, icon="retry"),
            Button((x + 177, 650, 165, 38), "NEXT MAP", self.font, self.start_crisis, icon="map"),
            Button((x, 698, 165, 38), "XEM", self.font, self.review_result, icon="plan"),
            Button((x + 177, 698, 165, 38), "MENU", self.font, self.to_menu, icon="menu"),
        ]
        modal_w, modal_h = 560, 360
        modal_x = (MAP_WIDTH - modal_w) // 2
        modal_y = (SCREEN_HEIGHT - modal_h) // 2
        self.result_modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        btn_y = modal_y + modal_h - 62
        self.result_modal_buttons = [
            Button((modal_x + 36, btn_y, 150, 38), "THỬ LẠI", self.font, self.retry_map, icon="retry"),
            Button((modal_x + 205, btn_y, 150, 38), "NEXT MAP", self.font, self.start_crisis, icon="map"),
            Button((modal_x + 374, btn_y, 150, 38), "XEM", self.font, self.review_result, icon="plan"),
        ]
        self.details_close_button = Button((SCREEN_WIDTH // 2 - 82, 650, 165, 38), "ĐÓNG", self.font, self.close_details_modal, icon="close")
        self.truck_close_button = Button((SCREEN_WIDTH // 2 - 82, 650, 165, 38), "ĐÓNG", self.font, self.close_truck_modal, icon="close")

    def set_speed(self, value):
        self.close_fire_info()
        self.animation_speed = value

    def toggle_visited_nodes(self):
        self.close_open_menus()
        self.show_visited_nodes = not self.show_visited_nodes

    def toggle_legend(self):
        self.close_open_menus()
        self.show_legend = not self.show_legend

    def open_details_modal(self):
        if not self.report:
            return
        if self.show_truck_modal:
            self.close_truck_modal()
        self.close_fire_info()
        self.show_details_modal = True
        self.details_scroll = 0

    def close_details_modal(self):
        self.show_details_modal = False

    def open_truck_modal(self):
        self.close_fire_info()
        self.show_details_modal = False
        self.show_truck_modal = True
        self.truck_slider_drag = None
        if self.truck_close_button:
            self.truck_close_button.rect = pygame.Rect(1035, 77, 125, 34)

    def close_truck_modal(self):
        self.commit_truck_text_edit()
        self.show_truck_modal = False
        self.truck_slider_drag = None
        self.truck_edit_key = None
        if self.truck_specs_dirty and self.state == STATE_PLANNING and self.planner:
            self.planner.reset_cache()
            self.benchmark_score, self.pass_score, self.best_report, tested, elapsed = self.planner.estimate_benchmark()
            self.benchmark_info = f"AI kiểm thử: {tested} tổ hợp trong {elapsed:.2f}s"
        self.truck_specs_dirty = False

    def close_fire_info(self):
        self.selected_fire = None
        self.fire_info_rect = None

    def close_open_menus(self):
        self.show_details_modal = False
        if self.show_truck_modal:
            self.close_truck_modal()
        self.close_fire_info()

    def reset_map_camera(self):
        self.map_zoom = 1.0
        self.map_camera_x = 0.0
        self.map_camera_y = 0.0

    def clamp_map_camera(self):
        self.map_zoom = max(self.map_min_zoom, min(self.map_max_zoom, self.map_zoom))
        view_w = MAP_WIDTH / self.map_zoom
        view_h = MAP_HEIGHT / self.map_zoom
        max_x = max(0.0, MAP_WIDTH - view_w)
        max_y = max(0.0, MAP_HEIGHT - view_h)
        self.map_camera_x = max(0.0, min(max_x, self.map_camera_x))
        self.map_camera_y = max(0.0, min(max_y, self.map_camera_y))

    def screen_to_map(self, pos):
        x, y = pos
        if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT):
            return None
        return (
            self.map_camera_x + x / self.map_zoom,
            self.map_camera_y + y / self.map_zoom,
        )

    def map_to_screen(self, point):
        x, y = point
        return (
            (x - self.map_camera_x) * self.map_zoom,
            (y - self.map_camera_y) * self.map_zoom,
        )

    def fire_screen_center(self, fire):
        return self.map_to_screen((
            fire.cell[1] * TILE_SIZE + TILE_SIZE // 2,
            fire.cell[0] * TILE_SIZE + TILE_SIZE // 2,
        ))

    def handle_map_zoom_event(self, event):
        if self.state == STATE_MENU or event.type != pygame.MOUSEWHEEL:
            return False
        if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
            return False
        if self.show_details_modal or self.show_truck_modal:
            return False

        mouse_pos = pygame.mouse.get_pos()
        map_pos = self.screen_to_map(mouse_pos)
        if map_pos is None:
            return False
        if not self.reviewing_result and self.state == STATE_RESULT and self.result_modal_rect and self.result_modal_rect.collidepoint(mouse_pos):
            return False
        if self.selected_fire and self.fire_info_rect and self.fire_info_rect.collidepoint(mouse_pos):
            return False

        old_zoom = self.map_zoom
        factor = 1.12 ** event.y
        self.map_zoom = max(self.map_min_zoom, min(self.map_max_zoom, self.map_zoom * factor))
        if abs(self.map_zoom - old_zoom) < 0.001:
            return True

        self.map_camera_x = map_pos[0] - mouse_pos[0] / self.map_zoom
        self.map_camera_y = map_pos[1] - mouse_pos[1] / self.map_zoom
        self.clamp_map_camera()
        return True

    def details_modal_rect(self):
        return pygame.Rect(145, 70, 990, 650)

    def truck_modal_rect(self):
        return pygame.Rect(90, 55, 1100, 670)

    def draw_details_button(self):
        if not self.details_button or not self.report:
            return
        self.details_button.draw(self.screen, active=self.show_details_modal)

    def draw_route_nodes_button(self):
        if not self.route_nodes_button:
            return
        self.route_nodes_button.draw(self.screen, active=self.show_visited_nodes)

    def draw_legend_button(self):
        if not self.legend_button:
            return
        self.legend_button.draw(self.screen, active=self.show_legend)

    def draw_truck_menu_button(self):
        if not self.truck_menu_button:
            return
        self.truck_menu_button.draw(self.screen, active=self.show_truck_modal)

    def new_crisis(self):
        self.reset_map_camera()
        self.city_map = CityMap(self.asset_loader)
        self.planner = CrisisPlanner(self.city_map)
        self.benchmark_score, self.pass_score, self.best_report, tested, elapsed = self.planner.estimate_benchmark()
        self.benchmark_info = f"AI kiểm thử: {tested} tổ hợp trong {elapsed:.2f}s"
        self.report = None
        self.compare_reports = []
        self.reviewing_result = False
        self.selected_fire = None
        self.fire_info_rect = None
        self.create_trucks()
        self.reset_execution_state()
        self.planning_started_at = time.perf_counter()

    def start_crisis(self):
        self.close_open_menus()
        self.new_crisis()
        self.state = STATE_PLANNING

    def random_map_menu(self):
        self.close_open_menus()
        self.new_crisis()
        self.state = STATE_PLANNING

    def retry_map(self):
        self.close_open_menus()
        self.report = None
        self.compare_reports = []
        self.reviewing_result = False
        self.create_trucks()
        self.reset_execution_state()
        self.planning_started_at = time.perf_counter()
        self.state = STATE_PLANNING

    def back_to_planning(self):
        self.close_open_menus()
        self.reviewing_result = False
        self.create_trucks()
        self.reset_execution_state()
        self.planning_started_at = time.perf_counter()
        self.state = STATE_PLANNING

    def review_result(self):
        if not self.report:
            self.back_to_planning()
            return
        self.close_open_menus()
        self.reviewing_result = True
        self.create_trucks()
        self.reset_execution_state()
        self.apply_report_paths_to_trucks()
        self.execution_done = True
        self.visited_visible = len(self.report.route_visited)
        self.path_visible = self.max_route_path_length()
        self.freeze_trucks_at_route_end()
        self.state = STATE_RESULT

    def to_menu(self):
        self.close_open_menus()
        self.reviewing_result = False
        self.state = STATE_MENU

    def quit_game(self):
        self.running = False

    def create_trucks(self):
        self.trucks = []
        for i, spec in enumerate(self.city_map.stations):
            color = self.truck_colors[i % len(self.truck_colors)]
            self.trucks.append(AnimatedTruck(spec, self.asset_loader, i, color=color))

    def reset_execution_state(self):
        self.execution_started_at = None
        self.execution_done = False
        self.visited_visible = 0
        self.path_visible = 0
        self.visible_logs = []
        for truck in self.trucks:
            truck.reset()

    def freeze_trucks_at_route_end(self):
        for truck in self.trucks:
            path = truck.path or [truck.spec.start]
            last = path[-1]
            truck.path = path
            truck.path_index = len(path)
            truck.cell = last
            if len(path) > 1:
                truck.x, truck.y = lane_center_for_direction(
                    last,
                    direction_between(path[-2], path[-1]),
                    truck.lane_slot,
                    ROUTE_LANE_COUNT,
                )
            else:
                truck.x = last[1] * TILE_SIZE + TILE_SIZE // 2
                truck.y = last[0] * TILE_SIZE + TILE_SIZE // 2
            truck.target_x = truck.x
            truck.target_y = truck.y
            truck.finished = True

    def apply_report_paths_to_trucks(self):
        if not self.report:
            return
        active_plans = [plan for plan in self.report.truck_plans.values() if len(plan.full_path) > 1]
        for truck in self.trucks:
            plan = self.report.truck_plans.get(truck.spec.id)
            if plan:
                active_index = next((index for index, item in enumerate(active_plans) if item.truck_id == plan.truck_id), truck.spec.station_index)
                truck.lane_slot = distributed_lane_slot(active_index, len(active_plans), ROUTE_LANE_COUNT)
                truck.set_path(plan.full_path)

    def selected_choice(self):
        return ComboChoice(
            self.dispatch_dropdown.selected,
            self.priority_dropdown.selected,
            self.route_dropdown.selected,
            self.risk_dropdown.selected,
        )

    def planning_seconds_used(self):
        return int(time.perf_counter() - self.planning_started_at)

    def planning_seconds_left(self):
        return max(0, PLANNING_SECONDS - self.planning_seconds_used())

    def execute_plan(self, timed_out=False, instant_result=False):
        used_seconds = self.planning_seconds_used()
        timed_out = timed_out or used_seconds >= PLANNING_SECONDS
        instant_result = instant_result or timed_out
        self.close_open_menus()
        choice = self.selected_choice()
        self.report = self.planner.build_plan(
            choice,
            planning_seconds_used=max(used_seconds, PLANNING_SECONDS if timed_out else used_seconds),
            benchmark_score=self.benchmark_score,
            pass_score=self.pass_score,
            timed_out=timed_out,
        )
        self.create_trucks()
        self.reset_execution_state()
        self.apply_report_paths_to_trucks()
        self.show_details_modal = False
        self.reviewing_result = False
        self.execution_started_at = time.perf_counter()
        if instant_result:
            self.execution_done = True
            self.visited_visible = len(self.report.route_visited)
            self.path_visible = self.max_route_path_length()
            self.state = STATE_RESULT
        else:
            self.state = STATE_EXECUTING

    def compare_combos(self):
        self.close_open_menus()
        self.compare_reports = self.planner.compare_current_map()

    def all_trucks_finished(self):
        return all(t.finished for t in self.trucks)

    def update(self):
        if self.state == STATE_PLANNING:
            if self.planning_seconds_left() <= 0:
                self.execute_plan(timed_out=True, instant_result=True)
            return
        if self.state != STATE_EXECUTING:
            return
        if self.report:
            self.visited_visible = min(len(self.report.route_visited), self.visited_visible + self.animation_speed * 4)
            self.path_visible = min(self.max_route_path_length(), self.path_visible + self.animation_speed)
            for truck in self.trucks:
                truck.update(self.animation_speed)
            if self.all_trucks_finished():
                self.execution_done = True
                self.state = STATE_RESULT

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.KEYDOWN:
                if self.show_truck_modal and event.key == pygame.K_ESCAPE:
                    self.close_truck_modal()
                    continue
                if self.show_details_modal and event.key == pygame.K_ESCAPE:
                    self.close_details_modal()
                    continue
                alt_enter = event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT
                if event.key == pygame.K_F11 or alt_enter:
                    self.toggle_fullscreen()
                    continue
            if self.show_truck_modal:
                if self.handle_truck_modal_event(event):
                    return
                if event.type in (pygame.KEYDOWN, pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    continue
            if self.show_details_modal:
                if event.type == pygame.KEYDOWN:
                    continue
                if event.type == pygame.MOUSEWHEEL:
                    self.scroll_details(-event.y * 3)
                    continue
                if self.details_close_button and self.details_close_button.handle_event(event):
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if not self.details_modal_rect().collidepoint(event.pos):
                        self.close_details_modal()
                        return
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    continue
            if self.handle_map_zoom_event(event):
                continue
            if self.handle_fire_info_event(event):
                return
            if self.state == STATE_MENU:
                for btn in self.menu_buttons:
                    btn.handle_event(event)
            elif self.state == STATE_PLANNING:
                # Dropdowns first so buttons do not steal clicks.
                for dd in [self.dispatch_dropdown, self.priority_dropdown, self.route_dropdown, self.risk_dropdown]:
                    if dd.handle_event(event):
                        return
                if self.speed_slider.handle_event(event):
                    return
                if self.legend_button and self.legend_button.handle_event(event):
                    return
                if self.route_nodes_button and self.route_nodes_button.handle_event(event):
                    return
                if self.truck_menu_button and self.truck_menu_button.handle_event(event):
                    return
                for btn in self.plan_buttons:
                    btn.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.execute_plan()
                    elif event.key == pygame.K_c:
                        self.compare_combos()
                    elif event.key == pygame.K_r:
                        self.start_crisis()
                    elif event.key == pygame.K_ESCAPE:
                        self.to_menu()
                    elif event.key == pygame.K_1:
                        self.dispatch_dropdown.next()
                    elif event.key == pygame.K_2:
                        self.priority_dropdown.next()
                    elif event.key == pygame.K_3:
                        self.route_dropdown.next()
                    elif event.key == pygame.K_4:
                        self.risk_dropdown.next()
            elif self.state == STATE_EXECUTING:
                if self.speed_slider.handle_event(event):
                    return
                if self.details_button and self.details_button.handle_event(event):
                    return
                if self.legend_button and self.legend_button.handle_event(event):
                    return
                if self.route_nodes_button and self.route_nodes_button.handle_event(event):
                    return
                if self.truck_menu_button and self.truck_menu_button.handle_event(event):
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = STATE_RESULT
            elif self.state == STATE_RESULT:
                if not self.reviewing_result:
                    for btn in self.result_modal_buttons:
                        if btn.handle_event(event):
                            return
                if self.details_button and self.details_button.handle_event(event):
                    return
                if self.legend_button and self.legend_button.handle_event(event):
                    return
                if self.route_nodes_button and self.route_nodes_button.handle_event(event):
                    return
                if self.truck_menu_button and self.truck_menu_button.handle_event(event):
                    return
                for btn in self.result_buttons:
                    btn.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.retry_map()
                    elif event.key == pygame.K_ESCAPE:
                        self.to_menu()

    def handle_fire_info_event(self, event):
        if self.state == STATE_MENU or not self.city_map:
            return False
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        pos = event.pos
        if self.selected_fire:
            rect = self.fire_info_card_rect(self.selected_fire)
            close_rect = pygame.Rect(rect.right - 30, rect.y + 10, 20, 20)
            if close_rect.collidepoint(pos):
                self.selected_fire = None
                self.fire_info_rect = None
                return True
            if rect.collidepoint(pos):
                return True

        if not self.reviewing_result and self.state == STATE_RESULT and self.result_modal_rect and self.result_modal_rect.collidepoint(pos):
            self.close_fire_info()
            return False

        map_pos = self.screen_to_map(pos)
        if map_pos is not None:
            truck = self.truck_at_pos(map_pos)
            if truck:
                self.open_truck_modal()
                return True
            fire = self.fire_at_pos(map_pos)
            if fire:
                self.select_fire(fire)
                return True
            if self.selected_fire:
                self.selected_fire = None
                self.fire_info_rect = None
                return True
        elif self.selected_fire:
            self.close_fire_info()
        return False

    def fire_at_pos(self, pos):
        row = int(pos[1] // TILE_SIZE)
        col = int(pos[0] // TILE_SIZE)
        for fire in self.city_map.fires:
            if fire.cell == (row, col):
                return fire
        for fire in self.city_map.fires:
            cx = fire.cell[1] * TILE_SIZE + TILE_SIZE // 2
            cy = fire.cell[0] * TILE_SIZE + TILE_SIZE // 2
            if math.hypot(pos[0] - cx, pos[1] - cy) <= 24:
                return fire
        return None

    def truck_at_pos(self, pos):
        if not (0 <= pos[0] < MAP_WIDTH and 0 <= pos[1] < MAP_HEIGHT):
            return None
        for truck in reversed(self.trucks):
            if math.hypot(pos[0] - truck.x, pos[1] - truck.y) <= 18:
                return truck
        return None

    def select_fire(self, fire):
        self.selected_fire = fire
        self.fire_info_rect = self.fire_info_card_rect(fire)
        for index, item in enumerate(self.city_map.fires):
            if item.id == fire.id:
                self.city_map.selected_fire_index = index
                break

    def handle_truck_modal_event(self, event):
        if self.truck_close_button and self.truck_close_button.handle_event(event):
            return True
        if self.truck_edit_key and event.type == pygame.KEYDOWN:
            return self.handle_truck_text_key(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.truck_modal_rect().collidepoint(event.pos):
                self.close_truck_modal()
                return True
            for key, rect in self.truck_input_rects.items():
                if rect.collidepoint(event.pos):
                    self.start_truck_text_edit(key)
                    return True
            if self.truck_edit_key:
                self.commit_truck_text_edit()
            for key, rect in self.truck_slider_hit_rects.items():
                if rect.collidepoint(event.pos):
                    self.truck_slider_drag = key
                    self.update_truck_slider_from_x(key, event.pos[0])
                    return True
        if event.type == pygame.MOUSEMOTION and self.truck_slider_drag:
            self.update_truck_slider_from_x(self.truck_slider_drag, event.pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.truck_slider_drag:
                self.update_truck_slider_from_x(self.truck_slider_drag, event.pos[0])
                self.truck_slider_drag = None
                return True
        return False

    def start_truck_text_edit(self, key):
        self.truck_slider_drag = None
        self.truck_edit_key = key
        self.truck_edit_text = str(self.truck_setting_value(*key))
        self.truck_edit_select_all = True

    def handle_truck_text_key(self, event):
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.commit_truck_text_edit()
            return True
        if event.key == pygame.K_ESCAPE:
            self.truck_edit_key = None
            self.truck_edit_text = ""
            self.truck_edit_select_all = False
            return True
        if event.key == pygame.K_BACKSPACE:
            if self.truck_edit_select_all:
                self.truck_edit_text = ""
                self.truck_edit_select_all = False
            else:
                self.truck_edit_text = self.truck_edit_text[:-1]
            self.apply_truck_edit_text()
            return True
        if event.unicode and event.unicode.isdigit():
            if self.truck_edit_select_all:
                self.truck_edit_text = ""
                self.truck_edit_select_all = False
            if len(self.truck_edit_text) < 3:
                self.truck_edit_text += event.unicode
                self.apply_truck_edit_text()
            return True
        return True

    def apply_truck_edit_text(self):
        if not self.truck_edit_key or not self.truck_edit_text.strip():
            return
        index, field = self.truck_edit_key
        min_value, max_value = self.truck_setting_range(field)
        value = max(min_value, min(max_value, int(self.truck_edit_text)))
        self.set_truck_setting(index, field, value)

    def commit_truck_text_edit(self):
        if not self.truck_edit_key:
            return
        text = self.truck_edit_text.strip()
        if text:
            index, field = self.truck_edit_key
            min_value, max_value = self.truck_setting_range(field)
            value = max(min_value, min(max_value, int(text)))
            self.set_truck_setting(index, field, value)
        self.truck_edit_key = None
        self.truck_edit_text = ""
        self.truck_edit_select_all = False

    def update_truck_slider_from_x(self, key, x):
        rect = self.truck_slider_rects.get(key)
        if not rect:
            return
        index, field = key
        min_value, max_value = self.truck_setting_range(field)
        x = max(rect.left, min(rect.right, x))
        ratio = (x - rect.left) / max(1, rect.width)
        value = int(round(min_value + ratio * (max_value - min_value)))
        self.set_truck_setting(index, field, value)

    def truck_setting_range(self, field):
        if field == "speed":
            return 1, 5
        if field == "water":
            return 30, 180
        return 0, 255

    def truck_setting_value(self, index, field):
        spec = self.city_map.stations[index]
        if field == "speed":
            return spec.speed
        if field == "water":
            return spec.water
        channel = {"r": 0, "g": 1, "b": 2}[field]
        return self.truck_colors[index][channel]

    def set_truck_setting(self, index, field, value):
        if index >= len(self.city_map.stations):
            return
        spec = self.city_map.stations[index]
        if field == "speed":
            spec.speed = value
            self.truck_specs_dirty = True
            if index < len(self.trucks):
                self.trucks[index].speed_px = 4 + value
            return
        if field == "water":
            spec.water = value
            spec.capacity = value
            self.truck_specs_dirty = True
            return
        channel = {"r": 0, "g": 1, "b": 2}[field]
        color = list(self.truck_colors[index])
        color[channel] = value
        self.truck_colors[index] = tuple(color)
        if index < len(self.trucks):
            self.trucks[index].color = self.truck_colors[index]

    def draw(self):
        if self.state == STATE_MENU:
            self.draw_menu()
        else:
            self.draw_game_world()
            self.draw_panel()
            if self.state == STATE_RESULT and not self.reviewing_result:
                self.draw_result_modal()
            if self.selected_fire:
                self.draw_fire_info_card()
            if self.show_details_modal:
                self.draw_details_modal()
            if self.show_truck_modal:
                self.draw_truck_modal()
            self.draw_map_hover_tooltip()
        pygame.display.flip()

    def draw_menu(self):
        bg = self.asset_loader.get("start_bg")
        if bg:
            self.screen.blit(pygame.transform.scale(bg, (SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))
        else:
            self.draw_dynamic_background(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), dark_overlay=70)
        title = self.title_font.render("MÃ ĐỎ: CHỈ HUY XE CỨU HỎA AI", True, WHITE)
        subtitle = self.font.render("Chọn thuật toán, điều xe và vượt điểm chuẩn của bản đồ.", True, TEXT_MUTED)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 175)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 225)))
        lines = [
            "Bạn là trung tâm điều phối khẩn cấp.",
            "Mỗi bản đồ có nhiều đám cháy, xe cứu hỏa, kẹt xe, đường rủi ro và điểm qua màn.",
            "Hãy chọn AI điều xe, ưu tiên, tìm đường và xử lý rủi ro trước khi hết giờ.",
            "Trò chơi sẽ mô phỏng xe và hiển thị kết quả của các thuật toán.",
        ]
        y = 275
        for line in lines:
            surf = self.small_font.render(line, True, TEXT_MUTED)
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, y)))
            y += 25
        for btn in self.menu_buttons:
            btn.draw(self.screen)

    def draw_game_world(self):
        map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
        original_screen = self.screen
        self.screen = map_surface
        try:
            self.draw_game_world_contents()
        finally:
            self.screen = original_screen

        self.screen.fill(DARK_BG)
        self.blit_map_surface(map_surface)
        if self.show_legend:
            self.draw_map_legend()

    def draw_game_world_contents(self):
        self.screen.fill(DARK_BG)
        extinguished_fires = self.current_extinguished_fires() if self.report else set()
        hover_highlight = self.hovered_fire_highlight(extinguished_fires)
        self.city_map.draw(self.screen, extinguished_fires=extinguished_fires, draw_fire_effects=False)
        self.draw_algorithm_overlay()
        self.city_map.draw_road_symbols(self.screen)
        if hover_highlight:
            self.draw_fire_route_highlight(hover_highlight)
        self.city_map.draw_fire_labels(self.screen, extinguished_fires)
        self.city_map.draw_selected_fire(self.screen)
        for truck in self.trucks:
            truck.draw(self.screen)

    def blit_map_surface(self, map_surface):
        self.clamp_map_camera()
        if self.map_zoom <= 1.001:
            self.screen.blit(map_surface, (0, 0))
            return

        view_w = max(1, int(round(MAP_WIDTH / self.map_zoom)))
        view_h = max(1, int(round(MAP_HEIGHT / self.map_zoom)))
        source_x = max(0, min(MAP_WIDTH - view_w, int(round(self.map_camera_x))))
        source_y = max(0, min(MAP_HEIGHT - view_h, int(round(self.map_camera_y))))
        source_rect = pygame.Rect(source_x, source_y, view_w, view_h)
        view = map_surface.subsurface(source_rect)
        scaled = pygame.transform.smoothscale(view, (MAP_WIDTH, MAP_HEIGHT))
        self.screen.blit(scaled, (0, 0))

    def draw_map_legend(self):
        items = [
            ("S", "Trạm xe", STATION_COLOR, WHITE),
            ("HYDRANT_ICON", "Trụ nước", HYDRANT_COLOR, BLACK),
            ("F1", "Đám cháy", FIRE_COLOR, WHITE),
            ("H", "Bệnh viện", HOSPITAL_COLOR, WHITE),
            ("G", "Trạm xăng", GAS_COLOR, WHITE),
            ("TRAFFIC_ICON", "Kẹt xe", TRAFFIC_COLOR, BLACK),
            ("X", "Đường chặn", BLOCKED_COLOR, WHITE),
            ("?", "Đường rủi ro", RISKY_COLOR, BLACK),
            ("T1", "Xe cứu hỏa", self.truck_colors[0], WHITE),
            ("--", "Dự phòng", ALT_PATH_COLOR, BLACK),
        ]
        rect = pygame.Rect(12, MAP_HEIGHT - 176, 292, 164)
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (18, 18, 26, 218), surface.get_rect(), border_radius=8)
        pygame.draw.rect(surface, (94, 94, 112, 180), surface.get_rect(), 1, border_radius=8)

        title = self.small_font.render("BẢNG KÝ HIỆU", True, CYAN)
        surface.blit(title, (12, 10))

        col_w = 136
        row_h = 23
        start_y = 38
        for index, item in enumerate(items):
            col = index // 5
            row = index % 5
            x = 12 + col * col_w
            y = start_y + row * row_h
            self.draw_legend_marker(surface, pygame.Rect(x, y + 1, 22, 18), item[0], item[2], item[3])
            label = self.tiny_font.render(item[1], True, WHITE)
            surface.blit(label, (x + 30, y + 3))

        self.screen.blit(surface, rect.topleft)

    def hovered_fire_highlight(self, extinguished_fires=None):
        if not self.report or self.state not in (STATE_EXECUTING, STATE_RESULT):
            return None
        if self.show_details_modal or self.show_truck_modal:
            return None

        screen_pos = pygame.mouse.get_pos()
        map_pos = self.screen_to_map(screen_pos)
        if map_pos is None:
            return None
        if not self.reviewing_result and self.state == STATE_RESULT and self.result_modal_rect and self.result_modal_rect.collidepoint(screen_pos):
            return None
        if self.selected_fire and self.fire_info_rect and self.fire_info_rect.collidepoint(screen_pos):
            return None

        fire = self.fire_at_pos(map_pos)
        if not fire:
            legend_rect = pygame.Rect(12, MAP_HEIGHT - 176, 292, 164)
            if self.show_legend and legend_rect.collidepoint(screen_pos):
                return None
            return None
        extinguished_fires = extinguished_fires if extinguished_fires is not None else self.current_extinguished_fires()
        if fire.id not in extinguished_fires:
            return None

        plans = self.fire_highlight_plans(fire.id)
        if not plans:
            return None
        return {
            "fire": fire,
            "plans": plans,
            "truck_ids": {plan.truck_id for plan, _paths in plans},
        }

    def fire_highlight_plans(self, fire_id):
        plans = []
        if not self.report:
            return plans
        for plan in self.report.truck_plans.values():
            if fire_id not in plan.arrival_times:
                continue
            paths = self.fire_route_paths(plan, fire_id)
            if paths:
                plans.append((plan, paths))
        return plans

    def fire_route_paths(self, plan, fire_id):
        end_index = self.fire_segment_end_index(plan, fire_id)
        if end_index is None or len(plan.full_path) < 2:
            return []
        end_index = min(end_index, len(plan.full_path) - 1)
        if end_index < 1:
            return []
        return [plan.full_path[:end_index + 1]]

    def route_slot_for_plan(self, truck_id):
        active_plans = [plan for plan in self.report.truck_plans.values() if len(plan.full_path) > 1]
        for index, plan in enumerate(active_plans):
            if plan.truck_id == truck_id:
                return distributed_lane_slot(index, len(active_plans), ROUTE_LANE_COUNT), ROUTE_LANE_COUNT
        return distributed_lane_slot(0, 1, ROUTE_LANE_COUNT), ROUTE_LANE_COUNT

    def draw_fire_route_highlight(self, highlight):
        route_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)
        ticks = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(ticks * 0.012)
        alpha = int(205 + 35 * pulse)

        for fallback_index, (plan, paths) in enumerate(highlight["plans"]):
            slot_index, slot_count = self.route_slot_for_plan(plan.truck_id)
            color = self.route_color_for_truck(plan.truck_id, fallback_index)
            for path_index, path in enumerate(paths):
                self.draw_emphasized_parallel_path(
                    route_surface,
                    path,
                    color,
                    slot_index,
                    slot_count,
                    alpha=alpha,
                )

        self.screen.blit(route_surface, (0, 0))

    def draw_hovered_fire_marker(self, highlight):
        fire = highlight["fire"]
        ticks = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(ticks * 0.014)
        x = fire.cell[1] * TILE_SIZE
        y = fire.cell[0] * TILE_SIZE
        cx = x + TILE_SIZE // 2
        cy = y + TILE_SIZE // 2

        marker = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2), pygame.SRCALPHA)
        center = (TILE_SIZE, TILE_SIZE)
        pygame.draw.circle(marker, (255, 235, 95, int(42 + 28 * pulse)), center, int(19 + 2 * pulse))
        pygame.draw.circle(marker, (95, 216, 255, int(36 + 24 * pulse)), center, int(14 + 2 * pulse), 2)
        self.screen.blit(marker, (cx - center[0], cy - center[1]))

        rect = pygame.Rect(x - 2, y - 2, TILE_SIZE + 4, TILE_SIZE + 4)
        pygame.draw.rect(self.screen, YELLOW, rect, 2, border_radius=7)

        truck_text = ",".join(sorted(highlight["truck_ids"]))
        if truck_text:
            badge = self.tiny_font.render(truck_text, True, WHITE)
            badge_rect = badge.get_rect(center=(cx, max(12, y - 10)))
            pygame.draw.rect(self.screen, (10, 10, 16), badge_rect.inflate(8, 4), border_radius=4)
            pygame.draw.rect(self.screen, YELLOW, badge_rect.inflate(8, 4), 1, border_radius=4)
            self.screen.blit(badge, badge_rect)

    def draw_truck_hover_halo(self, truck):
        ticks = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(ticks * 0.016 + truck.spec.station_index)
        cx, cy = int(truck.x), int(truck.y)
        size = 44
        halo = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)
        color = truck.color
        pygame.draw.ellipse(halo, (0, 0, 0, 105), (8, 29, 28, 9))
        pygame.draw.circle(halo, (*color, int(42 + 34 * pulse)), center, int(15 + 2 * pulse))
        pygame.draw.circle(halo, (255, 255, 255, 190), center, int(14 + pulse), 1)
        pygame.draw.circle(halo, YELLOW, center, int(18 + 2 * pulse), 2)
        self.screen.blit(halo, (cx - center[0], cy - center[1]))

    def draw_legend_marker(self, surface, rect, symbol, fill_color, text_color):
        if symbol == "--":
            pygame.draw.line(surface, (10, 10, 16), (rect.left + 2, rect.centery), (rect.right - 2, rect.centery), 4)
            x = rect.left + 2
            while x < rect.right - 2:
                pygame.draw.line(surface, fill_color, (x, rect.centery), (min(x + 6, rect.right - 2), rect.centery), 2)
                x += 10
            return
        if symbol == "HYDRANT_ICON":
            cx, cy = rect.center
            pygame.draw.ellipse(surface, (20, 20, 24), (cx - 5, cy + 5, 10, 3))
            pygame.draw.rect(surface, (180, 24, 28), (cx - 4, cy - 3, 8, 11), border_radius=2)
            pygame.draw.circle(surface, (224, 42, 45), (cx, cy - 5), 4)
            pygame.draw.rect(surface, (124, 16, 22), (cx - 7, cy, 14, 4), border_radius=2)
            pygame.draw.circle(surface, (245, 225, 120), (cx - 6, cy + 2), 2)
            pygame.draw.circle(surface, (245, 225, 120), (cx + 6, cy + 2), 2)
            return
        if symbol == "TRAFFIC_ICON":
            cars = [
                (rect.left + 1, rect.top + 4, 10, 6, (226, 52, 54)),
                (rect.left + 8, rect.top + 10, 10, 6, (70, 148, 232)),
                (rect.left + 13, rect.top + 3, 8, 6, (238, 202, 70)),
            ]
            for x, y, width, height, color in cars:
                car = pygame.Rect(x, y, width, height)
                pygame.draw.rect(surface, (18, 18, 22), car.move(1, 1), border_radius=2)
                pygame.draw.rect(surface, color, car, border_radius=2)
                pygame.draw.rect(surface, (245, 245, 248), car, 1, border_radius=2)
            return
        pygame.draw.rect(surface, fill_color, rect, border_radius=4)
        pygame.draw.rect(surface, (230, 230, 238), rect, 1, border_radius=4)
        text = self.tiny_font.render(symbol, True, text_color)
        surface.blit(text, text.get_rect(center=rect.center))

    def draw_map_hover_tooltip(self):
        if self.state == STATE_MENU or not self.city_map:
            return
        if self.show_details_modal or self.show_truck_modal:
            return
        mouse_pos = pygame.mouse.get_pos()
        map_pos = self.screen_to_map(mouse_pos)
        if map_pos is None:
            return
        if not self.reviewing_result and self.state == STATE_RESULT and self.result_modal_rect and self.result_modal_rect.collidepoint(mouse_pos):
            return
        if self.selected_fire and self.fire_info_rect and self.fire_info_rect.collidepoint(mouse_pos):
            return

        legend_rect = pygame.Rect(12, MAP_HEIGHT - 176, 292, 164)
        if self.show_legend and legend_rect.collidepoint(mouse_pos):
            return

        tooltip = self.map_hover_tooltip(map_pos)
        if not tooltip:
            return
        title, lines, accent = tooltip
        self.draw_tooltip(mouse_pos, title, lines, accent)

    def map_hover_tooltip(self, pos):
        fire = self.fire_at_pos(pos)
        if fire:
            return None

        row = int(pos[1] // TILE_SIZE)
        col = int(pos[0] // TILE_SIZE)
        tile = self.city_map.grid[row][col]
        tooltips = {
            HYDRANT: (
                "Trụ nước",
                [
                    "Điểm nạp nước ven đường.",
                    "Xe cứu hỏa có thể ghé khi thiếu nước.",
                ],
                HYDRANT_COLOR,
            ),
            TRAFFIC: (
                "Kẹt xe",
                [
                    "Cụm xe đang ùn lại trên đường.",
                    "Đi qua đây tốn chi phí và giảm điểm.",
                ],
                TRAFFIC_COLOR,
            ),
            RISKY: (
                "Đường rủi ro",
                [
                    "Tuyến có thể bị sự cố hoặc bị chặn.",
                    "AI rủi ro sẽ cân nhắc tránh hoặc lập dự phòng.",
                ],
                RISKY_COLOR,
            ),
            BLOCKED: (
                "Đường chặn",
                [
                    "Xe không thể đi qua ô này.",
                    "Thuật toán phải tìm tuyến vòng.",
                ],
                BLOCKED_COLOR,
            ),
            STATION: (
                "Trạm xe cứu hỏa",
                [
                    "Điểm xuất phát của một xe cứu hỏa.",
                    "Click vào xe để xem/chỉnh thông số.",
                ],
                STATION_COLOR,
            ),
        }
        return tooltips.get(tile)

    def draw_tooltip(self, mouse_pos, title, lines, accent):
        max_width = 250
        padding = 10
        line_height = 18
        wrapped_lines = []
        for line in lines:
            wrapped_lines.extend(self.wrap_tooltip_line(line, self.tiny_font, max_width - padding * 2))

        title_width = self.small_font.size(title)[0]
        line_width = max([self.tiny_font.size(line)[0] for line in wrapped_lines] + [0])
        width = min(max_width, max(150, title_width + padding * 2, line_width + padding * 2))
        height = padding * 2 + 21 + len(wrapped_lines) * line_height

        x = mouse_pos[0] + 16
        y = mouse_pos[1] + 18
        if x + width > MAP_WIDTH - 8:
            x = mouse_pos[0] - width - 16
        if y + height > MAP_HEIGHT - 8:
            y = mouse_pos[1] - height - 16
        x = max(8, min(x, MAP_WIDTH - width - 8))
        y = max(8, min(y, MAP_HEIGHT - height - 8))

        rect = pygame.Rect(x, y, width, height)
        shadow = rect.move(0, 4)
        pygame.draw.rect(self.screen, (0, 0, 0), shadow, border_radius=7)
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (22, 22, 30, 235), surface.get_rect(), border_radius=7)
        pygame.draw.rect(surface, (*accent, 230), (0, 0, 5, rect.height), border_radius=4)
        pygame.draw.rect(surface, (92, 92, 112, 210), surface.get_rect(), 1, border_radius=7)

        title_surf = self.small_font.render(title, True, accent)
        surface.blit(title_surf, (padding + 4, padding - 1))
        y_text = padding + 24
        for line in wrapped_lines:
            text_surf = self.tiny_font.render(line, True, WHITE)
            surface.blit(text_surf, (padding + 4, y_text))
            y_text += line_height
        self.screen.blit(surface, rect.topleft)

    def wrap_tooltip_line(self, text, font, max_width):
        words = str(text).split()
        if not words:
            return [""]
        lines = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = word
        if current:
            lines.append(current)
        return lines

    def fire_info_card_rect(self, fire):
        width = 310
        height = 306 if self.report else 268
        fire_center = self.fire_screen_center(fire)
        fx = fire_center[0] - TILE_SIZE // 2
        fy = fire_center[1] - TILE_SIZE // 2
        x = fire_center[0] + 24
        if x + width > MAP_WIDTH - 12:
            x = fire_center[0] - width - 24
        y = fire_center[1] - 12
        if y + height > MAP_HEIGHT - 12:
            y = MAP_HEIGHT - height - 12
        y = max(12, y)
        x = max(12, min(x, MAP_WIDTH - width - 12))

        rect = pygame.Rect(x, y, width, height)
        legend_rect = pygame.Rect(12, MAP_HEIGHT - 176, 292, 164)
        if self.show_legend and rect.colliderect(legend_rect):
            y = max(12, legend_rect.top - height - 8)
            rect.y = y
        return rect

    def draw_fire_info_card(self):
        fire = self.selected_fire
        if not fire:
            return
        rect = self.fire_info_card_rect(fire)
        self.fire_info_rect = rect
        fire_center = self.fire_screen_center(fire)
        near_x = max(rect.left, min(rect.right, fire_center[0]))
        near_y = max(rect.top, min(rect.bottom, fire_center[1]))

        pygame.draw.line(self.screen, YELLOW, fire_center, (near_x, near_y), 2)
        pygame.draw.circle(self.screen, YELLOW, fire_center, 13, 2)
        pygame.draw.rect(self.screen, (0, 0, 0), rect.move(0, 6), border_radius=8)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, (112, 112, 132), rect, 1, border_radius=8)

        close_rect = pygame.Rect(rect.right - 30, rect.y + 10, 20, 20)
        self.panel.text(f"ĐÁM CHÁY {fire.id}", rect.x + 14, rect.y + 12, FIRE_COLOR, self.font, max_width=rect.width - 56)
        pygame.draw.rect(self.screen, (55, 55, 68), close_rect, border_radius=5)
        pygame.draw.line(self.screen, DANGER, (close_rect.left + 5, close_rect.top + 5), (close_rect.right - 5, close_rect.bottom - 5), 2)
        pygame.draw.line(self.screen, DANGER, (close_rect.right - 5, close_rect.top + 5), (close_rect.left + 5, close_rect.bottom - 5), 2)

        per_truck = self.fire_required_water(fire)
        total_water = per_truck * fire.required_units
        highlight = pygame.Rect(rect.x + 14, rect.y + 48, rect.width - 28, 44)
        pygame.draw.rect(self.screen, (38, 58, 70), highlight, border_radius=7)
        pygame.draw.rect(self.screen, (86, 124, 146), highlight, 1, border_radius=7)
        self.panel.text("Nước cần dập", highlight.x + 10, highlight.y + 5, TEXT_MUTED, self.tiny_font, max_width=highlight.width - 20)
        water_text = f"{total_water} nước"
        if fire.required_units > 1:
            water_text += f" ({per_truck}/xe)"
        self.panel.text(water_text, highlight.x + 10, highlight.y + 21, CYAN, self.small_font, max_width=highlight.width - 20)

        rows = [
            ("Mức cháy", f"Cấp {fire.severity}/3"),
            ("Số xe cần", f"{fire.required_units} xe"),
            ("Khu vực", self.fire_danger_label(fire.danger_zone)),
            ("Hạn xử lý", f"Lượt {fire.deadline}"),
            ("Điểm cơ bản", str(fire.base_score)),
            ("Xe đủ bình", self.fire_capable_trucks_text(fire)),
        ]
        if self.report:
            rows.extend([
                ("Xe được giao", self.fire_assigned_trucks_text(fire)),
                ("Trạng thái", self.fire_status_text(fire)),
            ])

        y = rect.y + 106
        for label, value in rows:
            self.panel.text(label, rect.x + 16, y, TEXT_MUTED, self.tiny_font, max_width=110)
            self.panel.text(value, rect.x + 128, y, WHITE, self.tiny_font, max_width=rect.width - 146)
            y += 19

        self.panel.text("Nhấn đám cháy khác để đổi.", rect.x + 16, rect.bottom - 23, TEXT_MUTED, self.tiny_font, max_width=rect.width - 32)

    def fire_required_water(self, fire):
        return fire.severity * 35

    def fire_danger_label(self, danger_zone):
        labels = {
            "normal": "Thường",
            "hospital": "Bệnh viện",
            "gas": "Trạm xăng",
        }
        return labels.get(danger_zone, danger_zone)

    def fire_capable_trucks_text(self, fire):
        needed = self.fire_required_water(fire)
        capable = []
        for truck in self.city_map.stations:
            if truck.capacity < needed:
                continue
            if fire.severity >= 3 and truck.water < 80:
                continue
            if fire.danger_zone == "gas" and not truck.heavy and truck.water < 100:
                continue
            capable.append(truck.id)
        return ", ".join(capable) if capable else "Chưa có"

    def fire_assigned_trucks_text(self, fire):
        assigned = self.report.fire_to_trucks.get(fire.id, []) if self.report else []
        return ", ".join(assigned) if assigned else "Chưa phân công"

    def fire_status_text(self, fire):
        assigned = self.report.fire_to_trucks.get(fire.id, []) if self.report else []
        if not assigned:
            return "Chưa phân công"
        if fire.id in self.current_extinguished_fires():
            return "Đã dập"
        return "Đang xử lý" if self.state == STATE_EXECUTING else "Trong kế hoạch"

    def draw_algorithm_overlay(self):
        if not self.report:
            return
        route_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)

        if self.show_visited_nodes:
            # Visited nodes are intentionally faint so planned lanes stay readable.
            for row, col in self.report.route_visited[:self.visited_visible]:
                rect = pygame.Rect(col * TILE_SIZE + 11, row * TILE_SIZE + 11, TILE_SIZE - 22, TILE_SIZE - 22)
                pygame.draw.rect(route_surface, (*VISITED_COLOR, 65), rect, border_radius=4)

        # Backup routes stay subtle so they do not compete with actual truck routes.
        if self.state == STATE_RESULT:
            for path in self.report.backup_paths[:2]:
                if len(path) < 2:
                    continue
                self.draw_parallel_path(
                    route_surface,
                    path,
                    ALT_PATH_COLOR,
                    distributed_lane_slot(0, 1, ROUTE_LANE_COUNT),
                    ROUTE_LANE_COUNT,
                    alpha=65,
                    dashed=True,
                )

        active_plans = [plan for plan in self.report.truck_plans.values() if len(plan.full_path) > 1]
        for i, plan in enumerate(active_plans):
            path = self.visible_truck_path(plan.full_path, plan.truck_id)
            if len(path) < 2:
                continue
            color = self.route_color_for_truck(plan.truck_id, i)
            alpha = 220 if self.state == STATE_EXECUTING else 125
            slot_index, slot_count = self.route_slot_for_plan(plan.truck_id)
            self.draw_parallel_path(route_surface, path, color, slot_index, slot_count, alpha=alpha, label=plan.truck_id)

        self.screen.blit(route_surface, (0, 0))

    def max_route_path_length(self):
        if not self.report:
            return 0
        lengths = [len(plan.full_path) for plan in self.report.truck_plans.values()]
        if self.report.route_path_preview:
            lengths.append(len(self.report.route_path_preview))
        return max(lengths or [0])

    def visible_truck_path(self, path, truck_id=None):
        if self.state != STATE_EXECUTING:
            return path
        truck = next((item for item in self.trucks if item.spec.id == truck_id), None)
        if not truck:
            limit = max(2, min(len(path), self.path_visible))
            return path[:limit]
        start = max(0, truck.path_index - 3)
        end = min(len(path), max(truck.path_index + 12, start + 2))
        return path[start:end]

    def route_color_for_truck(self, truck_id, fallback_index):
        try:
            index = max(0, int(str(truck_id).replace("T", "")) - 1)
        except ValueError:
            index = fallback_index
        return self.truck_colors[index % len(self.truck_colors)]

    def algorithm_label(self, algorithm):
        return ALGORITHM_LABELS.get(algorithm, algorithm)

    def draw_parallel_path(self, surface, path, color, slot_index=0, slot_count=1, alpha=225, dashed=False, label=None):
        if len(path) < 2:
            return
        segments = self.parallel_route_segments(path, slot_index, slot_count)
        if not segments:
            return

        points = self.route_points_from_segments(segments)
        if dashed:
            self.draw_dashed_route(surface, segments, color, alpha)
        else:
            self.draw_route_polyline(surface, points, color, alpha)

        if label:
            self.draw_route_terminal(surface, path, color, slot_index, slot_count, label, alpha)

    def draw_emphasized_parallel_path(self, surface, path, color, slot_index=0, slot_count=1, alpha=255, label=None):
        if len(path) < 2:
            return
        segments = self.parallel_route_segments(path, slot_index, slot_count)
        if not segments:
            return

        points = self.route_points_from_segments(segments)
        outline_width = max(4, ROUTE_LINE_OUTLINE_WIDTH + 1)
        route_width = max(3, ROUTE_LINE_WIDTH + 1)

        self.draw_joined_route(surface, points, (5, 7, 12, min(230, alpha + 10)), outline_width)
        self.draw_joined_route(surface, points, (*color, alpha), route_width)
        self.draw_joined_route(surface, points, (255, 255, 255, min(120, alpha // 2)), 1, skip_caps=True)
        self.draw_route_arrows(surface, points, color, alpha)

        if label:
            self.draw_route_terminal(surface, path, color, slot_index, slot_count, label, 255)

    def draw_route_polyline(self, surface, points, color, alpha):
        outline_color = (7, 8, 14, min(255, alpha + 30))
        route_color = (*color, alpha)
        highlight_color = (255, 255, 255, min(95, max(40, alpha // 3)))
        outline_width = max(3, ROUTE_LINE_OUTLINE_WIDTH)
        route_width = max(2, ROUTE_LINE_WIDTH)

        self.draw_joined_route(surface, points, outline_color, outline_width)
        self.draw_joined_route(surface, points, route_color, route_width)
        self.draw_joined_route(surface, points, highlight_color, 1, skip_caps=True)

    def draw_dashed_route(self, surface, segments, color, alpha):
        outline = (7, 8, 14, min(255, alpha + 25))
        route_color = (*color, alpha)
        for start, end in segments:
            self.draw_dashed_line(surface, outline, start, end, max(3, ROUTE_LINE_OUTLINE_WIDTH))
        for start, end in segments:
            self.draw_dashed_line(surface, route_color, start, end, max(2, ROUTE_LINE_WIDTH))

    def draw_joined_route(self, surface, points, color, width, skip_caps=False):
        if len(points) < 2:
            return
        radius = max(1, width // 2)
        int_points = [(int(x), int(y)) for x, y in points]
        for start, end in zip(int_points, int_points[1:]):
            pygame.draw.line(surface, color, start, end, width)
        if not skip_caps:
            for point in int_points:
                pygame.draw.circle(surface, color, point, radius)

    def simplify_route_points(self, points):
        if len(points) <= 2:
            return points
        simplified = [points[0]]
        previous_direction = self.point_direction(points[0], points[1])
        for index in range(1, len(points) - 1):
            current_direction = self.point_direction(points[index], points[index + 1])
            if current_direction != previous_direction:
                simplified.append(points[index])
                previous_direction = current_direction
        simplified.append(points[-1])
        return simplified

    def route_points_from_segments(self, segments):
        if not segments:
            return []
        points = [segments[0][0], segments[0][1]]
        for start, end in segments[1:]:
            if self.point_distance(points[-1], start) > 0.5:
                points.append(start)
            if self.point_distance(points[-1], end) > 0.5:
                points.append(end)
        return points

    def point_distance(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def point_direction(self, start, end):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        if abs(dx) > abs(dy):
            return (1 if dx > 0 else -1, 0)
        if abs(dy) > 0:
            return (0, 1 if dy > 0 else -1)
        return (0, 0)

    def draw_route_arrows(self, surface, points, color, alpha):
        if len(points) < 2:
            return
        arrow_color = (255, 255, 255, min(190, alpha))
        shadow_color = (6, 7, 12, min(210, alpha))
        last_index = len(points) - 2
        for index, (start, end) in enumerate(zip(points, points[1:])):
            if index != last_index and index % 8 != 4:
                continue
            if math.hypot(end[0] - start[0], end[1] - start[1]) < TILE_SIZE * 0.65:
                continue
            self.draw_route_arrow(surface, start, end, shadow_color, 5)
            self.draw_route_arrow(surface, start, end, arrow_color, 3)

    def draw_route_arrow(self, surface, start, end, color, size):
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        length = math.hypot(dx, dy)
        if length <= 0:
            return
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        cx = sx + dx * 0.62
        cy = sy + dy * 0.62
        points = [
            (cx + ux * size, cy + uy * size),
            (cx - ux * size * 0.75 + px * size * 0.65, cy - uy * size * 0.75 + py * size * 0.65),
            (cx - ux * size * 0.75 - px * size * 0.65, cy - uy * size * 0.75 - py * size * 0.65),
        ]
        pygame.draw.polygon(surface, color, points)

    def parallel_route_segments(self, path, slot_index, slot_count):
        segments = []
        for index in range(len(path) - 1):
            start = path[index]
            end = path[index + 1]
            direction = direction_between(start, end)
            if direction == (0, 0):
                continue
            segments.append((
                self.parallel_route_point(start, direction, slot_index, slot_count),
                self.parallel_route_point(end, direction, slot_index, slot_count),
            ))
        return segments

    def parallel_route_point(self, cell, direction, slot_index, slot_count):
        return lane_center_for_direction(cell, direction, slot_index, slot_count)

    def draw_dashed_line(self, surface, color, start, end, width):
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        length = math.hypot(dx, dy)
        if length <= 0:
            return
        ux, uy = dx / length, dy / length
        distance = 0
        while distance < length:
            dash_end = min(distance + ROUTE_DASH_LENGTH, length)
            p1 = (sx + ux * distance, sy + uy * distance)
            p2 = (sx + ux * dash_end, sy + uy * dash_end)
            pygame.draw.line(surface, color, p1, p2, width)
            distance += ROUTE_DASH_LENGTH + ROUTE_GAP_LENGTH

    def draw_route_terminal(self, surface, path, color, slot_index, slot_count, label, alpha):
        direction = direction_between(path[-2], path[-1])
        x, y = self.parallel_route_point(path[-1], direction, slot_index, slot_count)
        center = (int(x), int(y))
        pygame.draw.circle(surface, (10, 10, 16, min(255, alpha + 25)), center, 8)
        pygame.draw.circle(surface, (*color, alpha), center, 6)
        text = self.tiny_font.render(label, True, WHITE)
        rect = text.get_rect(center=(int(x), int(y - 15)))
        pygame.draw.rect(surface, (10, 10, 16, 210), rect.inflate(8, 4), border_radius=4)
        surface.blit(text, rect)

    def draw_panel(self):
        panel_rect = pygame.Rect(PANEL_X, 0, SCREEN_WIDTH - PANEL_X, SCREEN_HEIGHT)
        self.draw_dynamic_background(panel_rect, dark_overlay=168)
        pygame.draw.line(self.screen, (76, 78, 92), (PANEL_X, 0), (PANEL_X, SCREEN_HEIGHT), 1)
        x = PANEL_X + 20
        y = 22
        self.panel.text("TRUNG TÂM AI", x, y, WHITE, self.title_font, max_width=PANEL_CONTENT_WIDTH)
        y += 44
        self.panel.text(f"Điểm tốt nhất: {self.benchmark_score}", x, y, CYAN, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 20
        self.panel.text(f"Điểm qua màn: {self.pass_score}", x, y, SUCCESS, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 20
        self.panel.text(self.benchmark_info, x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 26

        if self.state == STATE_PLANNING:
            self.draw_planning_panel(x, y)
        elif self.state == STATE_EXECUTING:
            self.draw_execution_panel(x, y)
        elif self.state == STATE_RESULT:
            self.draw_result_panel(x, y)

    def draw_planning_panel(self, x, y):
        left = self.planning_seconds_left()
        color = SUCCESS if left > 45 else WARNING if left > 15 else DANGER
        self.panel.text(f"Thời gian lập kế hoạch: {left}s", x, y, color, self.font, max_width=PANEL_CONTENT_WIDTH)
        y += 38

        self.panel.text("1. AI ĐIỀU XE - phân công xe", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 20
        self.dispatch_dropdown.draw(self.screen); y += 50
        self.panel.text("2. AI ƯU TIÊN - thứ tự dập cháy", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 20
        self.priority_dropdown.draw(self.screen); y += 50
        self.panel.text("3. AI ĐƯỜNG ĐI - tìm tuyến xe", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 20
        self.route_dropdown.draw(self.screen); y += 50
        self.panel.text("4. AI RỦI RO - đường chưa chắc chắn", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 20
        self.risk_dropdown.draw(self.screen); y += 50

        self.draw_algorithm_card(x, y)
        y = 546
        self.speed_slider.draw(self.screen)
        self.draw_legend_button()
        self.draw_route_nodes_button()
        self.draw_truck_menu_button()
        for btn in self.plan_buttons:
            btn.draw(self.screen)
        self.draw_compare_table(x, 720)
        self.draw_dropdowns_on_top()

    def draw_algorithm_card(self, x, y):
        selected = [
            self.dispatch_dropdown.selected,
            self.priority_dropdown.selected,
            self.route_dropdown.selected,
            self.risk_dropdown.selected,
        ]
        self.panel.text("AI đã chọn:", x, y, CYAN, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 18
        for alg in selected:
            group, _desc = ALGORITHM_INFO.get(alg, ("AI", ""))
            self.panel.text(f"{group}: {self.algorithm_label(alg)}", x, y, WHITE, self.tiny_font, max_width=PANEL_CONTENT_WIDTH)
            y += 18

    def draw_execution_panel(self, x, y):
        self.panel.text("ĐANG DẬP CHÁY...", x, y, WARNING, self.font, max_width=PANEL_CONTENT_WIDTH)
        y += 32
        if self.report:
            y = self.draw_execution_progress(x, y)
            self.draw_details_summary(x, y + 8, "Giải thích thuật toán")
        self.speed_slider.draw(self.screen)
        self.draw_details_button()
        self.draw_legend_button()
        self.draw_route_nodes_button()
        self.draw_truck_menu_button()

    def draw_execution_progress(self, x, y):
        progress = self.execution_progress()
        done = progress["extinguished"]
        total = max(1, progress["total_fires"])
        score = progress["score"]
        moving = progress["moving_trucks"]
        truck_total = progress["truck_total"]

        self.panel.text(f"Tiến trình: {done}/{progress['total_fires']} đám cháy", x, y, WHITE, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 24
        self.draw_progress_bar(x, y, PANEL_CONTENT_WIDTH, 14, done, total, SUCCESS)
        y += 28
        self.panel.text(f"Điểm tạm: {score}", x, y, CYAN, self.font, max_width=PANEL_CONTENT_WIDTH)
        y += 30
        self.panel.text(f"Điểm qua màn: {self.report.pass_score}", x, y, SUCCESS, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 22
        self.panel.text(f"Xe đang chạy: {moving}/{truck_total}", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 22
        current_fire = progress["current_fire"] or "Đang di chuyển"
        self.panel.text(f"Mục tiêu hiện tại: {current_fire}", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 26
        self.panel.text("Kết quả sẽ hiện khi chạy xong.", x, y, WARNING, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 28
        return y

    def draw_progress_bar(self, x, y, width, height, value, total, color):
        ratio = 0 if total <= 0 else max(0, min(1, value / total))
        rect = pygame.Rect(x, y, width, height)
        fill = pygame.Rect(x, y, int(width * ratio), height)
        pygame.draw.rect(self.screen, (40, 40, 52), rect, border_radius=height // 2)
        if fill.width > 0:
            pygame.draw.rect(self.screen, color, fill, border_radius=height // 2)
        pygame.draw.rect(self.screen, (90, 90, 108), rect, 1, border_radius=height // 2)

    def execution_progress(self):
        if not self.report:
            return {
                "extinguished": 0,
                "total_fires": 0,
                "score": 0,
                "moving_trucks": 0,
                "truck_total": len(self.trucks),
                "current_fire": "",
            }
        extinguished = self.current_extinguished_fires()
        score = self.current_execution_score(extinguished)
        moving = sum(1 for truck in self.trucks if not truck.finished)
        current_fire = self.next_pending_fire(extinguished)
        return {
            "extinguished": len(extinguished),
            "total_fires": self.report.total_fires,
            "score": score,
            "moving_trucks": moving,
            "truck_total": len(self.trucks),
            "current_fire": current_fire,
        }

    def current_extinguished_fires(self):
        extinguished = set()
        if not self.report:
            return extinguished
        for fid in self.report.fire_order:
            assigned = self.report.fire_to_trucks.get(fid, [])
            if assigned and all(self.truck_reached_fire(tid, fid) for tid in assigned):
                extinguished.add(fid)
        return extinguished

    def truck_reached_fire(self, truck_id, fire_id):
        plan = self.report.truck_plans.get(truck_id) if self.report else None
        truck = next((item for item in self.trucks if item.spec.id == truck_id), None)
        if not plan or not truck:
            return False
        end_index = self.fire_segment_end_index(plan, fire_id)
        if end_index is None:
            return False
        return truck.path_index > end_index or truck.finished

    def fire_segment_end_index(self, plan, fire_id):
        index = 0
        for kind, label, path in plan.path_segments:
            index += max(0, len(path) - 1)
            if kind == "CHÁY" and label == fire_id:
                return index
        return None

    def current_execution_score(self, extinguished):
        score = 0
        for fid in extinguished:
            fire = self.city_map.fire_lookup.get(fid)
            if not fire:
                continue
            score += fire.base_score
            arrival = min(
                (plan.arrival_times.get(fid, 9999) for plan in self.report.truck_plans.values() if fid in plan.arrival_times),
                default=9999,
            )
            if arrival <= fire.deadline:
                score += ON_TIME_BONUS
            else:
                score -= (arrival - fire.deadline) * LATE_TURN_PENALTY
                if fire.danger_zone == "gas":
                    score -= GAS_LATE_PENALTY
                if fire.danger_zone == "hospital":
                    score -= HOSPITAL_LATE_PENALTY
        travel_cost, traffic_tiles, risky_tiles = self.current_completed_path_stats()
        score -= int(travel_cost * TRAVEL_COST_SCORE_PENALTY)
        score -= traffic_tiles * TRAFFIC_TILE_SCORE_PENALTY
        risky_penalty = RISKY_TILE_SCORE_PENALTY_AND_OR if self.report.choice.risk_ai == "And-Or Search" else RISKY_TILE_SCORE_PENALTY_BELIEF
        score -= risky_tiles * risky_penalty
        score -= self.report.planning_penalty
        return max(0, int(score))

    def current_completed_path_stats(self):
        travel_cost = 0
        traffic_tiles = 0
        risky_tiles = 0
        for truck in self.trucks:
            if not truck.path:
                continue
            last_index = min(max(0, truck.path_index - 1), len(truck.path) - 1)
            for row, col in truck.path[1:last_index + 1]:
                tile = self.city_map.grid[row][col]
                travel_cost += self.city_map.get_tile_cost(row, col)
                if tile == TRAFFIC:
                    traffic_tiles += 1
                elif tile == RISKY:
                    risky_tiles += 1
        return travel_cost, traffic_tiles, risky_tiles

    def next_pending_fire(self, extinguished):
        if not self.report:
            return ""
        for fid in self.report.fire_order:
            if fid not in extinguished:
                assigned = ",".join(self.report.fire_to_trucks.get(fid, [])) or "-"
                return f"{fid} ({assigned})"
        return "Hoàn tất tuyến"

    def draw_result_panel(self, x, y):
        if self.report:
            y = self.panel.draw_report_summary(self.report, x, y)
            _stars, star_label, _ratio, _perfect = self.result_rating(self.report)
            self.panel.text(f"Sao: {star_label}", x, y, YELLOW, self.font, max_width=PANEL_CONTENT_WIDTH); y += 35
            self.draw_details_summary(x, y, "Vì sao có kết quả này")
        self.draw_details_button()
        self.draw_legend_button()
        self.draw_route_nodes_button()
        self.draw_truck_menu_button()
        for btn in self.result_buttons:
            btn.draw(self.screen)

    def draw_details_summary(self, x, y, title):
        lines = self.detail_lines()
        self.panel.text(title, x, y, CYAN, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 20
        count = max(0, len(lines))
        self.panel.text(f"Có {count} dòng giải thích.", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH)

    def result_rating(self, report):
        if not report:
            return 0, "0/3", 0.0, False
        ratio = report.score / max(1, report.benchmark_score)
        if not report.win:
            return 0, "0/3", ratio, False
        stars = 1
        if ratio >= STAR_2_RATIO:
            stars = 2
        if ratio >= STAR_3_RATIO:
            stars = 3
        perfect = ratio >= PERFECT_RATIO
        label = "3/3 HOÀN HẢO" if perfect else f"{stars}/3"
        return stars, label, ratio, perfect

    def draw_result_modal(self):
        if not self.report or not self.result_modal_rect:
            return

        overlay = pygame.Surface((MAP_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 118))
        self.screen.blit(overlay, (0, 0))

        rect = self.result_modal_rect
        shadow = rect.move(0, 8)
        pygame.draw.rect(self.screen, (0, 0, 0), shadow, border_radius=8)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, (96, 96, 116), rect, 1, border_radius=8)

        stars, star_label, ratio, perfect = self.result_rating(self.report)
        status = "HOÀN THÀNH NHIỆM VỤ" if self.report.win else "NHIỆM VỤ THẤT BẠI"
        status_color = SUCCESS if self.report.win else DANGER
        title = self.title_font.render(status, True, status_color)
        self.screen.blit(title, title.get_rect(center=(rect.centerx, rect.y + 42)))

        subtitle = self.panel.fit_text(self.report.fail_reason, self.small_font, rect.width - 80)
        subtitle_surf = self.small_font.render(subtitle, True, TEXT_MUTED)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(rect.centerx, rect.y + 78)))

        self.draw_star_row(rect.centerx, rect.y + 118, stars)
        label_color = YELLOW if stars else TEXT_MUTED
        label_surf = self.font.render(star_label, True, label_color)
        self.screen.blit(label_surf, label_surf.get_rect(center=(rect.centerx, rect.y + 152)))
        if perfect:
            perfect_surf = self.tiny_font.render("LƯỢT CHƠI HOÀN HẢO", True, YELLOW)
            self.screen.blit(perfect_surf, perfect_surf.get_rect(center=(rect.centerx, rect.y + 178)))

        table_x = rect.x + 48
        table_y = rect.y + 198
        row_h = 26
        self.draw_result_row(table_x, table_y, "Đám cháy đã xử lý", f"{self.report.extinguished_count}/{self.report.total_fires}", self.report.extinguished_count == self.report.total_fires)
        self.draw_result_row(table_x, table_y + row_h, "Điểm qua màn", f"{self.report.score}/{self.report.pass_score}", self.report.score >= self.report.pass_score)
        self.draw_result_row(table_x, table_y + row_h * 2, "Mốc 2 sao", f"{int(ratio * 100)}%/{int(STAR_2_RATIO * 100)}%", self.report.win and ratio >= STAR_2_RATIO)
        self.draw_result_row(table_x, table_y + row_h * 3, "Mốc 3 sao", f"{int(ratio * 100)}%/{int(STAR_3_RATIO * 100)}%", self.report.win and ratio >= STAR_3_RATIO)

        for btn in self.result_modal_buttons:
            btn.draw(self.screen)

    def detail_lines(self):
        if not self.report:
            return []
        lines = [
            ("TÓM TẮT", CYAN),
            (f"Điểm: {self.report.score} / Qua màn: {self.report.pass_score} / Tốt nhất: {self.report.benchmark_score}", WHITE),
            (f"Đám cháy: {self.report.extinguished_count}/{self.report.total_fires}", WHITE),
            (f"Thứ tự: {' -> '.join(self.report.fire_order)}", TEXT_MUTED),
            (f"Kết luận: {self.report.fail_reason}", WHITE),
            ("", TEXT_MUTED),
            ("CÁCH ĐỌC BẢNG NÀY", CYAN),
        ]
        self.append_wrapped_detail(
            lines,
            "Mỗi phần bên dưới giải thích thuật toán đang làm gì, điểm mạnh/yếu của nó, rồi mới hiển thị nhật ký thật của lần chạy này.",
            TEXT_MUTED,
        )
        self.append_wrapped_detail(
            lines,
            "Quy ước nhanh: chi phí càng thấp càng tốt; nút/ô đã thăm càng ít thì AI tính gọn hơn; miền là danh sách lựa chọn còn hợp lệ.",
            TEXT_MUTED,
        )
        lines.append(("", TEXT_MUTED))
        sections = [
            ("ĐIỀU XE", self.report.choice.dispatch_ai, self.report.dispatch_logs),
            ("ƯU TIÊN", self.report.choice.priority_ai, self.report.priority_logs),
            ("ĐƯỜNG ĐI", self.report.choice.route_ai, self.report.route_logs),
            ("RỦI RO", self.report.choice.risk_ai, self.report.risk_logs),
        ]
        for title, algorithm, logs in sections:
            lines.append((f"{title} - {self.algorithm_label(algorithm)}", CYAN))
            for explanation in self.algorithm_explanation_lines(algorithm):
                self.append_wrapped_detail(lines, f"- {explanation}", WHITE, max_chars=106)
            lines.append(("Nhật ký lần chạy:", WARNING))
            if logs:
                for line in logs:
                    self.append_wrapped_detail(lines, f"  {line}", TEXT_MUTED, max_chars=112, continuation="    ")
            else:
                lines.append(("Không có chi tiết.", TEXT_MUTED))
            lines.append(("", TEXT_MUTED))
        return lines

    def algorithm_explanation_lines(self, algorithm):
        _group, short_desc = ALGORITHM_INFO.get(algorithm, ("AI", ""))
        details = ALGORITHM_DETAILS.get(algorithm, [])
        lines = []
        if short_desc:
            lines.append(f"Mục đích: {short_desc}")
        lines.extend(details)
        return lines

    def append_wrapped_detail(self, lines, text, color=TEXT_MUTED, max_chars=108, continuation="  "):
        words = str(text).split()
        if not words:
            lines.append(("", color))
            return
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if len(candidate) > max_chars and line:
                lines.append((line, color))
                line = f"{continuation}{word}"
            else:
                line = candidate
        if line:
            lines.append((line, color))

    def scroll_details(self, delta):
        visible_lines = 24
        max_scroll = max(0, len(self.detail_lines()) - visible_lines)
        self.details_scroll = max(0, min(max_scroll, self.details_scroll + delta))

    def draw_details_modal(self):
        lines = self.detail_lines()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        rect = self.details_modal_rect()
        pygame.draw.rect(self.screen, (0, 0, 0), rect.move(0, 8), border_radius=8)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, (96, 96, 116), rect, 1, border_radius=8)

        self.panel.text("GIẢI THÍCH THUẬT TOÁN", rect.x + 28, rect.y + 24, WHITE, self.title_font, max_width=rect.width - 56)
        self.panel.text("Đọc mục đích, cách hoạt động và nhật ký thật của từng AI.", rect.x + 30, rect.y + 66, TEXT_MUTED, self.small_font, max_width=rect.width - 60)

        content_rect = pygame.Rect(rect.x + 30, rect.y + 104, rect.width - 60, rect.height - 190)
        pygame.draw.rect(self.screen, PANEL_BG, content_rect, border_radius=6)
        pygame.draw.rect(self.screen, (70, 70, 88), content_rect, 1, border_radius=6)

        old_clip = self.screen.get_clip()
        self.screen.set_clip(content_rect.inflate(-12, -10))
        y = content_rect.y + 12
        visible = lines[self.details_scroll:self.details_scroll + 24]
        for text, color in visible:
            if text:
                font = self.small_font if color == CYAN else self.tiny_font
                self.panel.text(text, content_rect.x + 14, y, color, font, max_width=content_rect.width - 34)
            y += 18
        self.screen.set_clip(old_clip)

        total = len(lines)
        showing_to = min(total, self.details_scroll + 24)
        footer = f"Đang xem {self.details_scroll + 1 if total else 0}-{showing_to} / {total}"
        self.panel.text(footer, rect.x + 30, rect.bottom - 58, TEXT_MUTED, self.tiny_font, max_width=300)

        if total > 24:
            track = pygame.Rect(rect.right - 42, content_rect.y + 12, 8, content_rect.height - 24)
            pygame.draw.rect(self.screen, (55, 55, 70), track, border_radius=4)
            ratio = 24 / total
            thumb_h = max(34, int(track.height * ratio))
            max_scroll = max(1, total - 24)
            thumb_y = track.y + int((track.height - thumb_h) * (self.details_scroll / max_scroll))
            pygame.draw.rect(self.screen, CYAN, (track.x, thumb_y, track.width, thumb_h), border_radius=4)

        if self.details_close_button:
            self.details_close_button.draw(self.screen)

    def draw_truck_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        rect = self.truck_modal_rect()
        pygame.draw.rect(self.screen, (0, 0, 0), rect.move(0, 8), border_radius=8)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, (96, 96, 116), rect, 1, border_radius=8)

        self.panel.text("XE CỨU HỎA", rect.x + 28, rect.y + 24, WHITE, self.title_font, max_width=rect.width - 56)
        self.panel.text("Xem thông số xe và chỉnh màu RGB cho từng xe.", rect.x + 30, rect.y + 66, TEXT_MUTED, self.small_font, max_width=rect.width - 60)

        self.truck_slider_rects = {}
        self.truck_slider_hit_rects = {}
        self.truck_input_rects = {}
        card_w, card_h = 330, 470
        gap = 25
        start_x = rect.x + 30
        card_y = rect.y + 112
        for index, spec in enumerate(self.city_map.stations[:3]):
            card = pygame.Rect(start_x + index * (card_w + gap), card_y, card_w, card_h)
            self.draw_truck_config_card(index, spec, card)

        self.panel.text("Bình nước là dung tích tối đa và là nước ban đầu. Xe xuất phát đầy bình.", rect.x + 30, rect.bottom - 64, TEXT_MUTED, self.tiny_font, max_width=820)
        self.panel.text("Bình nhỏ hơn nước cần dập thì xe không đủ điều kiện; thiếu nước còn lại thì xe ghé W để nạp.", rect.x + 30, rect.bottom - 45, TEXT_MUTED, self.tiny_font, max_width=880)
        if self.truck_close_button:
            self.truck_close_button.rect = pygame.Rect(rect.right - 155, rect.y + 22, 125, 34)
            self.truck_close_button.draw(self.screen)

    def draw_truck_config_card(self, index, spec, rect):
        color = self.truck_colors[index]
        pygame.draw.rect(self.screen, PANEL_BG, rect, border_radius=8)
        pygame.draw.rect(self.screen, (78, 78, 96), rect, 1, border_radius=8)

        header = f"XE {spec.id}"
        self.panel.text(header, rect.x + 18, rect.y + 14, CYAN, self.font, max_width=rect.width - 36)
        swatch = pygame.Rect(rect.right - 58, rect.y + 16, 38, 22)
        pygame.draw.rect(self.screen, color, swatch, border_radius=5)
        pygame.draw.rect(self.screen, (210, 210, 220), swatch, 1, border_radius=5)

        preview = pygame.Rect(rect.x + 62, rect.y + 58, rect.width - 124, 96)
        self.draw_large_truck_preview(preview, color, spec.id)

        info_y = rect.y + 174
        heavy_text = "Xe nặng" if spec.heavy else "Xe tiêu chuẩn"
        self.panel.text(heavy_text, rect.x + 18, info_y, TEXT_MUTED, self.small_font, max_width=rect.width - 36)
        self.panel.text(f"Tốc độ: {spec.speed}  |  Bình nước: {spec.water}", rect.x + 18, info_y + 22, WHITE, self.small_font, max_width=rect.width - 36)

        slider_x = rect.x + 20
        slider_w = rect.width - 40
        y = rect.y + 230
        self.draw_truck_setting_slider(index, "speed", "Tốc độ", slider_x, y, slider_w, SUCCESS)
        y += 44
        self.draw_truck_setting_slider(index, "water", "Bình", slider_x, y, slider_w, CYAN)
        y += 52
        self.panel.text("Màu RGB", slider_x, y - 12, YELLOW, self.small_font, max_width=slider_w)
        y += 32
        self.draw_truck_setting_slider(index, "r", "R", slider_x, y, slider_w, (235, 75, 80))
        y += 36
        self.draw_truck_setting_slider(index, "g", "G", slider_x, y, slider_w, (85, 225, 120))
        y += 36
        self.draw_truck_setting_slider(index, "b", "B", slider_x, y, slider_w, (90, 160, 255))

    def draw_large_truck_preview(self, rect, color, label):
        shadow = rect.move(0, 8)
        pygame.draw.ellipse(self.screen, (12, 12, 18), shadow.inflate(-18, -54))
        body = pygame.Rect(rect.x + 10, rect.y + 28, rect.width - 28, 38)
        cab = pygame.Rect(rect.right - 82, rect.y + 12, 58, 42)
        pygame.draw.rect(self.screen, color, body, border_radius=10)
        pygame.draw.rect(self.screen, color, cab, border_radius=8)
        pygame.draw.rect(self.screen, (245, 245, 245), (body.x + 18, body.y + 8, body.width - 72, 10), border_radius=3)
        pygame.draw.rect(self.screen, (120, 190, 235), (cab.x + 12, cab.y + 8, 28, 14), border_radius=3)
        pygame.draw.rect(self.screen, (35, 35, 44), body, 2, border_radius=10)
        pygame.draw.rect(self.screen, (35, 35, 44), cab, 2, border_radius=8)
        for wheel_x in (body.x + 30, body.right - 42):
            pygame.draw.circle(self.screen, BLACK, (wheel_x, body.bottom + 3), 13)
            pygame.draw.circle(self.screen, (95, 95, 105), (wheel_x, body.bottom + 3), 6)
        text = self.font.render(label, True, WHITE)
        self.screen.blit(text, text.get_rect(center=(body.centerx, body.centery + 2)))

    def draw_truck_setting_slider(self, index, field, label, x, y, width, color):
        min_value, max_value = self.truck_setting_range(field)
        value = self.truck_setting_value(index, field)
        key = (index, field)
        active = self.truck_edit_key == key

        label_text = self.tiny_font.render(f"{label}:", True, WHITE)
        self.screen.blit(label_text, (x, y - 18))

        value_rect = pygame.Rect(x + 64, y - 23, 54, 22)
        self.truck_input_rects[key] = value_rect
        box_color = (50, 64, 78) if active else (34, 34, 46)
        border_color = YELLOW if active else (92, 92, 112)
        pygame.draw.rect(self.screen, box_color, value_rect, border_radius=5)
        pygame.draw.rect(self.screen, border_color, value_rect, 1, border_radius=5)
        display_value = self.truck_edit_text if active else str(value)
        if active and pygame.time.get_ticks() // 350 % 2 == 0:
            display_value += "|"
        value_text = self.tiny_font.render(display_value or "0", True, CYAN if active else WHITE)
        self.screen.blit(value_text, value_text.get_rect(center=value_rect.center))

        rect = pygame.Rect(x + 132, y, width - 132, 8)
        self.truck_slider_rects[key] = rect
        self.truck_slider_hit_rects[key] = pygame.Rect(rect.x - 10, y - 18, rect.width + 20, 36)
        pygame.draw.rect(self.screen, (45, 45, 56), rect, border_radius=4)
        ratio = (value - min_value) / max(1, max_value - min_value)
        fill = pygame.Rect(rect.x, rect.y, int(rect.width * ratio), rect.height)
        pygame.draw.rect(self.screen, color, fill, border_radius=4)
        pygame.draw.rect(self.screen, (94, 94, 112), rect, 1, border_radius=4)
        knob_x = int(rect.x + rect.width * ratio)
        pygame.draw.circle(self.screen, color, (knob_x, rect.centery), 9)
        pygame.draw.circle(self.screen, WHITE, (knob_x, rect.centery), 9, 2)

    def draw_result_row(self, x, y, label, value, passed):
        width = self.result_modal_rect.width - 96
        row_rect = pygame.Rect(x, y, width, 22)
        pygame.draw.rect(self.screen, PANEL_BG, row_rect, border_radius=5)
        marker = "ĐẠT" if passed else "TRƯỢT"
        marker_color = SUCCESS if passed else DANGER
        self.panel.text(marker, x + 10, y + 3, marker_color, self.tiny_font, max_width=48)
        self.panel.text(label, x + 66, y + 3, TEXT_MUTED, self.tiny_font, max_width=232)
        self.panel.text(value, x + width - 130, y + 3, WHITE, self.tiny_font, max_width=120)

    def draw_star_row(self, center_x, y, filled_count):
        spacing = 58
        start_x = center_x - spacing
        for index in range(3):
            self.draw_star(start_x + index * spacing, y, 18, index < filled_count)

    def draw_star(self, cx, cy, radius, filled):
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            current_radius = radius if i % 2 == 0 else radius * 0.45
            points.append((
                cx + math.cos(angle) * current_radius,
                cy + math.sin(angle) * current_radius,
            ))
        fill = YELLOW if filled else (44, 44, 56)
        outline = (255, 244, 160) if filled else TEXT_MUTED
        pygame.draw.polygon(self.screen, fill, points)
        pygame.draw.polygon(self.screen, outline, points, 2)

    def draw_compare_table(self, x, y):
        if not self.compare_reports:
            self.panel.text("Phím: Dấu cách Chạy | C So sánh", x, y, TEXT_MUTED, self.tiny_font, max_width=PANEL_CONTENT_WIDTH)
            self.panel.text("1/2/3/4 đổi AI | R Bản đồ mới", x, y + 17, TEXT_MUTED, self.tiny_font, max_width=PANEL_CONTENT_WIDTH)
            return
        self.panel.text("So sánh nhanh tốt nhất:", x, y, CYAN, self.tiny_font, max_width=PANEL_CONTENT_WIDTH)
        y += 17
        for r in self.compare_reports[:4]:
            self.panel.text(f"{r.score:4d}  {self.algorithm_label(r.choice.route_ai)}/{self.algorithm_label(r.choice.priority_ai)[:8]}", x, y, TEXT_MUTED, self.tiny_font, max_width=PANEL_CONTENT_WIDTH)
            y += 16

    def draw_dropdowns_on_top(self):
        # Redraw opened dropdown last so it overlays lower widgets.
        for dd in [self.dispatch_dropdown, self.priority_dropdown, self.route_dropdown, self.risk_dropdown]:
            if dd.expanded:
                dd.draw(self.screen)

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()
