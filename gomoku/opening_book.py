"""开局策略模块

提供稳健的开局落子建议，包括：
- 黑棋第一手下天元
- 白棋第二手选择中心区域稳健点
- 前8手优先选择中心5×5区域
"""
from typing import Optional
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import index_to_coord, coord_to_index
from gomoku.forbidden import is_forbidden_move
from gomoku.evaluator import evaluate_move

_SIZE = 15

# 白2候选点（黑1=H8时）
_WHITE_SECOND_CANDIDATES = ["G8", "I8", "H7", "H9", "G7", "I7", "G9", "I9"]

# 中心5×5区域（F6到J10）
_CENTER_AREA = []
for r in range(5, 10):  # F=5, J=9
    for c in range(5, 10):
        _CENTER_AREA.append(index_to_coord(r, c))


class OpeningBook:
    """开局策略管理器"""

    def __init__(self):
        pass

    def choose_opening_move(
        self, board: Board, color: int, max_opening_moves: int = 8
    ) -> Optional[str]:
        """选择开局落子

        Args:
            board: 当前棋盘
            color: 落子方颜色
            max_opening_moves: 开局阶段最大步数

        Returns:
            推荐的落子坐标，或None（不在开局阶段）
        """
        # 统计当前步数
        move_count = self._count_moves(board)

        # 开局阶段定义：前max_opening_moves手
        if move_count >= max_opening_moves:
            return None

        # 空棋盘，黑1下天元
        if move_count == 0 and color == BLACK:
            return "H8"

        # 黑1=H8后，白2选择周围稳健点
        if move_count == 1 and color == WHITE:
            return self._choose_white_second(board)

        # 开局前8手，优先中心区域
        if color == WHITE or (color == BLACK and move_count > 0):
            return self._choose_center_move(board, color)

        return None

    def _count_moves(self, board: Board) -> int:
        """统计当前步数"""
        count = 0
        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] != EMPTY:
                    count += 1
        return count

    def _find_black_first_move(self, board: Board) -> Optional[str]:
        """查找黑1的位置"""
        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] == BLACK:
                    return index_to_coord(row, col)
        return None

    def _choose_white_second(self, board: Board) -> Optional[str]:
        """白2选择稳健落子（经过SafetyAdvisor过滤）"""
        black_first = self._find_black_first_move(board)
        if black_first is None:
            return None

        # 如果黑1是天元，白2选周围
        if black_first == "H8":
            candidates = _WHITE_SECOND_CANDIDATES
        else:
            # 黑1不在天元，白2跟棋
            candidates = self._get_adjacent_moves(board, black_first)

        best_move = None
        best_score = float("-inf")

        # 使用SafetyAdvisor过滤
        try:
            from gomoku.safety import SafetyAdvisor
            safety = SafetyAdvisor()
            candidates = safety.filter_safe_moves(board, WHITE, candidates)
        except:
            pass

        for move in candidates:
            row, col = coord_to_index(move)
            if board.grid[row][col] != EMPTY:
                continue

            score = evaluate_move(board, row, col, WHITE)
            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def _get_adjacent_moves(self, board: Board, coord: str) -> list:
        """获取某位置周围的候选点"""
        row, col = coord_to_index(coord)
        moves = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                    moves.append(index_to_coord(nr, nc))
        return moves

    def _choose_center_move(
        self, board: Board, color: int
    ) -> Optional[str]:
        """从中心区域选择落子（白棋使用SafetyAdvisor过滤）"""
        # 中心区域候选点
        center_candidates = []

        for move in _CENTER_AREA:
            row, col = coord_to_index(move)
            if board.grid[row][col] != EMPTY:
                continue

            # 黑棋检查禁手
            if color == BLACK:
                board.grid[row][col] = BLACK
                if is_forbidden_move(board, row, col, BLACK):
                    board.grid[row][col] = EMPTY
                    continue
                board.grid[row][col] = EMPTY

            center_candidates.append(move)

        if not center_candidates:
            return None

        # 白棋使用SafetyAdvisor过滤
        if color == WHITE:
            try:
                from gomoku.safety import SafetyAdvisor
                safety = SafetyAdvisor()
                safe_moves = safety.filter_safe_moves(board, color, center_candidates)
                if safe_moves:
                    center_candidates = safe_moves
            except:
                pass

        # 评分选择最高分
        best_move = None
        best_score = float("-inf")

        for move in center_candidates:
            row, col = coord_to_index(move)
            score = evaluate_move(board, row, col, color)
            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def is_in_opening_phase(self, board: Board, max_moves: int = 8) -> bool:
        """判断是否处于开局阶段"""
        return self._count_moves(board) < max_moves
