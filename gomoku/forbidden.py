"""黑棋禁手检测模块"""
from typing import Tuple, List
import re
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.pattern import get_line_string

_DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]


def count_line(board: Board, row: int, col: int, color: int, dr: int, dc: int) -> int:
    return board.count_continuous(row, col, color, dr, dc)


def is_overline(board: Board, row: int, col: int, color: int) -> bool:
    if board.grid[row][col] != color:
        return False
    for dr, dc in _DIRECTIONS:
        if board.get_line_count(row, col, color, dr, dc) > 5:
            return True
    return False


def _count_by_line(board: Board, row: int, col: int,
                   color: int) -> Tuple[int, int]:
    """统计四个方向的活三和四连数量

    策略：对每个方向使用滑动窗口统计重叠的四连和三连。
    - 四连：窗口大小4，两端为空
    - 三连：窗口大小3，两端为空

    注意：本版本基础覆盖连续活三、连续活四和基础冲四；
    复杂跳三、跳四和特殊禁手形态后续可继续强化。
    """
    live_threes = 0
    fours = 0

    for dr, dc in _DIRECTIONS:
        line = get_line_string(board, row, col, color, dr, dc, radius=7)

        # 使用滑动窗口统计四连（允许重叠）
        for i in range(len(line) - 4 + 1):
            window = line[i:i + 4]
            if window.count("X") != 4:
                continue
            left = line[i - 1] if i > 0 else "#"
            right = line[i + 4] if i + 4 < len(line) else "#"
            if left in (".", "#") and right in (".", "#", "O"):
                fours += 1

        # 使用滑动窗口统计活三（允许重叠）
        for i in range(len(line) - 3 + 1):
            window = line[i:i + 3]
            if window.count("X") != 3:
                continue
            left = line[i - 1] if i > 0 else "#"
            right = line[i + 3] if i + 3 < len(line) else "#"
            if left == "." and right == ".":
                live_threes += 1

    return live_threes, fours


def is_double_three(board: Board, row: int, col: int, color: int) -> bool:
    if color != BLACK:
        return False
    if board.grid[row][col] != BLACK:
        return False
    if board.has_exact_five(row, col, BLACK):
        return False
    lt, _ = _count_by_line(board, row, col, BLACK)
    return lt >= 2


def is_double_four(board: Board, row: int, col: int, color: int) -> bool:
    if color != BLACK:
        return False
    if board.grid[row][col] != BLACK:
        return False
    if board.has_exact_five(row, col, BLACK):
        return False
    _, f = _count_by_line(board, row, col, BLACK)
    return f >= 2


def is_forbidden_move(board: Board, row: int, col: int, color: int) -> bool:
    """检查黑棋是否禁手

    Args:
        board: 棋盘对象
        row: 行坐标
        col: 列坐标
        color: 棋子颜色

    Returns:
        如果是黑棋禁手返回True，否则返回False
    """
    if color != BLACK:
        return False
    if board.grid[row][col] != BLACK:
        return False
    if board.has_exact_five(row, col, BLACK):
        return False
    if is_overline(board, row, col, BLACK):
        return True
    if is_double_three(board, row, col, BLACK):
        return True
    if is_double_four(board, row, col, BLACK):
        return True
    return False


def get_forbidden_type(board: Board, row: int, col: int, color: int) -> Tuple[bool, str]:
    """获取禁手类型

    Args:
        board: 棋盘对象
        row: 行坐标
        col: 列坐标
        color: 棋子颜色

    Returns:
        (是否禁手, 禁手类型)
        禁手类型: "OVERLINE" / "DOUBLE_THREE" / "DOUBLE_FOUR" / ""
    """
    if color != BLACK:
        return (False, "")
    if board.grid[row][col] != BLACK:
        return (False, "")
    if board.has_exact_five(row, col, BLACK):
        return (False, "")
    if is_overline(board, row, col, BLACK):
        return (True, "OVERLINE")
    if is_double_three(board, row, col, BLACK):
        return (True, "DOUBLE_THREE")
    if is_double_four(board, row, col, BLACK):
        return (True, "DOUBLE_FOUR")
    return (False, "")
