import tkinter as tk
from tkinter import messagebox
import chess_rules as xr
import draw_board as db


class BoardCanvas:
    """棋盘画布类：负责绘制棋盘、处理点击与高亮等。"""

    def __init__(self, gui, parent):
        """初始化棋盘画布。"""
        self.gui = gui
        self.frame = tk.Frame(parent)
        self.canvas = tk.Canvas(self.frame, bg="#DEB887")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 事件绑定
        # 点击与移动
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Configure>", self._on_resize)

    # ---------- 绘制与高亮 ----------
    def draw_board(self):
        for r in range(db.BOARD_ROWS):
            for c in range(db.BOARD_COLS):
                piece = self.gui.board.piece_at((r, c))
                db.board_data[r][c] = (
                    "."
                    if piece is None
                    else (
                        piece.ptype.upper()
                        if piece.color == "r"
                        else piece.ptype.lower()
                    )
                )
        self.canvas.delete("all")
        db.draw_board(self.canvas, self.gui.piece_font)

    def clear_highlights(self):
        self.canvas.delete("sel")
        self.canvas.delete("hint")
        self.canvas.delete("hover")

    def update_highlights(self):
        self.clear_highlights()
        M, S = db.MARGIN, db.SQUARE_SIZE
        x1 = self.gui.offset_x + M
        y1 = self.gui.offset_y + M

        def center_of(rc):
            r, c = rc
            return (x1 + c * S, y1 + r * S)

        # 悬停高亮
        if self.gui.selected_sq is not None:
            cx, cy = center_of(self.gui.selected_sq)
            rad = S * 0.34
            self.canvas.create_oval(
                cx - rad,
                cy - rad,
                cx + rad,
                cy + rad,
                outline="#CC0000",
                width=3,
                tag="sel",
            )
        for tr in self.gui.legal_targets:
            cx, cy = center_of(tr)
            rad = S * 0.1
            tp = self.gui.board.piece_at(tr)
            if tp is None:
                self.canvas.create_oval(
                    cx - rad,
                    cy - rad,
                    cx + rad,
                    cy + rad,
                    fill="#2ecc71",
                    outline="",
                    tag="hint",
                )
            else:
                self.canvas.create_oval(
                    cx - rad * 1.5,
                    cy - rad * 1.5,
                    cx + rad * 1.5,
                    cy + rad * 1.5,
                    outline="#2ecc71",
                    width=3,
                    tag="hint",
                )

    # ---------- 事件 ----------
    def _on_motion(self, e):
        _ = self._pixel_to_sq(e.x, e.y)
        self.update_highlights()

    def _on_click(self, event):
        # 转换为格子
        sq = self._pixel_to_sq(event.x, event.y)

        # 无效点击
        if sq is None:
            return

        # 获取格子上的棋子
        piece = self.gui.board.piece_at(sq)

        # 1) 选择
        # 还没选：选/不选
        if self.gui.selected_sq is None:
            # 有子且轮到自己下
            if piece and piece.color == self.gui.board.side_to_move:
                self.gui.set_selection(sq)

            # 无子或对方子
            else:
                self.gui.set_selection(None)
            return

        # 2) 已选再点：切换/尝试走子
        # 点自己：取消选择
        if sq == self.gui.selected_sq:
            self.gui.set_selection(None)
            return
        # 点自己方子：切换选择
        if piece and piece.color == self.gui.board.side_to_move:
            self.gui.set_selection(sq)
            return

        # 合法性
        # 点空格或对方子：尝试走子
        if sq in self.gui.legal_targets:
            # —— 先验证合法性 —— #
            mv = xr.Move(self.gui.selected_sq, sq)
            # 获取所有合法走法，匹配当前走法
            legal = self.gui.board.generate_legal_moves(self.gui.board.side_to_move)
            matched = next(
                (
                    lm
                    for lm in legal
                    if lm.from_sq == mv.from_sq and lm.to_sq == mv.to_sq
                ),
                None,
            )
            # 无匹配，非法走子
            if not matched:
                messagebox.showwarning("非法走子", "该走法不合法或会使自己被将。")
                self.gui.set_selection(None)
                return

            # —— 先生成SAN，后落子 —— #
            # SAN记账需要在落子前生成
            san = self.gui.san_traditional(matched)

            # 落子
            self.gui.board.make_move(matched)

            # 交给GUI做“主线/变招”的记账
            # 注意：这里传入的是SAN字符串
            self.gui.record_move_played(san)

            # 刷新
            # 画面更新
            self.gui.set_selection(None)

            # 重绘棋盘与高亮
            self.draw_board()
            self.update_highlights()

            # 刷新走法列表
            self.gui.refresh_moves_list()

            # 检查对局结束
            res = self.gui.board.game_result()
            # 有结果
            if res:
                if res.endswith("+"):
                    winner = "红方" if res.startswith("r") else "黑方"
                    messagebox.showinfo("对局结束", f"将死！胜者：{winner}")
                else:
                    messagebox.showinfo("对局结束", f"对局结束：{res}")
            return

        self.gui.set_selection(None)

    # ---------- 缩放与像素↔格子 ----------
    def _on_resize(self, event):
        """
        画布尺寸变化时的处理：重新计算格子大小与偏移，重绘棋盘与高亮。
        """

        # 计算格子大小与偏移
        db.SQUARE_SIZE = min(
            max(20, (event.width - 2 * db.MARGIN) // db.BOARD_COLS),
            max(20, (event.height - 2 * db.MARGIN) // db.BOARD_ROWS),
        )

        # 计算偏移，使棋盘居中
        board_width = (db.BOARD_COLS - 1) * db.SQUARE_SIZE + 2 * db.MARGIN
        board_height = (db.BOARD_ROWS - 1) * db.SQUARE_SIZE + 2 * db.MARGIN
        self.gui.offset_x = (event.width - board_width) // 2
        self.gui.offset_y = (event.height - board_height) // 2

        # 重绘棋盘与高亮
        self.draw_board()
        self.update_highlights()

    def _pixel_to_sq(self, px, py):
        """
        像素坐标 → 格子坐标
        返回 (row, col) 或 None（无效）
        """

        # 计算起始位置
        start_x = self.gui.offset_x + db.MARGIN
        start_y = self.gui.offset_y + db.MARGIN

        # 遍历所有格子，找最近的那个
        # 遍历行
        for r in range(db.BOARD_ROWS):
            # 遍历列
            for c in range(db.BOARD_COLS):
                cx = start_x + c * db.SQUARE_SIZE
                cy = start_y + r * db.SQUARE_SIZE
                # 判断是否在该格子范围内
                if (
                    abs(px - cx) <= db.SQUARE_SIZE / 2
                    and abs(py - cy) <= db.SQUARE_SIZE / 2
                ):
                    return (r, c)
        return None
