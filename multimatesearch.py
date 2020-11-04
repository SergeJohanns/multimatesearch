#!/bin/env python3

import sys
import subprocess
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


class Solver:
    def __init__(self, moves=2, mate=1, threads=1):
        self.moves = moves
        self.mate = mate
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
        self.stockfish.stdin.write(f"go depth {self.mate * 2 - 1}\n")
        self.stockfish.stdin.flush()
        # [info string, move/depth 0 (if no possible moves), move... (n < self.moves), best move]
        self.stockfish.stdout.readline()
        results = []
        move = self.stockfish.stdout.readline()
        while not move.startswith("bestmove"):
            if move.startswith(f"info depth {self.mate * 2 - 1}") and f"score mate {self.mate}" in move:
                move = move.split()
                i = move.index("pv")
                results.append(move[i + 1])
            move = self.stockfish.stdout.readline()
        return results
    
    def find_positions(self, moves):
        res = []
        for i in range(len(moves)):
            self.play_moves(moves[:i + 1])
            if len(self.get_mates()) >= self.moves:
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


def parse_args():
    parser = ArgumentParser(prog="multimatesearch",
                            description="Search a database of chess games for mate in m positions with at least n solutions.",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="The file containing all of the games that should be processed.")
    parser.add_argument('-o', metavar="<file>", help="place the output into <file>", default="positions.fen")
    parser.add_argument('-n', metavar="<n>", type=int, default=2, help="only save positions with at least <n> different solutions")
    parser.add_argument('-m', metavar="<mate>", type=int, default=1, help="only save positions that are mate in <mate>")
    parser.add_argument('-q', '--quiet', action='store_true', help="run without informative output")
    parser.add_argument('-t', metavar="<threads>", type=int, default=1, help="run stockfish accross <threads> different threads")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    solver = Solver(moves=args.n, mate=args.m, threads=args.t)
    use_stdin, use_stdout = args.file == '-', args.o == '-'
    if use_stdout:
        args.quiet = True # STDOUT needs to be clear for the output
    _games = open(args.file, 'r') if not use_stdin else sys.stdin
    _output = open(args.o, 'w') if not use_stdout else sys.stdout
    with _games as games, _output as output:
        i = 0
        hits = 0
        for line in games:
            if line != '\n' and line[0] != '[' and not "eval" in line:
                i += 1
                if not args.quiet:
                    print(f"Processing game {i}: {hits} total hits", end='\r')
                positions = solver.find_positions(pgn_to_uci(line))
                hits += len(positions)
                output.writelines([position + '\n' for position in positions])
        if not args.quiet:
            print(f"\n\nProcessed all {i} games in '{args.file if args.file != '-' else 'STDIN'}'.")
            print(f"Found {hits} positions with {args.n} or more different mate in {args.m} solutions.")
            print(f"Wrote results to '{args.o}'.")