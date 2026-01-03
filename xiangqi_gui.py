import os
import tkinter as tk
from tkinter import ttk, font, messagebox
from typing import List, Dict, Optional, Tuple

import chess_rules as xr
import draw_board as db

from state_utils import read_json, write_json, SETTINGS_JSON
from variation_mgr import VariationManager, VariationNode
from menubar import create_menubar
from board_canvas import BoardCanvas
from moves_panel import MovesPanel
from variations_panel import VariationPanel
from file_ops import FileOps
from bookmark_ops import BookmarkOps
from transforms import Transforms


class XiangqiGUI:
    """
    主组合类：XiangqiGUI（含“变着=主线切换器”）
    - 右侧：上=棋谱属性；下=左右分栏（左=主线棋谱；右=垂直分栏：上=注释，下=变着列表）
    """
    def __init__(self, root: tk.Tk):
        # —— 基本窗口 ——
        self.root = root
        self.root.title("象棋摆谱器")
        # allow resizing by mouse drag
        try:
            self.root.resizable(True, True)
        except Exception:
            pass
        # set a reasonable minimum size so users can resize freely
        try:
            self.root.minsize(300, 200)
        except Exception:
            pass

        # 未保存标志 + 退出拦截
        self._dirty = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 棋子字体（棋盘用）
        available_fonts = list(font.families())
        fam = next((f for f in db.PIECE_FONT_FAMILY_PREFERRED if f in available_fonts), available_fonts[0])
        self.piece_font = font.Font(family=fam, size=db.PIECE_FONT_SIZE, weight='bold')

        # 规则与主线数据
        self.board = xr.Board()
        self.moves_list: List[List[str]] = []          # 主线：[[红, 黑], ...]
        self.metadata = {"title": "", "author": "", "remark": ""}

        # 注释：{ ply(int): "注释文本" }
        self.comments: Dict[int, str] = {}

        # 变着
        self.var_mgr = VariationManager()
        self._building_var: Optional[Tuple[int, int]] = None  # (pivot_ply, var_id) 当前“录制中的变着”
        self._viewing_variation: Optional[Tuple[int, int]] = None  # (pivot_ply, var_id) 当前在主界面查看的变着（若有）
        self._applied_variation: Optional[Tuple[int, int]] = None  # (pivot_ply, var_id) 当前已经应用到主线的变着（若有）

        # 视图/交互状态
        self.selected_sq = None
        self.legal_targets = []
        self.offset_x = 0
        self.offset_y = 0

        # 当前注释/当前选择的半步
        self._current_selected_ply: Optional[int] = None

        # 子模块
        self.file_ops = FileOps(self)
        self.bm_ops = BookmarkOps(self)
        self.transforms = Transforms(self)

        # ===== 布局：左棋盘 + 右综合面板 =====
        self.root_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.root_paned.pack(fill=tk.BOTH, expand=True)

        # 左：棋盘
        self.board_canvas = BoardCanvas(self, self.root_paned)
        self.root_paned.add(self.board_canvas.frame, weight=3)

        # 右：上属性 + 下（左主线棋谱 | 右：上注释 + 下变着）
        self.right_paned = ttk.PanedWindow(self.root_paned, orient=tk.VERTICAL)
        self.root_paned.add(self.right_paned, weight=2)

        # 右-上：属性
        self.attr_frame = self._build_attr_frame(self.right_paned)
        self.right_paned.add(self.attr_frame, weight=1)

        # 右-下：左右分栏
        self.lower_paned = ttk.PanedWindow(self.right_paned, orient=tk.HORIZONTAL)
        self.right_paned.add(self.lower_paned, weight=3)

        # 左下：主线棋谱
        self.moves_panel = MovesPanel(self, self.lower_paned)
        self.lower_paned.add(self.moves_panel.frame, weight=1)

        # 右下：垂直分栏（上=注释 下=变着列表）
        self.right_bottom = ttk.PanedWindow(self.lower_paned, orient=tk.VERTICAL)
        self.lower_paned.add(self.right_bottom, weight=1)

        self.notes_frame = self._build_notes_frame(self.right_bottom)
        self.right_bottom.add(self.notes_frame, weight=3)

        self.vari_panel = VariationPanel(self, self.right_bottom)
        self.right_bottom.add(self.vari_panel.frame, weight=2)

        # 菜单栏
        self.recent_submenu = None
        # Load saved settings (persisted across runs)
        _settings = read_json(SETTINGS_JSON, {})
        # restore window geometry if present
        try:
            geom = _settings.get('geometry')
            if geom:
                try:
                    self.root.geometry(geom)
                    # ensure geometry takes effect before user interaction
                    try:
                        self.root.update()
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
        # restore pane sash positions if present
        try:
            pane_sashes = _settings.get('pane_sashes', {})
            # Delay sash setting until widgets realized
            def _apply_sashes():
                try:
                    if 'root_paned' in pane_sashes:
                        vals = pane_sashes.get('root_paned', [])
                        if vals and hasattr(self, 'root_paned'):
                            try:
                                self.root_paned.sashpos(0, int(vals[0]))
                            except Exception:
                                pass
                    if 'right_paned' in pane_sashes:
                        vals = pane_sashes.get('right_paned', [])
                        if vals and hasattr(self, 'right_paned'):
                            try:
                                self.right_paned.sashpos(0, int(vals[0]))
                            except Exception:
                                pass
                    if 'lower_paned' in pane_sashes:
                        vals = pane_sashes.get('lower_paned', [])
                        if vals and hasattr(self, 'lower_paned'):
                            try:
                                self.lower_paned.sashpos(0, int(vals[0]))
                            except Exception:
                                pass
                    if 'right_bottom' in pane_sashes:
                        vals = pane_sashes.get('right_bottom', [])
                        if vals and hasattr(self, 'right_bottom'):
                            try:
                                self.right_bottom.sashpos(0, int(vals[0]))
                            except Exception:
                                pass
                except Exception:
                    pass

            try:
                # call after idle so widgets are mapped
                self.root.after(50, _apply_sashes)
            except Exception:
                pass
        except Exception:
            pass
        # Load saved visibility settings
        self.board_visible = tk.BooleanVar(value=_settings.get('board_visible', True))
        self.attr_visible = tk.BooleanVar(value=_settings.get('attr_visible', True))
        self.notes_visible = tk.BooleanVar(value=_settings.get('notes_visible', True))
        self.vari_visible = tk.BooleanVar(value=_settings.get('vari_visible', True))
        # create menubar and keep reference for keyboard menu activation
        try:
            self.menubar = create_menubar(self)
            self.root.config(menu=self.menubar)
        except Exception:
            self.root.config(menu=create_menubar(self))

        # Bind Alt+letter to open top-level menus (File=F, Edit=E, View=V, Bookmarks=M, Help=H)
        try:
            def _post_menu(idx):
                try:
                    mb = self.menubar
                    name = mb.entrycget(idx, 'menu')
                    if not name:
                        return
                    submenu = mb.nametowidget(name)
                    x = self.root.winfo_rootx() + 10
                    y = self.root.winfo_rooty() + 30
                    submenu.post(x, y)
                except Exception:
                    pass
            # bind both lower and upper case
            # map alt keys to menu labels to ensure correct menu is opened
            label_map = {
                'f': '文件(F)',
                'e': '编辑(E)',
                'v': '视图(V)',
                'm': '书签(M)',
                'h': '帮助(H)'
            }
            def _post_menu_by_label(lbl):
                try:
                    mb = self.menubar
                    end = mb.index('end')
                    if end is None:
                        return
                    for i in range(end + 1):
                        try:
                            entry_label = mb.entrycget(i, 'label')
                        except Exception:
                            entry_label = None
                        if entry_label == lbl:
                            name = mb.entrycget(i, 'menu')
                            if not name:
                                return
                            submenu = mb.nametowidget(name)
                            x = self.root.winfo_rootx() + 10
                            y = self.root.winfo_rooty() + 30
                            submenu.post(x, y)
                            # remember posted submenu and label
                            self._posted_submenu = submenu
                            self._posted_menu_label = lbl

                            # temporary key handler to accept single-letter activation
                            def _on_menu_key(event):
                                try:
                                    key = (event.char or event.keysym or '')
                                    ch = key.lower()
                                    # Try to find an entry in the posted submenu whose label contains the mnemonic like '(O)'
                                    try:
                                        # first try explicit mnemonic mapping attached to gui
                                        menu_map = getattr(self, '_menu_mnemonics', None)
                                        if menu_map and getattr(self, '_posted_menu_label', None):
                                            lbl = self._posted_menu_label
                                            mm = menu_map.get(lbl, {})
                                            if ch in mm:
                                                try:
                                                    mm[ch]()
                                                except Exception:
                                                    pass
                                                try:
                                                    if hasattr(self, '_posted_submenu') and self._posted_submenu:
                                                        self._posted_submenu.unpost()
                                                except Exception:
                                                    pass
                                                return
                                        # fallback: scan submenu labels for (X) style mnemonic
                                        submenu = getattr(self, '_posted_submenu', None)
                                        if submenu is not None:
                                            end = submenu.index('end')
                                            if end is not None:
                                                for ii in range(end + 1):
                                                    try:
                                                        lab = submenu.entrycget(ii, 'label') or ''
                                                    except Exception:
                                                        lab = ''
                                                    if not lab:
                                                        continue
                                                    # look for (X) style mnemonic
                                                    if f'({key.upper()})' in lab or f'({key.lower()})' in lab:
                                                        try:
                                                            submenu.invoke(ii)
                                                        except Exception:
                                                            pass
                                                        try:
                                                            submenu.unpost()
                                                        except Exception:
                                                            pass
                                                        return
                                    except Exception:
                                        pass
                                    # fallback: nothing invoked
                                finally:
                                    try:
                                        self.root.unbind_all('<Key>')
                                    except Exception:
                                        pass

                            # bind single-key handler (not global) and return
                            try:
                                # bind globally so we receive the next key even if menu has focus
                                self.root.bind_all('<Key>', _on_menu_key)
                            except Exception:
                                pass
                            return
                except Exception:
                    pass

            for key, lbl in label_map.items():
                def _make_alt_handler(L):
                    def _h(event=None):
                        _post_menu_by_label(L)
                        return "break"
                    return _h
                h = _make_alt_handler(lbl)
                self.root.bind_all(f'<Alt-{key}>', h)
                self.root.bind_all(f'<Alt-{key.upper()}>', h)
        except Exception:
            pass

        # Apply saved visibility settings: hide panes whose flags are False
        try:
            if not self.board_visible.get():
                try: self.root_paned.forget(self.board_canvas.frame)
                except Exception: pass
            if not self.attr_visible.get():
                try: self.right_paned.forget(self.attr_frame)
                except Exception: pass
            # If notes/vari both hidden, remove the right_bottom container so moves panel can expand
            if not self.notes_visible.get():
                try: self.right_bottom.forget(self.notes_frame)
                except Exception: pass
            if not self.vari_visible.get():
                try: self.right_bottom.forget(self.vari_panel.frame)
                except Exception: pass
            if (not self.notes_visible.get()) and (not self.vari_visible.get()):
                try:
                    self.lower_paned.forget(self.right_bottom)
                except Exception:
                    pass
            else:
                # ensure right_bottom is present if any child is visible
                try:
                    if str(self.right_bottom) not in self.lower_paned.panes():
                        self.lower_paned.add(self.right_bottom, weight=1)
                except Exception:
                    pass
        except Exception:
            pass

        # Adjust layout so moves panel expands if it's the only right-side subwindow
        try:
            self._adjust_right_layout()
        except Exception:
            pass

        # 初次绘制
        self.board_canvas.draw_board()
        self.board_canvas.update_highlights()
        self.refresh_moves_list()
        self._refresh_note_editor()
        self.refresh_variations_box()

        # 快捷键
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Down>", self.on_key_down)
        self.root.bind("<Up>", self.on_key_up)
        self.root.bind("<Home>", self.on_key_home)
        # Single-key panel focus shortcuts: h=主线棋谱, l=变着列表, n=注释面板
        def _focus_moves(event=None):
            if self._should_ignore_nav():
                return
            try:
                # select current ply row and focus listbox
                if self._current_selected_ply is None:
                    cur = len(self.board.history)
                else:
                    cur = self._current_selected_ply
                try:
                    self._select_moves_row_for_ply(cur)
                except Exception:
                    pass
                try:
                    self.moves_panel.listbox.focus_set()
                except Exception:
                    pass
            except Exception:
                pass
            return "break"

        def _focus_variations(event=None):
            if self._should_ignore_nav():
                return
            try:
                # ensure variations box shows current pivot and focus the tree
                try:
                    self.refresh_variations_box()
                except Exception:
                    pass
                try:
                    self.vari_panel.tree.focus_set()
                    # if nothing selected, select first node
                    ch = self.vari_panel.tree.get_children()
                    if ch:
                        try:
                            self.vari_panel.tree.selection_set(ch[0])
                            self.vari_panel.tree.focus(ch[0])
                            self.vari_panel.tree.see(ch[0])
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass
            return "break"

        def _focus_notes(event=None):
            if self._should_ignore_nav():
                return
            try:
                try:
                    self.txt_note.focus_set()
                except Exception:
                    pass
            except Exception:
                pass
            return "break"

        # bind both lower and upper case
        try:
            self.root.bind_all('<Key-h>', lambda e: _focus_moves(e))
            self.root.bind_all('<Key-H>', lambda e: _focus_moves(e))
            self.root.bind_all('<Key-l>', lambda e: _focus_variations(e))
            self.root.bind_all('<Key-L>', lambda e: _focus_variations(e))
            self.root.bind_all('<Key-n>', lambda e: _focus_notes(e))
            self.root.bind_all('<Key-N>', lambda e: _focus_notes(e))
        except Exception:
            pass

        # Restore last open file if it exists (Auto-Session)
        last_file = _settings.get('last_open_file')
        if last_file and os.path.exists(last_file):
            def _load_init():
                try:
                    # Silent load
                    self.file_ops.load_game_from_path(last_file, silent=True)
                    # Update recent index
                    if last_file in self.file_ops.recent_files:
                        self.file_ops.recent_index = self.file_ops.recent_files.index(last_file)
                    else:
                        self.file_ops.add_recent(last_file)
                        self.file_ops.recent_index = 0
                except Exception:
                    pass
            # Delay slightly to ensure UI is ready
            try:
                self.root.after(200, _load_init)
            except Exception:
                pass

    # =================== 展示层：主线 ===================
    def get_display_moves(self):
        return self.moves_list

    # ================= 右上：属性 =================
    def _build_attr_frame(self, parent):
        frm = ttk.Frame(parent)
        ttk.Label(frm, text="棋谱属性", font=("Microsoft YaHei", 11, "bold")).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        ttk.Label(frm, text="标题：").grid(row=1, column=0, sticky="e", padx=6, pady=2)
        ttk.Label(frm, text="作者：").grid(row=2, column=0, sticky="e", padx=6, pady=2)
        ttk.Label(frm, text="说明：").grid(row=3, column=0, sticky="ne", padx=6, pady=2)

        self.var_title = tk.StringVar(value=self.metadata.get("title", ""))
        self.var_author = tk.StringVar(value=self.metadata.get("author", ""))

        ent_title = ttk.Entry(frm, textvariable=self.var_title, width=38)
        ent_author = ttk.Entry(frm, textvariable=self.var_author, width=38)
        ent_title.grid(row=1, column=1, sticky="we", padx=6, pady=2)
        ent_author.grid(row=2, column=1, sticky="we", padx=6, pady=2)

        self.txt_remark = tk.Text(frm, width=44, height=4)
        self.txt_remark.insert("1.0", self.metadata.get("remark", ""))
        self.txt_remark.grid(row=3, column=1, sticky="we", padx=6, pady=2)

        def save_attr():
            self.metadata["title"] = self.var_title.get().strip()
            self.metadata["author"] = self.var_author.get().strip()
            self.metadata["remark"] = self.txt_remark.get("1.0", "end").strip()
            self.root.title(f"象棋摆谱器 - {self.metadata.get('title') or '未命名'}")
            self.mark_dirty()

        ttk.Button(frm, text="保存属性", command=save_attr).grid(row=4, column=1, sticky="e", padx=6, pady=(4, 8))
        frm.columnconfigure(1, weight=1)
        return frm

    def refresh_attr_panel(self):
        """Sync attribute panel fields with current metadata."""
        try:
            self.var_title.set(self.metadata.get("title", ""))
            self.var_author.set(self.metadata.get("author", ""))
            self.txt_remark.delete("1.0", "end")
            self.txt_remark.insert("1.0", self.metadata.get("remark", ""))
        except Exception:
            pass

    # ================= 右下：注释 =================
    def _build_notes_frame(self, parent):
        frm = ttk.Frame(parent)
        ttk.Label(frm, text="注释（针对所选半步）", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", padx=6, pady=(6, 2))
        self.txt_note = tk.Text(frm, width=40, height=8)
        self.txt_note.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, padx=6, pady=(0, 8))
        ttk.Button(btns, text="保存注释", command=self._save_current_note).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="清空", command=lambda: self.txt_note.delete("1.0", "end")).pack(side=tk.RIGHT, padx=4)
        return frm

    def _refresh_note_editor(self):
        ply = self._current_selected_ply
        self.txt_note.delete("1.0", "end")
        if ply is None:
            return
        # If currently viewing a variation, show variation's per-move comment when applicable
        view = getattr(self, '_viewing_variation', None)
        if view:
            pivot, var_id = view
            node = self.var_mgr.find_by_id(var_id)
            if node is not None:
                idx = ply - pivot
                if 0 <= idx < len(node.san_comments):
                    txt = node.san_comments[idx] or ""
                    # show variant comment (may be empty)
                    if txt:
                        self.txt_note.insert("1.0", txt)
                    return
        # If a variation is applied to the mainline and the current ply falls inside it,
        # show the variation's per-move comment (take precedence over mainline comment).
        applied = getattr(self, '_applied_variation', None)
        if applied:
            apivot, avar = applied
            node = self.var_mgr.find_by_id(avar)
            if node is not None:
                idx = ply - apivot
                if 0 <= idx < len(node.san_comments):
                    txt = node.san_comments[idx] or ""
                    if txt:
                        self.txt_note.insert("1.0", txt)
                    return
        # default: mainline comment
        txt = self.comments.get(ply, "")
        if txt:
            self.txt_note.insert("1.0", txt)

    def _save_current_note(self):
        ply = self._current_selected_ply
        if ply is None:
            messagebox.showinfo("提示", "请先在棋谱中选择一个半步。")
            return
        txt = self.txt_note.get("1.0", "end").strip()
        # If currently viewing a variation, save into that variation's san_comments
        view = getattr(self, '_viewing_variation', None)
        if view:
            pivot, var_id = view
            node = self.var_mgr.find_by_id(var_id)
            if node is not None:
                idx = ply - pivot
                if 0 <= idx < len(node.san_comments):
                    node.san_comments[idx] = txt
                    self.mark_dirty()
                    messagebox.showinfo("成功", f"已保存变着注释（ply={ply}）。")
                    return
        # If a variation was applied to mainline, also save into that variation's san_comments
        applied = getattr(self, '_applied_variation', None)
        if applied:
            apivot, avar = applied
            node = self.var_mgr.find_by_id(avar)
            if node is not None:
                idx = ply - apivot
                if 0 <= idx < len(node.san_comments):
                    node.san_comments[idx] = txt
                    self.mark_dirty()
                    messagebox.showinfo("成功", f"已保存变着注释（ply={ply}）。")
                    return
        # default: save to mainline comments
        self.comments[ply] = txt
        self.mark_dirty()
        messagebox.showinfo("成功", f"已保存注释（ply={ply}）。")

    # ================= 小工具 =================
    def mark_dirty(self):
        self._dirty = True

    def clear_dirty(self):
        self._dirty = False

    # ================= 规则封装 =================
    def san_traditional(self, move: xr.Move) -> str:
        return self.board.move_to_chinese(move)

    def append_move_mainline(self, san):
        """主线追加（根据最近一手的颜色记录走子，避免依赖可能被其他操作修改的 `side_to_move`）。"""
        # 参考：history 中每个三元组为 (move, captured, prev_side)
        moved_side = None
        if self.board.history:
            moved_side = self.board.history[-1][2]
        else:
            # 回退兼容：若 history 为空，则根据当前 side_to_move 推断上一步颜色
            moved_side = 'r' if self.board.side_to_move == 'b' else 'b'

        if moved_side == 'r':
            # 红方刚走：新增一行的红走
            if self.moves_list and self.moves_list[-1][0] == "":
                self.moves_list[-1][0] = san
            else:
                self.moves_list.append([san, ""])
        else:
            # 黑方刚走：填充本行的黑走
            if self.moves_list:
                self.moves_list[-1][1] = san
            else:
                self.moves_list.append(["", san])

    def refresh_moves_list(self):
        self.moves_panel.refresh()

    def set_selection(self, sq):
        self.selected_sq = sq
        if sq is None:
            self.legal_targets = []
            self.board_canvas.update_highlights()
            return
        legal = self.board.generate_legal_moves(self.board.side_to_move)
        self.legal_targets = [mv.to_sq for mv in legal if mv.from_sq == sq]
        self.board_canvas.update_highlights()

    # —— 记谱规范化（用于稳健匹配） ——
    def _normalize_san(self, s: str) -> str:
        if not s:
            return ""
        t = s.strip().replace(" ", "")
        full_to_half = str.maketrans("０１２３４５６７８９", "0123456789")
        t = t.translate(full_to_half)
        zh_digit_map = {"零": "0", "〇": "0", "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
                        "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
        for k, v in zh_digit_map.items():
            t = t.replace(k, v)
        rep = {"車": "车", "馬": "马", "傌": "马", "砲": "炮", "將": "将", "帥": "帅", "士": "仕"}
        for k, v in rep.items():
            t = t.replace(k, v)
        return t

    def play_san(self, san_str: str):
        target = self._normalize_san(san_str)
        legal = self.board.generate_legal_moves(self.board.side_to_move)
        for mv in legal:
            cand = self.board.move_to_chinese(mv)
            if cand == san_str or self._normalize_san(cand) == target or \
               self._normalize_san(cand).replace(".", "") == target.replace(".", ""):
                self.board.make_move(mv)
                return
        raise ValueError(f"无法在当前局面找到匹配的走法：{san_str}")

    def _play_san_force(self, san_str: str):
        try:
            self.play_san(san_str)
        except Exception:
            pass

    # ================= 撤销/跳转 =================
    def undo(self):
        if not self.board.history:
            return
        self.board.undo_move()
        self.board_canvas.draw_board()
        self.set_selection(None)
        self.refresh_moves_list()
        self.refresh_variations_box()
        self.mark_dirty()

    def delete_last_move(self):
        self.undo()

    def redo(self):
        messagebox.showinfo('提示', '暂未实现 Redo 功能。')

    def restore_to_ply(self, ply: int):
        """将棋局恢复到给定半步数（以“主线”为准）"""
        self.board = xr.Board()
        cur = 0
        for rmove, bmove in self.moves_list:
            if cur >= ply: break
            if rmove:
                if cur >= ply: break
                self._play_san_force(rmove); cur += 1
            if bmove:
                if cur >= ply: break
                self._play_san_force(bmove); cur += 1

        self._current_selected_ply = ply
        self._building_var = None            # 切换选择时，结束正在录制的变着
        self.board_canvas.draw_board()
        self.set_selection(None)
        self.refresh_moves_list()
        self._refresh_note_editor()
        self._select_moves_row_for_ply(ply)
        self.refresh_variations_box()

    def on_move_row_selected(self, ply: int):
        self.restore_to_ply(ply)

    def _select_moves_row_for_ply(self, ply: int):
        try:
            self.moves_panel.select_ply(ply)
        except Exception:
            pass

    def _should_ignore_nav(self):
        w = self.root.focus_get()
        if w is None:
            return False
        try:
            # Allow navigation keys in Listbox (we handle them manually to avoid full replay bugs)
            # Only ignore for actual text editors
            return w.winfo_class() in ('Text', 'Entry', 'TEntry')
        except Exception:
            return False

    def on_key_down(self, event=None):
        if self._should_ignore_nav():
            return
        flat = self._mainline_san_flat()
        max_ply = len(flat)
        # Keep current synced with actual board history length when possible
        current = self._current_selected_ply if self._current_selected_ply is not None else len(self.board.history)

        if current < max_ply:
            # Incremental forward: play the next move on the current board
            next_move_san = flat[current]
            try:
                self.play_san(next_move_san)
                # Sync selected ply to actual board history
                self._current_selected_ply = len(self.board.history)
                self._building_var = None  # Stop recording variation when navigating
                
                # Refresh UI
                self.board_canvas.draw_board()
                self.set_selection(None)
                self._select_moves_row_for_ply(self._current_selected_ply)
                self.refresh_variations_box()
                self._refresh_note_editor()
            except Exception:
                # If move fails to play, stay at current state
                pass
        return "break"

    def on_key_up(self, event=None):
        if self._should_ignore_nav():
            return
        # If no selection, initialize from actual board history
        if self._current_selected_ply is None:
            self._current_selected_ply = len(self.board.history)

        if self._current_selected_ply <= 0:
            return "break"

        # Incremental backward: undo the last move (if any on board)
        if self.board.history:
            self.board.undo_move()
            # Sync selected ply to actual board history
            self._current_selected_ply = len(self.board.history)
            self._building_var = None
            
            # Refresh UI
            self.board_canvas.draw_board()
            self.set_selection(None)
            self._select_moves_row_for_ply(self._current_selected_ply)
            self.refresh_variations_box()
            self._refresh_note_editor()
        return "break"

    def on_key_home(self, event=None):
        if self._should_ignore_nav():
            return
        self.restore_to_ply(0)
        return "break"

    # =================== 变着核心 ===================
    def _mainline_san_flat(self) -> List[str]:
        flat = []
        for rmove, bmove in self.moves_list:
            if rmove: flat.append(rmove)
            if bmove: flat.append(bmove)
        return flat

    def _apply_variation_to_mainline(self, pivot_ply: int, v: VariationNode, jump_to_end=False):
        """
        主线 := 主线[:pivot-1] + v.san_moves
        pivot_ply 从 1 开始；通常切换后跳到 pivot_ply 位置
        """
        old_flat = self._mainline_san_flat()
        new_flat = old_flat[:pivot_ply - 1] + list(v.san_moves)

        # 还原回 pair 结构
        new_pairs: List[Tuple[str, str]] = []
        it = iter(new_flat)
        for r in it:
            b = next(it, "")
            new_pairs.append([r, b])
        self.moves_list = new_pairs

        # 切换后定位
        if jump_to_end:
            tgt_ply = len(new_flat)
        else:
            tgt_ply = min(pivot_ply, len(new_flat))
        self.restore_to_ply(tgt_ply)

    def refresh_variations_box(self, pivot_ply: Optional[int] = None):
        if pivot_ply is None:
            # “当前步”的下一步为变着点
            base = self._current_selected_ply or 0
            pivot_ply = base + 1
        self.vari_panel.refresh_for_pivot(pivot_ply)

    def apply_variation_by_id(self, pivot_ply: int, var_id: int):
        v = self.var_mgr.get(pivot_ply, var_id)
        if not v:
            return
        # 保存当前主线备份（包含注释），以便可以恢复
        try:
            self._last_mainline_backup = {
                'moves': [list(p) for p in self.moves_list],
                'comments': dict(self.comments)
            }
        except Exception:
            self._last_mainline_backup = None

        self._apply_variation_to_mainline(pivot_ply, v, jump_to_end=False)
        # 将变着内的注释复制到主线相应半步（覆盖或写入）
        try:
            for i, c in enumerate(v.san_comments):
                ply = pivot_ply + i
                if c:
                    self.comments[ply] = c
        except Exception:
            pass
        self._building_var = None  # 应用后结束录制
        # stop viewing any variation when applying
        self._viewing_variation = None
        # remember which variation is now applied to mainline so edits persist back
        try:
            self._applied_variation = (pivot_ply, var_id)
        except Exception:
            self._applied_variation = None
        self.mark_dirty()
        # ensure note editor reflects variation comments (overwrite any stale mainline display)
        try:
            self._refresh_note_editor()
        except Exception:
            pass

    def restore_mainline(self):
        """恢复最近一次被替换前的主线（如果有备份）。"""
        bk = getattr(self, '_last_mainline_backup', None)
        if not bk:
            messagebox.showinfo("提示", "没有可恢复的主线。", parent=self.root)
            return
        try:
            if isinstance(bk, dict):
                self.moves_list = [list(p) for p in bk.get('moves', [])]
                # restore comments if present
                try:
                    self.comments = dict(bk.get('comments', {}))
                except Exception:
                    pass
            else:
                self.moves_list = [list(p) for p in bk]
        except Exception:
            # 恢复失败时告知用户
            messagebox.showwarning("恢复失败", "恢复主线时发生错误。", parent=self.root)
            return
        # 清除备份（一次性恢复）
        self._last_mainline_backup = None
        # clear applied variation state
        self._applied_variation = None
        # 恢复棋盘到当前选择或末尾
        flat_len = len(self._mainline_san_flat())
        cur = self._current_selected_ply if self._current_selected_ply is not None else flat_len
        tgt = min(cur, flat_len)
        self.restore_to_ply(tgt)
        self.mark_dirty()

    def record_move_played(self, san: str):
        """
        由 BoardCanvas 在 make_move 后调用。
        逻辑：
        - 若当前选择 ply 位于主线末尾 => 直接追加到主线
        - 否则 => 录入为“当前步+1”的变着（若已有录制中的变着，则追加到该变着）
        """
        prev_sel = self._current_selected_ply
        if prev_sel is None:
            prev_sel = len(self._mainline_san_flat())
        flat_len = len(self._mainline_san_flat())

        # 在末尾继续：主线追加
        if prev_sel == flat_len:
            self.append_move_mainline(san)
            self._current_selected_ply = len(self.board.history)
            self._select_moves_row_for_ply(self._current_selected_ply)
            self.refresh_variations_box()
            self.mark_dirty()
            # 末尾走子 → 不是变着，结束任何录制
            self._building_var = None
            return

        pivot = prev_sel + 1  # 变着从下一步开始

        # —— 非末尾：录为“变着” —— #
        if self._building_var != None:
            # 继续向同一条变着追加
            cur_var = self.var_mgr.get(pivot, self._building_var[1])
            if cur_var:
                cur_var.san_moves.append(san)
                # keep comments aligned
                cur_var.san_comments.append("")
        else:
            # 新建一条变着 (让 VariationManager 生成规范名称)
            var_id = self.var_mgr.add(pivot, [san], name=san)
            self._building_var = (pivot, var_id)
            # 更新右下变着列表（显示当前 pivot 的备选）
            self.refresh_variations_box(pivot_ply=pivot)
            self._current_selected_ply = len(self.board.history)
            self._select_moves_row_for_ply(self._current_selected_ply)
            # 注意：主线不变，等待用户从变着列表中选择切换
            self.mark_dirty()
        
        # keep pivot to start of variation
        # pivot = pivot - len(self._building_var)-1        

    # ================= 菜单委托 =================
    # 文件
    def new_game(self):
        self.board = xr.Board()
        self.moves_list.clear()
        self.comments.clear()
        self.var_mgr = VariationManager()
        self._building_var = None
        self.metadata = {"title": "", "author": "", "remark": ""}
        self.selected_sq = None
        self.legal_targets = []
        self._current_selected_ply = None

        self.board_canvas.draw_board()
        self.board_canvas.update_highlights()
        self.refresh_moves_list()
        self._refresh_note_editor()
        self.refresh_variations_box()
        self.refresh_attr_panel()
        self.root.title("象棋摆谱器 - 新局")
        self.clear_dirty()

    def new_game_wizard(self):
        self.file_ops.new_game_wizard()

    def spawn_new_window(self, **kwargs):
        self.file_ops.spawn_new_window(**kwargs)

    def save_quick(self):
        self.file_ops.save_quick()

    def save_game(self):
        self.file_ops.save_game()

    def load_game(self):
        self.file_ops.load_game()

    def load_game_from_path(self, fn):
        self.file_ops.load_game_from_path(fn)

    def edit_properties(self):
        self.file_ops.edit_properties()

    def delete_current_game(self):
        self.file_ops.delete_current_game()

    def export_canvas_ps(self):
        self.file_ops.export_canvas_ps()

    def copy_fen(self):
        self.file_ops.copy_fen()

    def copy_moves_text(self):
        self.file_ops.copy_moves_text()

    def add_recent(self, path):
        self.file_ops.add_recent(path)

    def refresh_recent_submenu(self):
        self.file_ops.refresh_recent_submenu()

    def open_recent_at(self, path, index):
        self.file_ops.open_recent_at(path, index)

    def open_recent_shift(self, delta):
        self.file_ops.open_recent_shift(delta)

    # 书签
    def bookmark_add(self):
        self.bm_ops.bookmark_add()

    def bookmark_manage(self):
        self.bm_ops.bookmark_manage()

    def bookmark_jump(self):
        self.bm_ops.bookmark_jump()

    # 变换
    def flip_left_right(self):
        self.transforms.flip_left_right()

    def swap_red_black(self):
        self.transforms.swap_red_black()

    # 其它
    def about(self):
        messagebox.showinfo(
            "About",
            "Chinese Chess Learning\n"
            "- 单击棋谱任一步即可跳转到该局面\n"
            "- 跳转后继续行棋会记录为该步的“变着”（主线不改）\n"
            "- 右下变着列表用于切换主线（双击或点击“应用为主线”）"
        )

    # 退出
    def on_close(self):
        if self._dirty:
            ans = messagebox.askyesnocancel("未保存的更改", "是否保存当前更改？")
            if ans is None:
                return
            if ans:
                self.save_quick()
        # persist current UI visibility settings and window geometry
        try:
            # merge into existing settings so we don't lose other keys
            _s = read_json(SETTINGS_JSON, {})
            
            # Save the current file path if valid
            curr_file = None
            if self.file_ops.recent_files and 0 <= self.file_ops.recent_index < len(self.file_ops.recent_files):
                curr_file = self.file_ops.recent_files[self.file_ops.recent_index]

            _s.update({
                'last_open_file': curr_file,
                'board_visible': bool(self.board_visible.get()),
                'attr_visible': bool(self.attr_visible.get()),
                'notes_visible': bool(self.notes_visible.get()),
                'vari_visible': bool(self.vari_visible.get()),
            })
            try:
                self.root.update_idletasks()
                _s['geometry'] = self.root.geometry()
            except Exception:
                pass
            # save current paned window sash positions
            try:
                sashes = {}
                try:
                    if hasattr(self, 'root_paned'):
                        sashes['root_paned'] = [self.root_paned.sashpos(0)]
                except Exception:
                    pass
                try:
                    if hasattr(self, 'right_paned'):
                        sashes['right_paned'] = [self.right_paned.sashpos(0)]
                except Exception:
                    pass
                try:
                    if hasattr(self, 'lower_paned'):
                        sashes['lower_paned'] = [self.lower_paned.sashpos(0)]
                except Exception:
                    pass
                try:
                    if hasattr(self, 'right_bottom'):
                        sashes['right_bottom'] = [self.right_bottom.sashpos(0)]
                except Exception:
                    pass
                if sashes:
                    _s['pane_sashes'] = sashes
            except Exception:
                pass
            write_json(SETTINGS_JSON, _s)
        except Exception:
            pass
        self.root.destroy()

    def toggle_board_visibility(self):
        """Show or hide the left board pane (game picture)."""
        try:
            vis = bool(self.board_visible.get())
        except Exception:
            return
        try:
            if not vis:
                try:
                    self.root_paned.forget(self.board_canvas.frame)
                except Exception:
                    # best-effort: try to hide canvas inside frame
                    try:
                        self.board_canvas.canvas.pack_forget()
                    except Exception:
                        pass
            else:
                # try to insert at left (index 0) if supported, else add
                try:
                    self.root_paned.insert(0, self.board_canvas.frame, weight=3)
                except Exception:
                    try:
                        self.root_paned.add(self.board_canvas.frame, weight=3)
                    except Exception:
                        # fallback: re-pack canvas
                        try:
                            self.board_canvas.canvas.pack(fill=tk.BOTH, expand=True)
                        except Exception:
                            pass
            # refresh layout/draw
            try:
                self.board_canvas.draw_board()
            except Exception:
                pass
        except Exception:
            pass
        try:
            self._adjust_right_layout()
        except Exception:
            pass

    def toggle_attr_visibility(self):
        """Show or hide the top-right attribute panel (棋谱属性)."""
        try:
            vis = bool(self.attr_visible.get())
        except Exception:
            return
        try:
            if not vis:
                try:
                    self.right_paned.forget(self.attr_frame)
                except Exception:
                    try:
                        self.attr_frame.pack_forget()
                    except Exception:
                        pass
            else:
                try:
                    self.right_paned.insert(0, self.attr_frame, weight=1)
                except Exception:
                    try:
                        self.right_paned.add(self.attr_frame, weight=1)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            self._adjust_right_layout()
        except Exception:
            pass

    def toggle_notes_visibility(self):
        """Show or hide the notes panel (注释) in the right-bottom area."""
        try:
            vis = bool(self.notes_visible.get())
        except Exception:
            return
        try:
            if not vis:
                try:
                    self.right_bottom.forget(self.notes_frame)
                except Exception:
                    try:
                        self.notes_frame.pack_forget()
                    except Exception:
                        pass
                # if both hidden, remove the right_bottom container from lower_paned
                try:
                    if (not self.vari_visible.get()):
                        if str(self.right_bottom) in self.lower_paned.panes():
                            self.lower_paned.forget(self.right_bottom)
                except Exception:
                    pass
            else:
                # Ensure right_bottom present
                try:
                    if str(self.right_bottom) not in self.lower_paned.panes():
                        self.lower_paned.add(self.right_bottom, weight=1)
                except Exception:
                    pass
                try:
                    if str(self.notes_frame) not in self.right_bottom.panes():
                        self.right_bottom.insert(0, self.notes_frame, weight=3)
                except Exception:
                    try:
                        self.right_bottom.add(self.notes_frame, weight=3)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            self._adjust_right_layout()
        except Exception:
            pass

    def toggle_variations_visibility(self):
        """Show or hide the variations panel (变着列表) in the right-bottom area."""
        try:
            vis = bool(self.vari_visible.get())
        except Exception:
            return
        try:
            if not vis:
                try:
                    self.right_bottom.forget(self.vari_panel.frame)
                except Exception:
                    try:
                        self.vari_panel.frame.pack_forget()
                    except Exception:
                        pass
                try:
                    if (not self.notes_visible.get()):
                        if str(self.right_bottom) in self.lower_paned.panes():
                            self.lower_paned.forget(self.right_bottom)
                except Exception:
                    pass
            else:
                try:
                    if str(self.right_bottom) not in self.lower_paned.panes():
                        self.lower_paned.add(self.right_bottom, weight=1)
                except Exception:
                    pass
                try:
                    if str(self.vari_panel.frame) not in self.right_bottom.panes():
                        self.right_bottom.add(self.vari_panel.frame, weight=2)
                except Exception:
                    try:
                        self.right_bottom.insert(1, self.vari_panel.frame, weight=2)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            self._adjust_right_layout()
        except Exception:
            pass

    def _adjust_right_layout(self):
        """Adjust right-side pane weights so that when only the moves panel remains
        it expands to occupy the available space.
        """
        try:
            attr_vis = bool(self.attr_visible.get())
            notes_vis = bool(self.notes_visible.get())
            vari_vis = bool(self.vari_visible.get())

            # If no top attr and no notes/vari, make lower_paned occupy full right area
            if (not attr_vis) and (not notes_vis) and (not vari_vis):
                try:
                    self.right_paned.paneconfigure(self.lower_paned, weight=1)
                except Exception:
                    pass
                try:
                    self.lower_paned.paneconfigure(self.moves_panel.frame, weight=1)
                except Exception:
                    pass
            else:
                # Restore default weights
                try:
                    self.right_paned.paneconfigure(self.attr_frame, weight=1)
                except Exception:
                    pass
                try:
                    self.right_paned.paneconfigure(self.lower_paned, weight=3)
                except Exception:
                    pass
                try:
                    self.lower_paned.paneconfigure(self.moves_panel.frame, weight=1)
                except Exception:
                    pass
        except Exception:
            pass


# ========== 方便外部导入 ==========
__all__ = ["XiangqiGUI"]
