import os
import json
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog

import chess_rules as xr
import draw_board as db
from state_utils import read_json, write_json, BOOKMARK_JSON

class BookmarkOps:
    def __init__(self, gui):
        self.gui = gui
        self.bookmarks = read_json(BOOKMARK_JSON, {})  # {file_key: [{name, ply}, ...]}

    def file_key(self):
        if 0 <= self.gui.file_ops.recent_index < len(self.gui.file_ops.recent_files):
            return os.path.abspath(self.gui.file_ops.recent_files[self.gui.file_ops.recent_index])
        return f"__MEM__:{self.gui.metadata.get('title','新局')}"

    def current_ply(self):
        return len(self.gui.board.history)

    def bookmark_add(self):
        name = simpledialog.askstring("添加书签", "书签名称：", parent=self.gui.root)
        if not name:
            return
        fk = self.file_key()
        self.bookmarks.setdefault(fk, [])
        self.bookmarks[fk].append({"name": name, "ply": self.current_ply()})
        write_json(BOOKMARK_JSON, self.bookmarks)
        messagebox.showinfo("成功", "书签已添加。")

    def bookmark_manage(self):
        fk = self.file_key()
        items = self.bookmarks.setdefault(fk, [])

        dlg = tk.Toplevel(self.gui.root)
        dlg.title("管理书签")
        dlg.transient(self.gui.root)
        dlg.grab_set()

        frm = ttk.Frame(dlg)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        lbl = ttk.Label(frm, text=f"当前棋谱：{os.path.basename(fk)}  共 {len(items)} 个书签")
        lbl.pack(anchor="w")

        body = ttk.Frame(frm)
        body.pack(fill=tk.BOTH, expand=True, pady=(6,4))

        listbox = tk.Listbox(body, width=38, height=12)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # preview canvas at right
        preview_frame = ttk.Frame(body)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8,0))
        preview_lbl = ttk.Label(preview_frame, text="预览")
        preview_lbl.pack()
        preview_canvas = tk.Canvas(preview_frame, width=220, height=220, bg='#DEB887')
        preview_canvas.pack(pady=(4,0))

        def refresh_list():
            listbox.delete(0, tk.END)
            for i, it in enumerate(items, start=1):
                name = it.get('name','')
                ply = it.get('ply', 0)
                listbox.insert(tk.END, f"{i}. {name} (ply={ply})")
            lbl.config(text=f"当前棋谱：{os.path.basename(fk)}  共 {len(items)} 个书签")

        def on_add():
            name = simpledialog.askstring("添加书签", "书签名称：", parent=dlg)
            if not name:
                return
            ply = simpledialog.askinteger("半步数", "跳转到的半步数 (ply)：", parent=dlg, initialvalue=self.current_ply())
            if ply is None:
                return
            items.append({"name": name, "ply": int(ply)})
            write_json(BOOKMARK_JSON, self.bookmarks)
            refresh_list()

        def on_edit():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("提示", "请先选择一个书签。", parent=dlg)
                return
            idx = sel[0]
            cur = items[idx]
            new_name = simpledialog.askstring("编辑书签", "名称：", parent=dlg, initialvalue=cur.get('name',''))
            if new_name is None:
                return
            new_ply = simpledialog.askinteger("编辑半步数", "半步数 (ply)：", parent=dlg, initialvalue=cur.get('ply', 0))
            if new_ply is None:
                return
            cur['name'] = new_name
            cur['ply'] = int(new_ply)
            write_json(BOOKMARK_JSON, self.bookmarks)
            refresh_list()

        def on_move_up():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx <= 0:
                return
            items[idx-1], items[idx] = items[idx], items[idx-1]
            write_json(BOOKMARK_JSON, self.bookmarks)
            refresh_list()
            listbox.selection_set(idx-1)

        def on_move_down():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(items)-1:
                return
            items[idx+1], items[idx] = items[idx], items[idx+1]
            write_json(BOOKMARK_JSON, self.bookmarks)
            refresh_list()
            listbox.selection_set(idx+1)

        def on_rename():
            # Already handled in on_edit, but if separate button needed:
            # Reusing on_edit logic partially
            pass 

        def on_delete():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("提示", "请先选择一个书签。", parent=dlg)
                return
            idx = sel[0]
            if not messagebox.askyesno("确认", "确认删除选中书签？", parent=dlg):
                return
            items.pop(idx)
            write_json(BOOKMARK_JSON, self.bookmarks)
            refresh_list()

        def on_import():
            fn = filedialog.askopenfilename(filetypes=[('JSON', '*.json'), ('All', '*.*')], parent=dlg)
            if not fn:
                return
            try:
                with open(fn, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    # expect list of {name, ply}
                    for it in data:
                        if 'name' in it and 'ply' in it:
                            items.append({'name': str(it['name']), 'ply': int(it['ply'])})
                elif isinstance(data, dict):
                    # try to accept full bookmarks file
                    for fk_load, lst in data.items():
                        if isinstance(lst, list):
                            for it in lst:
                                if 'name' in it and 'ply' in it:
                                    items.append({'name': str(it['name']), 'ply': int(it['ply'])})
                write_json(BOOKMARK_JSON, self.bookmarks)
                refresh_list()
                messagebox.showinfo('导入成功', '已导入书签。', parent=dlg)
            except Exception as e:
                messagebox.showwarning('导入失败', str(e), parent=dlg)

        def on_jump():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("提示", "请先选择一个书签。", parent=dlg)
                return
            idx = sel[0]
            ply = items[idx].get('ply', 0)
            self._restore_to_ply(ply)
            dlg.destroy()

        def on_export():
            # export current file's bookmarks as JSON to clipboard
            try:
                txt = json.dumps(items, ensure_ascii=False, indent=2)
                try:
                    self.gui.root.clipboard_clear()
                    self.gui.root.clipboard_append(txt)
                    messagebox.showinfo("已复制", "已将书签以 JSON 复制到剪贴板。", parent=dlg)
                except Exception:
                    # fallback: save to file
                    fn = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')], parent=dlg)
                    if fn:
                        with open(fn, 'w', encoding='utf-8') as f:
                            f.write(txt)
                        messagebox.showinfo("已保存", f"已保存到：{fn}", parent=dlg)
            except Exception as e:
                messagebox.showwarning("导出失败", str(e), parent=dlg)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(4,0))
        left_group = ttk.Frame(btns)
        left_group.pack(side=tk.LEFT)
        ttk.Button(left_group, text="添加", command=on_add).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_group, text="编辑", command=on_edit).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_group, text="上移", command=on_move_up).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_group, text="下移", command=on_move_down).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_group, text="删除", command=on_delete).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_group, text="导入", command=on_import).pack(side=tk.LEFT, padx=4)
        ttk.Button(left_group, text="导出", command=on_export).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="关闭", command=dlg.destroy).pack(side=tk.RIGHT, padx=4)

        def on_select(evt=None):
            sel = listbox.curselection()
            if not sel:
                # clear preview
                preview_canvas.delete('all')
                return
            idx = sel[0]
            ply = items[idx].get('ply', 0)
            # render preview board for this ply
            try:
                tmp_board = xr.Board()
                # build flattened san list
                flat = []
                for r,b in self.gui.moves_list:
                    if r: flat.append(r)
                    if b: flat.append(b)
                for m in flat[:ply]:
                    try:
                        tmp_board.play_san(m)
                    except Exception:
                        # best-effort, ignore failures
                        pass
                # prepare db.board_data from tmp_board
                for r in range(db.BOARD_ROWS):
                    for c in range(db.BOARD_COLS):
                        piece = tmp_board.piece_at((r,c))
                        db.board_data[r][c] = '.' if piece is None else (piece.ptype.upper() if piece.color == 'r' else piece.ptype.lower())
                # draw on preview canvas with temporary size
                old_size = db.SQUARE_SIZE
                try:
                    db.SQUARE_SIZE = min(32, old_size)
                    db.draw_board(preview_canvas, self.gui.piece_font)
                finally:
                    db.SQUARE_SIZE = old_size
            except Exception:
                preview_canvas.delete('all')

        listbox.bind('<Double-1>', lambda e: on_jump())
        listbox.bind('<<ListboxSelect>>', on_select)
        refresh_list()
        listbox.focus_set()
        self.gui.root.wait_window(dlg)

    def bookmark_jump(self):
        fk = self.file_key()
        items = self.bookmarks.get(fk, [])
        if not items:
            messagebox.showinfo("提示", "暂无书签。")
            return
        idx = simpledialog.askinteger("跳转到书签", f"共有 {len(items)} 个书签，输入序号(1~{len(items)})：", parent=self.gui.root)
        if not idx or not (1 <= idx <= len(items)):
            return
        ply = items[idx-1]["ply"]
        self._restore_to_ply(ply)

    def _restore_to_ply(self, ply):
        self.gui.restore_to_ply(ply)
