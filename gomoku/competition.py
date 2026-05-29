"""比赛版运行模式封装模块

提供适合比赛现场使用的简洁比赛模式，
稳定接收对方落子，输出我方落子，自动保存对局日志。
"""
import os
import sys
import datetime
from typing import Tuple, Optional

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.coordinate import coord_to_index, index_to_coord
from gomoku.engine import GomokuEngine
from gomoku.record import GameRecord
from gomoku.forbidden import is_forbidden_move


# 颜色到字符串的映射
_COLOR_NAMES = {
    BLACK: "黑棋",
    WHITE: "白棋",
}

# 字符串到颜色的映射
_STRING_TO_COLOR = {
    "B": BLACK,
    "W": WHITE,
    "BLACK": BLACK,
    "WHITE": WHITE,
    "黑": BLACK,
    "白": WHITE,
}


class CompetitionRunner:
    """比赛运行器

    提供简洁的比赛辅助接口，适合比赛现场使用。

    Attributes:
        my_color: 我方颜色 (BLACK 或 WHITE)
        opponent_color: 对方颜色
        board: 棋盘对象
        record: 棋谱记录对象
        game_over: 游戏是否结束
        winner: 胜者
        log: 运行日志列表
        move_count: 当前步数
    """

    def __init__(self, my_color: int):
        """初始化比赛运行器

        Args:
            my_color: 我方颜色，必须是 BLACK 或 WHITE

        Raises:
            ValueError: 如果 my_color 不是 BLACK 或 WHITE
        """
        if my_color not in (BLACK, WHITE):
            raise ValueError(f"my_color 必须是 BLACK({BLACK}) 或 WHITE({WHITE})，实际: {my_color}")

        self.my_color = my_color
        self.opponent_color = WHITE if my_color == BLACK else BLACK
        self.board = Board()
        self.record = GameRecord()
        self.game_over = False
        self.winner: Optional[str] = None
        self.log: list = []
        self.move_count = 0

        self._log(f"比赛开始，我方执{'黑' if my_color == BLACK else '白'}")

    def set_colors(self, my_color: int) -> None:
        """设置我方颜色并更新对方颜色

        Args:
            my_color: 新我方颜色 (BLACK 或 WHITE)
        """
        if my_color not in (BLACK, WHITE):
            raise ValueError(f"my_color 必须是 BLACK({BLACK}) 或 WHITE({WHITE})")

        self.my_color = my_color
        self.opponent_color = WHITE if my_color == BLACK else BLACK
        self._log(f"执棋颜色更新，我方现执{'黑' if my_color == BLACK else '白'}")

    def swap_colors(self) -> None:
        """交换双方执棋颜色"""
        self.my_color, self.opponent_color = self.opponent_color, self.my_color
        self._log(f"三手交换完成，我方现执{'黑' if self.my_color == BLACK else '白'}")

    def _set_result_and_log(self, winner: str) -> None:
        """设置比赛结果并记录日志

        Args:
            winner: 胜者 ("BLACK" / "WHITE" / "DRAW")
        """
        if winner == "BLACK":
            self.record.set_result("先手胜")
            self._log("对局结束：黑棋胜")
        elif winner == "WHITE":
            self.record.set_result("后手胜")
            self._log("对局结束：白棋胜")
        elif winner == "DRAW":
            self.record.set_result("和棋")
            self._log("对局结束：和棋")

    def start_if_black(self) -> Optional[str]:
        """如果我方执黑，自动落子

        Returns:
            如果执黑，返回第一手标准格式如 "B(H,8)"
            如果执白，返回 None
        """
        if self.my_color != BLACK:
            return None

        # 黑棋第一手应走 H8
        move = GomokuEngine.choose_move(self.board, BLACK)
        row, col = coord_to_index(move)

        # 落子
        self.board.place_stone(row, col, BLACK)
        self.record.add_move(BLACK, move.upper())
        self.move_count += 1

        # 判断胜负
        if self.board.has_exact_five(row, col, BLACK):
            self.game_over = True
            self.winner = "BLACK"
            self._set_result_and_log("BLACK")

        result = self.format_move(BLACK, move)
        self._log(f"我方落子: {result}")
        return result

    def receive_opponent_move(self, text: str) -> Tuple[bool, str]:
        """接收对方落子

        Args:
            text: 对方落子输入，支持 H8、B(H,8)、W(J,10) 等格式

        Returns:
            (成功标志, 结果信息)
            成功时: (True, "B(H,8)" 或 "W(J,10)")
            失败时: (False, "错误原因")
        """
        if self.game_over:
            return (False, "游戏已结束")

        # 解析输入
        color, coord = self._parse_input(text)

        if color is None:
            return (False, f"无法解析输入: {text}")

        # 检查颜色是否与对手一致
        if color != self.opponent_color:
            expected = "B" if self.opponent_color == BLACK else "W"
            received = "B" if color == BLACK else "W"
            return (False, f"颜色不符，期望{expected}方，实际{received}方")

        # 检查坐标合法性
        try:
            row, col = coord_to_index(coord)
        except ValueError:
            return (False, f"非法坐标: {coord}")

        # 检查是否为空
        if not self.board.is_empty(row, col):
            return (False, f"位置已有棋子: {coord}")

        # 落子
        self.board.place_stone(row, col, color)
        self.record.add_move(color, coord.upper())
        self.move_count += 1

        result = self.format_move(color, coord)
        self._log(f"对方落子: {result}")

        # 判断胜负
        game_over, winner = self.check_result(color, coord)
        if game_over:
            self.game_over = True
            self.winner = winner
            self._set_result_and_log(winner)

        return (True, result)

    def make_my_move(self) -> Tuple[bool, str]:
        """我方AI计算并落子

        Returns:
            (成功标志, 结果信息)
            成功时: (True, "B(H,8)" 或 "W(J,10)")
            失败时: (False, "错误原因")
        """
        if self.game_over:
            return (False, "游戏已结束")

        # AI选择落子
        try:
            move = GomokuEngine.choose_move(self.board, self.my_color)
        except Exception as e:
            return (False, f"AI选择落子异常: {e}")

        if move is None:
            return (False, "AI返回空坐标")

        # 检查坐标合法性
        try:
            row, col = coord_to_index(move)
        except ValueError:
            return (False, f"AI返回非法坐标: {move}")

        # 检查是否为空
        if not self.board.is_empty(row, col):
            return (False, f"AI选择了已有棋子位置: {move}")

        # 黑棋检查禁手
        if self.my_color == BLACK:
            self.board.grid[row][col] = BLACK
            if is_forbidden_move(self.board, row, col, BLACK):
                self.board.grid[row][col] = EMPTY
                return (False, f"AI选择了禁手点: {move}")
            self.board.grid[row][col] = EMPTY

        # 落子
        self.board.place_stone(row, col, self.my_color)
        self.record.add_move(self.my_color, move.upper())
        self.move_count += 1

        result = self.format_move(self.my_color, move)
        self._log(f"我方落子: {result}")

        # 判断胜负
        game_over, winner = self.check_result(self.my_color, move)
        if game_over:
            self.game_over = True
            self.winner = winner
            self._set_result_and_log(winner)

        return (True, result)

    def check_result(self, color: int, coord: str) -> Tuple[bool, Optional[str]]:
        """判断刚刚落子后是否结束

        Args:
            color: 落子方颜色
            coord: 落子坐标

        Returns:
            (是否结束, 胜者或None)
        """
        row, col = coord_to_index(coord)

        if color == BLACK:
            # 黑棋：先判五连
            if self.board.has_exact_five(row, col, BLACK):
                return (True, "BLACK")
            # 黑棋：再判禁手
            if is_forbidden_move(self.board, row, col, BLACK):
                return (True, "WHITE")
        else:
            # 白棋：五连及以上算胜
            if self.board.has_five_or_more(row, col, WHITE):
                return (True, "WHITE")

        # 和棋判断
        if self.board.is_full():
            return (True, "DRAW")

        return (False, None)

    @staticmethod
    def format_move(color: int, coord: str) -> str:
        """输出标准格式

        Args:
            color: 棋子颜色
            coord: 坐标如 H8

        Returns:
            标准格式如 "B(H,8)" 或 "W(J,10)"
        """
        color_char = "B" if color == BLACK else "W"
        col_letter = coord[0].upper()
        row_num = coord[1:]
        return f"{color_char}({col_letter},{row_num})"

    def _parse_input(self, text: str) -> Tuple[Optional[int], Optional[str]]:
        """解析输入文本

        Args:
            text: 输入文本如 H8、B(H,8)、W(J,10)

        Returns:
            (颜色, 坐标) 或 (None, None)
        """
        text = text.strip()

        # 格式1: B(H,8) 或 W(J,10)
        if len(text) >= 3 and text[1] == "(":
            color_char = text[0].upper()
            if color_char in _STRING_TO_COLOR:
                inner = text[2:-1]  # 去掉 B( 和 )
                parts = inner.split(",")
                if len(parts) == 2:
                    col = parts[0].upper()
                    row = parts[1]
                    coord = col + row
                    return (_STRING_TO_COLOR[color_char], coord)

        # 格式2: H8 (不带颜色)
        if len(text) >= 2:
            # 检查是否是纯坐标
            col = text[0].upper()
            row = text[1:]
            if col.isalpha() and row.isdigit():
                coord = col + row
                # 假设不带颜色的输入是对手的落子
                return (self.opponent_color, coord)

        return (None, None)

    def _log(self, message: str) -> None:
        """添加日志"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {message}")

    def save_log(self, output_dir: str = "logs") -> str:
        """保存比赛日志

        Args:
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"competition_log_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)

        lines = []
        lines.append("=" * 50)
        lines.append("五子棋比赛对局日志")
        lines.append("=" * 50)
        lines.append(f"我方颜色: {'黑棋' if self.my_color == BLACK else '白棋'}")
        lines.append(f"总步数: {self.move_count}")
        lines.append("")

        # 日志内容
        lines.append("--- 对局记录 ---")
        for entry in self.log:
            lines.append(entry)
        lines.append("")

        # 结果
        lines.append("--- 对局结果 ---")
        if self.game_over:
            if self.winner == "BLACK":
                lines.append("结果: 黑棋胜")
            elif self.winner == "WHITE":
                lines.append("结果: 白棋胜")
            else:
                lines.append("结果: 和棋")
        else:
            lines.append("结果: 对局进行中")
        lines.append("")

        # 棋谱
        lines.append("--- 棋谱 ---")
        lines.append(self.record.to_text())
        lines.append("=" * 50)

        content = "\n".join(lines)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            with open(filepath, "w", encoding="gbk") as f:
                f.write(content)

        self._log(f"日志已保存: {filepath}")
        return filepath

    def save_record(self, output_dir: str = "records/competition") -> str:
        """保存比赛棋谱

        Args:
            output_dir: 输出目录

        Returns:
            保存的文件路径
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"competition_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.record.to_text())
        except Exception:
            with open(filepath, "w", encoding="gbk") as f:
                f.write(self.record.to_text())

        self._log(f"棋谱已保存: {filepath}")
        return filepath

    def display_board(self) -> None:
        """显示棋盘"""
        print()
        COL_LETTERS = "ABCDEFGHIJKLMNO"
        print("    " + "  ".join(COL_LETTERS))
        for row in range(self.board.size - 1, -1, -1):
            row_num_str = f"{row + 1:2d} "
            cells = []
            for col in range(self.board.size):
                stone = self.board.grid[row][col]
                if stone == EMPTY:
                    cells.append(" . ")
                elif stone == BLACK:
                    cells.append(" X ")
                else:
                    cells.append(" O ")
            print(row_num_str + "".join(cells) + f" {row + 1:2d}")
        print("    " + "  ".join(COL_LETTERS))
        print()

    def display_record(self) -> None:
        """显示当前棋谱"""
        print("当前棋谱:")
        print(self.record.to_text())
        print()
