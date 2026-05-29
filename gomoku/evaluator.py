"""局面评分模块：对候选落子进行评分排序"""
from typing import List, Tuple
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.pattern import (
    FIVE, LIVE_FOUR, RUSH_FOUR,
    LIVE_THREE, SLEEP_THREE,
    LIVE_TWO, SLEEP_TWO,
    analyze_point_patterns,
)
from gomoku.coordinate import coord_to_index, index_to_coord
from gomoku.forbidden import is_forbidden_move


def get_candidate_moves(board: Board) -> List[str]:
    """获取候选落子位置列表

    优先返回已有棋子周围一格内的空位，
    如果棋盘为空则返回天元。

    Args:
        board: 当前棋盘

    Returns:
        候选坐标列表
    """
    candidates = []
    checked = set()
    SIZE = 15

    for row in range(SIZE):
        for col in range(SIZE):
            if board.grid[row][col] != EMPTY:
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = row + dr, col + dc
                        if 0 <= nr < SIZE and 0 <= nc < SIZE:
                            if board.grid[nr][nc] == EMPTY:
                                key = (nr, nc)
                                if key not in checked:
                                    checked.add(key)
                                    candidates.append(index_to_coord(nr, nc))

    return candidates

# 各棋型基础分值
_SCORES = {
    FIVE: 10_000_000,
    LIVE_FOUR: 1_000_000,
    RUSH_FOUR: 100_000,
    LIVE_THREE: 10_000,
    SLEEP_THREE: 1_000,
    LIVE_TWO: 100,
    SLEEP_TWO: 10,
}

# 特殊组合加分
_COMBO_BONUS = {
    # 双活三（两个活三同时存在，几乎必胜）
    "double_live_three": 500_000,
    # 活三+冲四组合
    "live_three_rush_four": 200_000,
    # 双冲四
    "double_rush_four": 300_000,
}


def score_point(board: Board, row: int, col: int, color: int) -> int:
    """假设在指定位置落子后，评估该落子的棋型分

    Args:
        board: 当前棋盘
        row: 落子行号
        col: 落子列号
        color: 落子方颜色

    Returns:
        该落子的评分（分数越高越好）
    """
    if board.grid[row][col] != EMPTY:
        return -1_000_000

    # 黑棋禁手检查
    if color == BLACK:
        board.grid[row][col] = BLACK
        if is_forbidden_move(board, row, col, BLACK):
            board.grid[row][col] = EMPTY
            return -1_000_000
        board.grid[row][col] = EMPTY

    # 临时落子
    board.grid[row][col] = color

    try:
        patterns = analyze_point_patterns(board, row, col, color)
        score = _compute_pattern_score(patterns)
    finally:
        board.grid[row][col] = EMPTY

    return score


def _compute_pattern_score(patterns: dict) -> int:
    """根据棋型统计计算总分"""
    total = 0
    p = patterns

    total += p[FIVE] * _SCORES[FIVE]
    total += p[LIVE_FOUR] * _SCORES[LIVE_FOUR]
    total += p[RUSH_FOUR] * _SCORES[RUSH_FOUR]
    total += p[LIVE_THREE] * _SCORES[LIVE_THREE]
    total += p[SLEEP_THREE] * _SCORES[SLEEP_THREE]
    total += p[LIVE_TWO] * _SCORES[LIVE_TWO]
    total += p[SLEEP_TWO] * _SCORES[SLEEP_TWO]

    # 特殊组合加分
    if p[LIVE_THREE] >= 2:
        total += _COMBO_BONUS["double_live_three"]
    if p[LIVE_THREE] >= 1 and p[RUSH_FOUR] >= 1:
        total += _COMBO_BONUS["live_three_rush_four"]
    if p[RUSH_FOUR] >= 2:
        total += _COMBO_BONUS["double_rush_four"]

    return total


def evaluate_board(board: Board, color: int) -> int:
    """计算当前棋盘对 color 的总体评分

    遍历所有 color 棋子，累加各棋型分数。

    Args:
        board: 当前棋盘
        color: 评估方颜色

    Returns:
        棋盘总分
    """
    total = 0
    for row in range(board.size):
        for col in range(board.size):
            if board.grid[row][col] == color:
                patterns = analyze_point_patterns(board, row, col, color)
                total += _compute_pattern_score(patterns)
    return total


def evaluate_move(
    board: Board, row: int, col: int, color: int
) -> int:
    """评估某候选落子的综合价值

    综合考虑我方进攻分和对方威胁分（白棋防守权重更高）。

    Args:
        board: 当前棋盘
        row: 候选行号
        col: 候选列号
        color: 我方颜色

    Returns:
        综合评分
    """
    opponent = WHITE if color == BLACK else BLACK

    # 位置非空，直接返回极低分
    if board.grid[row][col] != EMPTY:
        return -1_000_000

    # 我方进攻分
    attack = score_point(board, row, col, color)

    # 如果我方落子触发觉手，返回禁手极低分
    if attack <= -1_000_000:
        return attack

    # 对方威胁分（模拟对方落子后评估）
    defense = score_point(board, row, col, opponent)

    # 如果对方落子无效或禁手，分数设为0
    if defense < 0:
        defense = 0

    # 白棋适当提高防守权重，但仍保留进攻能力
    if color == WHITE:
        return int(attack * 1.05 + defense * 1.15)
    else:
        # 黑棋略偏进攻
        return int(attack * 1.15 + defense * 1.0)


def get_scored_moves(
    board: Board, color: int, limit: int = 10
) -> List[Tuple[str, int]]:
    """返回评分最高的候选落子列表

    候选点来自 engine 模块的 get_candidate_moves，
    黑棋会过滤禁手点。

    Args:
        board: 当前棋盘
        color: 落子方颜色
        limit: 返回数量上限

    Returns:
        按分数降序排列的列表，每个元素为 (坐标字符串, 分数)
    """
    candidates = _get_valid_candidates(board, color)

    scored = []
    for coord_str in candidates:
        row, col = coord_to_index(coord_str)
        score = evaluate_move(board, row, col, color)
        scored.append((coord_str, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def _get_valid_candidates(board: Board, color: int) -> List[str]:
    """获取有效候选点（黑棋过滤禁手）"""
    candidates = get_candidate_moves(board)
    if color != BLACK:
        return candidates

    valid = []
    for coord_str in candidates:
        row, col = coord_to_index(coord_str)
        board.grid[row][col] = BLACK
        if is_forbidden_move(board, row, col, BLACK):
            board.grid[row][col] = EMPTY
            continue
        board.grid[row][col] = EMPTY
        valid.append(coord_str)
    return valid if valid else candidates
