"""安全落子过滤模块

提供安全落子检测和过滤功能，避免落子后给对方留下必胜机会。
"""
from typing import List, Optional
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import coord_to_index, index_to_coord
from gomoku.forbidden import is_forbidden_move
from gomoku.evaluator import evaluate_move, get_scored_moves

_SIZE = 15


class SafetyAdvisor:
    """安全落子顾问"""

    def __init__(self):
        pass

    def is_safe_move(
        self, board: Board, row: int, col: int, color: int
    ) -> bool:
        """判断某落子是否安全

        Args:
            board: 当前棋盘
            row: 落子行号
            col: 落子列号
            color: 落子方颜色

        Returns:
            True表示安全，False表示危险
        """
        # 位置非空，不安全
        if board.grid[row][col] != EMPTY:
            return False

        # 黑棋检查禁手
        if color == BLACK:
            board.grid[row][col] = BLACK
            if is_forbidden_move(board, row, col, BLACK):
                board.grid[row][col] = EMPTY
                return False
            board.grid[row][col] = EMPTY

        # 临时落子
        board.grid[row][col] = color

        opponent = WHITE if color == BLACK else BLACK
        safe = True

        # 检查对方是否一步胜
        if self._has_winning_move(board, opponent):
            safe = False

        # 检查对方是否有VCF
        if safe and self._has_vcf(board, opponent):
            safe = False

        # 检查对方是否有VCT
        if safe and self._has_vct(board, opponent):
            safe = False

        # 还原棋盘
        board.grid[row][col] = EMPTY

        return safe

    def _has_winning_move(self, board: Board, opponent: int) -> bool:
        """检查是否存在一步胜"""
        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] == EMPTY:
                    board.grid[row][col] = opponent
                    if opponent == BLACK:
                        if is_forbidden_move(board, row, col, BLACK):
                            board.grid[row][col] = EMPTY
                            continue
                        win = board.has_exact_five(row, col, opponent)
                    else:
                        win = board.has_five_or_more(row, col, opponent)
                    board.grid[row][col] = EMPTY
                    if win:
                        return True
        return False

    def _has_vcf(self, board: Board, opponent: int) -> bool:
        """检查是否存在VCF"""
        try:
            from gomoku.threat_search import ThreatSearcher
            searcher = ThreatSearcher(max_vcf_depth=3)
            vcf_move = searcher.vcf_search(board, opponent, 3)
            return vcf_move is not None
        except:
            return False

    def _has_vct(self, board: Board, opponent: int) -> bool:
        """检查是否存在VCT"""
        try:
            from gomoku.threat_search import ThreatSearcher
            searcher = ThreatSearcher(max_vcf_depth=3, candidate_limit=6)
            vct_move = searcher.vct_search(board, opponent, 3)
            return vct_move is not None
        except:
            return False

    def filter_safe_moves(
        self, board: Board, color: int, moves: List[str]
    ) -> List[str]:
        """过滤危险落子，返回安全点列表

        Args:
            board: 当前棋盘
            color: 落子方颜色
            moves: 候选点列表

        Returns:
            安全点列表（保持原顺序）
        """
        safe_moves = []

        for move in moves:
            try:
                row, col = coord_to_index(move)
            except:
                continue

            if self.is_safe_move(board, row, col, color):
                safe_moves.append(move)

        # 如果存在安全点，返回安全点
        # 如果全部不安全，返回原列表（避免无子可下）
        if safe_moves:
            return safe_moves
        return moves

    def get_safest_move(
        self, board: Board, color: int, moves: List[str]
    ) -> Optional[str]:
        """在候选点中选择最安全的落子

        Args:
            board: 当前棋盘
            color: 落子方颜色
            moves: 候选点列表

        Returns:
            最佳落子坐标
        """
        if not moves:
            return None

        # 先过滤安全点
        safe_moves = self.filter_safe_moves(board, color, moves)

        # 对安全点评分
        best_move = None
        best_score = float("-inf")

        for move in safe_moves:
            try:
                row, col = coord_to_index(move)
            except:
                continue

            score = evaluate_move(board, row, col, color)

            # 白棋额外提高防守评分权重
            if color == WHITE:
                # 重新计算防守权重
                opponent = BLACK
                attack_score = score * 0.7  # 降低进攻权重
                defense_score = 0

                # 计算防守分数
                board.grid[row][col] = color
                for r in range(_SIZE):
                    for c in range(_SIZE):
                        if board.grid[r][c] == opponent:
                            pass  # 简化计算
                board.grid[row][col] = EMPTY

                score = int(attack_score + defense_score * 0.3)

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def get_defensive_safety_score(
        self, board: Board, row: int, col: int, color: int
    ) -> int:
        """计算某落子的防守安全分数

        综合考虑进攻和防守，返回分数越高越好。
        """
        opponent = WHITE if color == BLACK else BLACK

        # 临时落子
        board.grid[row][col] = color

        # 我方进攻分
        attack = self._count_threats(board, row, col, color)

        # 对方威胁分（落子后对方能形成什么）
        board.grid[row][col] = opponent
        defense = self._count_threats(board, row, col, opponent)
        board.grid[row][col] = EMPTY

        # 还原
        board.grid[row][col] = EMPTY

        # 综合评分
        return attack * 100 - defense * 50

    def _count_threats(
        self, board: Board, row: int, col: int, color: int
    ) -> int:
        """计算某位置落子后形成的威胁数量"""
        board.grid[row][col] = color
        count = 0

        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            length, open_ends = self._count_line(board, row, col, dr, dc, color)
            if length >= 4:
                count += 2
            elif length == 3 and open_ends >= 1:
                count += 1

        board.grid[row][col] = EMPTY
        return count

    def _count_line(
        self, board: Board, row: int, col: int, dr: int, dc: int, color: int
    ) -> tuple:
        """统计某方向的连续棋子数"""
        pos = 0
        for i in range(1, 5):
            nr, nc = row + dr * i, col + dc * i
            if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                if board.grid[nr][nc] == color:
                    pos += 1
                else:
                    break

        neg = 0
        for i in range(1, 5):
            nr, nc = row - dr * i, col - dc * i
            if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                if board.grid[nr][nc] == color:
                    neg += 1
                else:
                    break

        open_ends = 0

        nr, nc = row + dr * (pos + 1), col + dc * (pos + 1)
        if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
            if board.grid[nr][nc] == EMPTY:
                open_ends += 1

        nr, nc = row - dr * (neg + 1), col - dc * (neg + 1)
        if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
            if board.grid[nr][nc] == EMPTY:
                open_ends += 1

        return (pos + neg + 1, open_ends)
