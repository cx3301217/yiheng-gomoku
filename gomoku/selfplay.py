"""AI自我对弈与压力测试模块"""
import os
import sys
import datetime
from typing import Dict, List

# 添加父目录到路径以便导入 gomoku 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import coord_to_index
from gomoku.engine import GomokuEngine
from gomoku.record import GameRecord
from gomoku.forbidden import is_forbidden_move


# 快速搜索配置（用于自我对弈测试）
_FAST_SEARCH_DEPTH = 1
_FAST_CANDIDATE_LIMIT = 4
_FAST_TIME_LIMIT = 0.5


class SelfPlayRunner:
    """AI自我对弈压力测试运行器

    用于自动进行AI自我对弈，统计胜负、非法落子、超时情况、搜索节点等。

    Attributes:
        games: 对弈盘数
        max_moves: 每盘最大步数
        black_wins: 黑胜次数
        white_wins: 白胜次数
        draws: 和棋次数
        illegal_moves: 非法落子次数
        timeout_games: 搜索超时盘数
        total_moves: 总步数
        records: 每盘结果列表
    """

    def __init__(self, games: int = 10, max_moves: int = 225):
        self.games = games
        self.max_moves = max_moves
        self.black_wins: int = 0
        self.white_wins: int = 0
        self.draws: int = 0
        self.illegal_moves: int = 0
        self.timeout_games: int = 0
        self.total_moves: int = 0
        self.total_nodes: int = 0
        self.max_nodes_one_move: int = 0
        self.records: list = []

    def run_one_game(self, verbose: bool = False) -> Dict:
        """运行一盘AI自我对弈

        Args:
            verbose: 是否打印每步落子

        Returns:
            结果字典，包含 winner, moves, illegal, reason, record_text,
            timeout, nodes, avg_nodes_per_move, max_nodes_one_move
        """
        # 导入搜索模块用于快速搜索
        try:
            from gomoku.search import AlphaBetaSearcher
            use_fast_search = True
        except ImportError:
            use_fast_search = False

        board = Board()
        record = GameRecord()
        current_color = BLACK
        illegal = False
        reason = ""
        winner = ""
        game_timeout = False
        game_nodes = 0
        move_max_nodes = 0

        for move_num in range(1, self.max_moves + 1):
            move_nodes = 0

            # 获取AI落子
            try:
                if use_fast_search:
                    # 使用快速搜索配置
                    searcher = AlphaBetaSearcher(
                        max_depth=_FAST_SEARCH_DEPTH,
                        candidate_limit=_FAST_CANDIDATE_LIMIT,
                        time_limit=_FAST_TIME_LIMIT,
                    )
                    move = searcher.search_best_move(board, current_color)
                    move_nodes = searcher.nodes
                    if searcher.timeout:
                        game_timeout = True
                    # 如果搜索失败，回退到引擎
                    if move is None:
                        move = GomokuEngine.choose_move(board, current_color)
                else:
                    move = GomokuEngine.choose_move(board, current_color)
            except Exception as e:
                if verbose:
                    print(f"  AI选择落子时异常: {e}")
                illegal = True
                reason = "illegal_move"
                winner = "WHITE" if current_color == BLACK else "BLACK"
                break

            # 检查坐标合法性
            if move is None:
                if verbose:
                    print(f"  AI返回空坐标")
                illegal = True
                reason = "illegal_move"
                winner = "WHITE" if current_color == BLACK else "BLACK"
                break

            try:
                row, col = coord_to_index(move)
            except ValueError:
                if verbose:
                    print(f"  非法坐标: {move}")
                illegal = True
                reason = "illegal_move"
                winner = "WHITE" if current_color == BLACK else "BLACK"
                break

            # 检查是否为空位
            if not board.is_empty(row, col):
                if verbose:
                    print(f"  位置已有棋子: {move}")
                illegal = True
                reason = "illegal_move"
                winner = "WHITE" if current_color == BLACK else "BLACK"
                break

            # 黑棋检查禁手
            if current_color == BLACK:
                board.grid[row][col] = BLACK
                if is_forbidden_move(board, row, col, BLACK):
                    board.grid[row][col] = EMPTY
                    if verbose:
                        print(f"  黑棋禁手: {move}")
                    illegal = True
                    reason = "black_forbidden"
                    winner = "WHITE"
                    break
                board.grid[row][col] = EMPTY

            # 落子
            board.place_stone(row, col, current_color)
            record.add_move(current_color, move.upper())

            if verbose:
                color_name = "黑" if current_color == BLACK else "白"
                print(f"  {move_num:3d}: {color_name} {move}")

            # 累计搜索节点
            game_nodes += move_nodes
            if move_nodes > move_max_nodes:
                move_max_nodes = move_nodes

            # 判断胜负
            if current_color == BLACK:
                # 黑棋：先判五连
                if board.has_exact_five(row, col, BLACK):
                    winner = "BLACK"
                    reason = "black_exact_five"
                    break
                # 黑棋：再判禁手
                if is_forbidden_move(board, row, col, BLACK):
                    winner = "WHITE"
                    reason = "black_forbidden"
                    break
            else:
                # 白棋：五连及以上算胜
                if board.has_five_or_more(row, col, WHITE):
                    winner = "WHITE"
                    reason = "white_five"
                    break

            # 和棋判断
            if board.is_full():
                winner = "DRAW"
                reason = "draw"
                break

            # 切换颜色
            current_color = WHITE if current_color == BLACK else BLACK

        # 处理超时或超过最大步数
        if move_num >= self.max_moves and not winner:
            winner = "DRAW"
            reason = "max_moves"

        # 设置棋谱结果
        if illegal:
            # 非法落子导致判负
            if current_color == BLACK:
                record.set_result("后手胜")
            else:
                record.set_result("先手胜")
        elif winner == "BLACK":
            record.set_result("先手胜")
        elif winner == "WHITE":
            record.set_result("后手胜")
        else:
            record.set_result("和棋")

        # 获取棋谱文本
        record_text = record.to_text()

        # 计算平均节点数
        avg_nodes = round(game_nodes / move_num, 1) if move_num > 0 else 0

        return {
            "winner": winner,
            "moves": move_num,
            "illegal": illegal,
            "timeout": game_timeout,
            "reason": reason,
            "nodes": game_nodes,
            "avg_nodes_per_move": avg_nodes,
            "max_nodes_one_move": move_max_nodes,
            "record_text": record_text,
        }

    def run_many(self, games: int = 10, verbose: bool = False) -> Dict:
        """连续运行多盘自我对弈并统计结果

        Args:
            games: 对弈盘数
            verbose: 是否打印每步落子

        Returns:
            统计结果字典
        """
        self.games = games
        self.black_wins = 0
        self.white_wins = 0
        self.draws = 0
        self.illegal_moves = 0
        self.timeout_games = 0
        self.total_moves = 0
        self.total_nodes = 0
        self.max_nodes_one_move = 0
        self.records = []

        for i in range(games):
            if verbose:
                print(f"\n{'='*40}")
                print(f"第 {i+1}/{games} 盘")
                print('='*40)

            result = self.run_one_game(verbose=verbose)
            self.records.append(result)

            if result["winner"] == "BLACK":
                self.black_wins += 1
            elif result["winner"] == "WHITE":
                self.white_wins += 1
            else:
                self.draws += 1

            if result["illegal"]:
                self.illegal_moves += 1

            if result.get("timeout", False):
                self.timeout_games += 1

            self.total_moves += result["moves"]
            self.total_nodes += result["nodes"]
            if result["max_nodes_one_move"] > self.max_nodes_one_move:
                self.max_nodes_one_move = result["max_nodes_one_move"]

        # 计算统计数据
        avg_moves = round(self.total_moves / games, 1) if games > 0 else 0
        avg_nodes_game = round(self.total_nodes / games, 1) if games > 0 else 0
        avg_nodes_move = round(self.total_nodes / self.total_moves, 1) if self.total_moves > 0 else 0

        return {
            "games": games,
            "black_wins": self.black_wins,
            "white_wins": self.white_wins,
            "draws": self.draws,
            "illegal_moves": self.illegal_moves,
            "timeout_games": self.timeout_games,
            "average_moves": avg_moves,
            "total_nodes": self.total_nodes,
            "avg_nodes_per_game": avg_nodes_game,
            "avg_nodes_per_move": avg_nodes_move,
            "max_nodes_one_move": self.max_nodes_one_move,
        }

    @staticmethod
    def print_summary(summary: Dict) -> None:
        """格式化打印统计结果

        Args:
            summary: run_many 返回的统计结果字典
        """
        print()
        print("==============================")
        print("AI自我对弈压力测试结果")
        print("==============================")
        print(f"总盘数：{summary['games']}")
        print(f"黑棋胜：{summary['black_wins']}")
        print(f"白棋胜：{summary['white_wins']}")
        print(f"和棋：{summary['draws']}")
        print(f"非法落子：{summary['illegal_moves']}")
        if summary.get("timeout_games", 0) > 0:
            print(f"超时盘数：{summary['timeout_games']}")
        print(f"平均步数：{summary['average_moves']}")
        print("---")
        print(f"总搜索节点数：{summary['total_nodes']}")
        print(f"平均每盘节点数：{summary['avg_nodes_per_game']}")
        print(f"平均每步节点数：{summary['avg_nodes_per_move']}")
        print(f"单步最大节点数：{summary['max_nodes_one_move']}")
        print("==============================")
        print()

    def save_report(self, summary: Dict, output_dir: str = "reports") -> str:
        """保存自我对弈统计报告为 txt 文件

        Args:
            summary: run_many 返回的统计结果字典
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        # 创建目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"selfplay_report_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)

        # 生成报告内容
        lines = []
        lines.append("=" * 50)
        lines.append("AI自我对弈压力测试结果")
        lines.append("=" * 50)
        lines.append(f"测试时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"总盘数：{summary['games']}")
        lines.append(f"黑棋胜：{summary['black_wins']}")
        lines.append(f"白棋胜：{summary['white_wins']}")
        lines.append(f"和棋：{summary['draws']}")
        lines.append(f"非法落子：{summary['illegal_moves']}")
        if summary.get("timeout_games", 0) > 0:
            lines.append(f"超时盘数：{summary['timeout_games']}")
        lines.append(f"平均步数：{summary['average_moves']}")
        lines.append("---")
        lines.append(f"总搜索节点数：{summary['total_nodes']}")
        lines.append(f"平均每盘节点数：{summary['avg_nodes_per_game']}")
        lines.append(f"平均每步节点数：{summary['avg_nodes_per_move']}")
        lines.append(f"单步最大节点数：{summary['max_nodes_one_move']}")
        lines.append("=" * 50)
        lines.append("各盘简要结果")
        lines.append("=" * 50)

        for i, rec in enumerate(self.records):
            lines.append(f"第{i+1}盘: {rec['winner']}胜, {rec['moves']}步, {rec['nodes']}节点")

        lines.append("=" * 50)

        # 保存文件
        content = "\n".join(lines)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            with open(filepath, "w", encoding="gbk") as f:
                f.write(content)

        return filepath

    def save_records(self, output_dir: str = "records/selfplay") -> List[str]:
        """保存各盘棋谱为 txt 文件

        Args:
            output_dir: 输出目录

        Returns:
            保存的文件路径列表
        """
        # 创建目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        filepaths = []

        for i, rec in enumerate(self.records):
            # 生成文件名
            filename = f"selfplay_game_{i+1:03d}.txt"
            filepath = os.path.join(output_dir, filename)

            # 保存棋谱
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(rec["record_text"])
            except Exception:
                with open(filepath, "w", encoding="gbk") as f:
                    f.write(rec["record_text"])

            filepaths.append(filepath)

        return filepaths
