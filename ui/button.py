# ui/button.py

import math
import pygame
from config import BUTTON_COLOR, BUTTON_HOVER, BUTTON_ACTIVE, WHITE, TEXT_MUTED, CYAN, YELLOW, SUCCESS, WARNING, DANGER


class Button:
    CLICK_MS = 260

    def __init__(self, rect, text, font, action=None, icon=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.action = action
        self.icon = icon
        self.enabled = True
        self.pending_click = False
        self.pressed_until = 0

    def draw(self, screen, active=False):
        now = pygame.time.get_ticks()
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        color = BUTTON_ACTIVE if active else (BUTTON_HOVER if hovered else BUTTON_COLOR)
        if not self.enabled:
            color = (45, 45, 52)
        pressed = self.pending_click or now < self.pressed_until
        draw_rect = self.rect.move(0, 1 if pressed else 0)
        if pressed and self.enabled:
            color = self.mix_color(color, WHITE, 0.18)

        pygame.draw.rect(screen, color, draw_rect, border_radius=8)
        pygame.draw.rect(screen, (110, 110, 130), draw_rect, 1, border_radius=8)
        if active:
            pygame.draw.rect(screen, CYAN, draw_rect.inflate(-3, -3), 1, border_radius=7)
        if pressed and self.enabled:
            self.draw_press_flash(screen, draw_rect, now)

        text_color = WHITE if self.enabled else TEXT_MUTED
        icon_size = min(16, max(11, draw_rect.height - 14))
        gap = 5 if self.icon else 0
        text_max = max(8, draw_rect.width - 10 - (icon_size + gap if self.icon else 0))
        surf = self.render_text_to_fit(self.text, text_color, text_max, draw_rect.height - 8)
        content_w = surf.get_width() + (icon_size + gap if self.icon else 0)
        start_x = draw_rect.centerx - content_w // 2
        if self.icon:
            icon_rect = pygame.Rect(start_x, draw_rect.centery - icon_size // 2, icon_size, icon_size)
            self.draw_icon(screen, icon_rect, text_color)
            start_x += icon_size + gap
        screen.blit(surf, surf.get_rect(midleft=(start_x, draw_rect.centery)))

    def draw_press_flash(self, screen, rect, now):
        remaining = max(0, self.pressed_until - now)
        ratio = remaining / self.CLICK_MS
        pulse = 0.55 + 0.45 * math.sin(now * 0.06)
        alpha = int(40 + 90 * ratio * pulse)
        flash = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(flash, (255, 255, 255, alpha), flash.get_rect(), border_radius=8)
        screen.blit(flash, rect.topleft)
        pygame.draw.rect(screen, YELLOW, rect.inflate(-5, -5), 2, border_radius=7)

    def fit_text(self, text, max_width):
        text = str(text)
        if self.font.size(text)[0] <= max_width:
            return text
        suffix = "..."
        if self.font.size(suffix)[0] > max_width:
            return ""
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            candidate = text[:mid].rstrip() + suffix
            if self.font.size(candidate)[0] <= max_width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + suffix

    def render_text_to_fit(self, text, color, max_width, max_height):
        text = str(text)
        surf = self.font.render(text, True, color)
        if surf.get_width() <= max_width and surf.get_height() <= max_height:
            return surf
        if surf.get_width() > 0 and surf.get_height() > 0:
            scale = min(max_width / surf.get_width(), max_height / surf.get_height(), 1)
            if scale >= 0.55:
                size = (max(1, int(surf.get_width() * scale)), max(1, int(surf.get_height() * scale)))
                return pygame.transform.smoothscale(surf, size)
        label = self.fit_text(text, max_width)
        return self.font.render(label, True, color)

    def mix_color(self, color, target, amount):
        return tuple(int(color[i] + (target[i] - color[i]) * amount) for i in range(3))

    def draw_icon(self, screen, rect, color):
        cx, cy = rect.center
        w, h = rect.size
        stroke = max(2, w // 8)
        if self.icon == "play":
            points = [(rect.left + w * 0.34, rect.top + h * 0.22), (rect.left + w * 0.34, rect.bottom - h * 0.22), (rect.right - w * 0.18, cy)]
            pygame.draw.polygon(screen, SUCCESS, points)
        elif self.icon == "map":
            pygame.draw.rect(screen, color, rect.inflate(-2, -4), stroke, border_radius=2)
            pygame.draw.line(screen, CYAN, (rect.left + w * 0.38, rect.top + 3), (rect.left + w * 0.38, rect.bottom - 3), 1)
            pygame.draw.line(screen, YELLOW, (rect.left + w * 0.65, rect.top + 3), (rect.left + w * 0.65, rect.bottom - 3), 1)
        elif self.icon == "close":
            pygame.draw.line(screen, DANGER, (rect.left + 3, rect.top + 3), (rect.right - 3, rect.bottom - 3), stroke)
            pygame.draw.line(screen, DANGER, (rect.right - 3, rect.top + 3), (rect.left + 3, rect.bottom - 3), stroke)
        elif self.icon == "retry":
            arc_rect = rect.inflate(-2, -2)
            pygame.draw.arc(screen, WARNING, arc_rect, math.radians(35), math.radians(315), stroke)
            pygame.draw.polygon(screen, WARNING, [(rect.left + 3, cy), (rect.left + 8, cy - 5), (rect.left + 10, cy + 3)])
        elif self.icon == "menu":
            for yy in [rect.top + h * 0.28, cy, rect.bottom - h * 0.28]:
                pygame.draw.line(screen, color, (rect.left + 2, yy), (rect.right - 2, yy), stroke)
        elif self.icon == "compare":
            left = pygame.Rect(rect.left + 2, rect.top + 4, w // 3, h - 8)
            right = pygame.Rect(rect.right - w // 3 - 2, rect.top + 4, w // 3, h - 8)
            pygame.draw.rect(screen, CYAN, left, stroke, border_radius=2)
            pygame.draw.rect(screen, YELLOW, right, stroke, border_radius=2)
            pygame.draw.line(screen, color, (left.right + 1, cy), (right.left - 1, cy), 1)
        elif self.icon == "plan":
            pygame.draw.rect(screen, color, rect.inflate(-2, -2), stroke, border_radius=2)
            pygame.draw.line(screen, SUCCESS, (rect.left + 5, rect.top + h * 0.38), (cx - 1, rect.bottom - 5), stroke)
            pygame.draw.line(screen, SUCCESS, (cx - 1, rect.bottom - 5), (rect.right - 4, rect.top + 4), stroke)
        elif self.icon == "info":
            pygame.draw.circle(screen, CYAN, rect.center, w // 2 - 2, stroke)
            pygame.draw.circle(screen, CYAN, (cx, rect.top + 5), 1)
            pygame.draw.line(screen, CYAN, (cx, cy - 1), (cx, rect.bottom - 4), stroke)
        elif self.icon == "nodes":
            pts = [(rect.left + 4, cy), (cx, rect.top + 4), (rect.right - 4, cy), (cx, rect.bottom - 4)]
            pygame.draw.lines(screen, color, True, pts, 1)
            for p in pts:
                pygame.draw.circle(screen, CYAN, (int(p[0]), int(p[1])), 3)
        elif self.icon == "legend":
            pygame.draw.rect(screen, color, rect.inflate(-2, -2), 1, border_radius=2)
            for i, icon_color in enumerate([CYAN, YELLOW, SUCCESS]):
                y = rect.top + 4 + i * max(3, h // 4)
                pygame.draw.circle(screen, icon_color, (rect.left + 5, y), 2)
                pygame.draw.line(screen, color, (rect.left + 9, y), (rect.right - 3, y), 1)
        elif self.icon == "truck":
            body = pygame.Rect(rect.left + 2, rect.top + int(h * 0.32), w - 4, max(5, int(h * 0.42)))
            cab = pygame.Rect(rect.left + int(w * 0.58), rect.top + int(h * 0.20), max(4, int(w * 0.28)), max(5, int(h * 0.36)))
            pygame.draw.rect(screen, DANGER, body, border_radius=3)
            pygame.draw.rect(screen, DANGER, cab, border_radius=2)
            pygame.draw.rect(screen, WHITE, (body.left + 3, body.top + 2, body.width - 10, 3), border_radius=1)
            pygame.draw.circle(screen, color, (rect.left + 5, rect.bottom - 3), 2)
            pygame.draw.circle(screen, color, (rect.right - 5, rect.bottom - 3), 2)
        else:
            pygame.draw.circle(screen, color, rect.center, w // 2 - 2, stroke)

    def handle_event(self, event):
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.pending_click = True
            self.pressed_until = pygame.time.get_ticks() + self.CLICK_MS
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pending = self.pending_click
            self.pending_click = False
            if was_pending and self.rect.collidepoint(event.pos):
                self.pressed_until = pygame.time.get_ticks() + self.CLICK_MS
                if self.action:
                    self.action()
                return True
            return was_pending
        return False
