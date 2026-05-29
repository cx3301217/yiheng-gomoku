"""弈衡五子棋智能博弈程序 - 比赛运行版入口"""

from gomoku.board import BLACK, WHITE
from gomoku.competition import CompetitionRunner


def choose_color():
    while True:
        color_input = input("请选择我方执棋颜色(B=黑棋, W=白棋)：").strip().upper()
        if color_input == "B":
            return BLACK
        if color_input == "W":
            return WHITE
        print("输入无效，请输入B或W")


def run_competition_mode():
    print("=" * 50)
    print("弈衡五子棋智能博弈程序")
    print("比赛静默辅助模式")
    print("=" * 50)
    print("常用命令：")
    print("  save   保存日志和棋谱")
    print("  board  显示当前棋盘")
    print("  record 显示当前棋谱")
    print("  quit   退出并保存")
    print("=" * 50)
    print()

    my_color = choose_color()
    runner = CompetitionRunner(my_color)

    # 显示初始空棋盘
    runner.display_board()

    # 如果执黑，自动落子并显示棋盘
    if my_color == BLACK:
        first_move = runner.start_if_black()
        if first_move:
            print(f"我方输出：{first_move}")
            runner.display_board()

    # 主循环
    while not runner.game_over:
        user_input = input("\n请输入对方落子：").strip()

        # 处理命令
        if user_input.lower() == "save":
            log_path = runner.save_log()
            record_path = runner.save_record()
            print(f"日志已保存：{log_path}")
            print(f"棋谱已保存：{record_path}")
            continue

        if user_input.lower() == "board":
            runner.display_board()
            continue

        if user_input.lower() == "record":
            runner.display_record()
            continue

        if user_input.lower() == "quit":
            log_path = runner.save_log()
            record_path = runner.save_record()
            print(f"已保存日志：{log_path}")
            print(f"已保存棋谱：{record_path}")
            print("已退出比赛模式")
            return

        # 处理对方落子
        success, result = runner.receive_opponent_move(user_input)
        if not success:
            print(f"错误：{result}")
            continue

        print(f"对方落子：{result}")
        runner.display_board()

        # 检查游戏是否结束
        if runner.game_over:
            break

        # 我方落子
        success, result = runner.make_my_move()
        if not success:
            print(f"错误：{result}")
            continue

        print(f"我方输出：{result}")
        runner.display_board()

    # 对局结束
    print()
    if runner.winner == "BLACK":
        print("对局结束：黑棋胜")
    elif runner.winner == "WHITE":
        print("对局结束：白棋胜")
    else:
        print("对局结束：和棋")

    log_path = runner.save_log()
    record_path = runner.save_record()
    print(f"日志已保存：{log_path}")
    print(f"棋谱已保存：{record_path}")


if __name__ == "__main__":
    run_competition_mode()
