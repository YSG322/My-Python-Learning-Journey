# -*- coding: utf-8 -*-
"""
俄罗斯方块 Tetris —— 单文件 pygame 实现

运行:
    pip install pygame
    python tetris.py

操作:
    ← / →        左右移动
    ↓             软降
    ↑ 或 X        顺时针旋转
    Z             逆时针旋转
    空格          硬降（直接落底）
    P             暂停 / 继续
    R             重新开始
    Esc           退出
"""
from __future__ import annotations

import os
import random

import pygame

# ------------------------------------------------------------------ 配置
COLS, ROWS = 10, 20
CELL = 30
SIDE_CELLS = 6
BOARD_W = COLS * CELL
SIDE_W = SIDE_CELLS * CELL
SCREEN_W, SCREEN_H = BOARD_W + SIDE_W, ROWS * CELL
FPS = 60

COLOR_BG = (16, 18, 26)
COLOR_BOARD = (11, 13, 20)
COLOR_GRID = (34, 38, 52)
COLOR_FRAME = (70, 78, 102)
COLOR_TEXT = (232, 236, 246)
COLOR_MUTED = (138, 146, 168)
COLOR_ACCENT = (110, 200, 255)

COLORS = {
    "I": (64, 200, 232),
    "O": (246, 214, 84),
    "T": (176, 116, 232),
    "S": (108, 214, 132),
    "Z": (238, 108, 112),
    "J": (96, 132, 238),
    "L": (240, 158, 74),
}

# 每种方块的初始坐标（相对左上角），旋转后统一归一化，避免方块"漂移"
BASE_CELLS = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}

LINE_SCORES = [0, 100, 300, 500, 800]


def _normalize(cells):
    minx = min(x for x, _ in cells)
    miny = min(y for _, y in cells)
    return sorted((x - minx, y - miny) for x, y in cells)


def _rotate_cw(cells):
    # 屏幕坐标 y 向下，(x, y) -> (-y, x) 即顺时针 90 度
    return _normalize([(-y, x) for x, y in cells])


ROTATIONS = {}
for _t, _c in BASE_CELLS.items():
    _states = [_normalize(_c)]
    for _ in range(3):
        _states.append(_rotate_cw(_states[-1]))
    ROTATIONS[_t] = _states


# ------------------------------------------------------------------ 界面文案
# 优先使用系统中文字体；找不到就自动切换为英文，避免出现乱码方块
UI = {
    "next":    ("下一个", "NEXT"),
    "score":   ("分数", "SCORE"),
    "level":   ("等级", "LEVEL"),
    "lines":   ("消行", "LINES"),
    "paused":  ("已暂停", "PAUSED"),
    "over":    ("游戏结束", "GAME OVER"),
    "resume":  ("按 P 继续游戏", "Press P to resume"),
    "restart": ("按 R 重新开始", "Press R to restart"),
    "h1": ("← →  左右移动", "Left / Right   Move"),
    "h2": ("↑ / X  顺时针旋转", "Up / X   Rotate"),
    "h3": ("Z  逆时针旋转", "Z   Rotate CCW"),
    "h4": ("↓ 软降   空格 硬降", "Down Soft   Space Hard"),
    "h5": ("P 暂停   R 重开", "P Pause   R Restart"),
    "h6": ("Esc 退出", "Esc   Quit"),
}

CJK_PATHS = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

USE_CJK = False
CJK_PATH = None
FONTS = {}


def T(key):
    return UI[key][0 if USE_CJK else 1]


def detect_font():
    """返回可渲染中文的字体路径，找不到则返回 None。"""
    pygame.font.init()
    for path in CJK_PATHS:
        if os.path.isfile(path):
            try:
                pygame.font.Font(path, 18).render("中文", True, (255, 255, 255))
                return path
            except Exception:
                continue
    return None


def make_font(size):
    if CJK_PATH:
        try:
            return pygame.font.Font(CJK_PATH, size)
        except Exception:
            pass
    return pygame.font.Font(None, size)


def text(surf, font, s, pos, anchor="topleft", color=COLOR_TEXT):
    img = font.render(s, True, color)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    surf.blit(img, rect)


def paint_block(surf, px, py, color, size=CELL):
    """画一个带高光和暗边的小方块。"""
    r = pygame.Rect(px + 1, py + 1, size - 2, size - 2)
    pygame.draw.rect(surf, color, r, border_radius=4)
    hi = tuple(min(255, c + 55) for c in color)
    pygame.draw.rect(surf, hi,
                     (r.x + 2, r.y + 2, r.w - 4, max(3, r.h // 4)),
                     border_radius=3)
    lo = tuple(max(0, c - 70) for c in color)
    pygame.draw.rect(surf, lo, (r.x + 2, r.bottom - 4, r.w - 4, 3),
                     border_radius=2)


def draw_cell(surf, gx, gy, color):
    paint_block(surf, gx * CELL, gy * CELL, color)


def draw_ghost(surf, gx, gy, color):
    """半透明轮廓，标出当前方块的落点。"""
    layer = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
    rect = pygame.Rect(1, 1, CELL - 2, CELL - 2)
    pygame.draw.rect(layer, (*color, 28), rect, border_radius=4)
    pygame.draw.rect(layer, (*color, 110), rect, 2, border_radius=4)
    surf.blit(layer, (gx * CELL, gy * CELL))


# ------------------------------------------------------------------ 游戏逻辑
class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.bag = []
        self.next_type = self._take()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.fall_acc = 0
        self.spawn()

    def _take(self):
        # 7-bag 随机：每 7 个方块内每种各出现一次，手感更公平
        if not self.bag:
            self.bag = list(BASE_CELLS)
            random.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self):
        t = self.next_type
        self.next_type = self._take()
        cells = ROTATIONS[t][0]
        width = max(x for x, _ in cells) + 1
        self.piece = {"t": t, "r": 0, "x": (COLS - width) // 2, "y": 0}
        if not self.fits(self.piece_cells()):
            self.game_over = True

    def piece_cells(self, dx=0, dy=0, dr=0, piece=None):
        p = piece or self.piece
        r = (p["r"] + dr) % 4
        return [(p["x"] + x + dx, p["y"] + y + dy)
                for x, y in ROTATIONS[p["t"]][r]]

    def fits(self, cells):
        for x, y in cells:
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def move(self, dx):
        if self.game_over or self.paused:
            return False
        if self.fits(self.piece_cells(dx=dx)):
            self.piece["x"] += dx
            return True
        return False

    def soft_drop(self):
        if self.game_over or self.paused:
            return False
        if self.fits(self.piece_cells(dy=1)):
            self.piece["y"] += 1
            self.score += 1
            return True
        self.lock()
        return False

    def hard_drop(self):
        if self.game_over or self.paused:
            return
        dist = 0
        while self.fits(self.piece_cells(dy=dist + 1)):
            dist += 1
        self.piece["y"] += dist
        self.score += dist * 2
        self.lock()

    def rotate(self, dr):
        if self.game_over or self.paused:
            return
        # 简易墙踢：贴墙时尝试左右让位，必要时上抬一格
        for kick in (0, -1, 1, -2, 2):
            if self.fits(self.piece_cells(dx=kick, dr=dr)):
                self.piece["x"] += kick
                self.piece["r"] = (self.piece["r"] + dr) % 4
                return
        if self.fits(self.piece_cells(dy=-1, dr=dr)):
            self.piece["y"] -= 1
            self.piece["r"] = (self.piece["r"] + dr) % 4

    def lock(self):
        for x, y in self.piece_cells():
            if y < 0:
                self.game_over = True
                continue
            self.board[y][x] = self.piece["t"]
        if not self.game_over:
            self.clear_lines()
            self.spawn()

    def clear_lines(self):
        full = [i for i in range(ROWS) if all(self.board[i])]
        for i in full:
            del self.board[i]
            self.board.insert(0, [None] * COLS)
        n = len(full)
        if n:
            self.lines += n
            self.score += LINE_SCORES[n] * self.level
            self.level = self.lines // 10 + 1

    def fall_interval(self):
        return max(70, 800 - (self.level - 1) * 65)

    def tick(self, dt):
        """dt 为毫秒；按等级控制自动下落。"""
        if self.game_over or self.paused:
            return
        self.fall_acc += dt
        if self.fall_acc >= self.fall_interval():
            self.fall_acc = 0
            self.soft_drop()

    def ghost_y(self):
        d = 0
        while self.fits(self.piece_cells(dy=d + 1)):
            d += 1
        return self.piece["y"] + d


# ------------------------------------------------------------------ 渲染
def draw_sidebar(screen, game):
    x0 = BOARD_W
    cx = x0 + SIDE_W // 2
    f_lab, f_val, f_help = FONTS["lab"], FONTS["val"], FONTS["help"]

    pygame.draw.line(screen, COLOR_FRAME, (x0, 0), (x0, SCREEN_H), 2)
    text(screen, f_lab, T("next"), (cx, 16), "midtop", COLOR_MUTED)

    box = pygame.Rect(x0 + 20, 48, SIDE_W - 40, 88)
    pygame.draw.rect(screen, (24, 27, 38), box, border_radius=8)
    pygame.draw.rect(screen, COLOR_FRAME, box, 1, border_radius=8)
    cells = ROTATIONS[game.next_type][0]
    w = max(x for x, _ in cells) + 1
    h = max(y for _, y in cells) + 1
    ox = box.centerx - w * CELL / 2
    oy = box.centery - h * CELL / 2
    for dx, dy in cells:
        paint_block(screen, ox + dx * CELL, oy + dy * CELL,
                    COLORS[game.next_type])

    pygame.draw.line(screen, COLOR_GRID, (x0 + 16, 150), (SCREEN_W - 16, 150))

    def stat(key, value, y):
        text(screen, f_lab, T(key), (x0 + 20, y), color=COLOR_MUTED)
        text(screen, f_val, str(value), (x0 + 20, y + 26), color=COLOR_ACCENT)

    stat("score", game.score, 162)
    stat("level", game.level, 232)
    stat("lines", game.lines, 302)

    pygame.draw.line(screen, COLOR_GRID, (x0 + 16, 372), (SCREEN_W - 16, 372))
    for i, key in enumerate(("h1", "h2", "h3", "h4", "h5", "h6")):
        text(screen, f_help, T(key), (x0 + 18, 390 + i * 27),
             color=COLOR_MUTED)


def draw_overlay(screen, game):
    veil = pygame.Surface((BOARD_W, SCREEN_H), pygame.SRCALPHA)
    veil.fill((10, 12, 20, 190))
    screen.blit(veil, (0, 0))
    cx, cy = BOARD_W // 2, SCREEN_H // 2
    if game.game_over:
        text(screen, FONTS["big"], T("over"), (cx, cy - 52), "center",
             (255, 122, 122))
        text(screen, FONTS["lab"], "%s  %d" % (T("score"), game.score),
             (cx, cy + 2), "center")
        text(screen, FONTS["lab"], T("restart"), (cx, cy + 38), "center",
             COLOR_MUTED)
    else:
        text(screen, FONTS["big"], T("paused"), (cx, cy - 32), "center",
             COLOR_ACCENT)
        text(screen, FONTS["lab"], T("resume"), (cx, cy + 18), "center",
             COLOR_MUTED)


def render(screen, game):
    screen.fill(COLOR_BG)
    pygame.draw.rect(screen, COLOR_BOARD, (0, 0, BOARD_W, SCREEN_H))
    for x in range(1, COLS):
        pygame.draw.line(screen, COLOR_GRID, (x * CELL, 0),
                         (x * CELL, SCREEN_H))
    for y in range(1, ROWS):
        pygame.draw.line(screen, COLOR_GRID, (0, y * CELL),
                         (BOARD_W, y * CELL))

    for y in range(ROWS):
        for x in range(COLS):
            t = game.board[y][x]
            if t:
                draw_cell(screen, x, y, COLORS[t])

    if not game.game_over:
        t = game.piece["t"]
        gy = game.ghost_y()
        offset = gy - game.piece["y"]
        for x, y in game.piece_cells():
            if y + offset >= 0:
                draw_ghost(screen, x, y + offset, COLORS[t])
        for x, y in game.piece_cells():
            if y >= 0:
                draw_cell(screen, x, y, COLORS[t])

    pygame.draw.rect(screen, COLOR_FRAME, (0, 0, BOARD_W, SCREEN_H), 2)
    draw_sidebar(screen, game)
    if game.paused or game.game_over:
        draw_overlay(screen, game)


# ------------------------------------------------------------------ 主循环
WATCHED = (
    pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_UP,
    pygame.K_x, pygame.K_z, pygame.K_SPACE, pygame.K_p, pygame.K_r,
    pygame.K_ESCAPE,
)


def main():
    global USE_CJK, CJK_PATH, FONTS

    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.init()
    CJK_PATH = detect_font()
    USE_CJK = CJK_PATH is not None
    FONTS = {name: make_font(size) for name, size in
             (("lab", 18), ("val", 26), ("help", 15), ("big", 38))}

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("俄罗斯方块 Tetris")
    clock = pygame.time.Clock()
    game = Tetris()

    held = set()
    das = {}
    running = True
    while running:
        dt = clock.tick(FPS)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        pressed = pygame.key.get_pressed()
        cur = {k for k in WATCHED if pressed[k]}
        just = cur - held

        if pygame.K_r in just:
            game.reset()
        if pygame.K_p in just:
            game.paused = not game.paused

        if not game.paused and not game.game_over:
            if pygame.K_UP in just or pygame.K_x in just:
                game.rotate(1)
            if pygame.K_z in just:
                game.rotate(-1)
            if pygame.K_SPACE in just:
                game.hard_drop()
            repeat_actions = (
                (pygame.K_LEFT, lambda: game.move(-1)),
                (pygame.K_RIGHT, lambda: game.move(1)),
                (pygame.K_DOWN, game.soft_drop),
            )
            for key, action in repeat_actions:
                if key in just:
                    action()
                    das[key] = now + 170          # 首次按下后的延迟
                elif key in cur and now >= das.get(key, float("inf")):
                    action()
                    das[key] = now + 45           # 长按连发速度

        held = cur
        game.tick(dt)
        render(screen, game)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
