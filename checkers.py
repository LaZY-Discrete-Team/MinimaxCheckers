"""
Modified version of https://github.com/brettpilch/pygame-checkers

Helpful reference videos:
Depth limit minimax https://www.youtube.com/watch?v=mYbrH1Cl3nw
Alpha-Beta pruning https://www.youtube.com/watch?v=l-hh51ncgDI
"""

import copy
import pygame
import math
import random
import time

# Define some colors
BLACK	= (   0,   0,   0)
WHITE	= ( 255, 255, 255)
GREEN	= (   0, 255,   0)
RED	  	= ( 255,   0,   0)
BLUE	= (   0,   0, 255)
YELLOW  = ( 255, 255,   0)
TRANS	= (   1,   2,   3)

# CONSTANTS:
WIDTH = 600
HEIGHT = 600
ROWS = 8
COLS = 8
MARK_SIZE = int(WIDTH / ROWS / 2)

class Game:
	"""class to keep track of the status of the game."""
	def __init__(self):
		"""
		Start a new game with an empty board and random player going first.
		"""
		self.status = 'playing'
		self.turn = 0 # random.randrange(2)
		self.players = ['r','b']
		self.tokens = [12, 12]
		self.kings = [0, 0]
		self.selected_token = None
		self.jumping = False
		pygame.display.set_caption("%s's turn" % self.players[self.turn % 2])
		self.game_board = [['r','-','r','-','r','-','r','-'],
						   ['-','r','-','r','-','r','-','r'],
						   ['r','-','r','-','r','-','r','-'],
						   ['-','-','-','-','-','-','-','-'],
						   ['-','-','-','-','-','-','-','-'],
						   ['-','b','-','b','-','b','-','b'],
						   ['b','-','b','-','b','-','b','-'],
						   ['-','b','-','b','-','b','-','b']]

		# self.game_board = [['r','-','r','-','r'],
		# 				   ['-','r','-','r','-'],
		# 				   ['-','-','-','-','-'],
		# 				   ['-','b','-','b','-'],
		# 				   ['b','-','b','-','b']]

	def evaluate_click(self, mouse_pos):
		"""
		Select a token if none is selected.
		Move token to a square if it is a valid move.
		Start a new game if the game is over.
		"""
		if self.status == 'playing':
			to_loc = get_clicked_row(mouse_pos), get_clicked_column(mouse_pos)
			player = self.players[self.turn % 2]
			if self.selected_token:
				move = self.is_valid_move(player, self.selected_token, to_loc)
				if move[0]:
					winner = self.play(player, self.selected_token, to_loc, move[1])
					if winner is None:
						pygame.display.set_caption("%s's turn" % player)
					elif winner == 'draw':
						pygame.display.set_caption("It's a stalemate! Click to start again")
					else:
						pygame.display.set_caption("%s wins! Click to start again" % winner)
				elif to_loc[0] == self.selected_token[0] and to_loc[1] == self.selected_token[1]:
					self.selected_token = None
					if self.jumping:
						self.jumping = False
						self.next_turn()
				else:
					print('invalid move')
			else:
				if self.game_board[to_loc[0]][to_loc[1]].lower() == player:
					self.selected_token = to_loc
		elif self.status == 'game over':
			self.__init__()

	def is_valid_move(self, player, from_loc, to_loc):
		"""
		Check if clicked location is a valid square for player to move to.
		"""
		from_row = from_loc[0]
		from_col = from_loc[1]
		to_row = to_loc[0]
		to_col = to_loc[1]
		token_char = self.game_board[from_row][from_col]
		if self.game_board[to_row][to_col] != '-':
			return False, None
		if (((token_char.isupper() and abs(from_row - to_row) == 1) or (player == 'r' and to_row - from_row == 1) or
			 (player == 'b' and from_row - to_row == 1)) and abs(from_col - to_col) == 1) and not self.jumping:
			return True, None
		if (((token_char.isupper() and abs(from_row - to_row) == 2) or (player == 'r' and to_row - from_row == 2) or
			 (player == 'b' and from_row - to_row == 2)) and abs(from_col - to_col) == 2):
			jump_row = (to_row - from_row) / 2 + from_row
			jump_col = (to_col - from_col) / 2 + from_col
			if self.game_board[int(jump_row)][int(jump_col)].lower() not in [player, '-']:
				return True, [jump_row, jump_col]
		return False, None

	def get_all_pieces(self, player):
		pieces = []
		for i, x in enumerate(self.game_board):
			for j, y in enumerate(x):
				if y.lower() == player:
					pieces.append([i, j])
		return pieces

	def get_valid_moves(self, player):
		moves = []
		for i in self.get_all_pieces(player):
			# try all of the single diagonals
			for p,q in [[1,1],[-1,-1],[1,-1],[-1,1]]:
				to_loc = [i[0]+p, i[1]+q]
				if (to_loc[0] < ROWS) & (to_loc[0] >= 0) & (to_loc[1] < COLS) & (to_loc[1] >= 0):
					j = [i[0]+p, i[1]+q]
					is_valid_move, jumped = self.is_valid_move(player, i, j)
					if is_valid_move == True:
						moves.append([i, [i[0]+p, i[1]+q], None])

			# try all of the jumps, including multiple in a row
			can_jump = True
			from_loc = i
			jumped_list = []
			while can_jump:
				can_jump = False
				for p,q in [[2,2],[2,-2],[-2,2],[-2,-2]]:
					to_loc = [from_loc[0]+p, from_loc[1]+q]
					if (to_loc[0] < ROWS) & (to_loc[0] >= 0) & (to_loc[1] < COLS) & (to_loc[1] >= 0):
						is_valid_move, jumped = self.is_valid_move(player, from_loc, to_loc)
						if is_valid_move == True and jumped != None:
							can_jump = True
							jumped_list.append(jumped)
							moves.append([i, to_loc, jumped_list])
							from_loc = to_loc
		return moves

	def play(self, player, from_loc, to_loc, jump, auto=False):
		"""
		Move selected token to a particular square, then check to see if the game is over.
		"""
		from_row = from_loc[0]
		from_col = from_loc[1]
		to_row = to_loc[0]
		to_col = to_loc[1]
		token_char = self.game_board[from_row][from_col]
		self.game_board[to_row][to_col] = token_char
		self.game_board[from_row][from_col] = '-'
		if (player == 'r' and to_row == ROWS-1) or (player == 'b' and to_row == 0):
			self.game_board[to_row][to_col] = token_char.upper()
			self.kings[player == 'b'] += 1

		if auto and jump != None:
			# auto mode when computer playing does multiple jumps and advances to next turn
			for j in jump:
				self.game_board[int(j[0])][int(j[1])] = '-'
				self.tokens[player == self.players[0]] -= 1
			self.selected_token = None
			self.jumping = False
			self.next_turn()
		elif jump:
			self.game_board[int(jump[0])][int(jump[1])] = '-'
			self.selected_token = [to_row, to_col]
			self.jumping = True
			self.tokens[player == self.players[0]] -= 1
		else:
			self.selected_token = None
			self.next_turn()
		winner = self.check_winner()
		if winner != None:
			self.status = 'game over'
		return winner

	def next_turn(self):
		self.turn += 1
		pygame.display.set_caption("%s's turn" % self.players[self.turn % 2])

	def check_winner(self):
		"""
		check to see if someone won, or if it is a draw.
		"""
		# no possible moves, cornered
		if len(self.get_valid_moves(self.players[self.turn % 2])) == 0 and self.jumping == False:
			return self.players[1]
		if self.tokens[0] == 0:
			return self.players[1]
		if self.tokens[1] == 0:
			return self.players[0]
		if self.tokens[0] == 1 & self.tokens[1] == 1:
			return 'draw'
		return None

	def draw(self):
		"""
		Draw the game board and the X's and O's.
		"""
		for i in range(ROWS+1):
			for j in range(COLS+1):
				if (i+j) % 2 == 1: # flip color of board
					pygame.draw.rect(screen, WHITE, (i * WIDTH / ROWS, j * HEIGHT / COLS, WIDTH / ROWS, HEIGHT / COLS))

		for r in range(len(self.game_board)):
			for c in range(len(self.game_board[r])):
				mark = self.game_board[r][c]
				if self.players[0] == mark.lower():
					color = RED
				else:
					color = BLUE
				if self.selected_token:
					if self.selected_token[0] == r and self.selected_token[1] == c:
						color = YELLOW
				if mark != '-':
					x = WIDTH / ROWS * c + WIDTH / ROWS / 2
					y = HEIGHT / COLS * r + HEIGHT / COLS / 2
					pygame.draw.circle(screen, color, (int(x), int(y)), MARK_SIZE)
					if self.game_board[r][c].isupper():
						pygame.draw.circle(screen, BLACK, (int(x), int(y)), int(MARK_SIZE*7/8))
						pygame.draw.circle(screen, color, (int(x), int(y)), int(MARK_SIZE*3/4))

def evaluate(game, max_player):
	""" metric evaluating game state """
	your_pieces = game.tokens[max_player]
	their_pieces = game.tokens[(max_player+1)%2]
	your_kings = game.kings[max_player]
	their_kings = game.kings[(max_player+1)%2]
	# print("EVAL", (your_pieces - their_pieces), your_pieces, their_pieces)
	return your_pieces - their_pieces + 0.5*(your_kings - their_kings)

# Helper functions:
def get_clicked_column(mouse_pos):
	x = mouse_pos[0]
	for i in range(1, ROWS):
		if x < i * WIDTH / ROWS:
			return i - 1
	return ROWS-1

def get_clicked_row(mouse_pos):
	y = mouse_pos[1]
	for i in range(1, COLS):
		if y < i * HEIGHT / COLS:
			return i - 1
	return COLS-1

def minimax(game, depth, max_player_index, alpha=float('-inf'), beta=float('+inf')):
	"""	game: the game object holding game state
	depth: how many moves ahead to search in the game tree
	max_player_index: index of the player the computer is playing for
	eval: evaluation of game state
	best_move: the best move to make, given as [from_loc, to_loc, pieces_jumped]
	"""
	player_index = game.turn % 2 # player whose turn it is currently
	winner = game.check_winner()
	if winner != None: # base case: game over
		if winner == game.players[max_player_index]: # computer won
			return float('+inf'), None, []
		elif winner == game.players[(max_player_index + 1) % 2]:
			return float('-inf'), None, []
		else:
			return evaluate(game, max_player_index), None, []
	elif depth == 0: # base case: depth reached
		eval = evaluate(game, max_player_index)
		# print("eval", eval, "\ttokens", game.tokens)
		return eval, None

	elif max_player_index == player_index: # maximizing player's turn
		max_eval = float('-inf')
		best_move = None
		moves = game.get_valid_moves(game.players[player_index])
		for move in moves:
			# make a copy of the game to play out the current move in
			new_game = copy.deepcopy(game)
			new_game.play(game.players[player_index], move[0], move[1], move[2], True)
			eval = minimax(new_game, depth-1, max_player_index, alpha, beta)[0]
			max_eval = max(max_eval, eval)
			alpha = max(alpha, eval)
			if beta <= alpha:
				# print("\tprune")
				break
			if max_eval == eval: # better value than previous best move
				best_move = move
		# print("max_eval", max_eval, "\ttokens", game.tokens)
		return max_eval, best_move

	else: # minimizing player's turn
		min_eval = float('+inf')
		best_move = None
		moves = game.get_valid_moves(game.players[player_index])
		for move in moves:
			# make a copy of the game to play out the current move in
			new_game = copy.deepcopy(game)
			new_game.play(game.players[player_index], move[0], move[1], move[2], True)
			eval = minimax(new_game, depth-1, max_player_index, alpha, beta)[0]
			min_eval = min(min_eval, eval)
			beta = min(beta, eval)
			if beta <= alpha:
				# print("\tprune")
				break
			if min_eval == eval: # better value than previous best move
				best_move = move
		# print("min_eval", min_eval, "\ttokens", game.tokens)
		return min_eval, best_move

# game setup and constants
pygame.init()
size = (WIDTH, HEIGHT)
screen = pygame.display.set_mode(size)
game = Game() # start game
done = False # Loop until the user clicks the close button
clock = pygame.time.Clock() # Used to manage how fast the screen updates
framerate = 60

# flip to false to play normal 2-player checkers
run_minimax = True
depth = 5 # How many moves ahead to look
max_player = 0 # play as red 'r' index 0

while not done:

	# if it's the computer's turn
	if game.turn % 2 == max_player and run_minimax:

		# figure out which move would be best
		eval, best_move = minimax(game, depth, max_player)
		print("EVALUATION:", eval)
		print("BEST MOVE:", best_move)

		# check that no one won yet, so we know that best_move exists
		winner = game.check_winner()
		if winner != None:
			self.status = 'game over'
		else:
			# play the best move
			game.play(game.players[game.turn % 2], best_move[0], best_move[1], best_move[2], True)
			print('Score', game.tokens, "\tKings", game.kings, '\n')

	# if it's the human's turn
	else:
		for event in pygame.event.get(): # User did something
			if event.type == pygame.QUIT: # If user clicked close
				done = True # Flag that we are done so we exit this loop
			if event.type == pygame.KEYDOWN:
				entry = str(event.key)
			if event.type == pygame.MOUSEBUTTONDOWN:
				mouse_x, mouse_y = pygame.mouse.get_pos()
				game.evaluate_click(pygame.mouse.get_pos())

		screen.fill(BLACK) # clear the screen to black
		game.draw() # draw the game board and marks
		pygame.display.flip() # update the screen with what we've drawn
		clock.tick(60) # Limit to 60 frames per second

pygame.quit() # Close the window and quit.
