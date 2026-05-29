"""防守增强模块

提供紧急防守建议和威胁检测功能。
"""
from typing import Optional, List
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import index_to_coord, coord_to_index
from gomoku.forbidden import is_forbidden_move
from gomoku.evaluator import evaluate_move, get_scored_moves

_SIZE = 15

# 高威胁阈值 - 提高到500000，只处理真正的强威胁
_HIGH_THREAT_THRESHOLD = 500000

# 防守判定 - 只有超过此阈值才防守
_MUST_DEFEND_THRESHOLD = 300000


class DefenseAdvisor:
    """防守顾问"""

    def __init__(self):
        pass

    def find_urgent_defense(
        self, board: Board, color: int
    ) -> Optional[str]:
        """找出必须立即防守的位置

        只处理真正紧急的威胁：
        1. 对方一步成五
        2. 对方双胜点（两个活四/冲四）
        3. 对方活四/冲四
        4. 对方VCF杀棋
        5. 对方VCT必胜
        6. 对方连续活三（双端扩展威胁）

        Args:
            board: 当前棋盘
            color: 落子方颜色

        Returns:
            必须防守的坐标，或None
        """
        opponent = WHITE if color == BLACK else BLACK

        # 1. 对方一步成五，必须堵
        win_point = self._find_opponent_win_point(board, opponent)
        if win_point:
            return win_point

        # 2. 对方双胜点（同时形成两个活四/冲四）
        double_win = self._find_opponent_double_win(board, opponent)
        if double_win:
            return double_win

        # 3. 对方活四/冲四（只有一个强威胁）
        four_point = self._find_opponent_four(board, opponent)
        if four_point:
            return four_point

        # 4. 对方VCF杀棋防守
        vcf_defense = self._find_vcf_defense(board, opponent)
        if vcf_defense:
            return vcf_defense

        # 5. 对方VCT威胁防守
        vct_defense = self._find_vct_defense(board, opponent)
        if vct_defense:
            return vct_defense

        # 6. 对方连续活三防守（双端扩展威胁）
        open_three_defense = self.find_open_three_defense(board, color)
        if open_three_defense:
            return open_three_defense

        # 不再处理普通高威胁点，由Alpha-Beta和评分函数处理
        return None

    def _find_opponent_win_point(
        self, board: Board, opponent: int
    ) -> Optional[str]:
        """查找对方一步胜点"""
        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] == EMPTY:
                    board.grid[row][col] = opponent
                    if opponent == BLACK:
                        win = board.has_exact_five(row, col, opponent)
                    else:
                        win = board.has_five_or_more(row, col, opponent)
                    board.grid[row][col] = EMPTY
                    if win:
                        # 验证是否为合法防守点
                        if opponent == BLACK:
                            board.grid[row][col] = opponent
                            if is_forbidden_move(board, row, col, opponent):
                                board.grid[row][col] = EMPTY
                                continue
                            board.grid[row][col] = EMPTY
                        return index_to_coord(row, col)
        return None

    def _find_opponent_double_win(
        self, board: Board, opponent: int
    ) -> Optional[str]:
        """查找对方双胜点（同时形成两个威胁）"""
        threat_points = []

        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] == EMPTY:
                    board.grid[row][col] = opponent
                    if opponent == BLACK:
                        if is_forbidden_move(board, row, col, opponent):
                            board.grid[row][col] = EMPTY
                            continue
                    board.grid[row][col] = EMPTY

                    # 计算该点的威胁数量
                    threat_count = self._count_threats_at(
                        board, row, col, opponent
                    )
                    if threat_count >= 2:
                        threat_points.append((index_to_coord(row, col), threat_count))

        if threat_points:
            # 返回威胁数量最多的点
            threat_points.sort(key=lambda x: x[1], reverse=True)
            return threat_points[0][0]

        return None

    def _count_threats_at(
        self, board: Board, row: int, col: int, color: int
    ) -> int:
        """计算某位置落子后形成的威胁数量"""
        board.grid[row][col] = color
        count = 0

        # 检查四个方向
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            length, open_ends = self._count_line(board, row, col, dr, dc, color)
            if length >= 4:  # 活四或冲四
                count += 1
            elif length == 3 and open_ends >= 1:  # 活三
                count += 1

        board.grid[row][col] = EMPTY
        return count

    def _count_line(
        self, board: Board, row: int, col: int, dr: int, dc: int, color: int
    ) -> tuple:
        """统计某方向的连续棋子数"""
        # 正向
        pos = 0
        for i in range(1, 5):
            nr, nc = row + dr * i, col + dc * i
            if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                if board.grid[nr][nc] == color:
                    pos += 1
                else:
                    break

        # 负向
        neg = 0
        for i in range(1, 5):
            nr, nc = row - dr * i, col - dc * i
            if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                if board.grid[nr][nc] == color:
                    neg += 1
                else:
                    break

        # 计算开放端
        open_ends = 0

        # 正向开放
        nr, nc = row + dr * (pos + 1), col + dc * (pos + 1)
        if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
            if board.grid[nr][nc] == EMPTY:
                open_ends += 1

        # 负向开放
        nr, nc = row - dr * (neg + 1), col - dc * (neg + 1)
        if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
            if board.grid[nr][nc] == EMPTY:
                open_ends += 1

        return (pos + neg + 1, open_ends)

    def _find_opponent_four(
        self, board: Board, opponent: int
    ) -> Optional[str]:
        """查找对方活四/冲四点"""
        four_points = []

        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] == EMPTY:
                    # 黑棋检查禁手
                    if opponent == BLACK:
                        board.grid[row][col] = opponent
                        if is_forbidden_move(board, row, col, opponent):
                            board.grid[row][col] = EMPTY
                            continue
                        board.grid[row][col] = EMPTY

                    # 检查是否为活四/冲四
                    board.grid[row][col] = opponent
                    length, open_ends = self._count_line(board, row, col, 1, 0, opponent)
                    if length >= 4 and open_ends >= 1:
                        four_points.append(index_to_coord(row, col))
                    length, open_ends = self._count_line(board, row, col, 0, 1, opponent)
                    if length >= 4 and open_ends >= 1:
                        if index_to_coord(row, col) not in four_points:
                            four_points.append(index_to_coord(row, col))
                    length, open_ends = self._count_line(board, row, col, 1, 1, opponent)
                    if length >= 4 and open_ends >= 1:
                        if index_to_coord(row, col) not in four_points:
                            four_points.append(index_to_coord(row, col))
                    length, open_ends = self._count_line(board, row, col, 1, -1, opponent)
                    if length >= 4 and open_ends >= 1:
                        if index_to_coord(row, col) not in four_points:
                            four_points.append(index_to_coord(row, col))
                    board.grid[row][col] = EMPTY

        if four_points:
            # 返回评分最高的点
            best_move = None
            best_score = float("-inf")
            for move in four_points:
                row, col = coord_to_index(move)
                score = evaluate_move(board, row, col, opponent)
                if score > best_score:
                    best_score = score
                    best_move = move
            return best_move

        return None

    def get_opponent_four_threats(
        self, board: Board, opponent: int
    ) -> List[str]:
        """返回对方能够形成活四或冲四的点"""
        threats = []

        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] == EMPTY:
                    # 黑棋检查禁手
                    if opponent == BLACK:
                        board.grid[row][col] = opponent
                        if is_forbidden_move(board, row, col, opponent):
                            board.grid[row][col] = EMPTY
                            continue
                        board.grid[row][col] = EMPTY

                    board.grid[row][col] = opponent

                    # 检查四个方向
                    for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                        length, open_ends = self._count_line(
                            board, row, col, dr, dc, opponent
                        )
                        if length >= 4 and open_ends >= 1:
                            coord = index_to_coord(row, col)
                            if coord not in threats:
                                threats.append(coord)
                            break

                    board.grid[row][col] = EMPTY

        return threats

    def get_opponent_high_threat(
        self, board: Board, opponent: int, threshold: int = _HIGH_THREAT_THRESHOLD
    ) -> Optional[str]:
        """根据评估函数找对方高威胁点"""
        # 获取对方评分最高的点
        scored = get_scored_moves(board, opponent, limit=5)

        for move, score in scored:
            if score >= threshold:
                # 验证是合法防守点
                row, col = coord_to_index(move)
                if board.grid[row][col] == EMPTY:
                    # 黑棋检查禁手
                    if opponent == BLACK:
                        board.grid[row][col] = opponent
                        if is_forbidden_move(board, row, col, opponent):
                            board.grid[row][col] = EMPTY
                            continue
                        board.grid[row][col] = EMPTY
                    return move

        return None

    def find_multi_ply_defense(
        self, board: Board, color: int
    ) -> Optional[str]:
        """针对白棋后手，提前防守黑棋两步内可能形成的强威胁

        Args:
            board: 当前棋盘
            color: 落子方颜色（通常是白棋）

        Returns:
            最佳防守点，或None
        """
        opponent = WHITE if color == BLACK else BLACK

        # 生成候选防守点
        candidates = self._generate_defense_candidates(board, color)

        if not candidates:
            return None

        best_move = None
        best_score = float("-inf")

        for move in candidates:
            row, col = coord_to_index(move)

            # 临时落子
            board.grid[row][col] = color

            # 检查对方下一步是否仍有威胁
            opponent_has_threat = self._opponent_has_threat(board, opponent)

            if not opponent_has_threat:
                # 这个防守点有效，计算评分
                score = evaluate_move(board, row, col, color)
                if score > best_score:
                    best_score = score
                    best_move = move

            # 还原棋盘
            board.grid[row][col] = EMPTY

        return best_move

    def _generate_defense_candidates(
        self, board: Board, color: int
    ) -> List[str]:
        """生成防守候选点"""
        candidates = set()

        # 找对方棋子周围的所有空位
        opponent = WHITE if color == BLACK else BLACK

        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] == opponent:
                    # 检查周围8个方向
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            if dr == 0 and dc == 0:
                                continue
                            nr, nc = row + dr, col + dc
                            if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                                if board.grid[nr][nc] == EMPTY:
                                    # 黑棋检查禁手
                                    if color == BLACK:
                                        board.grid[nr][nc] = BLACK
                                        if is_forbidden_move(board, nr, nc, BLACK):
                                            board.grid[nr][nc] = EMPTY
                                            continue
                                        board.grid[nr][nc] = EMPTY
                                    candidates.add(index_to_coord(nr, nc))

        return list(candidates)

    def _opponent_has_threat(
        self, board: Board, opponent: int
    ) -> bool:
        """检查对方是否仍有威胁"""
        # 检查对方一步胜
        if self._find_opponent_win_point(board, opponent):
            return True

        # 检查对方VCF
        if self._has_vcf(board, opponent):
            return True

        # 检查对方VCT
        if self._has_vct(board, opponent):
            return True

        # 检查对方是否有活四/冲四
        if self._find_opponent_four(board, opponent):
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

    def _find_vcf_defense(self, board: Board, opponent: int) -> Optional[str]:
        """查找对方VCF杀棋的防守点"""
        try:
            from gomoku.threat_search import ThreatSearcher
            searcher = ThreatSearcher(max_vcf_depth=4)
            vcf_move = searcher.vcf_search(board, opponent, 4)
            return vcf_move
        except:
            return None

    def _find_vct_defense(self, board: Board, opponent: int) -> Optional[str]:
        """查找对方VCT威胁的防守点"""
        try:
            from gomoku.threat_search import ThreatSearcher
            searcher = ThreatSearcher(max_vcf_depth=3, candidate_limit=6)
            vct_move = searcher.vct_search(board, opponent, 3)
            return vct_move
        except:
            return None

    def find_open_three_defense(
        self, board: Board, color: int
    ) -> Optional[str]:
        """检测对方连续活三并返回必须防守的一端

        定义：连续三个对方棋子，两端均为空
        例如：G8-H7-I6，F9和J5为空

        Args:
            board: 当前棋盘
            color: 落子方颜色（防守方）

        Returns:
            防守点坐标（如F9或J5），或None
        """
        opponent = WHITE if color == BLACK else BLACK

        best_defense = None
        best_score = float("-inf")

        # 四个方向
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        # 遍历棋盘上所有对方棋子
        for row in range(_SIZE):
            for col in range(_SIZE):
                if board.grid[row][col] != opponent:
                    continue

                # 沿四个方向检查
                for dr, dc in directions:
                    result = self._check_open_three_in_direction(
                        board, row, col, dr, dc, opponent
                    )
                    if result is not None:
                        before_coord, after_coord = result

                        # 评估两个端点，选择更好的防守点
                        before_score = evaluate_move(board, before_coord[0], before_coord[1], color)
                        after_score = evaluate_move(board, after_coord[0], after_coord[1], color)

                        # 黑棋检查禁手
                        if color == BLACK:
                            board.grid[before_coord[0]][before_coord[1]] = BLACK
                            before_forbidden = is_forbidden_move(
                                board, before_coord[0], before_coord[1], BLACK
                            )
                            board.grid[before_coord[0]][before_coord[1]] = EMPTY

                            board.grid[after_coord[0]][after_coord[1]] = BLACK
                            after_forbidden = is_forbidden_move(
                                board, after_coord[0], after_coord[1], BLACK
                            )
                            board.grid[after_coord[0]][after_coord[1]] = EMPTY

                            if before_forbidden:
                                before_score = float("-inf")
                            if after_forbidden:
                                after_score = float("-inf")

                        # 选择评分更高的防守点
                        if before_score >= after_score and before_score > best_score:
                            best_score = before_score
                            best_defense = index_to_coord(before_coord[0], before_coord[1])
                        elif after_score > best_score:
                            best_score = after_score
                            best_defense = index_to_coord(after_coord[0], after_coord[1])

        return best_defense

    def _check_open_three_in_direction(
        self, board: Board, row: int, col: int, dr: int, dc: int, color: int
    ) -> Optional[tuple]:
        """检查某方向上是否存在连续三个棋子两端为空的情况

        Args:
            board: 棋盘
            row, col: 起始棋子位置
            dr, dc: 方向向量
            color: 棋子颜色

        Returns:
            (before_coord, after_coord) 如果找到连续活三，否则None
            before_coord: 起始点前一格坐标 (r, c)
            after_coord: 终点后一格坐标 (r, c)
        """
        # 统计正向和负向的连续棋子
        # 正向
        pos_count = 0
        pos_end_row, pos_end_col = row, col
        for i in range(1, 5):
            nr, nc = row + dr * i, col + dc * i
            if 0 <= nr < _SIZE and 0 <= nc < _SIZE and board.grid[nr][nc] == color:
                pos_count += 1
                pos_end_row, pos_end_col = nr, nc
            else:
                break

        # 负向
        neg_count = 0
        neg_end_row, neg_end_col = row, col
        for i in range(1, 5):
            nr, nc = row - dr * i, col - dc * i
            if 0 <= nr < _SIZE and 0 <= nc < _SIZE and board.grid[nr][nc] == color:
                neg_count += 1
                neg_end_row, neg_end_col = nr, nc
            else:
                break

        total = pos_count + neg_count + 1

        # 需要恰好是3个连续的棋子
        if total != 3:
            return None

        # 确定起始点和终止点
        start_r = neg_end_row + dr if neg_count > 0 else row
        start_c = neg_end_col + dc if neg_count > 0 else col
        end_r = pos_end_row if pos_count > 0 else row
        end_c = pos_end_col if pos_count > 0 else col

        # 两端坐标
        before_r, before_c = start_r - dr, start_c - dc
        after_r, after_c = end_r + dr, end_c + dc

        # 检查两端是否都在棋盘内且为空
        before_in_board = 0 <= before_r < _SIZE and 0 <= before_c < _SIZE
        after_in_board = 0 <= after_r < _SIZE and 0 <= after_c < _SIZE

        if not before_in_board or not after_in_board:
            return None

        if board.grid[before_r][before_c] != EMPTY or board.grid[after_r][after_c] != EMPTY:
            return None

        return ((before_r, before_c), (after_r, after_c))
