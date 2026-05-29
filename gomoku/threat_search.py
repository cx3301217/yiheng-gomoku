"""VCF/VCT连续威胁搜索模块

在VCF连续冲四搜索基础上，本模块进一步实现VCT连续威胁搜索，
能够识别由活三、冲四、活四构成的多步强制威胁链。
该策略用于在常规Alpha-Beta搜索前优先发现战术性杀棋路线，
从而提升程序在短时限竞赛环境下的局部战术能力。

算法命名：RCTS-AB 2.0（Rule-Constrained Threat-chain Search with Alpha-Beta Pruning）
中文名称：融合禁手约束、VCF/VCT威胁链与Alpha-Beta剪枝的五子棋智能决策算法
"""
from typing import List, Optional
from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import index_to_coord, coord_to_index
from gomoku.pattern import (
    FIVE, LIVE_FOUR, RUSH_FOUR,
    LIVE_THREE, SLEEP_THREE,
    analyze_point_patterns,
)
from gomoku.forbidden import is_forbidden_move
from gomoku.evaluator import evaluate_move

_SIZE = 15


def is_legal_move(board: Board, row: int, col: int, color: int) -> bool:
    """判断落子是否合法

    Args:
        board: 当前棋盘
        row: 落子行号
        col: 落子列号
        color: 落子方颜色

    Returns:
        是否可以合法落子
    """
    # 坐标必须为空
    if not board._in_bounds(row, col):
        return False
    if board.grid[row][col] != EMPTY:
        return False

    # 黑棋不能下禁手
    if color == BLACK:
        board.grid[row][col] = BLACK
        if is_forbidden_move(board, row, col, BLACK):
            board.grid[row][col] = EMPTY
            return False
        board.grid[row][col] = EMPTY

    return True


def is_win_after_move(board: Board, row: int, col: int, color: int) -> bool:
    """判断某落子后是否获胜（用于尚未落子前的模拟判断）

    必须在棋盘为空时调用，内部会临时落子并检查。

    Args:
        board: 当前棋盘
        row: 落子行号
        col: 落子列号
        color: 落子方颜色

    Returns:
        落子后是否获胜
    """
    if board.grid[row][col] != EMPTY:
        return False

    board.grid[row][col] = color
    try:
        if color == BLACK:
            win = board.has_exact_five(row, col, color)
        else:
            win = board.has_five_or_more(row, col, color)
    finally:
        board.grid[row][col] = EMPTY

    return win


def has_win_on_board(board: Board, row: int, col: int, color: int) -> bool:
    """判断当前位置已经落子后，该颜色是否获胜

    必须在棋盘已有棋子时调用，不会修改棋盘。

    Args:
        board: 当前棋盘
        row: 落子行号
        col: 落子列号
        color: 落子方颜色

    Returns:
        落子后是否获胜
    """
    if board.grid[row][col] != color:
        return False
    if color == BLACK:
        return board.has_exact_five(row, col, BLACK)
    else:
        return board.has_five_or_more(row, col, WHITE)


def get_winning_moves(board: Board, color: int) -> List[str]:
    """获取所有一步胜的落子点

    Args:
        board: 当前棋盘
        color: 落子方颜色

    Returns:
        一步胜的坐标列表
    """
    winning = []
    for row in range(_SIZE):
        for col in range(_SIZE):
            if is_legal_move(board, row, col, color):
                if is_win_after_move(board, row, col, color):
                    winning.append(index_to_coord(row, col))
    return winning


def get_four_threat_moves(board: Board, color: int) -> List[str]:
    """获取能形成冲四或活四威胁的候选落子点

    Args:
        board: 当前棋盘
        color: 落子方颜色

    Returns:
        四威胁候选点列表，按评分降序排序
    """
    threat_moves = []
    move_scores = []

    # 生成候选点：已有棋子周围一格
    candidates = set()
    for row in range(_SIZE):
        for col in range(_SIZE):
            if board.grid[row][col] != EMPTY:
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        nr, nc = row + dr, col + dc
                        if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                            if board.grid[nr][nc] == EMPTY:
                                candidates.add((nr, nc))

    for row, col in candidates:
        if not is_legal_move(board, row, col, color):
            continue

        # 临时落子
        board.grid[row][col] = color

        # 分析棋型
        patterns = analyze_point_patterns(board, row, col, color)
        live_four = patterns.get(LIVE_FOUR, 0)
        rush_four = patterns.get(RUSH_FOUR, 0)

        # 还原棋盘
        board.grid[row][col] = EMPTY

        # 如果有活四或冲四，加入候选
        if live_four + rush_four >= 1:
            coord = index_to_coord(row, col)
            threat_moves.append(coord)
            score = evaluate_move(board, row, col, color)
            move_scores.append((coord, score))

    # 按评分降序排序
    move_scores.sort(key=lambda x: x[1], reverse=True)
    result = [coord for coord, _ in move_scores]

    # 返回前 candidate_limit 个
    return result


def get_forced_responses(board: Board, attacker_color: int) -> List[str]:
    """获取强制应手点

    当攻击方形成四威胁后，防守方必须应对的位置。
    返回攻击方下一步可以成五的位置，防守方必须堵住这些位置。

    Args:
        board: 当前棋盘
        attacker_color: 攻击方颜色

    Returns:
        强制应手点列表（攻击方下一步胜点）
    """
    # 返回攻击方的下一步胜点，这些是防守方必须堵住的位置
    return get_winning_moves(board, attacker_color)


def get_three_threat_moves(board: Board, color: int) -> List[str]:
    """获取能形成活三威胁的候选落子点

    Args:
        board: 当前棋盘
        color: 落子方颜色

    Returns:
        三威胁候选点列表，按评分降序排序
    """
    threat_moves = []
    move_scores = []
    candidate_limit = 8

    # 生成候选点：已有棋子周围一格
    candidates = set()
    for row in range(_SIZE):
        for col in range(_SIZE):
            if board.grid[row][col] != EMPTY:
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        nr, nc = row + dr, col + dc
                        if 0 <= nr < _SIZE and 0 <= nc < _SIZE:
                            if board.grid[nr][nc] == EMPTY:
                                candidates.add((nr, nc))

    for row, col in candidates:
        if not is_legal_move(board, row, col, color):
            continue

        # 临时落子
        board.grid[row][col] = color

        # 分析棋型
        patterns = analyze_point_patterns(board, row, col, color)
        live_three = patterns.get(LIVE_THREE, 0)
        live_four = patterns.get(LIVE_FOUR, 0)
        rush_four = patterns.get(RUSH_FOUR, 0)

        # 还原棋盘
        board.grid[row][col] = EMPTY

        # 如果有活三，加入候选（活三+冲四/活四也保留）
        if live_three >= 1:
            coord = index_to_coord(row, col)
            threat_moves.append(coord)
            score = evaluate_move(board, row, col, color)
            move_scores.append((coord, score))
        # 如果没有活三但有活四或冲四，也保留（作为四威胁）
        elif live_four + rush_four >= 1:
            coord = index_to_coord(row, col)
            threat_moves.append(coord)
            score = evaluate_move(board, row, col, color)
            move_scores.append((coord, score))

    # 按评分降序排序
    move_scores.sort(key=lambda x: x[1], reverse=True)
    result = [coord for coord, _ in move_scores]

    # 返回前 candidate_limit 个
    return result[:candidate_limit]


def is_strong_threat_move(board: Board, row: int, col: int, color: int) -> bool:
    """判断某一步是否是强威胁点

    满足任一条件即可：
    - 一步成五
    - 形成活四
    - 形成冲四
    - 形成活三
    - 形成双活三
    - 形成活三+冲四

    注意：黑棋禁手点不算强威胁点。

    Args:
        board: 当前棋盘
        row: 落子行号
        col: 落子列号
        color: 落子方颜色

    Returns:
        是否是强威胁点
    """
    if board.grid[row][col] != EMPTY:
        return False

    # 黑棋禁手检查
    if color == BLACK:
        board.grid[row][col] = BLACK
        if is_forbidden_move(board, row, col, BLACK):
            board.grid[row][col] = EMPTY
            return False
        board.grid[row][col] = EMPTY

    # 临时落子
    board.grid[row][col] = color

    try:
        # 分析棋型
        patterns = analyze_point_patterns(board, row, col, color)

        # 检查各种强威胁条件
        if patterns.get(FIVE, 0) >= 1:
            return True
        if patterns.get(LIVE_FOUR, 0) >= 1:
            return True
        if patterns.get(RUSH_FOUR, 0) >= 1:
            return True
        if patterns.get(LIVE_THREE, 0) >= 1:
            return True
        # 双活三
        if patterns.get(LIVE_THREE, 0) >= 2:
            return True
        # 活三+冲四
        if patterns.get(LIVE_THREE, 0) >= 1 and patterns.get(RUSH_FOUR, 0) >= 1:
            return True
    finally:
        board.grid[row][col] = EMPTY

    return False


def get_all_threat_moves(board: Board, color: int) -> List[str]:
    """综合返回四威胁点和三威胁点

    Args:
        board: 当前棋盘
        color: 落子方颜色

    Returns:
        综合威胁候选点列表，按评分降序排序
    """
    candidate_limit = 8

    # 先取四威胁点
    four_threats = get_four_threat_moves(board, color)

    # 再取三威胁点
    three_threats = get_three_threat_moves(board, color)

    # 去重
    seen = set()
    unique_threats = []
    move_scores = []

    for coord in four_threats + three_threats:
        if coord not in seen:
            seen.add(coord)
            unique_threats.append(coord)
            row, col = coord_to_index(coord)
            score = evaluate_move(board, row, col, color)
            move_scores.append((coord, score))

    # 按评分降序排序
    move_scores.sort(key=lambda x: x[1], reverse=True)
    result = [coord for coord, _ in move_scores]

    return result[:candidate_limit]


class ThreatSearcher:
    """VCF/VCT连续威胁搜索器

    实现规则约束威胁链搜索，在Alpha-Beta搜索前识别连续冲四和连续威胁杀棋机会。
    """

    def __init__(self, max_vcf_depth: int = 5, candidate_limit: int = 10):
        """初始化搜索器

        Args:
            max_vcf_depth: VCF/VCT搜索最大深度
            candidate_limit: 候选点数量上限
        """
        self.max_vcf_depth = max_vcf_depth
        self.candidate_limit = candidate_limit
        self.nodes: int = 0

    def vcf_search(
        self, board: Board, attacker_color: int, depth: int
    ) -> Optional[str]:
        """VCF连续冲四杀搜索

        判断 attacker_color 是否存在连续冲四杀路线，如果存在，返回第一步杀棋点。

        Args:
            board: 当前棋盘
            attacker_color: 攻击方颜色
            depth: 剩余搜索深度

        Returns:
            第一步杀棋点，不存在则返回 None
        """
        self.nodes += 1

        # 深度耗尽，返回None
        if depth <= 0:
            return None

        # 先检查一步胜
        winning = get_winning_moves(board, attacker_color)
        if winning:
            return winning[0]

        # 生成四威胁候选点
        threat_moves = get_four_threat_moves(board, attacker_color)

        for threat_coord in threat_moves[:self.candidate_limit]:
            row, col = coord_to_index(threat_coord)

            # 检查是否合法
            if not is_legal_move(board, row, col, attacker_color):
                continue

            # 攻击方临时落子
            board.grid[row][col] = attacker_color

            try:
                # 使用 has_win_on_board 检查是否直接获胜（棋子已在棋盘上）
                if has_win_on_board(board, row, col, attacker_color):
                    return threat_coord

                # 找到防守方强制应手（攻击方下一步胜点）
                forced = get_forced_responses(board, attacker_color)

                # 如果没有强制应手点，攻击方获胜
                if not forced:
                    return threat_coord

                # 如果有多个强制应手点（>=2），攻击方形成多重胜点
                if len(forced) >= 2:
                    return threat_coord

                # 只有一个强制应手，防守方落子
                defend_row, defend_col = coord_to_index(forced[0])
                defender_color = WHITE if attacker_color == BLACK else BLACK
                board.grid[defend_row][defend_col] = defender_color

                try:
                    # 递归搜索（深度减少2，因为双方各走了一步）
                    result = self.vcf_search(board, attacker_color, depth - 2)

                    if result is not None:
                        # 杀棋路线成立
                        return threat_coord
                finally:
                    # 还原防守落子
                    board.grid[defend_row][defend_col] = EMPTY

            finally:
                # 还原攻击落子
                board.grid[row][col] = EMPTY

        # 所有候选失败
        return None

    def _get_vct_defense_moves(
        self, board: Board, attacker_color: int, threat_row: int, threat_col: int
    ) -> List[str]:
        """获取VCT防守应手点

        当攻击方已落子形成威胁后，防守方的可能应手。
        注意：调用此函数时，攻击方棋子已在棋盘上（threat_row, threat_col位置）
        本函数不会修改棋盘。

        Args:
            board: 当前棋盘
            attacker_color: 攻击方颜色
            threat_row: 攻击方威胁点行号（已有攻击方棋子）
            threat_col: 攻击方威胁点列号（已有攻击方棋子）

        Returns:
            防守应手点列表
        """
        # 1.如果攻击方有一步胜点，防守方必须堵
        attacker_winning = get_winning_moves(board, attacker_color)
        if attacker_winning:
            return attacker_winning

        # 2.检查攻击方是否形成活四，如果是，必须堵对应成五点
        # 直接分析棋盘上已有的威胁点（棋子已在棋盘上）
        patterns = analyze_point_patterns(board, threat_row, threat_col, attacker_color)

        if patterns.get(LIVE_FOUR, 0) >= 1:
            # 活四必须堵成五，直接返回攻击方一步胜点
            return get_winning_moves(board, attacker_color)

        # 3.检查攻击方是否形成活三，防守方优先堵高评分点
        if patterns.get(LIVE_THREE, 0) >= 1:
            defender_color = WHITE if attacker_color == BLACK else BLACK
            return get_three_threat_moves(board, defender_color)[:self.candidate_limit]

        # 4.默认返回空（无法防守）
        return []

    def vct_search(
        self, board: Board, attacker_color: int, depth: int
    ) -> Optional[str]:
        """VCT连续威胁搜索

        判断 attacker_color 是否存在连续威胁胜路线，如果存在，返回第一步威胁点。
        VCT搜索不仅考虑冲四，还考虑活三、活四等更广泛的威胁类型。

        Args:
            board: 当前棋盘
            attacker_color: 攻击方颜色
            depth: 剩余搜索深度（每步减少2，双方各走一步）

        Returns:
            第一步威胁点，不存在则返回 None
        """
        self.nodes += 1

        # 深度耗尽，返回None
        if depth <= 0:
            return None

        # 1.先检查一步胜
        winning = get_winning_moves(board, attacker_color)
        if winning:
            return winning[0]

        # 2.先调用VCF（优先VCF，因为冲四比活三更强）
        vcf_result = self.vcf_search(board, attacker_color, min(depth, self.max_vcf_depth))
        if vcf_result is not None:
            return vcf_result

        # 3.生成所有威胁候选点（三威胁+四威胁）
        threat_moves = get_all_threat_moves(board, attacker_color)

        for threat_coord in threat_moves[:self.candidate_limit]:
            row, col = coord_to_index(threat_coord)

            # 检查是否合法
            if not is_legal_move(board, row, col, attacker_color):
                continue

            # 攻击方临时落子
            board.grid[row][col] = attacker_color

            try:
                # 使用 has_win_on_board 检查是否直接获胜（棋子已在棋盘上）
                if has_win_on_board(board, row, col, attacker_color):
                    return threat_coord

                # 计算防守方可能应手（棋子已在棋盘上，直接传坐标）
                defense_moves = self._get_vct_defense_moves(board, attacker_color, row, col)

                # 如果防守方没有应手，认为攻击方威胁成立
                if not defense_moves:
                    return threat_coord

                # 尝试每个防守应手
                success = True
                for defend_coord in defense_moves[:self.candidate_limit]:
                    defend_row, defend_col = coord_to_index(defend_coord)
                    defender_color = WHITE if attacker_color == BLACK else BLACK

                    # 检查防守落子是否合法
                    if not is_legal_move(board, defend_row, defend_col, defender_color):
                        continue

                    # 防守方临时落子
                    board.grid[defend_row][defend_col] = defender_color

                    try:
                        # 递归调用VCT搜索
                        result = self.vct_search(board, attacker_color, depth - 2)

                        if result is None:
                            # 这条防守路线失败，威胁不成立
                            success = False
                            break
                    finally:
                        # 还原防守落子
                        board.grid[defend_row][defend_col] = EMPTY

                if success:
                    # 找到一条成功路线
                    return threat_coord

            finally:
                # 还原攻击落子
                board.grid[row][col] = EMPTY

        # 所有候选失败
        return None

    def find_opponent_vcf_defense(
        self, board: Board, my_color: int
    ) -> Optional[str]:
        """检测对方是否有VCF杀棋，并找出防守点

        Args:
            board: 当前棋盘
            my_color: 我方颜色

        Returns:
            防守点坐标，如果对方无VCF威胁则返回 None
        """
        opponent_color = WHITE if my_color == BLACK else BLACK

        # 检查对方是否有VCF杀棋
        threat_move = self.vcf_search(board, opponent_color, self.max_vcf_depth)

        if threat_move is None:
            return None

        # 返回威胁点作为优先防守位置
        return threat_move

    def find_opponent_vct_defense(
        self, board: Board, my_color: int
    ) -> Optional[str]:
        """检测对方是否存在VCT连续威胁胜，如果存在，返回我方优先防守点

        Args:
            board: 当前棋盘
            my_color: 我方颜色

        Returns:
            优先防守点坐标，如果对方无VCT威胁则返回 None
        """
        opponent_color = WHITE if my_color == BLACK else BLACK

        # 调用VCT搜索
        threat_move = self.vct_search(board, opponent_color, 5)

        if threat_move is None:
            return None

        # 检查威胁点是否仍然合法
        threat_row, threat_col = coord_to_index(threat_move)
        if is_legal_move(board, threat_row, threat_col, opponent_color):
            return threat_move

        # 如果威胁点已不合法，尝试返回对方一步胜点的堵点
        opponent_winning = get_winning_moves(board, opponent_color)
        if opponent_winning:
            return opponent_winning[0]

        return None


def find_opponent_vcf_defense(board: Board, my_color: int) -> Optional[str]:
    """便捷函数：检测对方是否有VCF杀棋

    Args:
        board: 当前棋盘
        my_color: 我方颜色

    Returns:
        防守点坐标，如果对方无VCF威胁则返回 None
    """
    searcher = ThreatSearcher(max_vcf_depth=5)
    return searcher.find_opponent_vcf_defense(board, my_color)


def find_opponent_vct_defense(board: Board, my_color: int) -> Optional[str]:
    """便捷函数：检测对方是否存在VCT连续威胁胜

    Args:
        board: 当前棋盘
        my_color: 我方颜色

    Returns:
        优先防守点坐标，如果对方无VCT威胁则返回 None
    """
    searcher = ThreatSearcher(max_vcf_depth=5, candidate_limit=8)
    return searcher.find_opponent_vct_defense(board, my_color)
