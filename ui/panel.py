# ui/panel.py

import pygame
from config import PANEL_X, PANEL_WIDTH, PANEL_CONTENT_WIDTH, SCREEN_HEIGHT, PANEL_BG, WHITE, TEXT_MUTED, SUCCESS, WARNING, DANGER, CYAN, CARD_BG


class Panel:
    def __init__(self, screen, font, small_font, title_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        self.title_font = title_font

    def background(self, asset_loader=None):
        image = asset_loader.get("panel_bg") if asset_loader else None
        if image:
            scaled = pygame.transform.scale(image, (PANEL_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(scaled, (PANEL_X, 0))
        else:
            pygame.draw.rect(self.screen, PANEL_BG, (PANEL_X, 0, PANEL_WIDTH, SCREEN_HEIGHT))

    def text(self, txt, x, y, color=WHITE, font=None, max_width=None):
        font = font or self.font
        value = str(txt)
        if max_width:
            value = self.fit_text(value, font, max_width)
        surf = font.render(value, True, color)
        self.screen.blit(surf, (x, y))

    def fit_text(self, text, font, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text
        suffix = "..."
        if font.size(suffix)[0] > max_width:
            return ""
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            candidate = text[:mid].rstrip() + suffix
            if font.size(candidate)[0] <= max_width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + suffix

    def card(self, rect, title=None):
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=10)
        pygame.draw.rect(self.screen, (80, 80, 96), rect, 1, border_radius=10)
        if title:
            self.text(title, rect.x + 10, rect.y + 7, CYAN, self.small_font)

    def wrapped(self, text, x, y, width_chars=42, color=TEXT_MUTED, line_height=18, max_lines=4, font=None, max_width=None):
        font = font or self.small_font
        max_width = max_width or PANEL_CONTENT_WIDTH
        words = str(text).split()
        line = ""
        count = 0
        for word in words:
            candidate = word if not line else line + " " + word
            if len(candidate) > width_chars or font.size(candidate)[0] > max_width:
                if line:
                    self.text(line, x, y, color, font, max_width=max_width)
                    y += line_height
                    count += 1
                line = word
                if count >= max_lines:
                    return y
            else:
                line = candidate
        if line and count < max_lines:
            self.text(line, x, y, color, font, max_width=max_width)
            y += line_height
        return y

    def draw_report_summary(self, report, x, y):
        if not report:
            self.text("Chưa chạy kế hoạch.", x, y, TEXT_MUTED, self.small_font)
            return y + 22
        status_color = SUCCESS if report.win else DANGER
        order = " -> ".join(report.fire_order)
        assignment = " ".join(
            f"{fid}:{','.join(report.fire_to_trucks.get(fid, [])) or '-'}"
            for fid in report.fire_order
        )
        self.text("KẾT QUẢ NHIỆM VỤ", x, y, CYAN, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 22
        self.text(f"Điểm: {report.score}", x, y, WHITE, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 19
        self.text(f"Qua màn: {report.pass_score} | Tốt nhất: {report.benchmark_score}", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 19
        self.text(f"Đám cháy: {report.extinguished_count}/{report.total_fires}", x, y, WHITE, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 19
        self.text(f"Thứ tự: {order}", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 19
        self.text(f"Phân công: {assignment}", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 19
        self.text(f"Chi phí đường: {int(report.total_travel_cost)} | Nút: {report.computation_nodes}", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 19
        if report.backup_paths:
            self.text(f"Dự phòng: {len(report.backup_paths)} tuyến AND-OR", x, y, WARNING, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 19
        self.text("THẮNG" if report.win else "THUA", x, y, status_color, self.font, max_width=PANEL_CONTENT_WIDTH); y += 27
        self.text(report.fail_reason, x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH); y += 20
        return y

    def draw_logs(self, lines, x, y, title="Chi tiết thuật toán", max_lines=8):
        self.text(title, x, y, CYAN, self.small_font, max_width=PANEL_CONTENT_WIDTH)
        y += 20
        if not lines:
            self.text("Chi tiết sẽ xuất hiện sau khi bấm CHẠY.", x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH)
            return y + 20
        for line in lines[:max_lines]:
            self.text(str(line), x, y, TEXT_MUTED, self.small_font, max_width=PANEL_CONTENT_WIDTH)
            y += 18
        return y
