# -*- coding: utf-8 -*-
"""
俄罗斯方块 Tetris —— 零依赖 tkinter 版

Anaconda / 官方 Python 自带 tkinter，不需要 pip 或 conda 安装任何东西。
运行（在文件所在目录）:
    python tetris_tk.py

操作:
    ← / →  左右移动      ↓  软降        ↑ 或 X  顺时针旋转
    Z      逆时针旋转    空格 硬降      P 暂停   R 重开   Esc 退出
"""
from __future__ import annotations

import random
import time
import tkinter as tk

# ---------------------------------------------------------------- 配置
COLS, ROWS = 10, 20
CELL = 30
SIDE_W = 180
BOARD_W = COLS * CELL
SCREEN_H = ROWS * CELL

BG = "#10121a"
BOARD_BG = "#0b0d14"
GRID = "#222634"
FRAME = "#464e66"
TEXT_C = "#e8ecf6"
MUTED = "#8a92a8"
ACCENT = "#6ec8ff"
PANEL = "#181b26"

FONT = "Microsoft YaHei"   # 非 Windows 系统改成任意中文字体名即可

RGB = {
    "I": (64, 200, 232),
    "O": (246, 214, 84),
    "T": (176, 116, 232),
    "S": (108, 214, 132),
    "Z": (238, 108, 112),
    "J": (96, 132, 238),
    "L": (240, 158, 74),
}
LINE_SCORES = [0, 100, 300, 500, 800]

BASE_CELLS = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}


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


def hx(color):
    return "#%02x%02x%02x" % tuple(color)


def lighter(color):
    return tuple(min(255, v + 55) for v in color)


def darker(color):
    return tuple(max(0, v - 70) for v in color)


# ---------------------------------------------------------------- 游戏逻辑
class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.next_type = self._take()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.spawn()

    def _take(self):
        # 7-bag：每 7 个方块内每种各出现一次
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

    def piece_cells(self, dx=0, dy=0, dr=0):
        p = self.piece
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
        # 简易墙踢：贴墙时左右让位，必要时上抬一格
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

    def ghost_y(self):
        d = 0
        while self.fits(self.piece_cells(dy=d + 1)):
            d += 1
        return self.piece["y"] + d


# ---------------------------------------------------------------- 界面
def font(size, bold=False):
    return (FONT, size, "bold" if bold else "normal")


def draw_block(canvas, px, py, color):
    x1, y1, x2, y2 = px + 1, py + 1, px + CELL - 1, py + CELL - 1
    canvas.create_rectangle(x1, y1, x2, y2, fill=hx(color), outline="")
    canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2,
                            y1 + 2 + max(3, (y2 - y1) // 4),
                            fill=hx(lighter(color)), outline="")
    canvas.create_rectangle(x1 + 2, y2 - 4, x2 - 2, y2 - 2,
                            fill=hx(darker(color)), outline="")


def draw_ghost(canvas, gx, gy, color):
    canvas.create_rectangle(gx * CELL + 2, gy * CELL + 2,
                            gx * CELL + CELL - 2, gy * CELL + CELL - 2,
                            outline=hx(color), width=2)


root = tk.Tk()
root.title("俄罗斯方块 Tetris")
root.resizable(False, False)
root.configure(bg=BG)

board = tk.Canvas(root, width=BOARD_W, height=SCREEN_H,
                  bg=BOARD_BG, highlightthickness=0)
board.pack(side="left")

side = tk.Frame(root, width=SIDE_W, height=SCREEN_H, bg=BG)
side.pack(side="right", fill="y")
side.pack_propagate(False)

tk.Label(side, text="下一个", fg=MUTED, bg=BG,
         font=font(13)).place(x=20, y=14)
preview = tk.Canvas(side, width=140, height=88, bg=PANEL,
                    highlightthickness=1, highlightbackground=FRAME)
preview.place(x=20, y=44)
tk.Frame(side, bg=GRID, height=1, width=140).place(x=20, y=148)


def stat(title, y):
    tk.Label(side, text=title, fg=MUTED, bg=BG,
             font=font(12)).place(x=20, y=y)
    value = tk.Label(side, text="0", fg=ACCENT, bg=BG, font=font(20, True))
    value.place(x=20, y=y + 22)
    return value


lbl_score = stat("分数", 160)
lbl_level = stat("等级", 228)
lbl_lines = stat("消行", 296)
tk.Frame(side, bg=GRID, height=1, width=140).place(x=20, y=368)

HELP = (
    "← →   左右移动",
    "↑ / X   顺时针旋转",
    "Z   逆时针旋转",
    "↓ 软降   空格 硬降",
    "P 暂停   R 重开",
    "Esc 退出",
)
for i, line in enumerate(HELP):
    tk.Label(side, text=line, fg=MUTED, bg=BG, font=font(10),
             justify="left").place(x=18, y=380 + i * 24)

game = None
last_hard = [0.0]


def draw_preview():
    preview.delete("all")
    cells = ROTATIONS[game.next_type][0]
    w = max(x for x, _ in cells) + 1
    h = max(y for _, y in cells) + 1
    pw, ph = int(preview["width"]), int(preview["height"])
    ox, oy = (pw - w * CELL) / 2, (ph - h * CELL) / 2
    for dx, dy in cells:
        draw_block(preview, ox + dx * CELL, oy + dy * CELL,
                   RGB[game.next_type])


def draw_overlay():
    cx, cy = BOARD_W // 2, SCREEN_H // 2
    board.create_rectangle(cx - 118, cy - 68, cx + 118, cy + 68,
                           fill="#141824", outline=FRAME, width=2)
    if game.game_over:
        board.create_text(cx, cy - 28, text="游戏结束", fill="#ff7a7a",
                          font=font(26, True))
        board.create_text(cx, cy + 8, text="分数  %d" % game.score,
                          fill=TEXT_C, font=font(13))
        board.create_text(cx, cy + 38, text="按 R 重新开始", fill=MUTED,
                          font=font(11))
    else:
        board.create_text(cx, cy - 16, text="已暂停", fill=ACCENT,
                          font=font(26, True))
        board.create_text(cx, cy + 26, text="按 P 继续", fill=MUTED,
                          font=font(11))


def redraw():
    board.delete("all")
    for x in range(1, COLS):
        board.create_line(x * CELL, 0, x * CELL, SCREEN_H, fill=GRID)
    for y in range(1, ROWS):
        board.create_line(0, y * CELL, BOARD_W, y * CELL, fill=GRID)
    for y in range(ROWS):
        for x in range(COLS):
            t = game.board[y][x]
            if t:
                draw_block(board, x * CELL, y * CELL, RGB[t])
    if not game.game_over:
        t = game.piece["t"]
        offset = game.ghost_y() - game.piece["y"]
        for x, y in game.piece_cells():
            if y + offset >= 0:
                draw_ghost(board, x, y + offset, RGB[t])
        for x, y in game.piece_cells():
            if y >= 0:
                draw_block(board, x * CELL, y * CELL, RGB[t])
    board.create_rectangle(1, 1, BOARD_W - 1, SCREEN_H - 1,
                           outline=FRAME, width=2)
    if game.paused or game.game_over:
        draw_overlay()
    draw_preview()
    lbl_score.config(text=str(game.score))
    lbl_level.config(text=str(game.level))
    lbl_lines.config(text=str(game.lines))


def on_key(event):
    key = event.keysym.lower()
    if key == "escape":
        root.destroy()
        return
    if key == "r":
        game.reset()
        redraw()
        return
    if key == "p":
        game.paused = not game.paused
        redraw()
        return
    if game.paused or game.game_over:
        return
    if key == "left":
        game.move(-1)
    elif key == "right":
        game.move(1)
    elif key == "down":
        game.soft_drop()
    elif key in ("up", "x"):
        game.rotate(1)
    elif key == "z":
        game.rotate(-1)
    elif key == "space":
        now = time.monotonic()
        if now - last_hard[0] >= 0.15:      # 防止系统按键重复连续硬降
            last_hard[0] = now
            game.hard_drop()
    redraw()


def timer_step():
    if not game.paused and not game.game_over:
        game.soft_drop()
        redraw()
    delay = 60 if (game.paused or game.game_over) else game.fall_interval()
    root.after(delay, timer_step)


game = Tetris()
root.bind_all("<Key>", on_key)
root.focus_set()
redraw()
root.after(game.fall_interval(), timer_step)
root.mainloop()
