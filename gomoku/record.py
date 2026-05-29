"""棋谱记录模块：记录并输出五子棋对局棋谱"""
from typing import List, Tuple
import datetime

# 棋子颜色常量
BLACK = 1
WHITE = 2


class GameRecord:
    """五子棋棋谱记录器

    支持记录落子序列并输出标准格式棋谱
    """

    def __init__(self):
        self.moves: List[Tuple[int, str]] = []
        self.result: str = "未知结果"

    def set_result(self, result: str) -> None:
        """设置对局结果

        Args:
            result: 对局结果，如"先手胜"、"后手胜"、"和棋"
        """
        self.result = result

    def add_move(self, color: int, coord: str) -> None:
        """添加一步落子记录

        Args:
            color: 棋子颜色(1=黑棋, 2=白棋)
            coord: 落子坐标(如"H8")
        """
        self.moves.append((color, coord))

    def to_text(self) -> str:
        """将棋谱转换为文本格式

        输出格式:
        {[C5][先手参赛队 B][后手参赛队 W][未知结果][2026 辽宁][辽宁省大学生计算机博弈大赛];B(H,8);W(J,10)}

        Returns:
            棋谱字符串
        """
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        move_parts = []
        for color, coord in self.moves:
            col_letter = coord[0]
            row_num = coord[1:]
            color_char = "B" if color == BLACK else "W"
            move_parts.append(f"{color_char}({col_letter},{row_num})")

        header = (
            f"[C5]"
            f"[先手参赛队 B]"
            f"[后手参赛队 W]"
            f"[{self.result}]"
            f"[{date_str} 辽宁]"
            f"[辽宁省大学生计算机博弈大赛]"
        )
        if move_parts:
            content = header + ";" + ";".join(move_parts)
        else:
            content = header
        return "{" + content + "}"

    def save(self, path: str) -> None:
        """将棋谱保存为txt文件

        Args:
            path: 文件保存路径
        """
        text = self.to_text()
        try:
            with open(path, "w", encoding="gb2312") as f:
                f.write(text)
        except UnicodeEncodeError:
            # GB2312不支持时使用UTF-8
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    def move_count(self) -> int:
        """返回已记录的总步数"""
        return len(self.moves)

    def get_last_move(self) -> Tuple[int, str]:
        """获取最后一步落子"""
        if self.moves:
            return self.moves[-1]
        return (None, None)
