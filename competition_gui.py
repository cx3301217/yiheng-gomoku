"""弈衡五子棋智能博弈程序 - 图形比赛界面 v2.3

支持2026省赛五子棋项目规则：
- 指定开局（三手五打）
- 三手交换
- 五手N打
- 双方各15分钟计时
- 禁手规则
"""
from __future__ import annotations
import tkinter as tk
from typing import Tuple, Optional, List
from tkinter import ttk, messagebox, scrolledtext
import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gomoku.board import Board, BLACK, WHITE, EMPTY
from gomoku.competition import CompetitionRunner
from gomoku.coordinate import coord_to_index, index_to_coord
from gomoku.forbidden import is_forbidden_move, get_forbidden_type
from gomoku.evaluator import evaluate_move, get_scored_moves
from gomoku.opening import (
    get_opening_names, get_official_opening, generate_first_three,
    validate_basic_specified_opening, validate_official_opening,
    OFFICIAL_OPENINGS, _TENGEN_ADJACENT, _parse_coords
)


# ============ 常量定义 ============
DEFAULT_OPENING_NAME = "寒星"
DEFAULT_FIFTH_N = 2
TOTAL_TIME_SECONDS = 15 * 60

ALL_OPENINGS = get_opening_names()
TENGEN_ADJACENT = list(_TENGEN_ADJACENT)

CENTER_5X5 = []
for r in range(5, 10):
    for c in range(5, 10):
        CENTER_5X5.append(index_to_coord(r, c))

PHASE_WAIT_OPENING = "等待生成指定开局"
PHASE_WAIT_SWAP = "等待对方三手交换选择"
PHASE_WAIT_OPPONENT_4 = "等待对方白4落子"
PHASE_FIFTH_N_SELECT = "五手N打：等待对方选择保留点"
PHASE_FIFTH_N_INPUT = "五手N打：等待输入候选点"
PHASE_FIFTH_N_CHOOSE = "五手N打：程序选择保留点"
PHASE_MY_TURN = "我方程序思考中"
PHASE_NORMAL = "正常对弈"


class CompetitionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("弈衡五子棋 - 比赛界面 v2.5")
        self.root.geometry("1500x820")
        self.root.minsize(1280, 720)
        self.root.resizable(True, True)

        # 尝试最大化窗口
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        self.runner: Optional[CompetitionRunner] = None
        self.game_started = False
        self.my_color = BLACK
        self.my_time_remaining = TOTAL_TIME_SECONDS
        self.opponent_time_remaining = TOTAL_TIME_SECONDS
        self.current_turn = BLACK
        self.timer_job = None
        self.is_timer_running = False

        self.opening_name = DEFAULT_OPENING_NAME
        self.fifth_n = DEFAULT_FIFTH_N
        self.current_phase = PHASE_WAIT_OPENING
        self.swap_done = False
        self.fifth_candidates: List[str] = []
        self.fifth_selected: Optional[str] = None
        self.opening_placed = False
        self.showing_forbidden = False

        # 我方初始颜色（用于区分交换来源）
        self.initial_my_color = BLACK

        # 棋盘参数（紧凑尺寸）
        self.board_size = 480
        self.margin = 28
        self.grid_size = self.board_size // 15
        self.canvas_width = self.board_size + self.margin * 2
        self.canvas_height = self.board_size + self.margin * 2
        self.stone_radius = self.grid_size // 2 - 2
        self.star_points = [(3, 3), (3, 11), (7, 7), (11, 3), (11, 11)]

        self.setup_ui()
        self.update_timer_display()
        self.update_phase()

    def setup_ui(self):
        """三栏布局：左-棋盘，中-流程，右-辅助，整体居中"""
        # 外层居中框架
        outer_frame = ttk.Frame(self.root)
        outer_frame.pack(fill=tk.BOTH, expand=True)

        main_frame = ttk.Frame(outer_frame, padding="3", width=1330)
        main_frame.pack(anchor="center")
        main_frame.pack_propagate(False)

        # ========== 左栏：棋盘区 ==========
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, padx=5)

        self.canvas = tk.Canvas(left_frame, width=self.canvas_width,
                                height=self.canvas_height, bg="#DEB887")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # ========== 中栏：比赛流程区 ==========
        middle_frame = ttk.Frame(main_frame, width=380)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)
        middle_frame.pack_propagate(False)

        # 标题
        ttk.Label(middle_frame, text="弈衡五子棋 v2.5",
                  font=("微软雅黑", 12, "bold")).pack(pady=2)

        # 当前阶段
        phase_frame = ttk.LabelFrame(middle_frame, text="当前阶段", padding="2")
        phase_frame.pack(fill=tk.X, pady=1)
        self.phase_label = ttk.Label(phase_frame, text=PHASE_WAIT_OPENING,
                                     font=("Consolas", 9, "bold"), foreground="blue")
        self.phase_label.pack(anchor=tk.W)

        # 计时器
        timer_frame = ttk.LabelFrame(middle_frame, text="计时器", padding="2")
        timer_frame.pack(fill=tk.X, pady=1)
        self.my_timer_label = ttk.Label(timer_frame, text="我方剩余: 15:00",
                                        font=("Consolas", 9, "bold"), foreground="blue")
        self.my_timer_label.pack(anchor=tk.W)
        self.opp_timer_label = ttk.Label(timer_frame, text="对方剩余: 15:00",
                                          font=("Consolas", 9, "bold"), foreground="red")
        self.opp_timer_label.pack(anchor=tk.W)
        self.turn_label = ttk.Label(timer_frame, text="当前行棋: 黑棋", font=("Consolas", 8))
        self.turn_label.pack(anchor=tk.W)
        self.my_color_label = ttk.Label(timer_frame, text="我方执棋: 黑棋", font=("Consolas", 8))
        self.my_color_label.pack(anchor=tk.W)
        timer_btn_frame = ttk.Frame(timer_frame)
        timer_btn_frame.pack(fill=tk.X, pady=1)
        self.pause_btn = ttk.Button(timer_btn_frame, text="暂停", command=self.toggle_timer, width=6)
        self.pause_btn.pack(side=tk.LEFT, padx=1)
        self.reset_btn = ttk.Button(timer_btn_frame, text="重置", command=self.reset_timers, width=6)
        self.reset_btn.pack(side=tk.LEFT, padx=1)

        # 指定开局（我方执黑）
        opening_frame = ttk.LabelFrame(middle_frame, text="指定开局（我方执黑）", padding="2")
        opening_frame.pack(fill=tk.X, pady=1)
        name_frame = ttk.Frame(opening_frame)
        name_frame.pack(fill=tk.X, pady=1)
        ttk.Label(name_frame, text="开局:").pack(side=tk.LEFT)
        self.opening_combo = ttk.Combobox(name_frame, values=ALL_OPENINGS,
                                           state="readonly", width=8)
        self.opening_combo.set(DEFAULT_OPENING_NAME)
        self.opening_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(name_frame, text="N:").pack(side=tk.LEFT)
        self.n_combo = ttk.Combobox(name_frame, values=[2, 3, 4, 5], state="readonly", width=3)
        self.n_combo.set(DEFAULT_FIFTH_N)
        self.n_combo.pack(side=tk.LEFT, padx=2)
        self.gen_btn = ttk.Button(opening_frame, text="程序生成指定开局",
                                   command=self.generate_opening)
        self.gen_btn.pack(fill=tk.X, pady=1)
        self.opening_info = scrolledtext.ScrolledText(opening_frame, height=4,
                                                      font=("Consolas", 7), state=tk.DISABLED)
        self.opening_info.pack(fill=tk.X, pady=1)

        # 对方执黑开局录入（我方执白）
        opp_opening_frame = ttk.LabelFrame(middle_frame, text="对方执黑开局录入（我方执白）", padding="2")
        opp_opening_frame.pack(fill=tk.X, pady=1)
        self.opp_opening_entry = ttk.Entry(opp_opening_frame, font=("Consolas", 8))
        self.opp_opening_entry.pack(fill=tk.X, pady=1)
        self.opp_opening_entry.insert(0, "B(H,8);W(H,9);B(H,10)")
        opp_hint_frame = ttk.Frame(opp_opening_frame)
        opp_hint_frame.pack(fill=tk.X, pady=1)
        ttk.Label(opp_hint_frame, text="开局:").pack(side=tk.LEFT)
        self.opp_opening_name_combo = ttk.Combobox(opp_hint_frame, values=ALL_OPENINGS,
                                                    state="readonly", width=8)
        self.opp_opening_name_combo.set(DEFAULT_OPENING_NAME)
        self.opp_opening_name_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(opp_hint_frame, text="N:").pack(side=tk.LEFT)
        self.opp_n_combo = ttk.Combobox(opp_hint_frame, values=[2, 3, 4, 5],
                                          state="readonly", width=3)
        self.opp_n_combo.set(DEFAULT_FIFTH_N)
        self.opp_n_combo.pack(side=tk.LEFT, padx=2)
        self.validate_opp_opening_btn = ttk.Button(opp_opening_frame, text="校验并录入对方开局",
                                                     command=self.validate_opponent_opening)
        self.validate_opp_opening_btn.pack(fill=tk.X, pady=1)

        # 三手交换
        swap_frame = ttk.LabelFrame(middle_frame, text="三手交换", padding="2")
        swap_frame.pack(fill=tk.X, pady=1)
        self.swap_label = ttk.Label(swap_frame, text="等待生成开局...",
                                     font=("Consolas", 8))
        self.swap_label.pack(anchor=tk.W)
        swap_btn_frame = ttk.Frame(swap_frame)
        swap_btn_frame.pack(fill=tk.X, pady=1)
        self.swap_yes_btn = ttk.Button(swap_btn_frame, text="对方交换",
                                        command=lambda: self.handle_swap(True), width=10)
        self.swap_yes_btn.pack(side=tk.LEFT, padx=1)
        self.swap_no_btn = ttk.Button(swap_btn_frame, text="对方不交换",
                                       command=lambda: self.handle_swap(False), width=10)
        self.swap_no_btn.pack(side=tk.LEFT, padx=1)
        self.swap_yes_btn.config(state=tk.DISABLED)
        self.swap_no_btn.config(state=tk.DISABLED)

        # 对方落子/五手候选输入
        input_frame = ttk.LabelFrame(middle_frame, text="对方落子/五手候选输入", padding="2")
        input_frame.pack(fill=tk.X, pady=1)
        self.opp_input_entry = ttk.Entry(input_frame, font=("Consolas", 9))
        self.opp_input_entry.pack(fill=tk.X)
        self.opp_input_entry.insert(0, "如 W(J,8) 或 B(J,8);B(I,9)")
        ttk.Button(input_frame, text="确认输入",
                   command=self.confirm_opponent_move).pack(fill=tk.X, pady=(2, 0))

        # 五手N打
        fifth_frame = ttk.LabelFrame(middle_frame, text="五手N打", padding="2")
        fifth_frame.pack(fill=tk.X, pady=1)
        self.fifth_n_label = ttk.Label(fifth_frame, text="N值: 待开局后显示", font=("Consolas", 8))
        self.fifth_n_label.pack(anchor=tk.W)
        self.fifth_candidates_label = ttk.Label(fifth_frame, text="候选点: 等待生成...",
                                                 font=("Consolas", 7), wraplength=360)
        self.fifth_candidates_label.pack(anchor=tk.W)
        fifth_input_frame = ttk.Frame(fifth_frame)
        fifth_input_frame.pack(fill=tk.X, pady=1)
        ttk.Label(fifth_input_frame, text="保留点:").pack(side=tk.LEFT)
        self.fifth_entry = ttk.Entry(fifth_input_frame, width=16)
        self.fifth_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(fifth_input_frame, text="确认", command=self.confirm_fifth).pack(side=tk.LEFT)

        # ========== 右栏：辅助信息区 ==========
        right_frame = ttk.Frame(main_frame, width=320)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)
        right_frame.pack_propagate(False)

        # 禁手检测
        forbidden_frame = ttk.LabelFrame(right_frame, text="禁手检测", padding="2")
        forbidden_frame.pack(fill=tk.X, pady=1)
        ttk.Label(forbidden_frame, text="黑：三三、四四、长连",
                  font=("Consolas", 7)).pack(anchor=tk.W)
        self.forbidden_status_label = ttk.Label(forbidden_frame, text="无禁手",
                                                font=("Consolas", 8, "bold"), foreground="green")
        self.forbidden_status_label.pack(anchor=tk.W, pady=1)
        self.forbidden_toggle_btn = ttk.Button(forbidden_frame, text="显示黑棋禁手点",
                                               command=self.toggle_forbidden_points)
        self.forbidden_toggle_btn.pack(fill=tk.X, pady=1)

        # 执棋颜色
        color_frame = ttk.LabelFrame(right_frame, text="执棋颜色", padding="2")
        color_frame.pack(fill=tk.X, pady=1)
        self.color_var = tk.StringVar(value="B")
        ttk.Radiobutton(color_frame, text="我方执黑 (B)",
                        variable=self.color_var, value="B",
                        command=self.on_color_change).pack(anchor=tk.W)
        ttk.Radiobutton(color_frame, text="我方执白 (W)",
                        variable=self.color_var, value="W",
                        command=self.on_color_change).pack(anchor=tk.W)

        # 操作按钮区
        btn_frame = ttk.LabelFrame(right_frame, text="操作", padding="2")
        btn_frame.pack(fill=tk.X, pady=1)
        self.start_btn = ttk.Button(btn_frame, text="开始对局", command=self.start_game)
        self.start_btn.pack(fill=tk.X, pady=1)
        self.save_btn = ttk.Button(btn_frame, text="保存日志和棋谱",
                                   command=self.save_game, state=tk.DISABLED)
        self.save_btn.pack(fill=tk.X, pady=1)
        self.record_btn = ttk.Button(btn_frame, text="显示棋谱",
                                      command=self.show_record, state=tk.DISABLED)
        self.record_btn.pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame, text="退出", command=self.quit_game).pack(fill=tk.X, pady=1)

        # 输出信息（固定高度，不撑满）
        output_frame = ttk.LabelFrame(right_frame, text="输出信息", padding="2")
        output_frame.pack(fill=tk.BOTH, pady=1)
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10,
                                                     font=("Consolas", 8), state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH)

        self.draw_board()

    def on_color_change(self):
        color = self.color_var.get()
        self.my_color = BLACK if color == "B" else WHITE
        self.my_color_label.config(text=f"我方执棋: {'黑棋' if self.my_color == BLACK else '白棋'}")

    def row_col_to_xy(self, row, col):
        x = self.margin + col * self.grid_size
        y = self.margin + (14 - row) * self.grid_size
        return x, y

    def xy_to_row_col(self, x, y):
        col = round((x - self.margin) / self.grid_size)
        row = round(14 - (y - self.margin) / self.grid_size)
        return row, col

    def draw_board(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height,
                                      fill="#DEB887", outline="#DEB887")
        for i in range(15):
            x = self.margin + i * self.grid_size
            self.canvas.create_line(x, self.margin, x,
                                    self.margin + 14 * self.grid_size, fill="black")
            y = self.margin + i * self.grid_size
            self.canvas.create_line(self.margin, y,
                                    self.margin + 14 * self.grid_size, y, fill="black")
        letters = "ABCDEFGHIJKLMNO"
        for i, letter in enumerate(letters):
            x = self.margin + i * self.grid_size
            self.canvas.create_text(x, self.margin - 18, text=letter, font=("Arial", 9))
            self.canvas.create_text(x, self.margin + 14 * self.grid_size + 18,
                                    text=letter, font=("Arial", 9))
        for i in range(15):
            y = self.margin + i * self.grid_size
            num = 15 - i
            self.canvas.create_text(self.margin - 18, y, text=str(num), font=("Arial", 9))
            self.canvas.create_text(self.margin + 14 * self.grid_size + 18, y,
                                    text=str(num), font=("Arial", 9))
        for row, col in self.star_points:
            x, y = self.row_col_to_xy(row, col)
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="black")
        if self.runner:
            for r in range(15):
                for c in range(15):
                    stone = self.runner.board.grid[r][c]
                    if stone != 0:
                        x, y = self.row_col_to_xy(r, c)
                        if stone == BLACK:
                            self.canvas.create_oval(
                                x - self.stone_radius, y - self.stone_radius,
                                x + self.stone_radius, y + self.stone_radius, fill="black")
                        else:
                            self.canvas.create_oval(
                                x - self.stone_radius, y - self.stone_radius,
                                x + self.stone_radius, y + self.stone_radius,
                                fill="white", outline="black", width=2)
        if self.showing_forbidden and self.runner:
            forbidden = self.get_forbidden_points()
            for coord, _ in forbidden:
                row, col = coord_to_index(coord)
                x, y = self.row_col_to_xy(row, col)
                size = 8
                self.canvas.create_line(x - size, y - size, x + size, y + size,
                                        fill="red", width=2, tags="forbidden")
                self.canvas.create_line(x - size, y + size, x + size, y - size,
                                        fill="red", width=2, tags="forbidden")

    def generate_opening(self):
        """生成指定开局前三手（我方执黑）"""
        self.opening_name = self.opening_combo.get()
        self.fifth_n = int(self.n_combo.get())
        self.initial_my_color = BLACK

        opening_info = get_official_opening(self.opening_name)
        if not opening_info:
            self.output_append(f"错误: 未知开局 {self.opening_name}")
            return

        b1, w2, b3 = opening_info["black1"], opening_info["white2"], opening_info["black3"]
        opening_type = opening_info["type"]

        self.opening_info.config(state=tk.NORMAL)
        self.opening_info.delete(1.0, tk.END)
        self.opening_info.insert(tk.END, f"开局名称: {self.opening_name}\n")
        self.opening_info.insert(tk.END, f"类型: {opening_type}\n")
        self.opening_info.insert(tk.END, f"N值: {self.fifth_n}\n")
        self.opening_info.insert(tk.END, f"前三手:\n")
        self.opening_info.insert(tk.END, f"1. B({b1})\n")
        self.opening_info.insert(tk.END, f"2. W({w2})\n")
        self.opening_info.insert(tk.END, f"3. B({b3})\n")
        self.opening_info.insert(tk.END, f"\n下一步: 等待对方选择是否三手交换")
        self.opening_info.config(state=tk.DISABLED)

        self.my_color = BLACK
        self.runner = CompetitionRunner(self.my_color)
        self.game_started = True
        self.swap_done = False
        self.fifth_candidates = []
        self.fifth_selected = None
        self.opening_placed = True

        self.my_time_remaining = TOTAL_TIME_SECONDS
        self.opponent_time_remaining = TOTAL_TIME_SECONDS
        self.current_turn = BLACK

        self.output_clear()
        self.output_append("=" * 40)
        self.output_append("指定开局已生成!")
        self.output_append(f"我方执黑")
        self.output_append(f"开局: {self.opening_name} ({opening_type})")
        self.output_append(f"前三手: B({b1});W({w2});B({b3})")
        self.output_append("=" * 40)

        self._place_first_three(b1, w2, b3)

        self.my_color_label.config(text="我方执棋: 黑棋")
        self.fifth_n_label.config(text=f"N值: {self.fifth_n}")
        self.current_phase = PHASE_WAIT_SWAP
        self.update_phase()
        self.update_turn()

        self.swap_label.config(text="等待对方选择是否交换...")
        self.swap_yes_btn.config(state=tk.NORMAL)
        self.swap_no_btn.config(state=tk.NORMAL)

        self.save_btn.config(state=tk.NORMAL)
        self.record_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.DISABLED)
        self.gen_btn.config(state=tk.DISABLED)
        self.validate_opp_opening_btn.config(state=tk.DISABLED)

        self.draw_board()
        self.start_timer()
        self.output_append("等待对方选择是否三手交换")

    def validate_opponent_opening(self):
        """校验并录入对方指定的局面（我方执白）- 程序自动判断三手交换"""
        text = self.opp_opening_entry.get().strip()
        opp_opening_name = self.opp_opening_name_combo.get()
        opp_n = int(self.opp_n_combo.get())

        coords = _parse_coords(text)
        if len(coords) != 3:
            self.output_append(f"错误: 坐标数量不正确，应为3个")
            return

        b1, w2, b3 = coords

        valid, msg = validate_basic_specified_opening(text)
        if not valid:
            self.output_append(f"基本校验失败: {msg}")
            return

        official_valid, official_msg = validate_official_opening(opp_opening_name, text)

        self.output_append(f"基本校验: {msg}")
        if official_valid:
            self.output_append(f"与官方图示方向一致")
        else:
            self.output_append(f"注意: {official_msg}")

        self.opening_name = opp_opening_name
        self.fifth_n = opp_n
        self.my_color = WHITE
        self.initial_my_color = WHITE
        self.runner = CompetitionRunner(self.my_color)
        self.game_started = True
        self.swap_done = False
        self.fifth_candidates = []
        self.fifth_selected = None
        self.opening_placed = True

        self.my_time_remaining = TOTAL_TIME_SECONDS
        self.opponent_time_remaining = TOTAL_TIME_SECONDS
        self.current_turn = BLACK

        self.output_clear()
        self.output_append("=" * 40)
        self.output_append("对方开局已录入!")
        self.output_append(f"我方执白")
        self.output_append(f"开局: {opp_opening_name}")
        self.output_append(f"前三手: B({b1});W({w2});B({b3})")
        self.output_append("=" * 40)

        self._place_first_three(b1, w2, b3)

        self.my_color_label.config(text="我方执棋: 白棋")
        self.fifth_n_label.config(text=f"N值: {self.fifth_n}")

        self.save_btn.config(state=tk.NORMAL)
        self.record_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.DISABLED)
        self.gen_btn.config(state=tk.DISABLED)
        self.validate_opp_opening_btn.config(state=tk.DISABLED)
        self.swap_yes_btn.config(state=tk.DISABLED)
        self.swap_no_btn.config(state=tk.DISABLED)

        self.draw_board()
        self.start_timer()

        # 程序自动判断是否三手交换
        self._auto_decide_swap()

    def _auto_decide_swap(self):
        """程序自动判断是否三手交换"""
        # 简单策略：评估当前局面
        # 如果执白方（我方）有明显劣势，选择交换
        # 这里用简化策略：随机或固定保守策略
        # 后续可以改进为基于评估函数的判断

        should_swap = self._evaluate_swap_benefit()

        if should_swap:
            self.output_append("程序决定：选择交换（三手交换）")
            self.swap_label.config(text="程序选择交换!", foreground="red")
            self.runner.swap_colors()
            self.my_color = self.runner.my_color
            self.my_color_label.config(text=f"我方执棋: {'黑棋' if self.my_color == BLACK else '白棋'}")
            self.output_append(f"三手交换完成，我方现执: {'黑棋' if self.my_color == BLACK else '白棋'}")
            # 交换后，我方现执黑，下一步是对方白4
            self.current_phase = PHASE_WAIT_OPPONENT_4
            self.update_phase()
            self.update_turn()
            self.output_append("请输入对方白4落子...")
            self.current_turn = WHITE
            self.update_turn()
        else:
            self.output_append("程序决定：不交换")
            self.swap_label.config(text="程序选择不交换", foreground="green")
            self.output_append("我方仍执白，自动输出白4...")
            # 不交换，我方仍执白，输出白4
            self.current_phase = PHASE_MY_TURN
            self.update_phase()
            self.update_turn()
            self.current_turn = WHITE
            self.update_turn()

            success, move = self.runner.make_my_move()
            if success:
                self.output_append(f"我方输出: {move}")
                self._log(f"我方落子: {move}")
            else:
                self.output_append(f"我方落子失败: {move}")

            self.draw_board()
            self.update_forbidden_status()

            if self.runner.game_over:
                self.end_game()
            else:
                # 下一步是黑5五手N打，对方执黑，需要等待对方输入N个候选点
                self.current_phase = PHASE_FIFTH_N_INPUT
                self.update_phase()
                self.output_append("黑5为五手N打，请输入对方选定的N个黑5候选点...")
                self.opp_input_entry.delete(0, tk.END)
                self.opp_input_entry.insert(0, f"B(J,8);B(I,9)")
                self.current_turn = BLACK
                self.update_turn()

    def _evaluate_swap_benefit(self) -> bool:
        """评估是否应该交换"""
        # 简化策略：固定不交换（保守策略）
        # 后续可改进为基于评估函数的判断
        return False

    def _place_first_three(self, b1: str, w2: str, b3: str):
        """落前三手到棋盘"""
        for color, coord in [(BLACK, b1), (WHITE, w2), (BLACK, b3)]:
            row, col = coord_to_index(coord)
            self.runner.board.place_stone(row, col, color)
            color_char = "B" if color == BLACK else "W"
            self.runner.record.add_move(color, coord.upper())
            self.runner.move_count += 1
        self.output_append(f"已落前三手: B({b1});W({w2});B({b3})")

    def start_game(self):
        """开始对局（不使用指定开局时）"""
        if not self.runner:
            self.my_color = BLACK if self.color_var.get() == "B" else WHITE
            self.initial_my_color = self.my_color
            self.runner = CompetitionRunner(self.my_color)
            self.game_started = True
            self.swap_done = False
            self.fifth_candidates = []
            self.my_time_remaining = TOTAL_TIME_SECONDS
            self.opponent_time_remaining = TOTAL_TIME_SECONDS
            self.current_turn = BLACK
            self.output_clear()
            self.output_append("=" * 40)
            self.output_append("比赛开始!")
            self.output_append(f"我方: {'黑棋' if self.my_color == BLACK else '白棋'}")
            self.output_append("=" * 40)
            self.my_color_label.config(text=f"我方执棋: {'黑棋' if self.my_color == BLACK else '白棋'}")
            if self.my_color == BLACK:
                self.current_phase = PHASE_MY_TURN
                self.update_phase()
                self.update_turn()
                move = self.runner.start_if_black()
                if move:
                    self.output_append(f"我方输出: {move}")
                    self.current_turn = WHITE
                    self.update_turn()
            else:
                self.current_phase = PHASE_WAIT_OPPONENT_4
                self.update_phase()
                self.update_turn()
                self.output_append("等待对方黑棋落子...")
            self.draw_board()
            self.start_timer()
        self.save_btn.config(state=tk.NORMAL)
        self.record_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.DISABLED)

    def handle_swap(self, swap: bool):
        """处理三手交换（仅用于我方执黑开局时）"""
        if self.swap_done:
            self.output_append("三手交换已完成")
            return
        self.swap_done = True

        if swap:
            self.swap_label.config(text="对方选择交换!", foreground="red")
            self.output_append("对方选择执行三手交换")
            self.runner.swap_colors()
            self.my_color = self.runner.my_color
            self.my_color_label.config(text=f"我方执棋: {'黑棋' if self.my_color == BLACK else '白棋'}")
            self.output_append(f"三手交换完成，我方现执: {'黑棋' if self.my_color == BLACK else '白棋'}")

            # 交换后，我方变白，需要输出白4
            self.current_phase = PHASE_MY_TURN
            self.update_phase()
            self.current_turn = WHITE
            self.update_turn()

            # make_my_move()已经完成落子、记录、move_count++
            success, move = self.runner.make_my_move()
            if success:
                self.output_append(f"我方输出: {move}")
                self._log(f"我方落子: {move}")
            else:
                self.output_append(f"我方落子失败: {move}")

            self.draw_board()
            self.update_forbidden_status()

            if self.runner.game_over:
                self.end_game()
            else:
                # 下一步是黑5，对方执黑，等待对方输入N个候选点
                self.current_phase = PHASE_FIFTH_N_INPUT
                self.update_phase()
                self.output_append("黑5为五手N打，请输入对方选定的N个黑5候选点...")
                self.opp_input_entry.delete(0, tk.END)
                self.opp_input_entry.insert(0, f"B(J,8);B(I,9)")
                self.current_turn = BLACK
                self.update_turn()
        else:
            self.swap_label.config(text="对方选择不交换", foreground="green")
            self.output_append("对方选择不交换")
            self.output_append(f"我方仍执: {'黑棋' if self.my_color == BLACK else '白棋'}")
            self.current_phase = PHASE_WAIT_OPPONENT_4
            self.update_phase()
            self.output_append("请输入对方白4落子...")
            self.current_turn = WHITE
            self.update_turn()

        self.draw_board()

    def confirm_opponent_move(self):
        """确认对方落子或五手N打候选点"""
        if not self.runner or not self.game_started:
            self.output_append("请先点击「程序生成指定开局」或「开始对局」")
            return
        if self.runner.game_over:
            self.output_append("对局已结束")
            return

        text = self.opp_input_entry.get().strip()
        if not text:
            self.output_append("请输入内容")
            return

        # 根据当前阶段处理
        if self.current_phase == PHASE_FIFTH_N_INPUT:
            # 对方输入N个黑5候选点
            self._handle_fifth_n_input(text)
        else:
            # 普通对方落子
            self._handle_normal_opponent_move(text)

    def _handle_fifth_n_input(self, text: str):
        """处理五手N打候选点输入"""
        # 解析候选点
        coords = _parse_coords(text)
        if len(coords) < self.fifth_n:
            self.output_append(f"错误: 候选点数量不足，需要{self.fifth_n}个")
            return

        candidates = coords[:self.fifth_n]

        # 校验候选点
        valid_candidates = []
        for coord in candidates:
            if coord in valid_candidates:
                continue
            row, col = coord_to_index(coord)
            if self.runner.board.grid[row][col] != EMPTY:
                self.output_append(f"警告: {coord}已有棋子，跳过")
                continue
            # 检查是否为禁手点
            self.runner.board.grid[row][col] = BLACK
            if is_forbidden_move(self.runner.board, row, col, BLACK):
                self.output_append(f"警告: {coord}是禁手点，跳过")
                self.runner.board.grid[row][col] = EMPTY
                continue
            self.runner.board.grid[row][col] = EMPTY
            valid_candidates.append(coord)

        if len(valid_candidates) < self.fifth_n:
            self.output_append(f"错误: 有效候选点不足{self.fifth_n}个")
            return

        self.fifth_candidates = valid_candidates
        candidates_str = ";".join([f"B({c})" for c in self.fifth_candidates])
        self.fifth_candidates_label.config(text=f"候选点: {candidates_str}")
        self.output_append(f"已录入候选点: {candidates_str}")

        # 程序自动选择对白棋最有利的保留点
        self.current_phase = PHASE_FIFTH_N_CHOOSE
        self.update_phase()
        self._auto_select_fifth()

    def _auto_select_fifth(self):
        """程序自动选择五手N打保留点"""
        # 策略：选择对白棋（防守方）威胁最小的点
        best_coord = None
        best_score = float('inf')

        for coord in self.fifth_candidates:
            row, col = coord_to_index(coord)
            # 临时落子
            self.runner.board.grid[row][col] = BLACK
            # 评估该点对白棋的威胁程度（越低越好）
            score = evaluate_move(self.runner.board, row, col, BLACK)
            self.runner.board.grid[row][col] = EMPTY
            if score < best_score:
                best_score = score
                best_coord = coord

        # 落保留点
        coord = best_coord or self.fifth_candidates[0]
        row, col = coord_to_index(coord)
        self.runner.board.place_stone(row, col, BLACK)
        self.runner.record.add_move(BLACK, coord.upper())
        self.runner.move_count += 1

        self.fifth_selected = coord
        self.output_append(f"程序选择保留: B({coord})")
        self.fifth_candidates_label.config(text=f"保留点: B({coord})")
        self.fifth_candidates = []

        self.draw_board()
        self.update_forbidden_status()

        if self.runner.game_over:
            self.end_game()
        elif self.runner.my_color == WHITE:
            # 我方执白，黑5落后轮到我方下白6
            self.current_phase = PHASE_MY_TURN
            self.update_phase()
            self.current_turn = WHITE
            self.update_turn()

            success, move = self.runner.make_my_move()
            if success:
                self.output_append(f"我方输出: {move}")
                self._log(f"我方落子: {move}")
            else:
                self.output_append(f"我方落子失败: {move}")

            self.draw_board()
            self.update_forbidden_status()

            if self.runner.game_over:
                self.end_game()
            else:
                self.current_phase = PHASE_WAIT_OPPONENT_4
                self.update_phase()
                self.output_append("请输入对方黑7落子...")
                self.opp_input_entry.delete(0, tk.END)
                self.current_turn = BLACK
                self.update_turn()
        else:
            # 我方执黑（对方执白），等待对方白6
            self.current_phase = PHASE_WAIT_OPPONENT_4
            self.update_phase()
            self.output_append("五手N打完成，请输入对方下一步落子...")
            self.opp_input_entry.delete(0, tk.END)
            self.current_turn = WHITE
            self.update_turn()

    def _handle_normal_opponent_move(self, text: str):
        """处理普通对方落子"""
        success, result = self.runner.receive_opponent_move(text)
        if not success:
            self.output_append(f"错误: {result}")
            return

        self.output_append(f"对方落子: {result}")
        self.draw_board()
        self.update_forbidden_status()

        if self.runner.game_over:
            self.end_game()
            return

        # 检查是否是黑5五手N打阶段
        if self.runner.my_color == BLACK and self.runner.move_count == 4:
            # 我方执黑，白4后轮到黑5五手N打
            self.current_phase = PHASE_FIFTH_N_SELECT
            self.update_phase()
            self.current_turn = BLACK
            self.update_turn()
            self.generate_my_black_fifth_candidates()
            self.output_append("请将候选点告知对方，并录入对方选择保留的点...")
            return

        # 我方落子
        self.current_phase = PHASE_MY_TURN
        self.update_phase()
        self.update_turn()

        success, my_result = self.runner.make_my_move()
        if success:
            self.output_append(f"我方输出: {my_result}")
            self._log(f"我方落子: {my_result}")
        else:
            self.output_append(f"我方落子失败: {my_result}")

        self.draw_board()
        self.update_forbidden_status()
        self.opp_input_entry.delete(0, tk.END)

        if self.runner.game_over:
            self.end_game()
        else:
            self.current_phase = PHASE_WAIT_OPPONENT_4
            self.update_phase()
            self.output_append("请输入对方下一步落子...")
            self.current_turn = self.runner.opponent_color
            self.update_turn()

    def confirm_fifth(self):
        """确认五手N打保留点（仅用于我方执黑时对方选择保留点）"""
        if self.current_phase != PHASE_FIFTH_N_SELECT:
            self.output_append("错误: 当前不是五手N打保留点选择阶段")
            return

        if not self.fifth_candidates:
            self.output_append("错误: 当前没有程序生成的五手N打候选点")
            return

        text = self.fifth_entry.get().strip().upper()
        if not text:
            self.output_append("请输入保留点坐标")
            return

        coord = text
        if "(" in text:
            coord = text.split("(")[1].split(")")[0]

        if coord not in self.fifth_candidates:
            self.output_append(f"保留点{coord}不在候选点{self.fifth_candidates}中")
            return

        # 落子
        row, col = coord_to_index(coord)
        self.runner.board.place_stone(row, col, BLACK)
        self.runner.record.add_move(BLACK, coord.upper())
        self.runner.move_count += 1

        self.fifth_selected = coord
        self.output_append(f"黑5已按对方选择保留: B({coord})")
        self.fifth_candidates_label.config(text=f"保留点: B({coord})")
        self.fifth_entry.delete(0, tk.END)
        self.fifth_candidates = []

        self.draw_board()
        self.update_forbidden_status()

        # 进入等待对方白6
        self.current_phase = PHASE_WAIT_OPPONENT_4
        self.update_phase()
        self.output_append("请输入对方白6落子...")
        self.current_turn = WHITE
        self.update_turn()

    def generate_my_black_fifth_candidates(self):
        """生成我方执黑时的五手N打候选点"""
        candidates_data = get_scored_moves(self.runner.board, BLACK, limit=self.fifth_n * 3)
        self.fifth_candidates = []

        for coord, score in candidates_data:
            if len(self.fifth_candidates) >= self.fifth_n:
                break
            row, col = coord_to_index(coord)
            if self.runner.board.grid[row][col] != EMPTY:
                continue
            # 检查是否为禁手点
            self.runner.board.grid[row][col] = BLACK
            if is_forbidden_move(self.runner.board, row, col, BLACK):
                self.runner.board.grid[row][col] = EMPTY
                continue
            self.runner.board.grid[row][col] = EMPTY
            if coord not in self.fifth_candidates:
                self.fifth_candidates.append(coord)

        candidates_str = ";".join([f"B({c})" for c in self.fifth_candidates])
        self.fifth_candidates_label.config(text=f"候选点: {candidates_str}")
        self.output_append(f"黑5候选点: {candidates_str}")

    def toggle_forbidden_points(self):
        """切换显示黑棋禁手点"""
        if not self.runner:
            self.output_append("请先生成开局或开始对局")
            return
        self.showing_forbidden = not self.showing_forbidden
        if self.showing_forbidden:
            self.forbidden_toggle_btn.config(text="隐藏黑棋禁手点")
            self.output_append("显示黑棋禁手点")
        else:
            self.forbidden_toggle_btn.config(text="显示黑棋禁手点")
            self.output_append("隐藏黑棋禁手点")
        self.draw_board()

    def get_forbidden_points(self) -> list:
        """获取所有黑棋禁手点"""
        forbidden = []
        board = self.runner.board
        for r in range(15):
            for c in range(15):
                if board.grid[r][c] != EMPTY:
                    continue
                board.grid[r][c] = BLACK
                is_forbidden, _ = get_forbidden_type(board, r, c, BLACK)
                board.grid[r][c] = EMPTY
                if is_forbidden:
                    coord = index_to_coord(r, c)
                    forbidden.append((coord, _))
        return forbidden

    def update_forbidden_status(self):
        """更新禁手状态显示"""
        if not self.runner:
            self.forbidden_status_label.config(text="当前禁手状态：无禁手", foreground="green")
            return
        last_move = self.runner.record.get_last_move()
        if last_move and last_move[0] == BLACK:
            row, col = coord_to_index(last_move[1])
            is_forbidden, f_type = get_forbidden_type(self.runner.board, row, col, BLACK)
            if is_forbidden:
                if f_type == "DOUBLE_THREE":
                    self.forbidden_status_label.config(text="当前禁手：黑棋三三禁手", foreground="red")
                    self.output_append("警告：黑棋三三禁手!")
                elif f_type == "DOUBLE_FOUR":
                    self.forbidden_status_label.config(text="当前禁手：黑棋四四禁手", foreground="red")
                    self.output_append("警告：黑棋四四禁手!")
                elif f_type == "OVERLINE":
                    self.forbidden_status_label.config(text="当前禁手：黑棋长连禁手", foreground="red")
                    self.output_append("警告：黑棋长连禁手!")
                else:
                    self.forbidden_status_label.config(text="当前禁手状态：无禁手", foreground="green")
            else:
                self.forbidden_status_label.config(text="当前禁手状态：无禁手", foreground="green")
        else:
            self.forbidden_status_label.config(text="当前禁手状态：无禁手", foreground="green")

    def start_timer(self):
        if self.is_timer_running:
            return
        self.is_timer_running = True
        self._timer_tick()

    def stop_timer(self):
        self.is_timer_running = False
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def _timer_tick(self):
        if not self.is_timer_running:
            return
        if self.current_turn == self.runner.my_color:
            self.my_time_remaining -= 1
        else:
            self.opponent_time_remaining -= 1
        if self.my_time_remaining <= 0:
            self.my_time_remaining = 0
            self.output_append("我方超时!")
            self.stop_timer()
            self.end_game()
            return
        if self.opponent_time_remaining <= 0:
            self.opponent_time_remaining = 0
            self.output_append("对方超时!")
            self.stop_timer()
            self.end_game()
            return
        self.update_timer_display()
        self.timer_job = self.root.after(1000, self._timer_tick)

    def update_timer_display(self):
        my_min = self.my_time_remaining // 60
        my_sec = self.my_time_remaining % 60
        self.my_timer_label.config(text=f"我方剩余: {my_min:02d}:{my_sec:02d}")
        opp_min = self.opponent_time_remaining // 60
        opp_sec = self.opponent_time_remaining % 60
        self.opp_timer_label.config(text=f"对方剩余: {opp_min:02d}:{opp_sec:02d}")

    def update_phase(self):
        self.phase_label.config(text=self.current_phase)

    def update_turn(self):
        turn_color = "黑棋" if self.current_turn == BLACK else "白棋"
        self.turn_label.config(text=f"当前行棋: {turn_color}")

    def toggle_timer(self):
        if self.is_timer_running:
            self.stop_timer()
            self.pause_btn.config(text="继续")
        else:
            self.start_timer()
            self.pause_btn.config(text="暂停")

    def reset_timers(self):
        self.stop_timer()
        self.my_time_remaining = TOTAL_TIME_SECONDS
        self.opponent_time_remaining = TOTAL_TIME_SECONDS
        self.update_timer_display()
        self.pause_btn.config(text="暂停")
        self.output_append("计时器已重置")

    def end_game(self):
        self.stop_timer()
        if self.runner.winner == "BLACK":
            self.output_append("对局结束：黑棋胜")
        elif self.runner.winner == "WHITE":
            self.output_append("对局结束：白棋胜")
        else:
            self.output_append("对局结束：和棋")
        self.save_game()

    def save_game(self):
        if not self.runner:
            self.output_append("没有可保存的对局")
            return
        log_path = self.runner.save_log()
        record_path = self.runner.save_record()
        self.output_append(f"日志已保存: {os.path.basename(log_path)}")
        self.output_append(f"棋谱已保存: {os.path.basename(record_path)}")

    def show_record(self):
        if not self.runner:
            self.output_append("没有可显示的棋谱")
            return
        win = tk.Toplevel(self.root)
        win.title("棋谱")
        win.geometry("400x500")
        text = scrolledtext.ScrolledText(win, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, self.runner.record.to_text())
        text.config(state=tk.DISABLED)

    def on_canvas_click(self, event):
        if not self.runner:
            return
        x, y = event.x, event.y
        if (x < self.margin - self.grid_size // 2 or
            x > self.margin + 14 * self.grid_size + self.grid_size // 2 or
            y < self.margin - self.grid_size // 2 or
            y > self.margin + 14 * self.grid_size + self.grid_size // 2):
            return
        row, col = self.xy_to_row_col(x, y)
        px, py = self.row_col_to_xy(row, col)
        if ((x - px) ** 2 + (y - py) ** 2) ** 0.5 > self.grid_size // 2:
            return
        row = max(0, min(14, row))
        col = max(0, min(14, col))
        col_letter = chr(ord('A') + col)
        coord = f"{col_letter}{row + 1}"
        opp_char = "W" if self.my_color == BLACK else "B"
        self.opp_input_entry.delete(0, tk.END)
        self.opp_input_entry.insert(0, f"{opp_char}({coord})")

    def output_append(self, text):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def output_clear(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)

    def _log(self, message: str):
        if self.runner:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.runner.log.append(f"[{timestamp}] {message}")

    def quit_game(self):
        self.stop_timer()
        if self.runner and self.game_started:
            self.save_game()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = CompetitionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_game)
    root.mainloop()


if __name__ == "__main__":
    main()
