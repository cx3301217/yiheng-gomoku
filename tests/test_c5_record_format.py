"""测试C5标准棋谱格式"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gomoku.record import GameRecord, BLACK, WHITE
from gomoku.competition import CompetitionRunner


def test_c5_format_basic():
    """基本C5格式测试"""
    rec = GameRecord()
    rec.set_match_info("弈衡五子棋", "对方队伍", "2026-05-30", "2026省赛五子棋项目")
    rec.add_move(BLACK, "H8")
    rec.add_move(WHITE, "H7")
    rec.add_move(BLACK, "G9")

    text = rec.to_text()

    # 验证格式
    assert text.startswith("{"), "必须以{开头"
    assert text.endswith("}"), "必须以}结尾"
    assert "[C5]" in text, "必须包含[C5]标识"
    assert "弈衡五子棋" in text, "必须包含黑方队名"
    assert "对方队伍" in text, "必须包含白方队名"
    print("[OK] 基本C5格式正确")


def test_c5_no_moves():
    """无落子时只输出头部"""
    rec = GameRecord()
    rec.set_match_info("A队", "B队")
    rec.set_result("未知结果")

    text = rec.to_text()

    assert text.startswith("{[C5]")
    assert text.endswith("}")
    assert ";" not in text, "无落子时不应包含分号"
    assert "弈衡五子棋" not in text
    print("[OK] 无落子格式正确")


def test_c5_move_format():
    """落子格式测试"""
    rec = GameRecord()
    rec.set_match_info("黑队", "白队")
    rec.add_move(BLACK, "H8")
    rec.add_move(WHITE, "H9")
    rec.add_move(BLACK, "H10")

    text = rec.to_text()

    # 落子格式必须为B(H,8);W(H,9);B(H,10)
    assert "B(H,8)" in text, "黑棋落子格式错误"
    assert "W(H,9)" in text, "白棋落子格式错误"
    assert "B(H,10)" in text, "黑棋落子格式错误"
    assert "B(H,8);W(H,9);B(H,10)" in text, "落子序列必须连续"
    print("[OK] 落子格式正确")


def test_c5_result_field():
    """结果字段测试"""
    rec = GameRecord()
    rec.set_match_info("A", "B")

    rec.set_result("先手胜")
    text = rec.to_text()
    assert "[先手胜]" in text

    rec.set_result("后手胜")
    text = rec.to_text()
    assert "[后手胜]" in text

    rec.set_result("和棋")
    text = rec.to_text()
    assert "[和棋]" in text

    rec.set_result("未知结果")
    text = rec.to_text()
    assert "[未知结果]" in text
    print("[OK] 结果字段正确")


def test_c5_save_gbk():
    """GBK编码保存测试"""
    rec = GameRecord()
    rec.set_match_info("弈衡五子棋", "测试队伍", "2026-05-30 沈阳", "2026省赛")
    rec.add_move(BLACK, "H8")
    rec.add_move(WHITE, "H9")

    text = rec.to_text()

    # 用GBK保存
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                     encoding="gbk") as f:
        f.write(text)
        path = f.name

    try:
        # 用GBK读取验证
        with open(path, "r", encoding="gbk") as f:
            loaded = f.read()
        assert loaded == text, "GBK保存/读取内容不一致"
        # 用GB2312也能读
        with open(path, "r", encoding="gb2312") as f:
            loaded2 = f.read()
        assert "弈衡五子棋" in loaded2, "GB2312应能读取中文"
        print("[OK] GBK编码保存/读取正确")
    finally:
        os.unlink(path)


def test_c5_filename_format():
    """文件名格式测试"""
    from gomoku.competition import CompetitionRunner

    runner = CompetitionRunner(BLACK)
    runner.record.set_match_info("弈衡队", "对手队", "2026-05-30", "比赛")
    runner.record.add_move(BLACK, "H8")
    runner.record.add_move(WHITE, "H9")

    path = runner.save_record(black_team="弈衡队", white_team="对手队")
    basename = os.path.basename(path)

    assert basename.startswith("C5-"), f"文件名应以C5-开头: {basename}"
    assert " vs " in basename, f"文件名应包含' vs ': {basename}"
    assert basename.endswith(".txt"), f"文件名应以.txt结尾: {basename}"

    # 验证无非法字符
    illegal = '\\/:*?"<>|'
    for c in illegal:
        assert c not in basename, f"文件名包含非法字符'{c}': {basename}"

    print(f"[OK] 文件名格式正确: {basename}")
    os.unlink(path)


def test_c5_swapped_colors():
    """三手交换后队名映射测试"""
    runner = CompetitionRunner(BLACK)
    runner.record.set_match_info("弈衡队", "对手队", "2026-05-30", "比赛")
    runner.record.add_move(BLACK, "H8")

    # 我方执黑：黑队=弈衡队
    assert runner.my_color == BLACK
    black_t = "弈衡队" if runner.my_color == BLACK else "对手队"
    white_t = "对手队" if runner.my_color == BLACK else "弈衡队"

    assert black_t == "弈衡队"
    assert white_t == "对手队"

    # 交换后
    runner.swap_colors()
    assert runner.my_color == WHITE

    black_t2 = "弈衡队" if runner.my_color == BLACK else "对手队"
    white_t2 = "对手队" if runner.my_color == BLACK else "弈衡队"

    assert black_t2 == "对手队", "交换后黑队应为对手"
    assert white_t2 == "弈衡队", "交换后白队应为弈衡"

    print("[OK] 三手交换后队名映射正确")


if __name__ == "__main__":
    test_c5_format_basic()
    test_c5_no_moves()
    test_c5_move_format()
    test_c5_result_field()
    test_c5_save_gbk()
    test_c5_filename_format()
    test_c5_swapped_colors()
    print("\n===================================")
    print("C5棋谱格式测试全部通过!")
    print("===================================")
