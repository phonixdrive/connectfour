import asyncio
import websockets
import random
import math
import json

# Board constants
ROWS = 6
COLS = 7

PLAYER_PIECE = None
OPPONENT_PIECE = None

def create_empty_board():
    return [[0]*COLS for _ in range(ROWS)]

def drop_piece(board, row, col, piece):
    board[row][col] = piece

def is_valid_location(board, col):
    return board[0][col] == 0

def get_next_open_row(board, col):
    for r in range(ROWS-1, -1, -1):
        if board[r][col] == 0:
            return r
    return None

def get_valid_locations(board):
    return [c for c in range(COLS) if is_valid_location(board, c)]

def is_winning_move(board, piece):
    # Check horizontal
    for c in range(COLS-3):
        for r in range(ROWS):
            if (board[r][c] == piece and board[r][c+1] == piece and
                board[r][c+2] == piece and board[r][c+3] == piece):
                return True

    # Check vertical
    for c in range(COLS):
        for r in range(ROWS-3):
            if (board[r][c] == piece and board[r+1][c] == piece and
                board[r+2][c] == piece and board[r+3][c] == piece):
                return True

    # Check positive diagonal
    for c in range(COLS-3):
        for r in range(3, ROWS):
            if (board[r][c] == piece and board[r-1][c+1] == piece and
                board[r-2][c+2] == piece and board[r-3][c+3] == piece):
                return True

    # Check negative diagonal
    for c in range(3, COLS):
        for r in range(3, ROWS):
            if (board[r][c] == piece and board[r-1][c-1] == piece and
                board[r-2][c-2] == piece and board[r-3][c-3] == piece):
                return True

    return False

def is_terminal_node(board):
    return (is_winning_move(board, PLAYER_PIECE) or
            is_winning_move(board, OPPONENT_PIECE) or
            len(get_valid_locations(board)) == 0)

def simulate_random_game(board, starting_piece):
    temp_board = [row[:] for row in board]
    turn_piece = starting_piece

    while not is_terminal_node(temp_board):
        valid_moves = get_valid_locations(temp_board)
        if not valid_moves:
            break
        col = random.choice(valid_moves)
        row = get_next_open_row(temp_board, col)
        drop_piece(temp_board, row, col, turn_piece)
        turn_piece = OPPONENT_PIECE if turn_piece == PLAYER_PIECE else PLAYER_PIECE

    if is_winning_move(temp_board, PLAYER_PIECE):
        return PLAYER_PIECE
    elif is_winning_move(temp_board, OPPONENT_PIECE):
        return OPPONENT_PIECE
    else:
        return 0

def monte_carlo_move(board, piece, simulations=5000):
    valid_moves = get_valid_locations(board)
    best_win_rate = -1
    best_col = random.choice(valid_moves)
    next_piece = OPPONENT_PIECE if piece == PLAYER_PIECE else PLAYER_PIECE

    for col in valid_moves:
        temp_board = [row[:] for row in board]
        row = get_next_open_row(temp_board, col)
        drop_piece(temp_board, row, col, piece)

        ai_wins = 0
        for _ in range(simulations):
            winner = simulate_random_game(temp_board, next_piece)
            if winner == piece:
                ai_wins += 1

        win_rate = ai_wins / simulations
        if win_rate > best_win_rate:
            best_win_rate = win_rate
            best_col = col

    return best_col

async def gameloop(socket, created):
    board = create_empty_board()
    global PLAYER_PIECE, OPPONENT_PIECE
    if created:
        PLAYER_PIECE = 1
        OPPONENT_PIECE = 2
    else:
        PLAYER_PIECE = 2
        OPPONENT_PIECE = 1

    active = True

    while active:
        raw_msg = await socket.recv()
        message = raw_msg.split(':')

        cmd = message[0]
        if cmd == 'GAMESTART':
            if created:
                # Our turn first
                col = monte_carlo_move(board, PLAYER_PIECE)
                await socket.send(f'PLAY:{col}')
                row = get_next_open_row(board, col)
                drop_piece(board, row, col, PLAYER_PIECE)

        elif cmd == 'OPPONENT':
            opp_col = int(message[1])
            # Opponent's move
            row = get_next_open_row(board, opp_col)
            drop_piece(board, row, opp_col, OPPONENT_PIECE)

            # Our move
            col = monte_carlo_move(board, PLAYER_PIECE)
            await socket.send(f'PLAY:{col}')
            row = get_next_open_row(board, col)
            drop_piece(board, row, col, PLAYER_PIECE)

        elif cmd == 'WIN':
            print("You Won!")
            active = False

        elif cmd == 'LOSS':
            print("You Lost!")
            active = False

        elif cmd == 'DRAW':
            print("Game Drawn!")
            active = False

        elif cmd == 'TERMINATED':
            print("Game Terminated by Opponent!")
            active = False

        elif cmd == 'ACK':
            # Acknowledgement - do nothing
            pass

        else:
            # Unknown message
            print("game id message:", raw_msg)

async def create_game(server):
    async with websockets.connect(f'ws://{server}/create') as socket:
        await gameloop(socket, True)

async def join_game(server, id):
    async with websockets.connect(f'ws://{server}/join/{id}') as socket:
        await gameloop(socket, False)

if __name__ == '__main__':
    server = input('Server IP (e.g. localhost:3000): ').strip()
    protocol = input('Join game or create game? (j/c): ').strip()

    if protocol == 'c':
        asyncio.run(create_game(server))
    elif protocol == 'j':
        game_id = input('Game ID(only needed for local vers: ').strip()
        asyncio.run(join_game(server, game_id))
    else:
        print('Invalid choice!')