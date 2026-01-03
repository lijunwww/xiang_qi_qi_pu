import tkinter as tk

def create_menubar(gui):
    menubar = tk.Menu(gui.root)

    # ================= 文件 =================
    file_menu = tk.Menu(menubar, tearoff=False)
    file_menu.add_command(label="新建(N)", command=gui.new_game)
    file_menu.add_command(label="新建向导(W)...", command=gui.new_game_wizard)
    file_menu.add_command(label="新建到新窗口(Y)", command=lambda: gui.spawn_new_window(new_game=True))
    file_menu.add_separator()
    file_menu.add_command(label="打开(O)...", command=gui.load_game)
    file_menu.add_command(label="打开到新窗口(Z)...", command=lambda: gui.spawn_new_window(open_dialog=True))
    file_menu.add_separator()
    file_menu.add_command(label="保存(S)", command=gui.save_quick)
    file_menu.add_command(label="另存为(E/F)...", command=gui.save_game)
    file_menu.add_separator()
    file_menu.add_command(label="棋谱属性(P)...", command=gui.edit_properties)
    file_menu.add_command(label="删除当前棋谱(D)", command=gui.delete_current_game)
    file_menu.add_separator()
    file_menu.add_command(label="打开前一局(←)", command=lambda: gui.open_recent_shift(-1))
    file_menu.add_command(label="打开后一局(→)", command=lambda: gui.open_recent_shift(+1))

    gui.recent_submenu = tk.Menu(file_menu, tearoff=False)
    gui.refresh_recent_submenu()
    file_menu.add_cascade(label="最近打开(H)", menu=gui.recent_submenu)
    file_menu.add_separator()
    file_menu.add_command(label="退出(X)", command=gui.on_close)
    menubar.add_cascade(label="文件(F)", menu=file_menu)

    # Also add direct Alt+letter bindings for common file actions (fallback for Alt+F then letter)
    try:
        gui.root.bind_all('<Alt-o>', lambda e: gui.load_game())
        gui.root.bind_all('<Alt-O>', lambda e: gui.load_game())
        gui.root.bind_all('<Alt-n>', lambda e: gui.new_game())
        gui.root.bind_all('<Alt-N>', lambda e: gui.new_game())
        gui.root.bind_all('<Alt-s>', lambda e: gui.save_quick())
        gui.root.bind_all('<Alt-S>', lambda e: gui.save_quick())
        gui.root.bind_all('<Alt-x>', lambda e: gui.on_close())
        gui.root.bind_all('<Alt-X>', lambda e: gui.on_close())
    except Exception:
        pass

    # ================= 编辑 =================
    edit_menu = tk.Menu(menubar, tearoff=False)
    edit_menu.add_command(label="撤销(U)    Ctrl+Z", command=gui.undo)
    edit_menu.add_command(label="重做(R)    Ctrl+Y", command=gui.redo)
    edit_menu.add_separator()
    edit_menu.add_command(label="复制棋谱文本(Q)", command=gui.copy_moves_text)
    edit_menu.add_command(label="复制 FEN", command=gui.copy_fen)
    edit_menu.add_command(label="导出棋盘图形(PS)...", command=gui.export_canvas_ps)
    edit_menu.add_separator()
    edit_menu.add_command(label="删除最后一步(Del)", command=gui.delete_last_move)
    edit_menu.add_command(label="左右交换(M)", command=gui.flip_left_right)
    edit_menu.add_command(label="红黑对调(A)", command=gui.swap_red_black)
    menubar.add_cascade(label="编辑(E)", menu=edit_menu)

    # ================= 视图 / View =================
    view_menu = tk.Menu(menubar, tearoff=False)
    # show accelerators in labels and bind shortcuts to toggle handlers
    view_menu.add_checkbutton(label="显示棋盘\tCtrl+B", variable=gui.board_visible, command=gui.toggle_board_visibility)
    view_menu.add_separator()
    view_menu.add_checkbutton(label="显示棋谱属性\tCtrl+P", variable=gui.attr_visible, command=gui.toggle_attr_visibility)
    view_menu.add_checkbutton(label="显示注释\tCtrl+N", variable=gui.notes_visible, command=gui.toggle_notes_visibility)
    view_menu.add_checkbutton(label="显示变着列表\tCtrl+L", variable=gui.vari_visible, command=gui.toggle_variations_visibility)
    # Bind shortcuts
    try:
        gui.root.bind_all('<Control-b>', lambda e: (gui.board_visible.set(not gui.board_visible.get()), gui.toggle_board_visibility()))
        gui.root.bind_all('<Control-B>', lambda e: (gui.board_visible.set(not gui.board_visible.get()), gui.toggle_board_visibility()))
        gui.root.bind_all('<Control-p>', lambda e: (gui.attr_visible.set(not gui.attr_visible.get()), gui.toggle_attr_visibility()))
        gui.root.bind_all('<Control-P>', lambda e: (gui.attr_visible.set(not gui.attr_visible.get()), gui.toggle_attr_visibility()))
        gui.root.bind_all('<Control-n>', lambda e: (gui.notes_visible.set(not gui.notes_visible.get()), gui.toggle_notes_visibility()))
        gui.root.bind_all('<Control-N>', lambda e: (gui.notes_visible.set(not gui.notes_visible.get()), gui.toggle_notes_visibility()))
        gui.root.bind_all('<Control-l>', lambda e: (gui.vari_visible.set(not gui.vari_visible.get()), gui.toggle_variations_visibility()))
        gui.root.bind_all('<Control-L>', lambda e: (gui.vari_visible.set(not gui.vari_visible.get()), gui.toggle_variations_visibility()))
    except Exception:
        pass
    menubar.add_cascade(label="视图(V)", menu=view_menu)

    # ================= 书签 =================
    bm_menu = tk.Menu(menubar, tearoff=False)
    bm_menu.add_command(label="添加书签(M)", command=gui.bookmark_add)
    bm_menu.add_command(label="管理书签...", command=gui.bookmark_manage)
    bm_menu.add_command(label="跳转到书签...", command=gui.bookmark_jump)
    menubar.add_cascade(label="书签(M)", menu=bm_menu)

    # ================= 帮助 =================
    help_menu = tk.Menu(menubar, tearoff=False)
    help_menu.add_command(label="关于", command=gui.about)
    menubar.add_cascade(label="帮助(H)", menu=help_menu)

    # build a mapping from top-level menu label -> { key: callable }
    try:
        gui._menu_mnemonics = {
            '文件(F)': {
                'n': gui.new_game,
                'w': gui.new_game_wizard,
                'y': lambda: gui.spawn_new_window(new_game=True),
                'o': gui.load_game,
                'z': lambda: gui.spawn_new_window(open_dialog=True),
                's': gui.save_quick,
                'e': gui.save_game,
                'f': gui.save_game,
                'p': gui.edit_properties,
                'd': gui.delete_current_game,
                'x': gui.on_close
            },
            '编辑(E)': {
                'z': gui.undo,
                'u': gui.undo,
                'r': gui.redo
            },
            '视图(V)': {
                'b': gui.toggle_board_visibility,
                'p': gui.toggle_attr_visibility,
                'n': gui.toggle_notes_visibility,
                'l': gui.toggle_variations_visibility
            },
            '书签(M)': {
                'm': gui.bookmark_add
            },
            '帮助(H)': {
                # no mnemonic actions by default
            }
        }
    except Exception:
        gui._menu_mnemonics = {}

    return menubar
