"""坐标转换模块：实现棋盘坐标与数组下标之间的转换"""
from typing import Optional, Tuple

# 横坐标字母到列索引的映射
_COL_LETTERS = "ABCDEFGHIJKLMNO"


def coord_to_index(coord: str) -> Tuple[int, int]:
    """将棋盘坐标(如'H8')转换为数组下标(row, col)

    Args:
        coord: 棋盘坐标，如"H8"、"J10"、"A1"，大小写均可

    Returns:
        (row, col)元组，row为行号(0-14)，col为列号(0-14)

    Raises:
        ValueError: 非法坐标格式或超出范围
    """
    coord = coord.strip()
    if not coord:
        raise ValueError("坐标不能为空")

    coord = coord.upper()

    # 格式1: "H8"、"J10" 等 (纯坐标)
    if len(coord) >= 2 and len(coord) <= 3:
        col_letter = coord[0]
        row_str = coord[1:]
        if col_letter in _COL_LETTERS and row_str.isdigit():
            col = _COL_LETTERS.index(col_letter)
            row = int(row_str) - 1
            if 0 <= row <= 14:
                return (row, col)

    raise ValueError(f"非法坐标: {coord}")


def index_to_coord(row: int, col: int) -> str:
    """将数组下标(row, col)转换为棋盘坐标(如'H8')

    Args:
        row: 行号(0-14)
        col: 列号(0-14)

    Returns:
        棋盘坐标字符串，如"H8"

    Raises:
        ValueError: 下标超出范围
    """
    if not (0 <= row <= 14 and 0 <= col <= 14):
        raise ValueError(f"非法下标: row={row}, col={col}")

    col_letter = _COL_LETTERS[col]
    row_num = row + 1
    return f"{col_letter}{row_num}"


def parse_move_text(text: str) -> Tuple[Optional[str], str]:
    """解析落子输入，支持带或不带棋色

    支持格式:
        "H8"      -> (None, "H8")
        "h8"      -> (None, "h8"  -> "H8")
        "B(H,8)"  -> ("B", "H8")
        "W(J,10)" -> ("W", "J10")

    Args:
        text: 用户输入的落子字符串

    Returns:
        (color, coord)元组
        color为"B"或"W"，无棋色时为None
        coord为标准化后的坐标字符串(如"H8")

    Raises:
        ValueError: 格式无法解析
    """
    text = text.strip()
    if not text:
        raise ValueError("输入不能为空")

    # 格式2: B(H,8) 或 W(J,10)
    if len(text) >= 5 and text[1] == "(" and "," in text:
        color_char = text[0].upper()
        if color_char not in ("B", "W"):
            raise ValueError(f"非法棋色: {color_char}")
        inner = text[2:].strip()
        if not inner.endswith(")"):
            raise ValueError(f"括号未闭合: {text}")
        inner = inner[:-1]
        parts = inner.split(",")
        if len(parts) != 2:
            raise ValueError(f"格式错误: {text}")
        col_part = parts[0].strip().upper()
        row_part = parts[1].strip()
        if col_part not in _COL_LETTERS:
            raise ValueError(f"非法横坐标: {col_part}")
        if not row_part.isdigit():
            raise ValueError(f"非法纵坐标: {row_part}")
        coord_raw = f"{col_part}{row_part}"
        try:
            row = int(row_part) - 1
            col = _COL_LETTERS.index(col_part)
            if not (0 <= row <= 14 and 0 <= col <= 14):
                raise ValueError(f"坐标超出范围: {coord_raw}")
        except ValueError as e:
            raise ValueError(f"坐标超出范围: {coord_raw}") from e
        return (color_char, coord_raw)

    # 格式1: 纯坐标 "H8"、"J10" 等
    text_upper = text.upper()
    if len(text_upper) >= 2 and len(text_upper) <= 3:
        col_letter = text_upper[0]
        row_str = text_upper[1:]
        if col_letter in _COL_LETTERS and row_str.isdigit():
            col = _COL_LETTERS.index(col_letter)
            row = int(row_str) - 1
            if 0 <= row <= 14:
                return (None, text_upper)
    raise ValueError(f"无法解析的落子格式: {text}")
