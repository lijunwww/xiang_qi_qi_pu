import tkinter as tk
from tkinter import ttk

class MovesPanel:
    """
    右侧左下：主线棋谱列表（两行一回合）
    - 单击/回车/双击：跳转到对应半步（ply）
    - 展示数据来自 GUI.get_display_moves()（当前主线）
    """
    def __init__(self, gui, parent):
        self.gui = gui
        self.frame = ttk.Frame(parent)

        ttk.Label(self.frame, text="主线棋谱", font=("Microsoft YaHei", 10, "bold")).pack(anchor=tk.W, padx=6, pady=(6, 2))

        box = ttk.Frame(self.frame)
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.listbox = tk.Listbox(
            box, font=("Courier New", 12),
            exportselection=False
        )
        vbar = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=vbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.index_to_ply = []  # 行索引 -> ply（可能为 None）

        self.listbox.bind("<<ListboxSelect>>", self._jump)
        self.listbox.bind("<Return>", self._jump)
        self.listbox.bind("<Double-Button-1>", self._jump)
        # Ensure Up/Down are handled by GUI navigation (avoid listbox changing selection first)
        self.listbox.bind("<Down>", lambda e: self.gui.on_key_down(e))
        self.listbox.bind("<Up>", lambda e: self.gui.on_key_up(e))
        self.listbox.bind("<j>", lambda e: self.gui.on_key_down(e))
        self.listbox.bind("<k>", lambda e: self.gui.on_key_up(e))

    def refresh(self):
        self.listbox.delete(0, tk.END)
        self.index_to_ply.clear()

        moves_pairs = self.gui.get_display_moves()

        for idx, (rmove, bmove) in enumerate(moves_pairs, start=1):
            rmove = rmove or ""
            bmove = bmove or ""
            prefix = f"{idx}.  "

            # 红走行
            self.listbox.insert(tk.END, f"{prefix}{rmove}")
            ply_red = (2 * (idx - 1) + 1) if rmove else None
            self.index_to_ply.append(ply_red)

            # 黑走行
            self.listbox.insert(tk.END, f"{' ' * len(prefix)}{bmove}")
            ply_black = (2 * (idx - 1) + 2) if bmove else None
            self.index_to_ply.append(ply_black)

        self.listbox.see(tk.END)

    def _jump(self, _evt=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        row = int(sel[0])
        if 0 <= row < len(self.index_to_ply):
            ply = self.index_to_ply[row]
            if ply is not None:
                self.gui.on_move_row_selected(ply)

    def select_ply(self, ply: int):
        if ply <= 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.see(0)
            return
        move_idx = (ply - 1) // 2 + 1
        is_black = (ply % 2 == 0)
        row = (move_idx - 1) * 2 + (1 if is_black else 0)
        row = max(0, min(row, self.listbox.size() - 1))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(row)
        self.listbox.see(row)
