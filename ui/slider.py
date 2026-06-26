# ui/slider.py

import pygame
from config import WHITE, TEXT_MUTED, BUTTON_ACTIVE


class Slider:
    def __init__(self, rect, min_value, max_value, value, font, label, on_change=None):
        self.rect = pygame.Rect(rect)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self.font = font
        self.label = label
        self.on_change = on_change
        self.dragging = False

    def draw(self, screen):
        label = self.font.render(f"{self.label}: x{int(self.value)}", True, WHITE)
        screen.blit(label, (self.rect.x, self.rect.y - 23))
        y = self.rect.centery
        pygame.draw.line(screen, TEXT_MUTED, (self.rect.x, y), (self.rect.right, y), 4)
        x = self.value_to_x(self.value)
        pygame.draw.circle(screen, BUTTON_ACTIVE, (x, y), 10)
        pygame.draw.circle(screen, WHITE, (x, y), 10, 2)

    def value_to_x(self, value):
        ratio = (value - self.min_value) / (self.max_value - self.min_value)
        return int(self.rect.x + ratio * self.rect.width)

    def x_to_value(self, x):
        x = max(self.rect.x, min(self.rect.right, x))
        ratio = (x - self.rect.x) / self.rect.width
        return int(round(self.min_value + ratio * (self.max_value - self.min_value)))

    def set_from_x(self, x):
        self.value = self.x_to_value(x)
        if self.on_change:
            self.on_change(self.value)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            knob_x = self.value_to_x(self.value)
            knob = pygame.Rect(knob_x - 14, self.rect.centery - 14, 28, 28)
            if knob.collidepoint(event.pos) or self.rect.collidepoint(event.pos):
                self.dragging = True
                self.set_from_x(event.pos[0])
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_x(event.pos[0])
            return True
        return False
