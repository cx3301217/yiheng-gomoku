"""棋盘模块：实现15×15棋盘数据结构及基本操作"""
from typing import List

EMPTY = 0
BLACK = 1
WHITE = 2


class Board:
    """15×15五子棋棋盘"""

    size = 15

    def __init__(self):
        self.grid: List[List[int]] = [[EMPTY] * self.size for _ in range(self.size)]

    def reset(self) -> None:
        """清空棋盘"""
        for r in range(self.size):
            for c in range(self.size):
                self.grid[r][c] = EMPTY

    def is_empty(self, row: int, col: int) -> bool:
        """判断指定位置是否为空"""
        if not self._in_bounds(row, col):
            return False
        return self.grid[row][col] == EMPTY

    def place_stone(self, row: int, col: int, color: int) -> bool:
        """在指定位置落子

        Args:
            row: 行号(0-14)
            col: 列号(0-14)
            color: 棋子颜色(1=黑棋, 2=白棋)

        Returns:
            落子成功返回True，失败返回False
        """
        if not self._in_bounds(row, col):
            return False
        if self.grid[row][col] != EMPTY:
            return False
        self.grid[row][col] = color
        return True

    def get(self, row: int, col: int) -> int:
        """获取指定位置棋子状态"""
        if not self._in_bounds(row, col):
            raise IndexError(f"下标超出范围: row={row}, col={col}")
        return self.grid[row][col]

    def is_full(self) -> bool:
        """判断棋盘是否已满"""
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == EMPTY:
                    return False
        return True

    def display(self) -> None:
        """在命令行打印棋盘"""
        COL_LETTERS = "ABCDEFGHIJKLMNO"

        print()
        print("    " + "  ".join(COL_LETTERS))
        for row in range(self.size - 1, -1, -1):
            row_num_str = f"{row + 1:2d} "
            cells = []
            for col in range(self.size):
                stone = self.grid[row][col]
                if stone == EMPTY:
                    cells.append(" . ")
                elif stone == BLACK:
                    cells.append(" ● ")
                else:
                    cells.append(" ○ ")
            print(row_num_str + "".join(cells) + f" {row + 1:2d}")
        print("    " + "  ".join(COL_LETTERS))
        print()

    def check_five(self, row: int, col: int, color: int) -> bool:
        """判断某落子后是否形成五连或长连

        Args:
            row: 落子行号
            col: 落子列号
            color: 落子方颜色

        Returns:
            形成五连及以上返回True
        """
        return self.has_five_or_more(row, col, color)

    def has_exact_five(self, row: int, col: int, color: int) -> bool:
        """判断该落子是否在任意方向形成刚好五连

        用于黑棋胜负判定：黑棋刚好五连为胜，长连（>5）为禁手。

        Args:
            row: 落子行号
            col: 落子列号
            color: 落子方颜色

        Returns:
            刚好五连返回True，长连（>5）不计入
        """
        if self.grid[row][col] != color:
            return False

        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            line_count = self.get_line_count(row, col, color, dr, dc)
            if line_count == 5:
                return True
        return False

    def has_five_or_more(self, row: int, col: int, color: int) -> bool:
        """判断该落子是否在任意方向形成五连或长连

        用于白棋胜负判定：白棋长连视同五连胜。

        Args:
            row: 落子行号
            col: 落子列号
            color: 落子方颜色

        Returns:
            五连及以上返回True
        """
        if self.grid[row][col] != color:
            return False

        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            line_count = self.get_line_count(row, col, color, dr, dc)
            if line_count >= 5:
                return True
        return False

    def count_continuous(
        self, row: int, col: int, color: int, dr: int, dc: int
    ) -> int:
        """统计某个位置在指定单方向上的连续同色棋子数量，包含该位置

        Args:
            row: 起始行号
            col: 起始列号
            color: 棋子颜色
            dr: 行方向增量(-1,0,1)
            dc: 列方向增量(-1,0,1)

        Returns:
            连续同色棋子数量
        """
        count = 1
        r, c = row + dr, col + dc
        while self._in_bounds(r, c) and self.grid[r][c] == color:
            count += 1
            r += dr
            c += dc
        return count

    def get_line_count(
        self, row: int, col: int, color: int, dr: int, dc: int
    ) -> int:
        """统计指定方向正反两个方向的总连续数量，包含该位置

        Args:
            row: 起始行号
            col: 起始列号
            color: 棋子颜色
            dr: 行方向增量
            dc: 列方向增量

        Returns:
            正反方向总连续数量
        """
        return self.count_continuous(row, col, color, dr, dc) \
             + self.count_continuous(row, col, color, -dr, -dc) - 1

    @staticmethod
    def _in_bounds(row: int, col: int) -> bool:
        """检查坐标是否在棋盘范围内"""
        return 0 <= row < Board.size and 0 <= col < Board.size
