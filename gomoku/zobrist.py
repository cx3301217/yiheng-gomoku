"""Zobrist哈希模块

本模块实现Zobrist哈希算法，用于快速计算和更新棋盘状态的哈希值。
结合置换表（Transposition Table）可以避免重复搜索相同的棋盘状态，
显著提升Alpha-Beta搜索效率。

算法说明：
- Zobrist哈希是一种针对棋盘类游戏的哈希技术
- 每个棋盘位置的每种棋子都有独立的随机64位哈希值
- 棋盘哈希由所有位置哈希的异或运算得出
- 落子/撤销落子只需异或对应位置的哈希值即可
"""
import random
from typing import Optional
from gomoku.board import BLACK, WHITE

_SIZE = 15


class ZobristHash:
    """Zobrist哈希计算器

    使用固定随机种子确保每次运行生成相同的哈希表，
    便于测试复现和调试。
    """

    def __init__(self, seed: int = 2026):
        """初始化Zobrist哈希表

        Args:
            seed: 随机种子，默认2026
        """
        # 固定随机种子，确保每次运行结果一致
        random.seed(seed)

        # 棋盘位置哈希表：[row][col][color_index]
        # color_index: 0=BLACK, 1=WHITE
        self.table: list = [[[0, 0] for _ in range(_SIZE)] for _ in range(_SIZE)]

        # 执棋方哈希（黑棋先手和白棋先手不同）
        self.side_hash: int = random.getrandbits(64)

        # 初始化所有位置的哈希值
        for row in range(_SIZE):
            for col in range(_SIZE):
                for color_index in range(2):
                    self.table[row][col][color_index] = random.getrandbits(64)

    @staticmethod
    def color_index(color: int) -> int:
        """获取颜色的索引

        Args:
            color: 棋子颜色 (BLACK 或 WHITE)

        Returns:
            color_index: 0 for BLACK, 1 for WHITE

        Raises:
            ValueError: 非法颜色
        """
        if color == BLACK:
            return 0
        elif color == WHITE:
            return 1
        else:
            raise ValueError(f"非法棋子颜色: {color}，应为 BLACK={BLACK} 或 WHITE={WHITE}")

    def compute_hash(self, board, current_color: Optional[int] = None) -> int:
        """计算当前棋盘的Zobrist哈希值

        Args:
            board: 当前棋盘
            current_color: 当前执棋方颜色，如果为None则不纳入哈希

        Returns:
            64位哈希值
        """
        hash_value = 0

        # 遍历棋盘，异或所有非空位置的哈希
        for row in range(_SIZE):
            for col in range(_SIZE):
                cell = board.grid[row][col]
                if cell != 0:  # 非空
                    color_idx = self.color_index(cell)
                    hash_value ^= self.table[row][col][color_idx]

        # 如果指定了执棋方，纳入哈希
        # 黑棋先手时异或，白棋先手时不异或（与黑棋和空产生区别）
        if current_color == BLACK:
            hash_value ^= self.side_hash

        return hash_value

    def update_hash(
        self, hash_value: int, row: int, col: int, color: int
    ) -> int:
        """更新哈希值（落子或撤销落子）

        落子和撤销落子使用同一个函数，
        因为异或两次等于原值。

        Args:
            hash_value: 当前哈希值
            row: 行号
            col: 列号
            color: 棋子颜色 (BLACK 或 WHITE)

        Returns:
            更新后的哈希值
        """
        color_idx = self.color_index(color)
        return hash_value ^ self.table[row][col][color_idx]
