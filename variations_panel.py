import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

class VariationPanel:
    """右下“变着列表”（仅用于切换主线；双击应用）"""
    def __init__(self, gui, parent):
        self.gui = gui
        self.frame = ttk.Frame(parent)

        self.lbl = ttk.Label(self.frame, text="变着列表（第 ? 步）", font=("Microsoft YaHei", 10, "bold"))
        self.lbl.pack(anchor=tk.W, padx=6, pady=(6, 2))

        box = ttk.Frame(self.frame)
        box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        # Use a Treeview to display nested variations with expand/collapse
        self.tree = ttk.Treeview(box, show='tree')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar = ttk.Scrollbar(box, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        btns = ttk.Frame(self.frame)
        btns.pack(fill=tk.X, padx=6, pady=(0, 8))
        self.btn_apply = ttk.Button(btns, text="应用为主线", command=self._apply_selected)
        self.btn_apply.pack(side=tk.RIGHT, padx=4)
        # 新增：恢复主线按钮
        self.btn_restore = ttk.Button(btns, text="恢复主线", command=self._restore_mainline)
        self.btn_restore.pack(side=tk.RIGHT, padx=4)
        self.btn_delete = ttk.Button(btns, text="删除", command=self._delete_selected)
        self.btn_delete.pack(side=tk.RIGHT, padx=4)
        self.btn_edit_comments = ttk.Button(btns, text="编辑注释", command=self._edit_selected_comments)
        self.btn_edit_comments.pack(side=tk.RIGHT, padx=4)
        self.btn_view = ttk.Button(btns, text="查看变着", command=self._toggle_view_selected)
        self.btn_view.pack(side=tk.RIGHT, padx=4)

        self.tree.bind("<Double-1>", lambda e: self._apply_selected())

        self._cur_pivot = None   # 当前面板显示的 pivot_ply

    def refresh_for_pivot(self, pivot_ply: int):
        """根据 pivot_ply （从1开始）刷新变着列表"""
        self._cur_pivot = pivot_ply
        # clear tree
        for it in self.tree.get_children():
            self.tree.delete(it)  # Clear existing items in the tree
        self.lbl.config(text=f"变着列表（第 {pivot_ply} 步）")
        vs = self.gui.var_mgr.list(pivot_ply)

        def _insert_node(parent_iid, node):
            iid = str(node.var_id)
            text = f"[{node.var_id}] {node.name}"
            try:
                self.tree.insert(parent_iid, 'end', iid=iid, text=text)
            except Exception:
                # fallback: let tree generate iid
                iid = self.tree.insert(parent_iid, 'end', text=text)
            # children: node.children is {pivot_index: [VariationNode]}
            for pivot_index in sorted(node.children.keys()):
                for child in node.children[pivot_index]:
                    _insert_node(iid, child)

        for v in vs:
            _insert_node('', v)

    def _selected_var_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        try:
            return int(iid)
        except Exception:
            # fallback: parse displayed text
            text = self.tree.item(iid, 'text')
            try:
                return int(text.split(']')[0].lstrip('['))
            except Exception:
                return None

    def _apply_selected(self):
        var_id = self._selected_var_id()
        if var_id is None or self._cur_pivot is None:
            return  # No variation selected or current pivot is None
        self.gui.apply_variation_by_id(self._cur_pivot, var_id)

    def _restore_mainline(self):
        try:
            self.gui.restore_mainline()  # Restore the main line from variations
        except Exception:
            pass

    def _edit_selected_comments(self):
        var_id = self._selected_var_id()
        if var_id is None:
            return
        node = self.gui.var_mgr.find_by_id(var_id)
        if node is None:
            return

        dlg = tk.Toplevel(self.frame)
        dlg.title(f"编辑变着注释 - {node.name}")
        dlg.transient(self.frame)
        dlg.grab_set()

        # list moves with a text box per half-move
        rows = []
        for i, san in enumerate(node.san_moves, start=1):
            lbl = ttk.Label(dlg, text=f"{i}. {san}")
            lbl.grid(row=(i-1)*2, column=0, sticky="w", padx=6, pady=(6,0))
            txt = tk.Text(dlg, width=60, height=3)
            txt.grid(row=(i-1)*2+1, column=0, padx=6, pady=(0,6))
            # prefill
            try:
                txt.insert("1.0", node.san_comments[i-1])
            except Exception:
                pass
            rows.append(txt)

        def on_save():
            try:
                node.san_comments = [t.get("1.0", "end").strip() for t in rows]
                self.gui.mark_dirty()
                dlg.destroy()
                messagebox.showinfo("已保存", "已保存变着注释。", parent=self.gui.root)
            except Exception:
                messagebox.showwarning("保存失败", "无法保存变着注释。", parent=self.gui.root)

        btn = ttk.Frame(dlg)
        btn.grid(row=len(rows)*2, column=0, sticky="e", padx=6, pady=6)
        ttk.Button(btn, text="保存", command=on_save).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn, text="取消", command=dlg.destroy).pack(side=tk.RIGHT, padx=4)

    def _toggle_view_selected(self):
        var_id = self._selected_var_id()
        if var_id is None or self._cur_pivot is None:
            return
        cur = getattr(self.gui, '_viewing_variation', None)
        if cur and cur[0] == self._cur_pivot and cur[1] == var_id:
            # cancel viewing
            self.gui._viewing_variation = None
            # update UI
            try:
                self.lbl.config(text=f"变着列表（第 {self._cur_pivot} 步）", foreground="black")
                self.btn_view.config(text="查看变着")
                self.tree.selection_remove(str(var_id))
            except Exception:
                pass
        else:
            self.gui._viewing_variation = (self._cur_pivot, var_id)
            # update UI: show which variation is being viewed and select it
            node = self.gui.var_mgr.find_by_id(var_id)
            try:
                name = node.name if node is not None else str(var_id)
                self.lbl.config(text=f"查看变着：{name}（第 {self._cur_pivot} 步）", foreground="#0066CC")
                # select and ensure visibility
                try:
                    self.tree.selection_set(str(var_id))
                    self.tree.see(str(var_id))
                except Exception:
                    pass
                self.btn_view.config(text="取消查看")
            except Exception:
                pass
        # refresh note editor to show appropriate comments
        try:
            self.gui._refresh_note_editor()
        except Exception:
            pass

    def _delete_selected(self):
        var_id = self._selected_var_id()
        if var_id is None or self._cur_pivot is None:
            return
        if messagebox.askyesno("删除变着", "确认删除选中变着？", parent=self.gui.root):
            if self.gui.var_mgr.remove(self._cur_pivot, var_id):
                self.refresh_for_pivot(self._cur_pivot)
