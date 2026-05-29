"""AI决策引擎模块：提供五子棋落子选择接口"""

from typing import Optional, List
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import index_to_coord, coord_to_index
from gomoku.forbidden import is_forbidden_move

_SIZE = 15


def find_winning_move(board: Board, color: int) -> Optional[str]:
    """检查是否存在一步能胜的位置

    黑棋：必须是刚好五连（has_exact_five），长连是禁手不算胜
    白棋：五连及以上（has_five_or_more）都算胜

    Args:
        board: 当前棋盘
        color: 落子方颜色(BLACK或WHITE)

    Returns:
        能胜的坐标字符串(如"H8")，不存在则返回None
    """
    for row in range(_SIZE):
        for col in range(_SIZE):
            if board.grid[row][col] == EMPTY:
                board.grid[row][col] = color
                if color == BLACK:
                    win = board.has_exact_five(row, col, color)
                else:
                    win = board.has_five_or_more(row, col, color)
                board.grid[row][col] = EMPTY
                if win:
                    return index_to_coord(row, col)
    return None


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

    return candidates


def _distance_to_center(coord: str) -> int:
    """计算坐标到天元H8的曼哈顿距离近似值"""
    row, col = coord_to_index(coord)
    return abs(row - 7) + abs(col - 7)


class GomokuEngine:
    """五子棋AI决策引擎

    攻防平衡策略：
    1. 立即胜利永远最高优先级
    2. 对方一步胜必须堵
    3. 我方VCF/VCT强攻优先于普通防守
    4. 只有真正高危威胁才防守
    """

    @staticmethod
    def choose_move(board: Board, color: int) -> str:
        """根据棋盘状态和执棋颜色选择落子

        决策顺序：
        1. 棋盘已满抛出错误
        2. 棋盘为空，下天元H8
        3. 我方一步胜
        4. 对方一步胜，必须堵
        5. 对方连续活三防守
        6. 我方VCF连续冲四杀
        7. 我方VCT连续威胁胜
        8. 我方强攻击点
        9. 对方VCF杀棋防守
        10. 对方VCT威胁防守
        11. DefenseAdvisor紧急防守
        12. 白棋多步防守预判
        13. OpeningBook开局策略
        14. Alpha-Beta迭代加深
        15. SafetyAdvisor过滤
        16. 评分兜底
        17. 中心距离兜底

        Args:
            board: 当前棋盘状态
            color: 我方颜色(BLACK=1或WHITE=2)

        Returns:
            落子坐标字符串(如"H8")

        Raises:
            ValueError: 棋盘已满无法落子
        """
        opponent = WHITE if color == BLACK else BLACK

        # 1. 棋盘已满，抛出错误
        if board.is_full():
            raise ValueError("棋盘已满，无处落子")

        # 2. 棋盘为空，下天元
        empty_count = sum(1 for r in range(_SIZE) for c in range(_SIZE)
                         if board.grid[r][c] == EMPTY)
        if empty_count == _SIZE * _SIZE:
            return "H8"

        # 3. 我方一步胜
        win_move = find_winning_move(board, color)
        if win_move is not None:
            return win_move

        # 4. 对方一步成五，必须堵
        block_move = find_winning_move(board, opponent)
        if block_move is not None:
            return block_move

        # 5. 对方连续活三防守（双端扩展威胁，优先于我方VCT/VCF进攻）
        # 当对方有连续三子且两端为空时，必须先防守
        try:
            from gomoku.defense import DefenseAdvisor
            defense = DefenseAdvisor()
            open_three_defense = defense.find_open_three_defense(board, color)
            if open_three_defense is not None:
                row, col = coord_to_index(open_three_defense)
                if board.grid[row][col] == EMPTY:
                    return open_three_defense
        except Exception:
            pass

        # 6. 我方VCF连续冲四杀搜索
        try:
            from gomoku.threat_search import ThreatSearcher
            searcher = ThreatSearcher(max_vcf_depth=5)
            vcf_move = searcher.vcf_search(board, color, 5)
            if vcf_move is not None:
                row, col = coord_to_index(vcf_move)
                if board.grid[row][col] == EMPTY:
                    if color == BLACK:
                        board.grid[row][col] = BLACK
                        if is_forbidden_move(board, row, col, BLACK):
                            board.grid[row][col] = EMPTY
                        else:
                            board.grid[row][col] = EMPTY
                            return vcf_move
                    else:
                        return vcf_move
        except Exception:
            pass

        # 7. 我方VCT连续威胁胜搜索
        try:
            from gomoku.threat_search import ThreatSearcher
            searcher = ThreatSearcher(max_vcf_depth=5, candidate_limit=8)
            vct_move = searcher.vct_search(board, color, 5)
            if vct_move is not None:
                row, col = coord_to_index(vct_move)
                if board.grid[row][col] == EMPTY:
                    if color == BLACK:
                        board.grid[row][col] = BLACK
                        if is_forbidden_move(board, row, col, BLACK):
                            board.grid[row][col] = EMPTY
                        else:
                            board.grid[row][col] = EMPTY
                            return vct_move
                    else:
                        return vct_move
        except Exception:
            pass

        # 8. 我方强攻击点（普通进攻）
        try:
            from gomoku.attack import AttackAdvisor
            attack_move = AttackAdvisor.find_strong_attack(board, color)
            if attack_move is not None:
                row, col = coord_to_index(attack_move)
                if board.grid[row][col] == EMPTY:
                    if color == BLACK:
                        board.grid[row][col] = BLACK
                        if is_forbidden_move(board, row, col, BLACK):
                            board.grid[row][col] = EMPTY
                        else:
                            board.grid[row][col] = EMPTY
                            return attack_move
                    else:
                        return attack_move
        except Exception:
            pass

        # 9. 对方VCF杀棋防守
        try:
            from gomoku.threat_search import find_opponent_vcf_defense
            defense_move = find_opponent_vcf_defense(board, color)
            if defense_move is not None:
                row, col = coord_to_index(defense_move)
                if board.grid[row][col] == EMPTY:
                    return defense_move
        except Exception:
            pass

        # 10. 对方VCT威胁防守
        try:
            from gomoku.threat_search import find_opponent_vct_defense
            vct_defense = find_opponent_vct_defense(board, color)
            if vct_defense is not None:
                row, col = coord_to_index(vct_defense)
                if board.grid[row][col] == EMPTY:
                    return vct_defense
        except Exception:
            pass

        # 11. DefenseAdvisor紧急防守（只处理真正高危威胁）
        try:
            from gomoku.defense import DefenseAdvisor
            defense = DefenseAdvisor()
            urgent_defense = defense.find_urgent_defense(board, color)
            if urgent_defense is not None:
                row, col = coord_to_index(urgent_defense)
                if board.grid[row][col] == EMPTY:
                    if color == BLACK:
                        board.grid[row][col] = BLACK
                        if is_forbidden_move(board, row, col, BLACK):
                            board.grid[row][col] = EMPTY
                        else:
                            board.grid[row][col] = EMPTY
                            return urgent_defense
                    else:
                        return urgent_defense
        except Exception:
            pass

        # 12. 白棋多步防守预判
        if color == WHITE:
            try:
                from gomoku.defense import DefenseAdvisor
                defense = DefenseAdvisor()
                multi_defense = defense.find_multi_ply_defense(board, color)
                if multi_defense is not None:
                    row, col = coord_to_index(multi_defense)
                    if board.grid[row][col] == EMPTY:
                        return multi_defense
            except Exception:
                pass

        # 13. OpeningBook开局策略
        try:
            from gomoku.opening_book import OpeningBook
            opening = OpeningBook()
            opening_move = opening.choose_opening_move(board, color)
            if opening_move is not None:
                row, col = coord_to_index(opening_move)
                if board.grid[row][col] == EMPTY:
                    if color == BLACK:
                        board.grid[row][col] = BLACK
                        if is_forbidden_move(board, row, col, BLACK):
                            board.grid[row][col] = EMPTY
                        else:
                            board.grid[row][col] = EMPTY
                            return opening_move
                    else:
                        return opening_move
        except Exception:
            pass

        # 14. Alpha-Beta搜索
        search_move = None
        try:
            from gomoku.search import AlphaBetaSearcher
            searcher = AlphaBetaSearcher(max_depth=3, candidate_limit=8, time_limit=2.0)
            search_move = searcher.iterative_deepening_search(board, color)
        except Exception:
            pass

        if search_move is None:
            try:
                from gomoku.search import AlphaBetaSearcher
                searcher = AlphaBetaSearcher(max_depth=2, candidate_limit=8, time_limit=1.5)
                search_move = searcher.search_best_move(board, color)
            except Exception:
                pass

        if search_move is not None:
            return search_move

        # 15. 评分兜底（白棋使用SafetyAdvisor）
        try:
            from gomoku.evaluator import get_scored_moves
            scored = get_scored_moves(board, color, limit=1)
            if scored:
                if color == WHITE:
                    try:
                        from gomoku.safety import SafetyAdvisor
                        safety = SafetyAdvisor()
                        safe_moves = safety.filter_safe_moves(board, color, [m for m, _ in scored])
                        if safe_moves:
                            return safe_moves[0]
                    except Exception:
                        pass
                return scored[0][0]
        except Exception:
            pass

        # 16. 在已有棋子周围选位
        candidates = get_candidate_moves(board)
        if candidates:
            if color == WHITE:
                try:
                    from gomoku.safety import SafetyAdvisor
                    safety = SafetyAdvisor()
                    safe_moves = safety.filter_safe_moves(board, color, candidates)
                    if safe_moves:
                        safe_moves.sort(key=_distance_to_center)
                        return safe_moves[0]
                except Exception:
                    pass

            valid = []
            for coord_str in candidates:
                r, c = coord_to_index(coord_str)
                if color == BLACK:
                    board.grid[r][c] = BLACK
                    if is_forbidden_move(board, r, c, color):
                        board.grid[r][c] = EMPTY
                        continue
                    board.grid[r][c] = EMPTY
                valid.append(coord_str)
            if valid:
                valid.sort(key=_distance_to_center)
                return valid[0]

        # 17. 选距离天元最近的空位
        all_empty = []
        for row_s in range(_SIZE):
            for col_s in range(_SIZE):
                if board.grid[row_s][col_s] == EMPTY:
                    if color == BLACK:
                        board.grid[row_s][col_s] = BLACK
                        if is_forbidden_move(board, row_s, col_s, color):
                            board.grid[row_s][col_s] = EMPTY
                            continue
                        board.grid[row_s][col_s] = EMPTY
                    all_empty.append(index_to_coord(row_s, col_s))
        all_empty.sort(key=_distance_to_center)
        return all_empty[0]
