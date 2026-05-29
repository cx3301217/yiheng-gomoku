"""Alpha-Beta 搜索模块：使用极大极小搜索配合 Alpha-Beta 剪枝提升 AI 决策能力

本模块在Alpha-Beta剪枝搜索基础上引入Zobrist哈希和置换表缓存，
用于识别不同搜索路径下出现的重复棋盘状态，减少重复计算。
同时结合迭代加深策略，在有限时间内逐步扩大搜索深度，
保证程序在比赛时限内始终能够返回当前最优可用落子。
"""
import time
from typing import Optional, Tuple
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import coord_to_index, index_to_coord
from gomoku.evaluator import evaluate_board, get_scored_moves
from gomoku.forbidden import is_forbidden_move
from gomoku.zobrist import ZobristHash


# 胜负判定分值
_WIN_SCORE = 10_000_000
_LOSE_SCORE = -10_000_000

# 置换表标志
_TT_EXACT = "EXACT"
_TT_LOWER = "LOWER"
_TT_UPPER = "UPPER"


class AlphaBetaSearcher:
    """Alpha-Beta 搜索器

    使用标准极大极小搜索配合 Alpha-Beta 剪枝，在给定深度内搜索最佳落子点。
    支持Zobrist哈希置换表缓存和迭代加深搜索。

    Attributes:
        max_depth: 最大搜索深度，默认2
        candidate_limit: 每层搜索的候选点数量上限，默认8
        time_limit: 单次搜索的最大时间限制（秒），默认2.0
        use_tt: 是否使用置换表，默认True
        start_time: 搜索开始时间
        nodes: 搜索的节点数
        timeout: 是否超时
        zobrist: Zobrist哈希计算器
        tt: 置换表字典
    """

    def __init__(
        self,
        max_depth: int = 2,
        candidate_limit: int = 8,
        time_limit: float = 2.0,
        use_tt: bool = True,
    ):
        self.max_depth = max_depth
        self.candidate_limit = candidate_limit
        self.time_limit = time_limit
        self.use_tt = use_tt
        self.start_time: float = 0
        self.nodes: int = 0
        self.timeout: bool = False
        self.tt: dict = {}  # 置换表
        self.zobrist = ZobristHash()

    def search_best_move(self, board: Board, color: int) -> Optional[str]:
        """搜索当前局面下的最佳落子

        Args:
            board: 当前棋盘
            color: 我方颜色 (BLACK 或 WHITE)

        Returns:
            最佳落子坐标字符串，失败返回 None
        """
        self.start_time = time.time()
        self.nodes = 0
        self.timeout = False

        # 获取候选点（按评分从高到低）
        candidates = get_scored_moves(board, color, limit=self.candidate_limit)

        if not candidates:
            return None

        best_move: Optional[str] = None
        best_score = float("-inf")

        for coord_str, _ in candidates:
            if self._is_timeout():
                self.timeout = True
                break

            row, col = coord_to_index(coord_str)

            # 黑棋过滤禁手点
            if color == BLACK:
                board.grid[row][col] = BLACK
                if is_forbidden_move(board, row, col, BLACK):
                    board.grid[row][col] = EMPTY
                    continue
                board.grid[row][col] = EMPTY

            # 临时落子
            board.grid[row][col] = color

            # 检查终局
            terminal, terminal_score = self.is_terminal_after_move(
                board, row, col, color
            )

            if terminal:
                # 终局分数转成 root_color 视角
                score = self.terminal_score_for_root(color, terminal_score, color)
                board.grid[row][col] = EMPTY

                if score > best_score:
                    best_score = score
                    best_move = coord_str
                    # 如果是我方直接胜利，可以提前返回
                    if terminal_score == _WIN_SCORE:
                        return best_move
                continue

            # 调用 alpha_beta 搜索
            score = self.alpha_beta(
                board,
                self.max_depth - 1,
                _LOSE_SCORE,
                _WIN_SCORE,
                WHITE if color == BLACK else BLACK,
                color,
            )

            # 还原棋盘
            board.grid[row][col] = EMPTY

            if score > best_score:
                best_score = score
                best_move = coord_str

        return best_move

    def search_best_move_depth(
        self, board: Board, color: int, depth: int
    ) -> Optional[str]:
        """使用指定深度搜索最佳落子

        与 search_best_move 类似，但使用传入的 depth。

        Args:
            board: 当前棋盘
            color: 我方颜色
            depth: 搜索深度

        Returns:
            最佳落子坐标字符串，失败返回 None
        """
        self.start_time = time.time()
        self.nodes = 0
        self.timeout = False

        # 获取候选点
        candidates = get_scored_moves(board, color, limit=self.candidate_limit)

        if not candidates:
            return None

        best_move: Optional[str] = None
        best_score = float("-inf")

        for coord_str, _ in candidates:
            if self._is_timeout():
                self.timeout = True
                break

            row, col = coord_to_index(coord_str)

            # 黑棋过滤禁手点
            if color == BLACK:
                board.grid[row][col] = BLACK
                if is_forbidden_move(board, row, col, BLACK):
                    board.grid[row][col] = EMPTY
                    continue
                board.grid[row][col] = EMPTY

            # 临时落子
            board.grid[row][col] = color

            # 检查终局
            terminal, terminal_score = self.is_terminal_after_move(
                board, row, col, color
            )

            if terminal:
                score = self.terminal_score_for_root(color, terminal_score, color)
                board.grid[row][col] = EMPTY

                if score > best_score:
                    best_score = score
                    best_move = coord_str
                    if terminal_score == _WIN_SCORE:
                        return best_move
                continue

            # 调用 alpha_beta 搜索
            score = self.alpha_beta(
                board,
                depth - 1,
                _LOSE_SCORE,
                _WIN_SCORE,
                WHITE if color == BLACK else BLACK,
                color,
            )

            # 还原棋盘
            board.grid[row][col] = EMPTY

            if score > best_score:
                best_score = score
                best_move = coord_str

        return best_move

    def iterative_deepening_search(
        self, board: Board, color: int
    ) -> Optional[str]:
        """迭代加深搜索

        在 time_limit 内从 depth=1 逐步加深到 max_depth。

        Args:
            board: 当前棋盘
            color: 我方颜色

        Returns:
            最佳落子坐标字符串
        """
        start_time = time.time()
        best_move = None

        for depth in range(1, self.max_depth + 1):
            # 检查是否超时
            if time.time() - start_time >= self.time_limit:
                break

            # 保存当前状态用于恢复
            saved_nodes = self.nodes
            saved_timeout = self.timeout

            # 使用指定深度搜索
            move = self.search_best_move_depth(board, color, depth)

            # 检查是否成功完成搜索（未超时）
            if move is not None and not self.timeout:
                best_move = move

                # 如果找到必胜，可以提前返回
                row, col = coord_to_index(move)
                if board.grid[row][col] == EMPTY:
                    board.grid[row][col] = color
                    if color == BLACK:
                        if board.has_exact_five(row, col, BLACK):
                            board.grid[row][col] = EMPTY
                            return move
                    else:
                        if board.has_five_or_more(row, col, WHITE):
                            board.grid[row][col] = EMPTY
                            return move
                    board.grid[row][col] = EMPTY

            # 如果超时，停止加深
            if self.timeout:
                break

        # 如果迭代加深没有结果，使用兜底
        if best_move is None:
            best_move = self.search_best_move(board, color)

        return best_move

    def alpha_beta(
        self,
        board: Board,
        depth: int,
        alpha: int,
        beta: int,
        current_color: int,
        root_color: int,
    ) -> int:
        """标准 Minimax Alpha-Beta 搜索（带置换表）

        Args:
            board: 当前棋盘
            depth: 剩余搜索深度
            alpha: Alpha 值（我方最优）
            beta: Beta 值（对方最优）
            current_color: 当前落子方
            root_color: 最初落子方（用于局面评估）

        Returns:
            局面评估分数（root_color 视角）
        """
        self.nodes += 1

        # 1. 检查超时
        if self._is_timeout():
            self.timeout = True
            return self.evaluate_position(board, root_color)

        # 2. 深度为0，返回局面评估
        if depth <= 0:
            return self.evaluate_position(board, root_color)

        # 3. 置换表查找
        original_alpha = alpha
        best_move_in_tt = None
        if self.use_tt:
            hash_key = self.zobrist.compute_hash(board, current_color)
            tt_entry = self.tt.get(hash_key)
            if tt_entry is not None:
                # 只在深度足够时使用
                if tt_entry["depth"] >= depth:
                    if tt_entry["flag"] == _TT_EXACT:
                        return tt_entry["score"]
                    elif tt_entry["flag"] == _TT_LOWER:
                        alpha = max(alpha, tt_entry["score"])
                    elif tt_entry["flag"] == _TT_UPPER:
                        beta = min(beta, tt_entry["score"])

                    if alpha >= beta:
                        return tt_entry["score"]

                best_move_in_tt = tt_entry.get("best_move")

        # 4. 获取候选点
        candidates = get_scored_moves(board, current_color, limit=self.candidate_limit)

        # 如果置换表有最佳走法，优先考虑
        if best_move_in_tt and best_move_in_tt in [c[0] for c in candidates]:
            candidates = [(best_move_in_tt, 0)] + [c for c in candidates if c[0] != best_move_in_tt]

        # 5. 如果没有候选点，返回局面评估
        if not candidates:
            return self.evaluate_position(board, root_color)

        # 6. 极大层（current_color == root_color）
        if current_color == root_color:
            value = _LOSE_SCORE
            best_move = None

            for coord_str, _ in candidates:
                row, col = coord_to_index(coord_str)

                # 黑棋过滤禁手点
                if current_color == BLACK:
                    board.grid[row][col] = BLACK
                    if is_forbidden_move(board, row, col, BLACK):
                        board.grid[row][col] = EMPTY
                        continue
                    board.grid[row][col] = EMPTY

                # 临时落子
                board.grid[row][col] = current_color

                # 检查终局
                terminal, terminal_score = self.is_terminal_after_move(
                    board, row, col, current_color
                )

                if terminal:
                    # 转成 root_color 视角分数
                    score = self.terminal_score_for_root(
                        current_color, terminal_score, root_color
                    )
                    board.grid[row][col] = EMPTY
                    if score > value:
                        value = score
                        best_move = coord_str
                    alpha = max(alpha, value)
                    if alpha >= beta:
                        break
                    continue

                # 递归搜索
                next_color = WHITE if current_color == BLACK else BLACK
                score = self.alpha_beta(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    next_color,
                    root_color,
                )

                # 还原棋盘
                board.grid[row][col] = EMPTY

                if score > value:
                    value = score
                    best_move = coord_str
                alpha = max(alpha, value)
                if alpha >= beta:
                    break

            # 写入置换表（只在未超时且非胜负分数时写入）
            if self.use_tt and not self.timeout and best_move is not None:
                if value <= original_alpha:
                    flag = _TT_UPPER
                elif value >= beta:
                    flag = _TT_LOWER
                else:
                    flag = _TT_EXACT

                if not self.timeout:
                    hash_key = self.zobrist.compute_hash(board, current_color)
                    self.tt[hash_key] = {
                        "depth": depth,
                        "score": value,
                        "flag": flag,
                        "best_move": best_move,
                    }

            return value

        # 7. 极小层（current_color != root_color）
        else:
            value = _WIN_SCORE
            best_move = None

            for coord_str, _ in candidates:
                row, col = coord_to_index(coord_str)

                # 黑棋过滤禁手点
                if current_color == BLACK:
                    board.grid[row][col] = BLACK
                    if is_forbidden_move(board, row, col, BLACK):
                        board.grid[row][col] = EMPTY
                        continue
                    board.grid[row][col] = EMPTY

                # 临时落子
                board.grid[row][col] = current_color

                # 检查终局
                terminal, terminal_score = self.is_terminal_after_move(
                    board, row, col, current_color
                )

                if terminal:
                    # 转成 root_color 视角分数
                    score = self.terminal_score_for_root(
                        current_color, terminal_score, root_color
                    )
                    board.grid[row][col] = EMPTY
                    if score < value:
                        value = score
                        best_move = coord_str
                    beta = min(beta, value)
                    if alpha >= beta:
                        break
                    continue

                # 递归搜索
                next_color = WHITE if current_color == BLACK else BLACK
                score = self.alpha_beta(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    next_color,
                    root_color,
                )

                # 还原棋盘
                board.grid[row][col] = EMPTY

                if score < value:
                    value = score
                    best_move = coord_str
                beta = min(beta, value)
                if alpha >= beta:
                    break

            # 写入置换表（只在未超时且非胜负分数时写入）
            if self.use_tt and not self.timeout and best_move is not None:
                if value <= original_alpha:
                    flag = _TT_UPPER
                elif value >= beta:
                    flag = _TT_LOWER
                else:
                    flag = _TT_EXACT

                if not self.timeout:
                    hash_key = self.zobrist.compute_hash(board, current_color)
                    self.tt[hash_key] = {
                        "depth": depth,
                        "score": value,
                        "flag": flag,
                        "best_move": best_move,
                    }

            return value

    def terminal_score_for_root(
        self, color: int, terminal_score: int, root_color: int
    ) -> int:
        """将终局分数从当前落子方视角转换为 root_color 视角

        Args:
            color: 当前落子方颜色
            terminal_score: is_terminal_after_move 返回的分数（当前落子方视角）
            root_color: 根节点落子方颜色

        Returns:
            root_color 视角的分数
        """
        if terminal_score == 0:
            return 0

        if color == root_color:
            return terminal_score
        else:
            return -terminal_score

    def evaluate_position(self, board: Board, root_color: int) -> int:
        """评估当前局面对 root_color 的好坏

        Args:
            board: 当前棋盘
            root_color: 评估方颜色

        Returns:
            局面评分（分数越高对 root_color 越有利）
        """
        opponent = WHITE if root_color == BLACK else BLACK

        # 使用评估函数差值
        my_score = evaluate_board(board, root_color)
        opp_score = evaluate_board(board, opponent)

        return my_score - int(opp_score * 0.9)

    @staticmethod
    def is_terminal_after_move(
        board: Board, row: int, col: int, color: int
    ) -> Tuple[bool, int]:
        """判断刚刚落子后是否终局

        Args:
            board: 当前棋盘
            row: 落子行号
            col: 落子列号
            color: 落子方颜色

        Returns:
            (是否终局, 分数)
            - (True, 10_000_000): 当前落子方胜
            - (True, -10_000_000): 当前落子方负
            - (True, 0): 和棋
            - (False, 0): 非终局
        """
        # 黑棋：先判五连
        if color == BLACK:
            if board.has_exact_five(row, col, BLACK):
                return (True, _WIN_SCORE)
            # 黑棋：再判禁手
            if is_forbidden_move(board, row, col, BLACK):
                return (True, _LOSE_SCORE)
        else:
            # 白棋：五连及以上（含长连）算胜
            if board.has_five_or_more(row, col, WHITE):
                return (True, _WIN_SCORE)

        # 和棋判断
        if board.is_full():
            return (True, 0)

        return (False, 0)

    def _is_timeout(self) -> bool:
        """检查是否超时"""
        return (time.time() - self.start_time) >= self.time_limit

    def clear_tt(self) -> None:
        """清空置换表"""
        self.tt.clear()

    def get_tt_size(self) -> int:
        """获取置换表大小"""
        return len(self.tt)
