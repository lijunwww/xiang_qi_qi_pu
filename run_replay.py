import json
import tkinter as tk
from xiangqi_ui_all import XiangqiGUI

# Moves copied from user's test.json
moves = [
    ["炮二平五","馬8进7"],
    ["马二进三","車9平8"],
    ["车一平二","馬2进3"],
    ["兵七进一","卒7进1"],
    ["车二进六","炮8平9"],
    ["车二平三","炮9退1"],
    ["马八进七","士4进5"],
    ["马七进六","炮9平7"],
    ["车三平四","馬7进8"],
    ["马六进四","卒7进1"],
    ["车四平三","馬8退9"],
    ["卒7进2",""]
]

root = tk.Tk()
root.withdraw()

gui = XiangqiGUI(root)
# ensure fresh
gui.board = gui.board.__class__()
gui.moves_list = []

from copy import deepcopy

print("Replaying moves and logging append behavior:\n")

for idx, (rmove, bmove) in enumerate(moves, start=1):
    if rmove:
        # find matching legal move
        legal = gui.board.generate_legal_moves(gui.board.side_to_move)
        matched = None
        for mv in legal:
            cand = gui.board.move_to_chinese(mv)
            if cand == rmove or gui._normalize_san(cand) == gui._normalize_san(rmove):
                matched = mv
                break
        if not matched:
            print(f"Failed to match red move {rmove} at pair {idx}")
        else:
            san = gui.san_traditional(matched)
            print(f"Red about to play: {san}; side_to_move before move={gui.board.side_to_move}")
            gui.board.make_move(matched)
            gui.record_move_played(san)
            print(f"After append, moves_list: {gui.moves_list}")

    if bmove:
        legal = gui.board.generate_legal_moves(gui.board.side_to_move)
        matched = None
        for mv in legal:
            cand = gui.board.move_to_chinese(mv)
            if cand == bmove or gui._normalize_san(cand) == gui._normalize_san(bmove):
                matched = mv
                break
        if not matched:
            print(f"Failed to match black move {bmove} at pair {idx}")
        else:
            san = gui.san_traditional(matched)
            print(f"Black about to play: {san}; side_to_move before move={gui.board.side_to_move}")
            gui.board.make_move(matched)
            gui.record_move_played(san)
            print(f"After append, moves_list: {gui.moves_list}")

print("\nFinal moves_list:")
print(json.dumps(gui.moves_list, ensure_ascii=False, indent=2))
