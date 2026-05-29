"""棋型识别模块：识别五子棋常见棋型"""
from gomoku.board import Board, BLACK, WHITE, EMPTY

# 四个方向: 横向、纵向、左上到右下、左下到右上
_DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]

# 棋型名称常量
FIVE = "FIVE"
LIVE_FOUR = "LIVE_FOUR"
RUSH_FOUR = "RUSH_FOUR"
LIVE_THREE = "LIVE_THREE"
SLEEP_THREE = "SLEEP_THREE"
LIVE_TWO = "LIVE_TWO"
SLEEP_TWO = "SLEEP_TWO"
NONE = "NONE"

# 所有棋型名称列表（用于统计分析）
ALL_PATTERNS = [
    FIVE, LIVE_FOUR, RUSH_FOUR,
    LIVE_THREE, SLEEP_THREE,
    LIVE_TWO, SLEEP_TWO,
]


def get_line_string(
    board: Board,
    row: int,
    col: int,
    color: int,
    dr: int,
    dc: int,
    radius: int = 5
) -> str:
    """以(row,col)为中心，沿指定方向取一条线段并转成字符串

    编码规则:
    - "X" 表示当前颜色棋子
    - "O" 表示对方棋子
    - "." 表示空位
    - "#" 表示棋盘边界

    Args:
        board: 当前棋盘
        row: 中心行号
        col: 中心列号
        color: 当前颜色
        dr: 行方向增量
        dc: 列方向增量
        radius: 向每个方向扩展的格数（默认5，即总长11）

    Returns:
        线段字符串
    """
    opponent = WHITE if color == BLACK else BLACK
    chars = []

    for i in range(-radius, radius + 1):
        r = row + i * dr
        c = col + i * dc
        if not board._in_bounds(r, c):
            chars.append("#")
        else:
            cell = board.grid[r][c]
            if cell == EMPTY:
                chars.append(".")
            elif cell == color:
                chars.append("X")
            else:
                chars.append("O")

    return "".join(chars)


def classify_line_pattern(line: str) -> str:
    """根据线段字符串识别棋型

    识别顺序从高到低：先判五连，再判活四/冲四，最后判三、二。

    边界符号 "#" 表示该方向已达到棋盘边缘。

    Args:
        line: 由 get_line_string 生成的字符串

    Returns:
        棋型名称字符串
    """
    # ---- 五连 ----
    if "XXXXX" in line:
        return FIVE

    # ---- 活四：两端都是空位的四连 ----
    if ".XXXX." in line:
        return LIVE_FOUR

    # ---- 冲四：一端被堵的四连 ----
    # 形态1: OXXXX.  .XXXXO  #XXXX.  .XXXX#
    if "OXXXX." in line or ".XXXXO" in line:
        return RUSH_FOUR
    if "#XXXX." in line or ".XXXX#" in line:
        return RUSH_FOUR

    # 形态2: 跳四形态
    # XX.XX: 中间有空格的四连
    if "XX.XX" in line:
        return RUSH_FOUR
    # XXX.X: 末尾有跳空
    if "XXX.X" in line:
        return RUSH_FOUR
    # X.XXX: 开头有跳空
    if "X.XXX" in line:
        return RUSH_FOUR

    # ---- 活三：两端都是空位的三连 ----
    # .XXX.  中心为活三
    if ".XXX." in line:
        return LIVE_THREE
    # .X.XX. 和 .XX.X. 也是活三（可以延伸到活四）
    if ".X.XX." in line or ".XX.X." in line:
        return LIVE_THREE
    # 跳三形态: X.XX.  .XX.X  （一端空位，一端有棋）
    if "X.XX.." in line or "..XX.X" in line:
        return LIVE_THREE

    # ---- 眠三：一端被堵住的三连 ----
    # OXXX.  .XXXO  #XXX.  .XXX#
    if "OXXX." in line or ".XXXO" in line:
        return SLEEP_THREE
    if "#XXX." in line or ".XXX#" in line:
        return SLEEP_THREE
    # XX.X.  .X.XX  （三连中间有跳空，一端堵住）
    if "XX.X." in line or ".X.XX" in line:
        return SLEEP_THREE

    # ---- 活二：两端都是空位的二连 ----
    if ".XX." in line:
        return LIVE_TWO
    if ".X.X." in line:
        return LIVE_TWO

    # ---- 眠二：一端被堵住的二连 ----
    if "OXX.." in line or "..XXO" in line:
        return SLEEP_TWO
    if "#XX.." in line or "..XX#" in line:
        return SLEEP_TWO

    return NONE


def analyze_point_patterns(
    board: Board, row: int, col: int, color: int
) -> dict:
    """分析某个位置在四个方向上的棋型

    Args:
        board: 当前棋盘
        row: 落子行号
        col: 落子列号
        color: 落子方颜色

    Returns:
        字典，键为棋型名称，值为该棋型在四个方向中出现的次数
    """
    result = {p: 0 for p in ALL_PATTERNS}

    for dr, dc in _DIRECTIONS:
        line = get_line_string(board, row, col, color, dr, dc, radius=5)
        pattern = classify_line_pattern(line)
        if pattern in result:
            result[pattern] += 1

    return result


def classify_all(board: Board, color: int) -> list:
    """对棋盘上所有 color 棋子进行棋型分析

    Args:
        board: 当前棋盘
        color: 要分析的颜色

    Returns:
        列表，每个元素是 (row, col, patterns_dict)
    """
    results = []
    for row in range(board.size):
        for col in range(board.size):
            if board.grid[row][col] == color:
                patterns = analyze_point_patterns(board, row, col, color)
                results.append((row, col, patterns))
    return results


def count_patterns_after_move(
    board: Board, row: int, col: int, color: int
) -> dict:
    """分析某落子后在四个方向上的各类型数量（不过滤FIVE）

    与 analyze_point_patterns 的区别：
    该函数按 FIVE > LIVE_FOUR > RUSH_FOUR > LIVE_THREE > SLEEP_THREE 优先匹配，
    每个方向只返回一个最高类型。
    本函数不过滤 FIVE，直接统计各类型在四个方向中出现的次数，
    用于三三禁手、四四禁手的判定。

    Returns:
        字典，键为棋型名称，值为该棋型在四个方向中出现的次数
    """
    result = {p: 0 for p in ALL_PATTERNS}

    for dr, dc in _DIRECTIONS:
        line = get_line_string(board, row, col, color, dr, dc, radius=7)
        pattern = _classify_without_five(line)
        if pattern in result:
            result[pattern] += 1

    return result


def _classify_without_five(line: str) -> str:
    """分析线串棋型（跳过FIVE优先匹配）

    与 classify_line_pattern 的区别是不判五连，
    使活三/活四计数在三三/四四禁手判断中始终有效。
    """
    # ---- 活四：两端都是空位的四连 ----
    if ".XXXX." in line:
        return LIVE_FOUR

    # ---- 冲四：一端被堵的四连 ----
    if "OXXXX." in line or ".XXXXO" in line:
        return RUSH_FOUR
    if "#XXXX." in line or ".XXXX#" in line:
        return RUSH_FOUR

    # 形态2: 跳四形态
    if "XX.XX" in line:
        return RUSH_FOUR
    if "XXX.X" in line:
        return RUSH_FOUR
    if "X.XXX" in line:
        return RUSH_FOUR

    # ---- 活三：两端都是空位的三连 ----
    if ".XXX." in line:
        return LIVE_THREE
    if ".X.XX." in line or ".XX.X." in line:
        return LIVE_THREE
    if "X.XX.." in line or "..XX.X" in line:
        return LIVE_THREE

    # ---- 眠三：一端被堵住的三连 ----
    if "OXXX." in line or ".XXXO" in line:
        return SLEEP_THREE
    if "#XXX." in line or ".XXX#" in line:
        return SLEEP_THREE
    if "XX.X." in line or ".X.XX" in line:
        return SLEEP_THREE

    # ---- 活二：两端都是空位的二连 ----
    if ".XX." in line:
        return LIVE_TWO
    if ".X.X." in line:
        return LIVE_TWO

    # ---- 眠二：一端被堵住的二连 ----
    if "OXX.." in line or "..XXO" in line:
        return SLEEP_TWO
    if "#XX.." in line or "..XX#" in line:
        return SLEEP_TWO

    # ---- 五连（放最后，因为活四也含XXXX） ----
    if "XXXXX" in line:
        return FIVE

    return NONE
