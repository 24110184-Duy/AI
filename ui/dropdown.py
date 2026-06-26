# ui/dropdown.py

import pygame
from config import BUTTON_COLOR, BUTTON_HOVER, BUTTON_ACTIVE, WHITE, TEXT_MUTED


class Dropdown:
    def __init__(self, rect, options, font, label="", on_change=None, max_visible=8, display_labels=None):
        self.rect = pygame.Rect(rect)
        self.options = options[:]
        self.font = font
        self.label = label
        self.on_change = on_change
        self.max_visible = max_visible
        self.display_labels = display_labels or {}
        self.index = 0
        self.expanded = False

    @property
    def selected(self):
        if not self.options:
            return None
        self.index %= len(self.options)
        return self.options[self.index]

    def set_selected(self, value):
        if value in self.options:
            self.index = self.options.index(value)
            if self.on_change:
                self.on_change(self.selected)

    def next(self):
        if not self.options:
            return
        self.index = (self.index + 1) % len(self.options)
        if self.on_change:
            self.on_change(self.selected)

    def display_text(self, value):
        return self.display_labels.get(value, value)

    def fit_text(self, text, max_width):
        if self.font.size(text)[0] <= max_width:
            return text
        suffix = "..."
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            candidate = text[:mid].rstrip() + suffix
            if self.font.size(candidate)[0] <= max_width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + suffix

    def draw(self, screen):
        pygame.draw.rect(screen, BUTTON_COLOR, self.rect, border_radius=7)
        pygame.draw.rect(screen, (112, 112, 130), self.rect, 1, border_radius=7)
        text = self.display_text(self.selected) if self.selected else "Không có"
        surf = self.font.render(self.fit_text(text, self.rect.width - 42), True, WHITE)
        screen.blit(surf, (self.rect.x + 10, self.rect.y + 8))
        arrow = self.font.render("v" if not self.expanded else "^", True, TEXT_MUTED)
        screen.blit(arrow, (self.rect.right - 24, self.rect.y + 8))
        if self.expanded:
            self.draw_options(screen)

    def draw_options(self, screen):
        h = self.rect.height
        count = min(len(self.options), self.max_visible)
        for i in range(count):
            item = pygame.Rect(self.rect.x, self.rect.bottom + i * h, self.rect.width, h)
            hovered = item.collidepoint(pygame.mouse.get_pos())
            color = BUTTON_ACTIVE if i == self.index else (BUTTON_HOVER if hovered else (42, 42, 56))
            pygame.draw.rect(screen, color, item)
            pygame.draw.rect(screen, (100, 100, 120), item, 1)
            surf = self.font.render(self.fit_text(self.display_text(self.options[i]), self.rect.width - 20), True, WHITE)
            screen.blit(surf, (item.x + 10, item.y + 8))

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self.rect.collidepoint(event.pos):
            self.expanded = not self.expanded
            return True
        if self.expanded:
            h = self.rect.height
            count = min(len(self.options), self.max_visible)
            for i in range(count):
                item = pygame.Rect(self.rect.x, self.rect.bottom + i * h, self.rect.width, h)
                if item.collidepoint(event.pos):
                    self.index = i
                    self.expanded = False
                    if self.on_change:
                        self.on_change(self.selected)
                    return True
            self.expanded = False
            return False
        return False
