"""棋谱记录模块：记录并输出五子棋对局棋谱（C5标准格式）"""
from typing import List, Tuple
import datetime

# 棋子颜色常量
BLACK = 1
WHITE = 2


class GameRecord:
    """五子棋棋谱记录器

    支持记录落子序列并输出标准C5格式棋谱
    """

    def __init__(self):
        self.moves: List[Tuple[int, str]] = []
        self.result: str = "未知结果"
        self.black_team: str = "先手队"
        self.white_team: str = "后手队"
        self.date_place: str = ""
        self.event_name: str = "2026省赛五子棋项目"

    def set_match_info(self, black_team: str, white_team: str,
                       date_place: str = "", event_name: str = "") -> None:
        """设置比赛信息

        Args:
            black_team: 先手/黑方队名
            white_team: 后手/白方队名
            date_place: 日期和地点
            event_name: 比赛名称
        """
        self.black_team = black_team
        self.white_team = white_team
        self.date_place = date_place or datetime.datetime.now().strftime("%Y-%m-%d")
        self.event_name = event_name or "2026省赛五子棋项目"

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
        """将棋谱转换为C5标准文本格式

        输出格式:
        {[C5][先手队][后手队][结果][日期地点][比赛名称];B(H,8);W(H,9)}

        Returns:
            棋谱字符串
        """
        header = (
            f"[C5]"
            f"[{self.black_team}]"
            f"[{self.white_team}]"
            f"[{self.result}]"
            f"[{self.date_place}]"
            f"[{self.event_name}]"
        )
        if self.moves:
            move_parts = []
            for color, coord in self.moves:
                col_letter = coord[0].upper()
                row_num = coord[1:]
                color_char = "B" if color == BLACK else "W"
                move_parts.append(f"{color_char}({col_letter},{row_num})")
            content = header + ";" + ";".join(move_parts)
        else:
            content = header
        return "{" + content + "}"

    def save(self, path: str) -> None:
        """将棋谱保存为txt文件（GBK编码）

        Args:
            path: 文件保存路径
        """
        text = self.to_text()
        try:
            with open(path, "w", encoding="gbk", errors="replace") as f:
                f.write(text)
        except Exception:
            with open(path, "w", encoding="gb2312", errors="replace") as f:
                f.write(text)

    def move_count(self) -> int:
        """返回已记录的总步数"""
        return len(self.moves)

    def get_last_move(self) -> Tuple[int, str]:
        """获取最后一步落子"""
        if self.moves:
            return self.moves[-1]
        return (None, None)
