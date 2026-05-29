"""开局管理模块：处理指定开局、三手交换和五手N打的流程"""
from __future__ import annotations
from typing import Optional, Tuple, List
from gomoku.coordinate import coord_to_index

# 开局模式常量
OPENING_SPECIFIED = "specified"
OPENING_FREE = "free"

# 开局类型常量
OPENING_DIAGONAL = "diagonal"
OPENING_DIRECT = "direct"

# 斜指开局名称列表（13种）
DIAGONAL_OPENINGS = [
    "斜月", "名月", "恒星", "岚月", "明星", "峡月", "长星",
    "浦月", "云月", "水月", "银月", "流星", "彗星",
]

# 直指开局名称列表（13种）
DIRECT_OPENINGS = [
    "残月", "瑞星", "雨月", "疏星", "松月", "新月", "花月",
    "寒星", "丘月", "山月", "金星", "溪月", "游星",
]

# 天元坐标
_TENGEN = "H8"

# 天元8个相邻点
_TENGEN_ADJACENT = {"G7", "H7", "I7", "G8", "I8", "G9", "H9", "I9"}

# 斜侧相邻点（对角方向）
_DIAGONAL_ADJACENT = {"G7", "I7", "G9", "I9"}

# 直侧相邻点（正交方向）
_DIRECT_ADJACENT = {"H7", "G8", "I8", "H9"}

# 中心5x5区域：横坐标F-J(5-9)，纵坐标6-10
_CENTER5X5_COLS = set("FGHIJ")
_CENTER5X5_ROWS = {"6", "7", "8", "9", "10"}

# 官方26种指定开局表（《中国五子棋竞赛规则（2013）附录七》图示方向）
OFFICIAL_OPENINGS = {
    # 斜指开局：白2=I9
    "斜月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "G7"},
    "名月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "G6"},
    "恒星": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "J8"},
    "岚月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "I6"},
    "明星": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "H6"},
    "峡月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "J9"},
    "长星": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "J10"},
    "浦月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "I7"},
    "云月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "I8"},
    "水月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "J7"},
    "银月": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "H7"},
    "流星": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "J6"},
    "彗星": {"type": "斜指", "black1": "H8", "white2": "I9", "black3": "F6"},

    # 直指开局：白2=H9
    "残月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "J9"},
    "瑞星": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "H6"},
    "雨月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "I8"},
    "疏星": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "J10"},
    "松月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "H7"},
    "新月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "J7"},
    "花月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "I9"},
    "寒星": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "H10"},
    "丘月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "I7"},
    "山月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "I6"},
    "金星": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "J8"},
    "溪月": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "I10"},
    "游星": {"type": "直指", "black1": "H8", "white2": "H9", "black3": "J6"},
}


def get_opening_names() -> List[str]:
    """返回26种开局名称列表"""
    return list(OFFICIAL_OPENINGS.keys())


def get_official_opening(opening_name: str) -> dict:
    """返回指定开局的官方坐标信息"""
    return OFFICIAL_OPENINGS.get(opening_name, None)


def generate_first_three(opening_name: str) -> List[Tuple[str, str]]:
    """生成标准前三手

    Args:
        opening_name: 开局名称

    Returns:
        标准前三手列表，每项为 (棋子颜色, 坐标)，如 [("B", "H8"), ("W", "H9"), ("B", "H10")]
    """
    opening = OFFICIAL_OPENINGS.get(opening_name)
    if not opening:
        return [("B", "H8"), ("W", "H9"), ("B", "H10")]  # 默认寒星

    return [
        ("B", opening["black1"]),
        ("W", opening["white2"]),
        ("B", opening["black3"]),
    ]


def validate_official_opening(opening_name: str, first_three_text: str) -> Tuple[bool, str]:
    """校验输入前三手是否与官方图示方向一致

    Args:
        opening_name: 开局名称
        first_three_text: 前三手文本，如 "B(H8);W(H9);B(H10)" 或 "H8,H9,H10"

    Returns:
        (是否一致, 提示信息)
    """
    opening = OFFICIAL_OPENINGS.get(opening_name)
    if not opening:
        return (False, f"未知开局名称: {opening_name}")

    # 解析输入
    coords = _parse_coords(first_three_text)
    if len(coords) != 3:
        return (False, f"输入坐标数量不正确，应为3个")

    b1, w2, b3 = coords

    # 检查是否与官方一致
    official_b1 = opening["black1"]
    official_w2 = opening["white2"]
    official_b3 = opening["black3"]

    if b1 == official_b1 and w2 == official_w2 and b3 == official_b3:
        return (True, "与官方图示方向一致")

    # 不一致但满足基本规则
    valid, msg = validate_basic_specified_opening(first_three_text)
    if valid:
        return (False,
                f"该前三手满足基本指定开局规则，但与内置官方图示方向({official_b1},{official_w2},{official_b3})不一致。"
                f"可能是旋转/镜像摆法，请核对。")

    return (False, msg)


def validate_basic_specified_opening(first_three_text: str) -> Tuple[bool, str]:
    """校验基本指定开局规则

    Args:
        first_three_text: 前三手文本

    Returns:
        (是否合法, 提示信息)
    """
    coords = _parse_coords(first_three_text)
    if len(coords) != 3:
        return (False, f"输入坐标数量不正确，应为3个")

    b1, w2, b3 = coords

    # 黑1必须是H8
    if b1.upper() != "H8":
        return (False, f"黑1({b1})必须为H8")

    # 三个点不能重复
    coords_upper = [c.upper() for c in [b1, w2, b3]]
    if len(set(coords_upper)) != 3:
        return (False, f"前三手存在重复坐标")

    # 白2必须紧邻H8
    if w2.upper() not in _TENGEN_ADJACENT:
        return (False, f"白2({w2})必须紧邻H8(应为G7/I7/G8/I8/G9/H9/I9之一)")

    # 黑3必须在中心5×5区域
    b3_upper = b3.upper()
    col = b3_upper[0] if len(b3_upper) >= 1 else ""
    row = b3_upper[1:] if len(b3_upper) >= 2 else ""

    if col not in _CENTER5X5_COLS or row not in _CENTER5X5_ROWS:
        return (False, f"黑3({b3})必须在中心5×5区域(F6-J10)")

    return (True, "基本指定开局规则校验通过")


def _parse_coords(text: str) -> List[str]:
    """解析坐标文本，返回坐标列表"""
    # 清理文本
    text = text.upper().replace(" ", "").replace("B(", "").replace("W(", "").replace(")", "")

    # 按分号或逗号分割
    if ";" in text:
        parts = text.split(";")
    else:
        parts = text.split(",")

    coords = []
    for part in parts:
        part = part.strip()
        if part:
            # 移除颜色前缀
            if part.startswith("B") or part.startswith("W"):
                part = part[1:]
            coords.append(part)

    return coords


class OpeningState:
    """开局状态管理器"""

    def __init__(self):
        self.mode: str = OPENING_SPECIFIED
        self.opening_name: Optional[str] = None
        self.opening_type: Optional[str] = None
        self.n_for_fifth: int = 2
        self.swapped: bool = False
        self.first_three_done: bool = False
        self.fifth_candidates: list[str] = []
        self.selected_fifth: Optional[str] = None
        self.black1: Optional[str] = None
        self.white2: Optional[str] = None
        self.black3: Optional[str] = None

    def is_tengen(self, coord: str) -> bool:
        """判断是否为天元H8"""
        return coord.upper() == _TENGEN

    def is_adjacent_to_tengen(self, coord: str) -> bool:
        """判断是否紧邻天元"""
        return coord.upper() in _TENGEN_ADJACENT

    def get_opening_type_by_white2(self, coord: str) -> str:
        """根据白2位置判断开局类型"""
        c = coord.upper()
        if c in _DIAGONAL_ADJACENT:
            return OPENING_DIAGONAL
        if c in _DIRECT_ADJACENT:
            return OPENING_DIRECT
        raise ValueError(
            f"白2({coord})不在天元相邻的8个位置中"
        )

    def is_black3_in_center_5x5(self, coord: str) -> bool:
        """判断黑3是否落在以H8为中心的5x5区域内"""
        c = coord.upper()
        if len(c) < 2:
            return False
        col_letter = c[0]
        row_str = c[1:]
        return col_letter in _CENTER5X5_COLS and row_str in _CENTER5X5_ROWS

    def validate_first_three(self, black1: str, white2: str, black3: str) -> Tuple[bool, str]:
        """验证指定开局前三手是否合法"""
        b1 = black1.upper()
        w2 = white2.upper()
        b3 = black3.upper()

        # 三个点不能重复
        if len({b1, w2, b3}) != 3:
            return (False, f"前三手存在重复坐标")

        # 黑1必须是H8
        if b1 != _TENGEN:
            return (False, f"黑1({black1})必须为H8")

        # 白2必须紧邻H8
        if not self.is_adjacent_to_tengen(w2):
            return (False, f"白2({white2})必须紧邻H8")

        # 黑3必须在中心5x5区域
        if not self.is_black3_in_center_5x5(b3):
            return (False, f"黑3({black3})不在中心5×5区域(F6-J10)")

        return (True, "指定开局前三手合法")

    def apply_three_hand_swap(self) -> str:
        """执行三手交换"""
        if not self.first_three_done:
            raise ValueError("前三手尚未完成，不能执行三手交换")
        if self.swapped:
            raise ValueError("已经执行过三手交换，不能重复执行")

        self.swapped = True
        return "已执行三手交换，双方执棋颜色互换"

    def set_fifth_n(self, n: int) -> None:
        """设置五手N打数量"""
        if n < 1:
            raise ValueError(f"五手N打数量必须>=1")
        self.n_for_fifth = n

    def set_fifth_candidates(self, coords: List[str]) -> Tuple[bool, str]:
        """设置五手N打候选点"""
        n = len(coords)

        if n != self.n_for_fifth:
            return (False, f"候选点数量({n})必须等于N({self.n_for_fifth})")

        upper_coords = [c.upper() for c in coords]
        if len(set(upper_coords)) != n:
            return (False, "候选点坐标存在重复")

        for coord in upper_coords:
            try:
                coord_to_index(coord)
            except ValueError:
                return (False, f"坐标({coord})超出棋盘范围")

        self.fifth_candidates = upper_coords
        return (True, f"五手{self.n_for_fifth}打候选点已设置")

    def select_fifth_candidate(self, coord: str) -> Tuple[bool, str]:
        """白方从N个黑5候选点中选择保留一个"""
        c = coord.upper()
        if c not in self.fifth_candidates:
            return (False, f"所选坐标({coord})不在候选点中")
        self.selected_fifth = c
        return (True, f"白方已选定黑5为{c}")
