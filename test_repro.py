
import chess_rules as xr

def normalize_san(s):
    if not s: return ""
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

class MockGUI:
    def __init__(self):
        self.board = xr.Board()
        self.moves_list = []
    
    def play_san(self, san_str: str):
        target = normalize_san(san_str)
        legal = self.board.generate_legal_moves(self.board.side_to_move)
        for mv in legal:
            cand = self.board.move_to_chinese(mv)
            if cand == san_str or normalize_san(cand) == target:
                self.board.make_move(mv)
                return
        print(f"FAILED to play {san_str}")
        raise ValueError(f"No match for {san_str}")

    def _play_san_force(self, san):
        try:
            self.play_san(san)
        except:
            pass

    def restore_to_ply(self, ply):
        print(f"--- Restore to {ply} ---")
        self.board = xr.Board()
        cur = 0
        for rmove, bmove in self.moves_list:
            if cur >= ply: break
            if rmove:
                if cur >= ply: break
                print(f"Playing Red: {rmove} (cur={cur})")
                self._play_san_force(rmove); cur += 1
            if bmove:
                if cur >= ply: break
                print(f"Playing Black: {bmove} (cur={cur})")
                self._play_san_force(bmove); cur += 1
        print(f"Result Board History Len: {len(self.board.history)}")
        if len(self.board.history) == 0:
            print("BOARD IS EMPTY (Start State)")

def test():
    gui = MockGUI()
    # Simulate: 1. 炮二平五 炮8平5  2. 马二进三
    # Moves: [["炮二平五", "炮8平5"], ["马二进三", ""]]
    gui.moves_list = [["炮二平五", "炮8平5"], ["马二进三", ""]]
    
    # Test Ply 1
    gui.restore_to_ply(1)
    
    # Test Ply 2
    gui.restore_to_ply(2)
    
    # Test Ply 3
    gui.restore_to_ply(3)

if __name__ == "__main__":
    test()
