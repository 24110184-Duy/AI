# core/entities.py

import pygame
from config import TILE_SIZE, WHITE, BLACK, TRUCK_COLORS, TRUCK_ASSET_SIZE, TRUCK_RENDER_HEIGHT, TRUCK_RENDER_WIDTH
from utils.traffic_lanes import lane_path_waypoints


class AnimatedTruck:
    def __init__(self, spec, asset_loader=None, color_index=0, color=None):
        self.spec = spec
        self.asset_loader = asset_loader
        self.color = color or TRUCK_COLORS[color_index % len(TRUCK_COLORS)]
        self.use_asset = color is None
        self.asset_key = f"truck_{color_index + 1}"
        self.lane_slot = color_index
        self.reset()

    def reset(self):
        self.cell = self.spec.start
        self.path = [self.spec.start]
        self.path_index = 0
        self.x = self.spec.start[1] * TILE_SIZE + TILE_SIZE // 2
        self.y = self.spec.start[0] * TILE_SIZE + TILE_SIZE // 2
        self.target_x = self.x
        self.target_y = self.y
        self.waypoints = []
        self.waypoint_cells = []
        self.waypoint_index = 0
        self.finished = True
        self.speed_px = 4 + self.spec.speed

    def set_path(self, path):
        self.reset()
        if not path:
            return
        self.path = path
        self.path_index = 0
        self.cell = path[0]
        waypoint_data = lane_path_waypoints(path, self.lane_slot)
        if waypoint_data:
            self.waypoints = [point for point, _cell_index in waypoint_data]
            self.waypoint_cells = [cell_index for _point, cell_index in waypoint_data]
            self.x, self.y = self.waypoints[0]
        else:
            self.x = path[0][1] * TILE_SIZE + TILE_SIZE // 2
            self.y = path[0][0] * TILE_SIZE + TILE_SIZE // 2
        self.finished = len(path) <= 1
        if not self.finished:
            self.waypoint_index = 1
            self.set_target()

    def set_target(self):
        if self.waypoint_index >= len(self.waypoints):
            self.finished = True
            return
        self.target_x, self.target_y = self.waypoints[self.waypoint_index]

    def update(self, speed_multiplier=1):
        if self.finished:
            return
        speed = self.speed_px * max(1, speed_multiplier)
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if abs(dx) <= speed and abs(dy) <= speed:
            self.x = self.target_x
            self.y = self.target_y
            self.path_index = max(self.path_index, self.waypoint_cells[self.waypoint_index])
            self.cell = self.path[min(self.path_index, len(self.path) - 1)]
            self.waypoint_index += 1
            self.set_target()
            return
        if dx:
            self.x += speed if dx > 0 else -speed
        if dy:
            self.y += speed if dy > 0 else -speed

    def draw(self, screen):
        image = self.asset_loader.get(self.asset_key) if self.use_asset and self.asset_loader else None
        if image:
            image = pygame.transform.scale(image, (TRUCK_ASSET_SIZE, TRUCK_ASSET_SIZE))
            screen.blit(image, image.get_rect(center=(int(self.x), int(self.y))))
            return
        rect = pygame.Rect(0, 0, TRUCK_RENDER_WIDTH, TRUCK_RENDER_HEIGHT)
        rect.center = (int(self.x), int(self.y))
        pygame.draw.rect(screen, self.color, rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, (rect.x + 4, rect.y + 3, rect.w - 8, 6), border_radius=2)
        pygame.draw.circle(screen, BLACK, (rect.x + 5, rect.bottom + 1), 3)
        pygame.draw.circle(screen, BLACK, (rect.right - 5, rect.bottom + 1), 3)
        font = pygame.font.SysFont("Arial", 10, bold=True)
        label = font.render(self.spec.id, True, WHITE)
        screen.blit(label, (rect.x + 3, rect.y + 11))
