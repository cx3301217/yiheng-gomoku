"""攻击增强模块：提供强进攻点识别功能"""

from typing import Optional, List, Tuple
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import index_to_coord, coord_to_index
from gomoku.forbidden import is_forbidden_move
from gomoku.pattern import (
    analyze_point_patterns, FIVE, LIVE_FOUR, RUSH_FOUR,
    LIVE_THREE, SLEEP_THREE, LIVE_TWO, SLEEP_TWO
)

_SIZE = 15

# 强攻阈值：分数超过此值认为是强攻点
STRONG_ATTACK_THRESHOLD = 200000

# 棋型分数表
PATTERN_SCORES = {
    FIVE: 1000000,
    LIVE_FOUR: 500000,
    RUSH_FOUR: 100000,
    LIVE_THREE: 50000,
    SLEEP_THREE: 10000,
    LIVE_TWO: 5000,
    SLEEP_TWO: 1000,
}


class AttackAdvisor:
    """攻击增强顾问：寻找我方强进攻点"""

    @staticmethod
    def _is_legal_move(board: Board, row: int, col: int, color: int) -> bool:
        """检查落子是否合法"""
        if board.grid[row][col] != EMPTY:
            return False
        if color == BLACK:
            board.grid[row][col] = BLACK
            if is_forbidden_move(board, row, col, BLACK):
                board.grid[row][col] = EMPTY
                return False
            board.grid[row][col] = EMPTY
        return True

    @staticmethod
    def is_strong_attack_move(board: Board, row: int, col: int, color: int) -> bool:
        """判断单个点是否为强攻击点

        强攻判定：
        - 能形成活四
        - 能形成双冲四
        - 能形成活三+冲四
        - 能形成双活三
        - 综合分数超过阈值

        Args:
            board: 当前棋盘
            row: 行号(0-14)
            col: 列号(0-14)
            color: 我方颜色

        Returns:
            是否为强攻击点
        """
        if not AttackAdvisor._is_legal_move(board, row, col, color):
            return False

        # 临时落子
        board.grid[row][col] = color

        try:
            patterns = analyze_point_patterns(board, row, col, color)

            # 获取各棋型数量
            live_four = patterns.get(LIVE_FOUR, 0)
            rush_four = patterns.get(RUSH_FOUR, 0)
            live_three = patterns.get(LIVE_THREE, 0)
            sleep_three = patterns.get(SLEEP_THREE, 0)

            # 强攻判定1: 能形成活四
            if live_four >= 1:
                return True

            # 强攻判定2: 能形成双冲四
            if rush_four >= 2:
                return True

            # 强攻判定3: 能形成活三+冲四
            if live_three >= 1 and rush_four >= 1:
                return True

            # 强攻判定4: 能形成双活三
            if live_three >= 2:
                return True

            # 强攻判定5: 计算综合分数
            score = (
                live_four * PATTERN_SCORES[LIVE_FOUR] +
                rush_four * PATTERN_SCORES[RUSH_FOUR] +
                live_three * PATTERN_SCORES[LIVE_THREE] +
                sleep_three * PATTERN_SCORES[SLEEP_THREE]
            )
            if score >= STRONG_ATTACK_THRESHOLD:
                return True

        finally:
            # 还原棋盘
            board.grid[row][col] = EMPTY

        return False

    @staticmethod
    def find_strong_attack(board: Board, color: int) -> Optional[str]:
        """寻找我方强进攻点

        遍历所有候选位置，找到评分最高的强攻点。

        Args:
            board: 当前棋盘
            color: 我方颜色

        Returns:
            强进攻点坐标，不存在则返回None
        """
        candidates = AttackAdvisor._get_candidates(board)

        best_move = None
        best_score = 0

        for coord in candidates:
            row, col = coord_to_index(coord)

            if not AttackAdvisor._is_legal_move(board, row, col, color):
                continue

            # 临时落子
            board.grid[row][col] = color

            try:
                patterns = analyze_point_patterns(board, row, col, color)

                # 计算分数
                score = 0
                is_strong = False

                live_four = patterns.get(LIVE_FOUR, 0)
                rush_four = patterns.get(RUSH_FOUR, 0)
                live_three = patterns.get(LIVE_THREE, 0)
                sleep_three = patterns.get(SLEEP_THREE, 0)
                live_two = patterns.get(LIVE_TWO, 0)
                sleep_two = patterns.get(SLEEP_TWO, 0)

                # 强攻判定
                if live_four >= 1:
                    is_strong = True
                    score = PATTERN_SCORES[LIVE_FOUR] + rush_four * 1000 + live_three * 100
                elif rush_four >= 2:
                    is_strong = True
                    score = PATTERN_SCORES[RUSH_FOUR] * 2 + live_three * 100
                elif live_three >= 1 and rush_four >= 1:
                    is_strong = True
                    score = PATTERN_SCORES[RUSH_FOUR] + PATTERN_SCORES[LIVE_THREE] * 2
                elif live_three >= 2:
                    is_strong = True
                    score = PATTERN_SCORES[LIVE_THREE] * 2 + rush_four * 100
                else:
                    # 非强攻点，计算普通分数
                    score = (
                        rush_four * PATTERN_SCORES[RUSH_FOUR] +
                        live_three * PATTERN_SCORES[LIVE_THREE] +
                        sleep_three * PATTERN_SCORES[SLEEP_THREE] +
                        live_two * PATTERN_SCORES[LIVE_TWO] +
                        sleep_two * PATTERN_SCORES[SLEEP_TWO]
                    )
                    if score >= STRONG_ATTACK_THRESHOLD:
                        is_strong = True

                # 只返回强攻点
                if is_strong and score > best_score:
                    best_score = score
                    best_move = coord

            finally:
                board.grid[row][col] = EMPTY

        return best_move

    @staticmethod
    def get_attack_score(board: Board, row: int, col: int, color: int) -> int:
        """获取落子点的攻击评分

        不改变棋盘状态。

        Args:
            board: 当前棋盘
            row: 行号
            col: 列号
            color: 颜色

        Returns:
            攻击评分
        """
        if board.grid[row][col] != EMPTY:
            return 0

        # 临时落子
        board.grid[row][col] = color

        try:
            patterns = analyze_point_patterns(board, row, col, color)

            live_four = patterns.get(LIVE_FOUR, 0)
            rush_four = patterns.get(RUSH_FOUR, 0)
            live_three = patterns.get(LIVE_THREE, 0)
            sleep_three = patterns.get(SLEEP_THREE, 0)
            live_two = patterns.get(LIVE_TWO, 0)
            sleep_two = patterns.get(SLEEP_TWO, 0)

            return (
                live_four * PATTERN_SCORES[LIVE_FOUR] +
                rush_four * PATTERN_SCORES[RUSH_FOUR] +
                live_three * PATTERN_SCORES[LIVE_THREE] +
                sleep_three * PATTERN_SCORES[SLEEP_THREE] +
                live_two * PATTERN_SCORES[LIVE_TWO] +
                sleep_two * PATTERN_SCORES[SLEEP_TWO]
            )
        finally:
            board.grid[row][col] = EMPTY

    @staticmethod
    def _get_candidates(board: Board) -> List[str]:
        """获取候选落子位置"""
        candidates = []
        checked = set()

        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] != EMPTY:
                    for dr in range(-1, 2):
                        for dc in range(-1, 2):
                            if dr == 0 and dc == 0:
                                continue
                            nr, nc = row + dr, col + dc
                            if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                                if board.grid[nr][nc] == EMPTY:
                                    key = (nr, nc)
                                    if key not in checked:
                                        checked.add(key)
                                        candidates.append(index_to_coord(nr, nc))

        return candidates if candidates else [index_to_coord(7, 7)]
