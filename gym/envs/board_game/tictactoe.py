"""
Game of Tic-Tac-Toe
"""

from six import StringIO
import sys
import gym
from gym import spaces
import numpy as np
from gym import error
from gym.utils import seeding

def make_random_policy(np_random):
    def random_policy(state):
        possible_moves = TicTacToeEnv.get_possible_actions(state)
        # No moves left
        if len(possible_moves) == 0:
            return None
        a = np_random.randint(len(possible_moves))
        return possible_moves[a]
    return random_policy

class TicTacToeEnv(gym.Env):
    """
    Tic-Tac-Toe environment. Play against a fixed opponent.
    """
    CIRCLE = 0
    CROSS = 1
    metadata = {"render.modes": ["ansi","human"]}

    def __init__(self, player_color, opponent, observation_type, illegal_move_mode):
        """
        Args:
            player_color: Stone color for the agent. Either 'circle' or 'cross'
            opponent: An opponent policy
            observation_type: State encoding
            illegal_move_mode: What to do when the agent makes an illegal move. Choices: 'raise' or 'lose'
        """

        colormap = {
            'circle': TicTacToeEnv.CIRCLE,
            'cross': TicTacToeEnv.CROSS,
        }
        try:
            self.player_color = colormap[player_color]
        except KeyError:
            raise error.Error("player_color must be 'circle' or 'cross', not {}".format(player_color))

        self.opponent = opponent

        assert observation_type in ['numpy3c']
        self.observation_type = observation_type

        assert illegal_move_mode in ['lose', 'raise']
        self.illegal_move_mode = illegal_move_mode

        if self.observation_type != 'numpy3c':
            raise error.Error('Unsupported observation type: {}'.format(self.observation_type))

        # One action for each board position
        self.action_space = spaces.Discrete(9)
        observation = self.reset()
        self.observation_space = spaces.Box(np.zeros(observation.shape), np.ones(observation.shape))

        self._seed()

    def _seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)

        # Update the random policy if needed
        if isinstance(self.opponent, str):
            if self.opponent == 'random':
                self.opponent_policy = make_random_policy(self.np_random)
            else:
                raise error.Error('Unrecognized opponent policy {}'.format(self.opponent))
        else:
            self.opponent_policy = self.opponent

        return [seed]

    def _reset(self):
        self.state = np.zeros((3, 3, 3), dtype = np.int8)
        self.state[2, :, :] = 1
        self.to_play = TicTacToeEnv.CIRCLE
        self.done = False

        # Let the opponent play if it's not the agent's turn
        if self.player_color != self.to_play:
            a = self.opponent_policy(self.state)
            TicTacToeEnv.make_move(self.state, a, TicTacToeEnv.CIRCLE)
            self.to_play = TicTacToeEnv.CROSS
        return self.state

    def _step(self, action):
        assert self.to_play == self.player_color
        # If already terminal, then don't do anything
        if self.done:
            return self.state, 0., True, {'state': self.state}
        elif not TicTacToeEnv.valid_move(self.state, action):
            if self.illegal_move_mode == 'raise':
                raise
            elif self.illegal_move_mode == 'lose':
                # Automatic loss on illegal move
                self.done = True
                return self.state, -1., True, {'state': self.state}
            else:
                raise error.Error('Unsupported illegal move mode: {}'.format(self.illegal_move_mode))
        else:
            TicTacToeEnv.make_move(self.state, action, self.player_color)

        # Opponent play
        a = self.opponent_policy(self.state)

        # Making move if there are moves left and the game is still ongoing
        if a is not None and TicTacToeEnv.game_finished(self.state) == 0:
            TicTacToeEnv.make_move(self.state, a, 1 - self.player_color)

        reward = TicTacToeEnv.game_finished(self.state)
        if self.player_color == TicTacToeEnv.CROSS:
            reward = - reward
        self.done = reward != 0
        return self.state, reward, self.done, {'state': self.state}

    def _render(self, mode='human', close=False):
        if close:
            return
        board = self.state
        outfile = StringIO() if mode == 'ansi' else sys.stdout

        code = ['O', 'X', ' ']
        code = np.array(code)
        b = board[1, :, :] + 2*board[2, :, :]

        outfile.write('    1   2   3\n')
        outfile.write('             \n')
        outfile.write('A   %s | %s | %s\n'%tuple(code[b[0]]))
        outfile.write('    - + - + -\n')
        outfile.write('B   %s | %s | %s\n'%tuple(code[b[1]]))
        outfile.write('    - + - + -\n')
        outfile.write('C   %s | %s | %s\n'%tuple(code[b[2]]))

        if mode != 'human':
            return outfile

    @staticmethod
    def valid_move(board, action):
        coords = TicTacToeEnv.action_to_coordinate(board, action)
        if board[2, coords[0], coords[1]] == 1:
            return True
        else:
            return False

    @staticmethod
    def make_move(board, action, player):
        coords = TicTacToeEnv.action_to_coordinate(board, action)
        board[2, coords[0], coords[1]] = 0
        board[player, coords[0], coords[1]] = 1

    @staticmethod
    def coordinate_to_action(board, coords):
        return coords[0] * 3 + coords[1]

    @staticmethod
    def action_to_coordinate(board, action):
        return action // 3, action % 3

    @staticmethod
    def get_possible_actions(board):
        free_x, free_y = np.where(board[2, :, :] == 1)
        return [TicTacToeEnv.coordinate_to_action(board, [x, y]) for x, y in zip(free_x, free_y)]

    @staticmethod
    def game_finished(board):
        # Returns 1 if circle player 1 wins, -1 if cross player 2 wins and 0 otherwise
        xwin = 0
        owin = 0
        win_lines = [[[0, 0], [0, 1], [0, 2]], [[1, 0], [1, 1], [1, 2]], [[2, 0], [2, 1], [2, 2]], [[0, 0], [1, 0], [2, 0]], [[0, 1], [1, 1], [2, 1]], [[0, 2], [1, 2], [2, 2]], [[0, 0], [1, 1], [2, 2]], [[0, 2], [1, 1], [2, 0]]]
        for line in win_lines:
            curxwin = 1
            curowin = 1
            for pos in line:
                curowin *= board[tuple([0]+pos)]
                curxwin *= board[tuple([1]+pos)]
            xwin += curxwin
            owin += curowin
        if xwin == 0 and owin == 0:
            return 0
        elif xwin > 0 and owin == 0:
            return -1
        elif xwin == 0 and owin > 0:
            return 1
        else:
            raise error.Error("Both players got a winning line, which should not be possible!")
