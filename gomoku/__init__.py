"""弈衡五子棋智能博弈程序包"""

from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import coord_to_index, index_to_coord, parse_move_text
from gomoku.record import GameRecord
from gomoku.engine import GomokuEngine
from gomoku.forbidden import (
    is_overline,
    is_forbidden_move,
    is_double_three,
    is_double_four,
)
from gomoku.pattern import (
    FIVE, LIVE_FOUR, RUSH_FOUR,
    LIVE_THREE, SLEEP_THREE,
    LIVE_TWO, SLEEP_TWO,
    get_line_string,
    classify_line_pattern,
    analyze_point_patterns,
)
from gomoku.evaluator import (
    score_point,
    evaluate_board,
    evaluate_move,
    get_scored_moves,
    get_candidate_moves,
)
from gomoku.rules import RulesConfig
from gomoku.opening import (
    OpeningState,
    OPENING_SPECIFIED,
    OPENING_FREE,
    OPENING_DIAGONAL,
    OPENING_DIRECT,
    DIAGONAL_OPENINGS,
    DIRECT_OPENINGS,
)

__all__ = [
    "Board",
    "GameRecord",
    "GomokuEngine",
    "BLACK",
    "WHITE",
    "EMPTY",
    "coord_to_index",
    "index_to_coord",
    "parse_move_text",
    "is_overline",
    "is_forbidden_move",
    "is_double_three",
    "is_double_four",
    "FIVE", "LIVE_FOUR", "RUSH_FOUR",
    "LIVE_THREE", "SLEEP_THREE",
    "LIVE_TWO", "SLEEP_TWO",
    "get_line_string",
    "classify_line_pattern",
    "analyze_point_patterns",
    "score_point",
    "evaluate_board",
    "evaluate_move",
    "get_scored_moves",
    "RulesConfig",
    "OpeningState",
    "OPENING_SPECIFIED", "OPENING_FREE",
    "OPENING_DIAGONAL", "OPENING_DIRECT",
    "DIAGONAL_OPENINGS", "DIRECT_OPENINGS",
]
