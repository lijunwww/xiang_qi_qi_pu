import os
import sys
import subprocess
import json
import re
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

import chess_rules as xr
from state_utils import read_json, write_json, RECENT_JSON
from variation_mgr import VariationManager

class FileOps:
    def __init__(self, gui):
        self.gui = gui
        self.recent_files = read_json(RECENT_JSON, [])
        self.recent_index = -1

    # ---- 最近文件 ----
    def add_recent(self, path):
        if not path:
            return
        abspath = os.path.abspath(path)
        self.recent_files = [p for p in [abspath] + self.recent_files if p and os.path.exists(p)]
        uniq = []
        for p in self.recent_files:
            if p not in uniq:
                uniq.append(p)
        self.recent_files = uniq[:12]
        write_json(RECENT_JSON, self.recent_files)
        self.gui.refresh_recent_submenu()

    def refresh_recent_submenu(self):
        self.gui.recent_submenu.delete(0, 'end')
        if not self.recent_files:
            self.gui.recent_submenu.add_command(label="（空）", state='disabled')
            return
        for idx, p in enumerate(self.recent_files):
            disp = p if len(p) < 60 else ("..." + p[-57:])
            self.gui.recent_submenu.add_command(
                label=f"{idx+1}. {disp}",
                command=lambda pp=p, i=idx: self.open_recent_at(pp, i)
            )

    def open_recent_at(self, path, index):
        if not os.path.exists(path):
            messagebox.showwarning("提示", "文件不存在，已从‘最近’列表移除。")
            self.recent_files = [p for p in self.recent_files if p != path]
            write_json(RECENT_JSON, self.recent_files)
            self.gui.refresh_recent_submenu()
            return
        self.load_game_from_path(path)
        self.recent_index = index

    def open_recent_shift(self, delta):
        if not self.recent_files:
            messagebox.showinfo("提示", "暂无最近文件。")
            return
        if self.recent_index == -1:
            self.recent_index = 0
        self.recent_index = (self.recent_index + delta) % len(self.recent_files)
        self.open_recent_at(self.recent_files[self.recent_index], self.recent_index)

    # ---- 新建/打开/保存 ----
    def new_game(self):
        if messagebox.askyesno("确认", "是否开始新局？", parent=self.gui.root):
            self.gui.new_game()

    def new_game_wizard(self):
        title = simpledialog.askstring("新建向导", "棋谱标题：", parent=self.gui.root) or ""
        author = simpledialog.askstring("新建向导", "作者：", parent=self.gui.root) or ""
        side = simpledialog.askstring("新建向导", "先行方（r=红 / b=黑，默认红）：", parent=self.gui.root) or "r"
        self.gui.new_game()
        self.gui.metadata["title"] = title
        self.gui.metadata["author"] = author
        self.gui.board.side_to_move = 'r' if side.lower() != 'b' else 'b'
        self.gui.root.title(f"象棋摆谱器 - {self.gui.metadata['title'] or '新局'}")
        self.gui.refresh_attr_panel()
        self.gui.mark_dirty()

    def spawn_new_window(self, new_game=False, open_dialog=False):
        exe = sys.executable
        # Try to find main.py relative to this file's location, or current working dir
        # Assuming the structure is flat or standard
        base_dir = os.path.dirname(os.path.abspath(__file__))
        main_py = os.path.join(base_dir, "main.py")
        if not os.path.exists(main_py):
             main_py = os.path.join(os.getcwd(), "main.py")
        
        main_py = os.path.abspath(main_py)
        args = [exe, main_py]
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(args, creationflags=subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen(args)
        except Exception as e:
            messagebox.showerror("错误", f"无法启动新窗口：{e}")
            return
        if open_dialog:
            messagebox.showinfo("提示", "已打开新窗口，请在新窗口中执行‘文件-打开’。")

    def save_quick(self):
        if 0 <= self.recent_index < len(self.recent_files):
            path = self.recent_files[self.recent_index]
            self.save_to_path(path)
        else:
            self.save_game()

    def save_game(self):
        filetypes = [
            ("JSON 棋谱（主线+注释）", "*.json"),
            ("文本棋谱（主线）", "*.txt"),
            ("PGN 棋谱（主线）", "*.pgn"),
            ("CBR 棋谱", "*.cbr"),
            ("XQF 棋谱", "*.xqf"),
            ("所有文件", "*.*"),
        ]
        fn = filedialog.asksaveasfilename(defaultextension=".json", filetypes=filetypes, parent=self.gui.root)
        if not fn:
            return
        self.save_to_path(fn)
        self.add_recent(fn)
        self.recent_index = self.recent_files.index(os.path.abspath(fn))

    def save_to_path(self, fn):
        _, ext = os.path.splitext(fn)
        ext = ext.lower()
        try:
            if ext in ('.json', '.xqf', '.cbr'):
                data = {
                    "moves": self.gui.moves_list,                    # 仅主线
                    "meta": self.gui.metadata,
                    "comments": {str(k): v for k, v in self.gui.comments.items()},
                    "variations": self.gui.var_mgr.to_dict(),
                }
                write_json(fn, data)

            elif ext == '.txt':
                with open(fn, 'w', encoding='utf-8') as f:
                    for idx, (rmove, bmove) in enumerate(self.gui.moves_list, start=1):
                        r = rmove or ""
                        b = bmove or ""
                        prefix = f"{idx}.  "
                        f.write(f"{prefix}{r}\n")
                        f.write(f"{' ' * len(prefix)}{b}\n")

            elif ext == '.pgn':
                headers = [
                    f"[Event \"{self.gui.metadata.get('title', 'Chinese Chess')}\"]",
                    f"[Date \"{datetime.date.today().strftime('%Y.%m.%d')}\"]",
                    f"[Round \"*\"]",
                    f"[White \"{self.gui.metadata.get('author', '')}\"]",
                    f"[Black \"*\"]",
                    f"[Result \"*\"]",
                    f"[Remark \"{self.gui.metadata.get('remark', '')}\"]",
                    ""
                ]
                tokens = []
                for idx, (rmove, bmove) in enumerate(self.gui.moves_list, start=1):
                    if rmove:
                        tokens.append(f"{idx}. {rmove}")
                    if bmove:
                        tokens.append(f"{bmove}")
                body = ' '.join(tokens) + ' *\n'
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(headers))
                    f.write(body)

            else:
                data = {"moves": self.gui.moves_list, "meta": self.gui.metadata}
                write_json(fn, data)

            self.gui.clear_dirty()
            messagebox.showinfo('保存成功', f'已保存：{fn}', parent=self.gui.root)
        except Exception as e:
            messagebox.showerror('保存失败', str(e), parent=self.gui.root)

    def load_game(self):
        filetypes = [
            ("JSON 棋谱（主线+注释）", "*.json"),
            ("文本棋谱", "*.txt"),
            ("PGN 棋谱", "*.pgn"),
            ("CBR 棋谱", "*.cbr"),
            ("XQF 棋谱", "*.xqf"),
            ("所有文件", "*.*"),
        ]
        fn = filedialog.askopenfilename(filetypes=filetypes, parent=self.gui.root)
        if not fn:
            return
        self.load_game_from_path(fn)
        self.add_recent(fn)
        self.recent_index = self.recent_files.index(os.path.abspath(fn))

    def load_game_from_path(self, fn, silent=False):
        _, ext = os.path.splitext(fn)
        ext = ext.lower()
        try:
            if ext in ('.json', '.xqf', '.cbr'):
                with open(fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.gui.moves_list = data.get('moves', [])
                self.gui.metadata = data.get('meta', {"title": "", "author": "", "remark": ""})
                raw_comm = data.get('comments', {})
                self.gui.comments = {int(k): v for k, v in raw_comm.items()}
                # load variations (if present)
                self.gui.var_mgr = VariationManager.from_dict(data.get('variations', {}))

            elif ext == '.txt':
                moves = []
                with open(fn, 'r', encoding='utf-8') as f:
                    raw_lines = [ln.rstrip("\n") for ln in f]
                i = 0
                n = len(raw_lines)
                while i < n:
                    line = raw_lines[i].strip()
                    if not line:
                        i += 1; continue
                    m = re.match(r'^(\d+)\.\s+(.*)$', line)
                    if m:
                        rmove = (m.group(2) or "").strip()
                        bmove = ""
                        j = i + 1
                        while j < n and raw_lines[j].strip() == "":
                            j += 1
                        if j < n:
                            nxt = raw_lines[j].strip()
                            if not re.match(r'^\d+\.\s+', nxt):
                                bmove = nxt
                                i = j + 1
                            else:
                                i = i + 1
                        else:
                            i = i + 1
                        moves.append([rmove, bmove])
                        continue
                    parts = line.split('.', 1)
                    rest = parts[1].strip() if len(parts) == 2 else line
                    tokens = [t for t in rest.split() if t]
                    if tokens:
                        if len(tokens) == 1: moves.append([tokens[0], ""])
                        else: moves.append([tokens[0], tokens[1]])
                    i += 1
                self.gui.moves_list = moves
                self.gui.metadata = {"title": os.path.basename(fn), "author": "", "remark": ""}
                self.gui.comments = {}

            elif ext == '.pgn':
                with open(fn, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                lines = text.splitlines()
                # Parse headers
                meta = {"title": os.path.basename(fn), "author": "", "remark": ""}
                for ln in lines:
                    if ln.startswith('['):
                        m = re.match(r'^\[(\w+)\s+"(.*)"\]', ln)
                        if m:
                            key, val = m.group(1), m.group(2)
                            if key == "Event" and val != "Chinese Chess": meta["title"] = val
                            elif key == "Title": meta["title"] = val
                            elif key == "White" or key == "Author": meta["author"] = val
                            elif key == "Remark": meta["remark"] = val
                
                body = '\n'.join([ln for ln in lines if not ln.startswith('[')])
                body = body.replace('\\n', ' ').strip()
                body = re.sub(r'\{[^}]*\}', '', body)
                tokens = [t for t in re.split(r'\s+', body) if t]
                cur = []
                for tok in tokens:
                    if re.match(r'^\d+\.$', tok): continue
                    if tok in ('*', '1-0', '0-1', '1/2-1/2'): break
                    cur.append(tok)
                pairs = []
                for i in range(0, len(cur), 2):
                    rmove = cur[i]
                    bmove = cur[i+1] if i+1 < len(cur) else ""
                    pairs.append([rmove, bmove])
                self.gui.moves_list = pairs
                self.gui.metadata = meta
                self.gui.comments = {}

            else:
                with open(fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.gui.moves_list = data.get('moves', [])
                self.gui.metadata = data.get('meta', {"title": "", "author": "", "remark": ""})
                self.gui.comments = {}

            # 重放到棋盘（主线）
            self.gui.board = xr.Board()
            for rmove, bmove in self.gui.moves_list:
                if rmove: self.gui._play_san_force(rmove)
                if bmove: self.gui._play_san_force(bmove)

            # 复位状态/界面
            self.gui._current_selected_ply = len(self.gui.board.history)
            self.gui._building_var = None
            self.gui.board_canvas.draw_board()
            self.gui.set_selection(None)
            self.gui.refresh_moves_list()
            self.gui._refresh_note_editor()
            self.gui.refresh_variations_box()  # 刷新当前步的变着列表
            self.gui.refresh_attr_panel()
            self.gui.root.title(f"象棋摆谱器 - {self.gui.metadata.get('title') or os.path.basename(fn)}")
            self.gui.clear_dirty()
            if not silent:
                messagebox.showinfo('加载成功', f'已加载：{fn}', parent=self.gui.root)
        except Exception as e:
            messagebox.showerror('加载失败', str(e), parent=self.gui.root)

    def edit_properties(self):
        """Open a simple dialog to edit metadata (title, author, remark)."""
        dlg = tk.Toplevel(self.gui.root)
        dlg.title("编辑棋谱属性")
        dlg.transient(self.gui.root)
        dlg.grab_set()

        ttk.Label(dlg, text="标题：").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        ttk.Label(dlg, text="作者：").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        ttk.Label(dlg, text="说明：").grid(row=2, column=0, sticky="ne", padx=6, pady=4)

        var_title = tk.StringVar(value=self.gui.metadata.get("title", ""))
        var_author = tk.StringVar(value=self.gui.metadata.get("author", ""))
        ent_title = ttk.Entry(dlg, textvariable=var_title, width=48)
        ent_author = ttk.Entry(dlg, textvariable=var_author, width=48)
        ent_title.grid(row=0, column=1, sticky="we", padx=6, pady=4)
        ent_author.grid(row=1, column=1, sticky="we", padx=6, pady=4)

        txt_remark = tk.Text(dlg, width=48, height=6)
        txt_remark.insert("1.0", self.gui.metadata.get("remark", ""))
        txt_remark.grid(row=2, column=1, sticky="we", padx=6, pady=4)

        def on_save():
            self.gui.metadata["title"] = var_title.get().strip()
            self.gui.metadata["author"] = var_author.get().strip()
            self.gui.metadata["remark"] = txt_remark.get("1.0", "end").strip()
            # update main UI fields if present
            try:
                self.gui.var_title.set(self.gui.metadata["title"])
                self.gui.var_author.set(self.gui.metadata["author"])
                self.gui.txt_remark.delete("1.0", "end")
                self.gui.txt_remark.insert("1.0", self.gui.metadata["remark"])
                self.gui.root.title(f"象棋摆谱器 - {self.gui.metadata.get('title') or '未命名'}")
            except Exception:
                pass
            self.gui.mark_dirty()
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        btns = ttk.Frame(dlg)
        btns.grid(row=3, column=1, sticky="e", pady=(2,8), padx=6)
        ttk.Button(btns, text="保存", command=on_save).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btns, text="取消", command=on_cancel).pack(side=tk.RIGHT, padx=4)

        dlg.columnconfigure(1, weight=1)
        ent_title.focus_set()
        self.gui.root.wait_window(dlg)
    
    # Delegate methods that were previously in main_ui but logically belong here or are wrappers
    def delete_current_game(self):
        # Implementation for delete current game logic if it was intended to delete file
        # Based on previous code, there was no implementation shown in the snippet for `delete_current_game` inside FileOps
        # but it was called from `xiangqi_ui_all.py`.
        # Assuming we just clear the board for now as "delete" from view, 
        # or if it means deleting the file from disk:
        if not self.gui.file_ops.recent_files:
             messagebox.showinfo("提示", "没有打开的文件。")
             return
        
        # This seems to be "Close" or "Delete file". Let's assume it deletes the file as per name.
        # However, looking at the code I read, I didn't see the logic for `delete_current_game` in FileOps class in the snippet.
        # It was called in lines 2400+.
        # I'll implement a safe version that asks for confirmation.
        
        # Update: In line 257 of original file: `file_menu.add_command(label="删除当前棋谱(D)", command=gui.delete_current_game)`
        # And gui.delete_current_game calls `self.file_ops.delete_current_game()`.
        # But I didn't see `delete_current_game` method in `FileOps` class in the view_file output of lines 800-1117.
        # Wait, let me double check the `FileOps` class content I read.
        pass

    def export_canvas_ps(self):
        fn = filedialog.asksaveasfilename(defaultextension=".ps", filetypes=[("PostScript", "*.ps")], parent=self.gui.root)
        if fn:
            try:
                self.gui.board_canvas.canvas.postscript(file=fn, colormode='color')
                messagebox.showinfo("成功", f"已导出截图：{fn}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败：{e}")

    def copy_fen(self):
        try:
            fen = self.gui.board.to_fen()
            self.gui.root.clipboard_clear()
            self.gui.root.clipboard_append(fen)
            messagebox.showinfo("复制成功", "当前局面 FEN 已复制到剪贴板。")
        except Exception:
            pass

    def copy_moves_text(self):
        try:
            lines = []
            for idx, (rmove, bmove) in enumerate(self.gui.moves_list, start=1):
                r = rmove or ""
                b = bmove or ""
                lines.append(f"{idx}. {r}  {b}")
            text = "\n".join(lines)
            self.gui.root.clipboard_clear()
            self.gui.root.clipboard_append(text)
            messagebox.showinfo("复制成功", "棋谱文本已复制到剪贴板。")
        except Exception:
            pass

    def delete_current_game(self):
        """Deletes the current game file from disk."""
        if self.recent_index < 0 or self.recent_index >= len(self.recent_files):
             messagebox.showinfo("提示", "当前未关联到磁盘文件，无法删除。")
             return
        path = self.recent_files[self.recent_index]
        if messagebox.askyesno("删除确认", f"确定要彻底删除文件吗？\n{path}", parent=self.gui.root):
            try:
                os.remove(path)
                # Remove from recent
                self.recent_files = [p for p in self.recent_files if p != path]
                write_json(RECENT_JSON, self.recent_files)
                self.refresh_recent_submenu()
                self.gui.new_game() # Reset board
                messagebox.showinfo("已删除", "文件已删除。")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败：{e}")
