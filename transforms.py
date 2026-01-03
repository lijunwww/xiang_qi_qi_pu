import chess_rules as xr

class Transforms:
    def __init__(self, gui):
        self.gui = gui

    def flip_left_right(self):
        new_board = xr.Board()
        new_board.history.clear()
        for r in range(10):
            for c in range(9):
                p = self.gui.board.piece_at((r, c))
                if p:
                    new_board.set_piece((r, 8 - c), xr.Piece(p.color, p.ptype, pid=p.pid))
                else:
                    new_board.set_piece((r, 8 - c), None)
        new_board.side_to_move = self.gui.board.side_to_move
        self.gui.board = new_board
        self.gui.board_canvas.draw_board()
        self.gui.set_selection(None)
        self.gui.refresh_moves_list()
        self.gui.refresh_variations_box()
        self.gui.mark_dirty()

    def swap_red_black(self):
        new_board = xr.Board()
        new_board.history.clear()
        for r in range(10):
            for c in range(9):
                p = self.gui.board.piece_at((r, c))
                if p:
                    new_color = 'b' if p.color == 'r' else 'r'
                    new_board.set_piece((9 - r, 8 - c), xr.Piece(new_color, p.ptype, pid=p.pid))
                else:
                    new_board.set_piece((9 - r, 8 - c), None)
        new_board.side_to_move = 'b' if self.gui.board.side_to_move == 'r' else 'r'
        self.gui.board = new_board
        self.gui.board_canvas.draw_board()
        self.gui.set_selection(None)
        self.gui.refresh_moves_list()
        self.gui.refresh_variations_box()
        self.gui.mark_dirty()
