#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function
"""
sls
"""
from collections import OrderedDict
import random
import logging
log = logging.getLogger()

class ChipStates:
    NEW = 0
    PRISONER = 1
    DEAD = 2


class Chip(object):
    def __init__(self, color, owner):
        self.color = color
        self.owner = owner
        self.state = ChipStates.NEW

    def capture(self, player):
        self.owner = player
        self.state = ChipStates.PRISONER

    def kill(self, player):
        self.state = ChipStates.DEAD

    def __str__(self):
        return "%s (%s)" % (self.color, self.owner)


class Pile(object):
    def __init__(self, id, chips=None):
        self.id = id
        self.chips = chips or []

    def __str__(self):
        return '#%4d: %2d: %r' % (
                self.id,
                len(self.chips),
                ', '.join(str(c) for c in self.chips))

    def __iter__(self):
        return self.chips.__iter__()

    def __getitem__(self, item):
        return self.chips.__getitem__(item)

    def __len__(self):
        return len(self.chips)

    @property
    def players(self):
        return [c.owner for c in self.chips]

    def has_player(self, player):
        return player in (c.owner for c in self.chips)


class PlayerStates:
    ALIVE = 1
    DEAD = 0


class Player(object):
    def __init__(self, color):
        self.color = color
        self.chips = [Chip(color, self) for c in xrange(7)]
        self.state = PlayerStates.ALIVE

    def __str__(self):
        return self.color

    def capture(self, pile, chip_to_kill):
        pile.chips.pop(chip_to_kill)
        for chip in pile:
            chip.capture(self)
        self.chips.extend(pile)

    def defeat(self):
        self.state = PlayerStates.DEAD

    @property
    def alive(self):
        return self.state == PlayerStates.ALIVE

    def prompt_for_move(self):
        # TODO
        raise NotImplementedError()


    def prompt_for_chip_to_kill(self, pile):
        print(
                '\n'.join(
                    "%s. %s (%s)" % (i, c.color, c.owner) for (i,c) in
                        enumerate(pile)))
        chips = dict((n,True) for n in xrange(len(pile)))
        chip_to_kill = None
        while chip_to_kill is None:
            user_input = raw_input("Choose a chip to kill: ")
            try:
                chip_to_kill = int(user_input.strip())
                if chip_to_kill not in chips:
                    raise Exception("Not a valid option.")
                return
            except Exception, e:
                log.exception(e)
                pass
        return chip_to_kill

    def prompt_for_next_player(self, players):
        """
        :param players: valid next player choices
        """
        next_player = None
        enumerated_players = tuple(enumerate(players))
        print(
            '\n'.join(
                "%s. %s" % (i, player) for (i,player) in
                    enumerated_players))
        playerdict = dict((i, player) for (i, player) in enumerated_players)
        while next_player is None:
            user_input = raw_input("Choose the next player: ")
            try:
                next_player_int = int(user_input.strip())
                next_player = playerdict[next_player_int]
            except KeyError, e:
                log.exception(e)
                log.error("%r is not a valid option" % next_player_int)
                log.debug(playerdict)
            except ValueError, e:
                #log.exception(e)
                log.error("%r is not an integer between 0 and %d" % (
                            user_input, len(players)))
                continue
            except Exception, e:
                log.exception(e)
                log.debug(players)
                pass

        return next_player


class MockPlayer(Player):
    def prompt_for_move(self):
        return {
            'action': PlayerAction.NEW,
            'pile_id': None,
            'dest_player': None
        }

    def prompt_for_chip_to_kill(self, pile):
        return pile[random.randint(0, len(pile)-1)]

    def prompt_for_next_player(self, players):
        return players[random.randint(0, len(players)-1)]


class PlayerAction:
    NEW = 0
    EXISTING = 1
    TRANSFER = 3
    DEFEATED = 4


class PlayerMove(object):
    def __init__(self, player,
                    action=None,
                    chip=None,
                    pile_id=None,
                    dest_player=None):
        """

        :param player: player making move
        :param action:

            (PlayerAction.NEW) ||
            (PlayerAction.EXISTING, chip=chip, pile_id=pile_id) ||
            (PlayerAction.TRANSFER, chip=chip, dest_player=dest_player)

        e.g. BLUE creates NEW pile
        e.g. BLUE adds to EXISTING pile #1
        e.g. BLUE TRANSFERs to RED
        e.g. BLUE is out of chips and DEFATED
        """
        self.player = player
        self.action = action
        self.chip = chip
        self.pile_id = pile_id
        self.dest_player = dest_player

    def __str__(self):
        return ' - '.join(str(s) for s in (
            self.player,
            self.action,
            self.chip,
            self.pile_id,
            self.dest_player))


class MoveOutcomes:
    NONE = 0
    CAPTURE = 1
    PENDING_DEFEAT = 2


class Game(object):
    def __init__(self, players, playercls=Player, seed=None):
        self.players = [playercls(p) for p in players]
        self.pilecount = 0
        self.piles = OrderedDict()
        self.moves = []
        self.game_log = []

        self.most_recent_pile = None
        random.seed(seed)

    @property
    def living_players(self):
        return [p for p in self.players if p.alive]

    def turn(self, player, move):
        outcome = None
        pile = None

        self.moves.append(move)
        if move.action == PlayerAction.NEW:
            if not len(player.chips):
                outcome = MoveOutcomes.PENDING_DEFEAT
                # TODO: FIXME: wait for help
                player.defeat()
            else:
                self.pilecount += 1
                chip = move.chip or player.chips.pop(0)
                newpile = Pile(self.pilecount, [chip])
                self.piles[self.pilecount] = newpile
                self.most_recent_pile = newpile
                outcome = MoveOutcomes.NONE

        elif move.action == PlayerAction.EXISTING:
            pile = self.piles.get(move.pile_id, None)
            if pile is None:
                raise Exception("pile %r does not exist" % move.pile_id)

            elif pile[-1] == move.player.color:
                # CAPTURED : chose one chip to kill, take others
                # TODO: w/ other chips
                chip_to_kill = player.prompt_for_chip_to_kill(pile)
                player.capture(pile, chip_to_kill)
                self.most_recent_pile = self.piles.pop(move.pile_id)
                outcome = MoveOutcomes.CAPTURE

            else:
                pile.append(move.chip)


        if outcome == MoveOutcomes.CAPTURE:
            next_player = player
        else:
            next_player = None

            # They may give the move to any player (including themselves)
            # whose color is not represented in the pile just played upon.
            choices = tuple(
                set(self.living_players) - set(self.most_recent_pile.players))

            # If all players are represented in that pile, the move goes to
            # the player whose most-recently-played chip is furthest down in
            # the pile.
            if not(choices):
                if pile is None:
                    pile = self.most_recent_pile
                next_player = pile[0].owner
            else:
                next_player = player.prompt_for_next_player(choices)

        return outcome, next_player

    def log_moves(self, header=''):
        log.info('~'*79)
        log.info(header)
        for i, move in enumerate(self.game_log):
            log.info("%4d. %r" % (i, [str(s) for s in move]))
        log.info('~'*79)

    def log_piles(self, header=''):
        log.info('='*79)
        log.info(header)
        for k,v in self.piles.iteritems():
            log.info(str(v))
        log.info('='*79)

    def log_players(self, header=''):
        log.info('-'*79)
        log.info('Players:')
        for player in self.players:
            log.info('%10s: %4d: %s' % (
                    player,
                    len(player.chips),
                    ', '.join(str(c) for c in player.chips)))
        log.info('-'*79)

    def log_game_state(self, header=None, t=None):
        headerstr = header or ('@ t=%d' % t)
        self.log_piles('Piles %s' % headerstr)
        self.log_players('Players %s' % headerstr)
        self.log_moves('Moves %s' % headerstr)

    def start(self):
        first_player = random.randint(0, len(self.players)-1)
        player = self.players[first_player]
        i = 0
        while any(p.alive for p in self.players):
            self.log_game_state(t=i)
            move = PlayerMove(player, **player.prompt_for_move())
            outcome, player = self.turn(player, move)
            log.debug("TURN: %s ==> %s ==> %s" % (move, outcome, player))
            self.game_log.append( (move,outcome,player) )
            i += 1

        log.info('+'*79)
        self.log_game_state('@ Final')


def sls():
    """
    mainfunc
    """
    pass


import unittest
class TestPlayer(unittest.TestCase):
    def test_player(self):
        p = Player('red')
        log.debug(p)
        self.assertEqual(len(p.chips), 7)

class TestChip(unittest.TestCase):
    def test_chip(self):
        p = Player('red')
        c = Chip('red', p)
        log.debug(c)

class TestPile(unittest.TestCase):
    def test_pile(self):
        player = Player('red')
        p = Pile(1, player.chips)
        log.debug(p)

class Test_sls(unittest.TestCase):
    # TODO ...
    def test_sls(self):
        game = Game([' red','gree','blue','oran'], playercls=MockPlayer, seed=1)
        self.assertEqual(len(game.players), 4)
        game.start()
    pass

def main():
    import optparse
    import logging

    prs = optparse.OptionParser(usage="./%prog : args")

    prs.add_option('-v', '--verbose',
                    dest='verbose',
                    action='store_true',)
    prs.add_option('-q', '--quiet',
                    dest='quiet',
                    action='store_true',)
    prs.add_option('-t', '--test',
                    dest='run_tests',
                    action='store_true',)

    (opts, args) = prs.parse_args()

    if not opts.quiet:
        logging.basicConfig(
            format='%(levelname)-8s| %(message)s'
        )

        if opts.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    if opts.run_tests:
        import sys
        sys.argv = [sys.argv[0]] + args
        import unittest
        exit(unittest.main())

    sls()

if __name__ == "__main__":
    main()
