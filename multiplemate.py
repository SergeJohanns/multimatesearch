#!/bin/env python3

import subprocess


class Solver:
    def __init__(self, moves=4, threads=4):
        self.moves = moves
        self.threads = threads
        self.stockfish = self.init_stockfish()

    def init_stockfish(self):
        stockfish = subprocess.Popen( "stockfish", text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stockfish.stdout.readline()
        stockfish.stdin.write(f"setoption name MultiPV value {self.moves}\n")
        stockfish.stdin.write(f"setoption name Threads value {self.threads}\n")
        return stockfish

    def get_fen(self):
        self.stockfish.stdin.write("d\n")
        self.stockfish.stdin.flush()
        # read entire response -> get fen -> remove "Fen: " -> remove trailing newline
        return [self.stockfish.stdout.readline() for _ in range(23)][-3].split(' ', 1)[1][:-1]
    
    def play_moves(self, moves):
        self.stockfish.stdin.write(f"position startpos moves {' '.join(moves)}\n")

    def get_mates(self):
        self.stockfish.stdin.write(f"go depth 1\n")
        self.stockfish.stdin.flush()
        # [info string, move/depth 0 (if no possible moves), move... (n < self.moves), best move]
        self.stockfish.stdout.readline()
        results = []
        move = self.stockfish.stdout.readline()
        while "bestmove" not in move:
            if "info depth 1" == move[:len("info depth 1")] and "score mate 1" in move:
                move = move.split()
                i = move.index("pv")
                results.append(move[i + 1])
            move = self.stockfish.stdout.readline()
        return results
    
    def find_positions(self, moves):
        res = []
        for i in range(len(moves)):
            self.play_moves(moves[:i + 1])
            if len(self.get_mates()) >= 3:
                res.append(self.get_fen())
        return res


def pgn_to_uci(pgn):
    """
    Convert a pgn game to a uci game using pgn-extract.

    pgn-extract outputs a report of the form.
    ```
    Processing stdin
    [Event "?"]
    [Site "?"]
    [Date "????.??.??"]
    [Round "?"]
    [White "?"]
    [Black "?"]
    [Result "1-0"]

    d2d4 c7c6 c2c4 e7e6 e2e4 f7f6 e4e5 g7g5 d4d5 f6f5 d5e6 g5g4 h2h3 g4h3 d1h5 1-0


    1 game matched out of 1.
    ```
    """
    convert = subprocess.Popen(f'echo "{pgn}" | pgn-extract -Wuci 2> /dev/null', shell=True, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    uci = [convert.stdout.readline() for _ in range(13)][8].split()[:-1]
    return uci


if __name__ == "__main__":
    solver = Solver()
    with open("lichess_db_standard_rated_2013-01.pgn", 'r') as games, open("output.txt", 'w') as output:
        i = 1
        hits = 0
        for line in games:
            print(f'Processing game {i}: {hits} hits', end='\r')
            if line != '\n' and line[0] != '[' and not "eval" in line:
                positions = solver.find_positions(pgn_to_uci(line))
                hits += len(positions)
                output.writelines([position + '\n' for position in positions])
                i += 1