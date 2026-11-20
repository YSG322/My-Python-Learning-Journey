# My-Python-Learning-Journey

> 我的第一个 GitHub 仓库：用 Python 从零实现俄罗斯方块（Tetris），包含 **pygame** 与 **tkinter** 两个版本。本文件严格使用 [Markdown](https://www.markdownguide.org/basic-syntax/) 语法编写，可到 [仓库页面](https://github.com/YSG322/My-Python-Learning-Journey) 查看渲染后的效果。

用 [Python](https://www.python.org/) 从零实现的俄罗斯方块小游戏，同时作为 Python 课程的学习记录仓库。

---

## 项目简介

**解决的问题**：想要一个 *开箱即玩、不用装任何第三方库* 的桌面小游戏，同时用一份完整可读的代码把游戏循环、二维碰撞检测、状态机这些基础概念讲清楚。

**做法**：把游戏拆成两层——`Tetris` 类只负责规则（棋盘、方块、碰撞、消行、计分），界面层只负责画图和接收按键。因此同一套规则可以配两种界面：

- **pygame 版**：画面细腻，支持半透明落点预览、圆角方块，依赖 [pygame](https://www.pygame.org/)
- **tkinter 版**：只用标准库，装好 Python 就能运行，无需 `pip install`

**主要功能**

- [x] 7 种标准方块，7-bag 随机算法（每 7 个方块内每种恰好出现一次）
- [x] 四向旋转，带简易墙踢（贴墙、贴地旋转时自动让位）
- [x] 半透明落点预览、下一个方块预览
- [x] 消行计分：1 / 2 / 3 / 4 行分别得 100 / 300 / 500 / 800 分，再乘以当前等级
- [x] 每消 10 行升一级，下落速度随之加快
- [x] 暂停、重新开始、游戏结束判定
- [x] 界面优先使用系统中文字体，找不到时自动切换为英文，不出现乱码方块
- [x] 游戏逻辑与渲染分离，便于测试和替换界面
- [ ] 音效与排行榜（列入后续规划，尚未实现）

---

## 目录结构

```text
My-Python-Learning-Journey/
├── tetris.py           # pygame 版本
├── tetris_tk.py        # tkinter 零依赖版本
├── requirements.txt    # pygame 版本的依赖清单
├── README.md           # 项目说明（本文件，Markdown 格式）
└── .gitignore          # 忽略缓存与本地临时文件
```

## 文件说明

| 文件 | 类型 | 用途 |
| :--- | :--- | :--- |
| `tetris.py` | Python 源码 | pygame 版本入口。包含 `Tetris` 规则类、字体探测、棋盘/侧栏渲染与 `main()` 主循环，约 470 行 |
| `tetris_tk.py` | Python 源码 | tkinter 版本入口。规则类与上面一致，界面改用 `Canvas` 绘制，定时器改用 `after()` 驱动，无需第三方库，约 385 行 |
| `requirements.txt` | 依赖清单 | 仅一行 `pygame>=2.5.0`，供 `pip install -r` 使用 |
| `README.md` | Markdown 文档 | 项目简介、目录与文件说明、运行方式、核心代码讲解、学习心得 |
| `.gitignore` | 配置 | 排除 `__pycache__/`、虚拟环境、编辑器配置等 |

## 运行

按下面两步任选一种方式启动：

1. **tkinter 版（推荐，零依赖）**：装好 Python 即可，无需 `pip install`。
2. **pygame 版**：先安装 [pygame](https://www.pygame.org/) 依赖，再运行游戏。

```bash
# 方式一：tkinter 版
python tetris_tk.py

# 方式二：pygame 版
pip install -r requirements.txt
python tetris.py
```

两个版本规则完全相同，玩法一致。只有 Python 环境、没有网络时，用方式一即可。

## 操作

| 按键 | 作用 |
| :--- | :--- |
| `←` / `→` | 左右移动（长按连发） |
| `↓` | 软降，每格 +1 分 |
| `↑` 或 `X` | 顺时针旋转 |
| `Z` | 逆时针旋转 |
| `空格` | 硬降，每格 +2 分 |
| `P` | 暂停 / 继续 |
| `R` | 重新开始 |
| `Esc` | 退出 |

---

## 代码说明

> 说明：以下代码块节选自 [`tetris.py`](tetris.py)，为便于阅读省略了类方法的缩进层级，逻辑与实际源码一致。

### 1. 方块形状与旋转：用一份基准坐标生成四个旋转态

每种方块只手写一个初始形态，其余三个旋转态由坐标变换自动推导，避免手抄 28 组坐标出错。旋转公式为屏幕坐标下的顺时针 90 度：`(x, y) -> (-y, x)`，旋转后再统一"归一化"到左上角，防止方块在旋转时整体漂移。

```python
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
```

`ROTATIONS[t][r]` 即可取到方块 `t` 的第 `r` 个旋转态，渲染和碰撞检测都只读这张表。

### 2. 随机出块：7-bag 算法

纯随机容易出现"连着来五个 S 形"的难受体验。这里用 7-bag：把 7 种方块放进一个袋子打乱，逐个取出，取空再补一袋。这样任意连续 7 个方块内每种恰好出现一次。

```python
def _take(self):
    # 7-bag 随机：每 7 个方块内每种各出现一次，手感更公平
    if not self.bag:
        self.bag = list(BASE_CELLS)
        random.shuffle(self.bag)
    return self.bag.pop()
```

### 3. 碰撞检测：整个游戏的判定基石

移动、旋转、下落、落点预览全都复用同一个 `fits()`。它只做两件事：越界判断（左右下出界）和占用判断（目标格已有方块）。允许 `y < 0`，是为了让方块在顶部"半露"时也能正常出生。

```python
def fits(self, cells):
    for x, y in cells:
        if x < 0 or x >= COLS or y >= ROWS:
            return False
        if y >= 0 and self.board[y][x] is not None:
            return False
    return True
```

### 4. 旋转墙踢：贴墙时不至于转不动

严格按原坐标旋转，方块贴墙时会因越界而"转不了"。这里按 `0, -1, +1, -2, +2` 的顺序尝试左右平移，都不行再上抬一格，实现最基础的墙踢。

```python
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
```

### 5. 消行与计分：删行 + 顶部补空行

判断某行是否填满用 `all(row)`；消行时直接删除整行，再在顶部插入一个全空行，行数天然保持不变，不需要额外维护索引。

```python
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
```

### 6. 下落节奏：按等级缩短间隔

自动下落不用固定延时，而是累计时间到达间隔才落一格，等级越高间隔越短，最低 70 毫秒封顶，避免高等级下快到无法操作。

```python
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
```

### 7. 逻辑与界面分离：换界面不用改规则

`Tetris` 类不导入任何界面库，只暴露 `move()`、`rotate()`、`hard_drop()`、`tick()` 等方法。pygame 版把这些方法绑到键盘事件上，tkinter 版绑到 `on_key()`，两边共用同一套规则：

```python
class Tetris:
    def __init__(self):
        self.reset()
```

其中 `board` 是 `ROWS × COLS` 的二维列表，空格为 `None`，已固定的方块存放类型字母。这样做的好处是：规则可以脱离窗口单独测试，新增第三个界面（比如命令行版本）时不必重写任何判定逻辑。

---

## 学习心得与规划

浏览 GitHub 上其他 Python 小项目后，我发现受欢迎的仓库有个共同点：README 开头三句话就说清"这是什么、解决什么问题、怎么跑起来"，然后才展开细节。我第 1 次作业的 README 只列了功能，别人进来并不知道从哪下手，这次把它改成"先讲用途、再给可复制的命令、最后解释核心代码"的顺序。

过程中也踩了坑。最初想把所有内容堆在一个文件里，改一处要动好几处；拆成"规则层 + 界面层"后，两个版本共用一套判定，新增界面只写绘制。这让我意识到文档写得短，前提是代码结构本身清楚。

具体启发有三点：一是 README 是个人项目的门面，读者（包括几个月后的自己）先看文档再看代码；二是提交信息要能独立读懂，我坚持用 `feat:` 前缀加一句说明，回看历史能还原当时思路；三是展示技能靠可运行的东西，而不是罗列名词。

后续我打算把这个仓库当作学习台账：每学一个主题就新增一个独立项目目录，配一份说明它解决什么问题的 README；每个项目至少有一次"能跑通"的提交和一张运行截图；每月整理一次目录与更新记录，把重复代码抽成可复用模块。这样半年后回看，仓库本身就是一份能证明进步的记录。

---

## 更新记录

- 2026-11-19：完成 pygame 版俄罗斯方块，添加项目说明
- 2026-11-19：新增 tkinter 零依赖版本
- 2026-11-20：按第 2 次作业要求重写 README，补充项目简介、文件说明与核心代码讲解
- 2026-11-20：按严格 Markdown 语法校正 README，补全有序列表、引用块、超链接、分割线与任务列表

> 说明：本项目为 Python 课程平时作业，代码与文档均为个人独立完成；仓库内仅保留 `.py` 源码及必要的项目文件。
