from itertools import groupby
from copy import deepcopy

from . import pieces
import re


class ChessError(Exception): pass
class InvalidCoord(ChessError): pass
class InvalidColor(ChessError): pass
class InvalidMove(ChessError): pass
class Check(ChessError): pass
class CheckMate(ChessError): pass
class Draw(ChessError): pass
class NotYourTurn(ChessError): pass


FEN_STARTING = '4k2r/8/8/8/8/8/3PP3/4K3 w KQkq - 0 1'
RANK_REGEX = re.compile(r"^[A-Z][1-8]$")


class Board(dict):
    '''
       Board

       A simple chessboard class

       TODO:

        * PGN export
        * En passant (Done TJS)
        * Castling (Done TJS)
        * Promoting pawns (Done TJS)
        * 3-time repition (Done TJS)
        * Fifty-move rule
        * Take-backs
        * row/column lables
        * captured piece imbalance (show how many pawns pieces player is up)
    '''

    axis_y = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H')
    axis_x = tuple(range(1, 9))  # (1,2,3,...8)

    captured_pieces = { 'white': [], 'black': [] }
    player_turn = None

    halfmove_clock = 0
    fullmove_number = 1

    def __init__(self, fen = None):
        if fen is None: self.load(FEN_STARTING)
        else: self.load(fen)
        self.last_move = None ## to support en passent
        self.positions = [None]
        
    def __getitem__(self, coord):
        if isinstance(coord, str):
            coord = coord.upper()
            if not re.match(RANK_REGEX, coord.upper()): raise KeyError
        elif isinstance(coord, tuple):
            coord = self.letter_notation(coord)
        try:
            return super(Board, self).__getitem__(coord)
        except KeyError:
            return None

    def save_to_file(self): pass

    def is_in_check_after_move(self, p1, p2):
        # Create a temporary board
        tmp = deepcopy(self)
        tmp._do_move(p1, p2)
        return tmp.is_in_check(self[p1].color)

    def move(self, p1, p2, promote='r'):
        p1, p2 = p1.upper(), p2.upper()
        piece = self[p1]
        dest  = self[p2]

        if self.player_turn != piece.color:
            raise NotYourTurn("Not " + piece.color + "'s turn!")

        enemy = self.get_enemy(piece.color)
        possible_moves = piece.possible_moves(p1)
        # 0. Check if p2 is in the possible moves
        if p2 not in possible_moves:
            raise InvalidMove
        
        # If enemy has any moves look for check
        if self.all_possible_moves(enemy):
            if self.is_in_check_after_move(p1, p2):
                raise Check
        if not possible_moves and self.is_in_check(piece.color):
            raise CheckMate
        elif not possible_moves:
            raise Draw
        else:
            self._do_move(p1, p2, promote)
            self._finish_move(piece, dest, p1,p2)
            if self.positions[-1] in self.positions[:-1]:
                count = 1
                for position in self.positions[:-1]:
                    count += (position == self.positions[-1])
                print('repetition count:', count)
                if count >= 3:
                    raise Draw

    def get_enemy(self, color):
        if color == "white":
            return "black"
        else:
            return "white"

    def _do_move(self, p1, p2, promote='r'):
        '''
            Move a piece without validation
        '''
        piece = self[p1]
        dest  = self[p2]

        # if piece is a king and move is a castle, move the rook too

        del self[p1]
        self.last_move = (p1, p2)
        # check pawn promotion

        if self.is_pawn(piece) and p2[1] in '18':
            piece = pieces.Pieces[promote.upper()](piece.color)
            piece.board = self
        self[p2] = piece

        # for three-fold repetition

        fen = self.export().split()
        self.positions.append(fen[0] + fen[1])

    def _finish_move(self, piece, dest, p1, p2):
        '''
            Set next player turn, count moves, log moves, etc.
        '''
        enemy = self.get_enemy(piece.color)
        if piece.color == 'black':
            self.fullmove_number += 1
        self.halfmove_clock +=1
        self.player_turn = enemy
        abbr = piece.abbreviation
        if abbr == 'P':
            # Pawn has no letter
            abbr = ''
            # Pawn resets halfmove_clock
            self.halfmove_clock = 0
        if dest is None:
            # No capturing
            movetext = abbr +  p2.lower()
        else:
            # Capturing
            movetext = abbr + 'x' + p2.lower()
            # Capturing resets halfmove_clock
            self.halfmove_clock = 0

    def all_possible_moves(self, color):
        '''
            Return a list of `color`'s possible moves.
            Does not check for check.
        '''
        if(color not in ("black", "white")): raise InvalidColor
        result = []
        for coord in list(self.keys()):
            if (self[coord] is not None) and self[coord].color == color:
                moves = self[coord].possible_moves(coord)
                if moves: result += moves
        return result

    def occupied(self, color):
        '''
            Return a list of coordinates occupied by `color`
        '''
        result = []
        if(color not in ("black", "white")): raise InvalidColor

        for coord in self:
            if self[coord].color == color:
                result.append(coord)
        return result

    def is_king(self, piece):
        return isinstance(piece, pieces.King)

    def is_rook(self, piece):
        return isinstance(piece, pieces.Rook)

    def is_pawn(self, piece):
        return isinstance(piece, pieces.Pawn)


    def get_king_position(self, color):
        for pos in list(self.keys()):
            if self.is_king(self[pos]) and self[pos].color == color:
                return pos

    def get_king(self, color):

        if color not in ("black", "white"):
            raise InvalidColor
        return self[self.get_king_position(color)]

    def is_in_check(self, color):
        if color not in ("black", "white"):
            raise InvalidColor
        king = self.get_king(color)
        enemy = self.get_enemy(color)
        return king in list(map(self.__getitem__, self.all_possible_moves(enemy)))

    def letter_notation(self,coord):
        if not self.is_in_bounds(coord): return
        try:
            return self.axis_y[int(coord[1])] + str(self.axis_x[int(coord[0])])
        except IndexError:
            raise InvalidCoord

    def number_notation(self, coord):
        return int(coord[1])-1, self.axis_y.index(coord[0])

    def is_in_bounds(self, coord):
        if coord[1] < 0 or coord[1] > 7 or\
           coord[0] < 0 or coord[0] > 7:
            return False
        else:
            return True

    def clear(self):
        dict.clear(self)
        self.positions = [None]
        
    def load(self, fen):
        '''
            Import state from FEN notation
        '''
        self.clear()
        # Split data
        fen = fen.split(' ')
        # Expand blanks
        def expand(match): return ' ' * int(match.group(0))

        fen[0] = re.compile(r'\d').sub(expand, fen[0])
        self.positions = [None]
        for x, row in enumerate(fen[0].split('/')):
            for y, letter in enumerate(row):
                if letter == ' ': continue
                coord = self.letter_notation((7-x,y))
                self[coord] = pieces.piece(letter)
                self[coord].place(self)

        if fen[1] == 'w': self.player_turn = 'white'
        else: self.player_turn = 'black'


        self.halfmove_clock = int(fen[4])
        self.fullmove_number = int(fen[5])

    def export(self):
        '''
            Export state to FEN notation
        '''
        def join(k, g):
            if k == ' ': return str(len(g))
            else: return "".join(g)

        def replace_spaces(row):
            # replace spaces with their count
            result = [join(k, list(g)) for k,g in groupby(row)]
            return "".join(result)


        result = ''
        for number in self.axis_x[::-1]:
            for letter in self.axis_y:
                piece = self[letter+str(number)]
                if piece is not None:
                    result += piece.abbreviation
                else: result += ' '
            result += '/'

        result = result[:-1] # remove trailing "/"
        result = replace_spaces(result)
        result += " " + (" ".join([self.player_turn[0],
                         str(self.halfmove_clock),
                         str(self.fullmove_number)]))
        return result
