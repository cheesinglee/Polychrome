#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Created: 30 January 2012, Chee Sing Lee

from __future__ import print_function
from random import shuffle, sample, random
from itertools import combinations_with_replacement
import sys, time
import copy

import terminal

if sys.version_info.major == 2:
    input = raw_input

# define scoring schemes
scoring1 = [0,1,3,6,10,15,21]
scoring2 = [0,1,4,8,7,6,5]

class PolychromeGame:
    """ Class for playing Polychrome """
    deck = []
    players = []
    two_player = False
    colors = ['green','blue','brown','yellow','gray','pink','orange']
    piles = []
    piles_taken = []
    scoring = []
    log_buffer = ''
    log_mode = 'buffer'
    log_filename = ''

    def __init__(self,players,scoring):
        self.scoring = scoring
        self.players = players
        self.two_player = len(self.players) == 2
        if not self.two_player:
            self.piles = [list() for p in self.players]
        else:
            self.piles = [list(),list(),list()]

    def initialize_deck(self):
        """ populate the Polychrome deck """

        # 7 colors (if >3 players, 6 if >2 players, else 5 colors), 9 of each
        reduce_colors_by = 2 if len(self.players) == 2 else 1 if len(self.players) == 3 else 0
        self.deck = self.colors[reduce_colors_by:]*9
        self.colors = self.colors[reduce_colors_by:]

        # 3 wilds
        self.deck.extend(['wild']*3)

        # 10 bonus "+2" cards
        self.deck.extend(['+2']*10)

        # shuffle
        shuffle(self.deck)

    def play(self):
        """ Play one game of Polychrome
        """
        self.initialize_deck()
        if not self.two_player:
            self.piles = [list() for p in self.players]
        else:
            self.piles = [list(),list(),list()]
        n_players = len(self.players)
        # deal initial colors
        if not self.two_player:
            start_colors = sample(self.colors,n_players)
            for i in range(n_players):
                self.players[i].take_cards([start_colors[i]])
                self.deck.remove(start_colors[i])
        else:
            start_colors = sample(self.colors,4)
            self.players[0].take_cards(start_colors[0:2])
            self.players[1].take_cards(start_colors[2:])
            for i in range(4):
                self.deck.remove(start_colors[i])
        shuffle(self.deck)

        last_round = False
        player_idx = -1
        n_rounds = 0
        while not last_round:
            n_rounds += 1
            self.log('\n----Round '+str(n_rounds)+'----')
            # clear the piles
            if not self.two_player:
                self.piles = [list() for p in self.players]
            else:
                self.piles = [list(),list(),list()]
            # all players are in again
            if not self.two_player:
                self.piles_taken = [False]*n_players
            else:
                self.piles_taken = [False]*3
            for p in self.players:
                p.out = False
                self.print_player_status(p)
            all_out = False
            while not all_out:
                # choose next player
                while True:
                    player_idx += 1
                    if player_idx == n_players:
                        player_idx = 0
                    if not self.players[player_idx].out:
                        break
                player = self.players[player_idx]
                self.log("\nIt's "+player.name+"'s turn")
                self.print_piles()
                player.update(self)
                if not any(self.piles):
                    # all piles are empty, player must draw
                    self.log('All piles are empty, draw a card')
                    c = self.deck.pop(0)
                    self.log('Drew a '+c)
                    pile_idx = player.select_pile(c)
                    self.piles[pile_idx].append(c)
                    self.log('Placed on pile '+str(pile_idx))
                elif self.all_piles_full():
                    # all available piles full, player must take one
                    self.log('All available piles are full')
                    pile_idx = player.select_pile()
                    player.take_cards(self.piles[pile_idx])
                    self.piles[pile_idx] = []
                    self.piles_taken[pile_idx] = True
                    self.log(player.name+' takes pile '+str(pile_idx))
                    player.out = True
                else:
                    # player can choose an action
                    action = player.get_action()
                    if action == 'take':
                        pile_idx = player.select_pile()
                        player.take_cards(self.piles[pile_idx])
                        self.piles[pile_idx] = []
                        self.piles_taken[pile_idx] = True
                        self.log(player.name+' takes pile '+str(pile_idx))
                        player.out = True
                    elif action == 'draw':
                        c = self.deck.pop(0)
                        self.log('Drew a '+c)
                        pile_idx = player.select_pile(c)
                        self.piles[pile_idx].append(c)
                        self.log('Placed on pile '+str(pile_idx))
                # check for last round
                cards_left = len(self.deck)
                self.log('Cards left: '+str(cards_left))
                if cards_left < 15:
                    self.log('Last Round!')
                    last_round = True
                # check if everyone is out
                all_out = True
                for p in self.players:
                    all_out = all_out and p.out
            # adjust the player index so that the last player to take in this
            # round is the starting player for the next round
            player_idx -= 1
        self.log('\n----Game Over----')
        final_scores = self.compute_scores()
        for p in self.players:
            p.end_game()
            p.out = False
            self.print_player_status(p)
        self.log('Remaining cards: '+str(self.deck))
        # determine the winner
        winner = 0
        for i in range(n_players):
            if final_scores[i] > final_scores[winner]:
                winner = i
        self.log(self.players[winner].name+' is the winner')

    def score(self,argin):
        """ compute scores for a player or list of cards
        """
        try:
            # input is a player
            cards = argin.cards
        except(AttributeError):
            # input is a list of cards
            cards = argin
        color_counts_no_wild = [cards.count(c) for c in self.colors]
        # assign wilds
        # TODO: find optimal wild assignment in a not brute force manner
        n_wilds = cards.count('wild')
        score = -1
        if n_wilds > 0:
            max_score = -1
            for wild_assignments in \
            combinations_with_replacement(range(len(self.colors)),n_wilds):
                # make a copy of the wild-less color counts
                color_counts = list(color_counts_no_wild)

                # make the wild assignments
                for i in wild_assignments:
                    color_counts[i] += 1
               
                # truncate the color counts if the exceed the defined values 
                # in the scoring scheme
                for i in range(len(color_counts)):
                    if color_counts[i] >= len(self.scoring):
                        color_counts[i] = len(self.scoring)-1
                
                # compute scoring
                values = [self.scoring[n] for n in color_counts]
                values.sort(reverse=True)
                tmp_score = 0
                for n in range(len(self.colors)):
                    if n < 3:
                        tmp_score += values[n]
                    else:
                        tmp_score -= values[n]
                if tmp_score > max_score:
                    max_score = tmp_score
            score = max_score
        else:
            # truncate the color counts if the exceed the defined values 
            # in the scoring scheme
            for i in range(len(color_counts_no_wild)):
                if color_counts_no_wild[i] >= len(self.scoring):
                    color_counts_no_wild[i] = len(self.scoring)-1
            # scoring without wilds
            values = [self.scoring[n] for n in color_counts_no_wild]
            values.sort(reverse=True)
            score = 0
            for n in range(len(self.colors)):
                if n < 3:
                    score += values[n]
                else:
                    score -= values[n]

        # add bonus cards
        score += 2*cards.count('+2')
        return score


    def compute_scores(self):
        player_scores = []
        for p in self.players:
            s = self.score(p.cards)
            player_scores.append(s)
        return player_scores

    def all_piles_full(self):
        """ check if all available piles are full """
        if not self.two_player:
            n_players = len(self.players)
            full = [len(self.piles[i])==3 for i in range(n_players) if not self.piles_taken[i]]
            return all(full)
        else:
            return (
                (len(self.piles[0]) == 1 or self.piles_taken[0]) and
                (len(self.piles[1]) == 2 or self.piles_taken[1]) and
                (len(self.piles[2]) == 3 or self.piles_taken[2]))

    def set_log_mode(self,mode,filename=''):
        if mode == 'buffer' or mode == 'print' or mode == 'file':
            self.log_mode = mode
            self.log_filename = ''
        else:
            raise(ValueError,'acceptable log modes are "buffer", "print", or "file"')

    def log(self,s):
        if self.log_mode == 'buffer':
            self.log_buffer += s+'\n'
        elif self.log_mode == 'print':
            print(s)
        elif self.log_mode == 'file':
            try:
                fid = open(s,'a')
                fid.write(s+'\n')
                fid.close()
            except:
                print('Error, could not write log to file '+self.log_dest)
                
    def flush_log(self):
        flushed = self.log_buffer
        self.log_buffer = ''
        return flushed

    def print_player_status(self,p):
        score = self.score(p.cards)
        cards = list(p.cards)
        cards.sort()

        template = '{name}:\t{score} points\n\
        Orange: {n_orange}\tBlue: {n_blue}\tBrown: {n_brown}\n\
        Yellow: {n_yellow}\tGray: {n_gray}\tGreen: {n_green}\n\
        Pink  : {n_pink}\tWild: {n_wild}\t+2   : {n_bonus}'
        s = template.format(name=p.name,score=str(score),
                            n_orange=str(cards.count('orange')),
                            n_blue=str(cards.count('blue')),
                            n_brown=str(cards.count('brown')),
                            n_yellow=str(cards.count('yellow')),
                            n_gray=str(cards.count('gray')),
                            n_green=str(cards.count('green')),
                            n_pink=str(cards.count('pink')),
                            n_wild=str(cards.count('wild')),
                            n_bonus=str(cards.count('+2')))
        self.log(s)

    def print_piles(self):
        s = 'Pile contents: \n'
        for i in range(len(self.piles)):
            if not self.piles_taken[i]:
                s += str(i)+':'+str(self.piles[i])+' '
            else:
                s += str(i)+':'+'[TAKEN] '
        self.log(s)

    def get_piles_take(self):
        """ get the piles which can be taken

        Returns a tuple (P,I), where P is a list of the available piles, and
        I is a list of indices corresponding to the full list of piles.

        """
        idx_take = []
        piles_take = []
        i = 0
        for p in self.piles:
            if not self.piles_taken[i] and len(p) > 0:
                idx_take.append(i)
                piles_take.append(p)
            i += 1
        return (piles_take,idx_take)

    def get_piles_draw(self):
        """ get the piles which can accept another card

        Returns a tuple (P,I), where P is a list of the available piles, and
        I is a list of indices corresponding to the full list of piles.

        """
        idx_draw = []
        piles_draw = []
        i = 0
        for p in self.piles:
            if not self.two_player:
                if not self.piles_taken[i] and len(p) < 3:
                    idx_draw.append(i)
                    piles_draw.append(p)
            else:
                if len(p) <= i and not self.piles_taken[i]:
                    idx_draw.append(i)
                    piles_draw.append(p)
            i += 1
        return (piles_draw,idx_draw)

class PolychromePlayer(object):
    """ Base Polychrome Player class

    Subclasses should re-implement the get_action(), decision_take(), and
    decision_draw() methods

    """
    cards = []
    game = []
    out = False
    name = ''
    def __init__(self,name):
        self.name=name
        self.out = False
        self.cards = list()

    def take_cards(self,card_list):
        self.cards.extend(card_list)

    def update(self,game):
        """ Make a private copy of the game state"""
#        self.game = copy.deepcopy(game)
        self.game = game

    def get_action(self):
        pass
    def end_game(self):
        pass

    def select_pile(self,new_card=-1):
        if new_card == -1:
            # select a pile to take
            return self.decision_take()
            pass
        else:
            # select a pile to put the card on
            return self.decision_draw(new_card)
            pass

    def decision_take(self):
        return 0

    def decision_draw(self,card):
        return 0

    def get_cards(self):
        return self.cards

    def is_out(self):
        return self.is_out()
        
    def find_optimal_pile_take(self):
        # score each available pile and pick up the one that is worth the most
        idx = -1
        max_score = -1000
        counter = -1
        [piles_take,idx_take] = self.game.get_piles_take()
        for p in piles_take:
            counter += 1
            pile_score = self.evaluate_pile(p)
            if pile_score > max_score:
                max_score = pile_score
                idx = idx_take[counter]
        return idx

    def find_optimal_pile_draw(self,new_card):
        # loop through each pile, and score each one with the addition of
        # the new card. place the new card where the score would be the
        # highest
        idx = -1
        max_score = -1000
        counter = -1
        [piles_draw,idx_draw] = self.game.get_piles_draw()
        for p in piles_draw:
            counter += 1
            pile_score = self.evaluate_pile(p+[new_card])
            if pile_score > max_score:
                max_score = pile_score
                idx = idx_draw[counter]
        return idx

    def evaluate_pile(self,pile):
        """
        compute the difference in score if the player were to pick up a
        particular pile.
        """
        cards_new = self.cards + pile
        return self.game.score(cards_new) - self.game.score(self.cards)

class GreedyBot(PolychromePlayer):
    """ A Greedy Polychrome AI

    GreedyBot always takes a pile if it will result in a score increase. It
    only draws when none of the piles are worth positive points.

    """
    def __init__(self,name):
        PolychromePlayer.__init__(self,name)
    def get_action(self):
        piles_take = self.game.get_piles_take()
        for p in piles_take:
            if self.evaluate_pile(p) > 0:
                return 'take'
        return 'draw'

    def decision_take(self):
        return self.find_optimal_pile_take()

    def decision_draw(self,new_card):
        return self.find_optimal_pile_draw(new_card)

class BuilderBot(PolychromePlayer):
    """
    BuilderBot will always draw if possible. It places the drawn card in the
    pile which will give the maximum score increase
    """
    def __init__(self,name):
        PolychromePlayer.__init__(self,name)
        
    def get_action(self):
        [piles_draw,idx_draw] = self.game.get_piles_draw()
        if len(idx_draw) > 0:
            return 'draw'
        else:
            return 'take'

    def decision_take(self):
        return self.find_optimal_pile_take()

    def decision_draw(self,new_card):
        return self.find_optimal_pile_draw(new_card)


class HumanPlayer(PolychromePlayer):
    """ Human Polychrome Player

    All decisions are made through input()
    """
    def __init__(self,name):
        PolychromePlayer.__init__(self, name)
        # Set up the terminal window for this player.
        self.polychrome_layout = terminal.PolychromeLayout(terminal.Terminal(sys.stdout))
        self.take_pile = 0
    def display_draw_or_take_status(self):
        """ draw the current game status in self.polychrome_layout """
        # Prepare and draw all the player's stacks
        player_piles = [{'name': p.name, 'cards': p.cards, 'score': self.game.score(p.cards)} for p in self.game.players]
        self.polychrome_layout.player_piles = terminal.Piles(self.polychrome_layout.left_col, player_piles)
        self.polychrome_layout.player_piles.refresh()

        # Prepare the deck stack and the regular piles
        piles  = [{'name': 'Deck',
                   'cards': ['black']*len(self.game.deck),
                   'action_text': 'Draw a card from the deck',
                   'action_response': { 'action': 'draw' } }]
        for i,p in enumerate(self.game.piles):
            piles.append({ 'cards': p,
                           'name': 'Pile {0}'.format(i),
                           'action_text': 'Take pile {0}'.format(i),
                           'action_response': { 'action': 'take', 'pile': i },
                           'pile_taken': self.game.piles_taken[i],
                           'selectable': not self.game.piles_taken[i] })
        self.polychrome_layout.piles = terminal.Piles(self.polychrome_layout.right_col, piles)
        self.polychrome_layout.piles.select_first()
        self.polychrome_layout.piles.refresh()
        self.polychrome_layout.print_pile_action()

    def display_place_on_pile_status(self, card):
        """ draw the current game status in self.polychrome_layout """
        # Prepare and draw all the player's stacks
        player_piles = [{'name': p.name, 'cards': p.cards, 'score': self.game.score(p.cards)} for p in self.game.players]
        self.polychrome_layout.player_piles = terminal.Piles(self.polychrome_layout.left_col, player_piles)
        self.polychrome_layout.player_piles.refresh()

        # Prepare the deck stack and the regular piles
        piles  = [{'name': 'Deck',
                   'cards': [None]*len(self.game.deck),
                   'action_text': 'Draw a card from the deck',
                   'action_response': { 'action': 'draw' },
                   'selectable': False }]
        for i,p in enumerate(self.game.piles):
            piles.append({ 'cards': p,
                           'name': 'Pile {0}'.format(i),
                           'action_text': ['Place ', terminal.ColoredString(terminal.CARD_CHAR, card), ' on Pile {0}'.format(i)],
                           'action_response': { 'action': 'place', 'pile': i },
                           'pile_taken': self.game.piles_taken[i],
                           'selectable': not self.game.piles_taken[i] })
        self.polychrome_layout.piles = terminal.Piles(self.polychrome_layout.right_col, piles)
        self.polychrome_layout.piles.select_first()
        self.polychrome_layout.piles.refresh()
        self.polychrome_layout.print_pile_action()
    def end_game(self):
        self.display_draw_or_take_status()
        self.polychrome_layout.exit()

    def get_action(self):
        while True:
            self.display_draw_or_take_status()
            action = self.polychrome_layout.block_for_input()
            if action['action'] == 'draw':
                return 'draw'
            if action['action'] == 'take':
                self.take_pile = action['pile']
                return 'take'
            if action['action'] == 'quit':
                self.polychrome_layout.exit()
            else:
                self.polychrome_layout.bottom_area.add_str(0,0,'Error, action not understood')


    def decision_take(self):
        return self.take_pile

    def decision_draw(self, new_card):
        while True:
            self.display_place_on_pile_status(new_card)
            time.sleep(.1)
            action = self.polychrome_layout.block_for_input()
            if action['action'] == 'place':
                return action['pile']
            if action['action'] == 'quit':
                self.polychrome_layout.exit()
            else:
                self.polychrome_layout.bottom_area.add_str(0,0,'Error, action not understood')

    def print_status(self):
        """ print game status

        reprint the player statuses and pile contents so the human player can
        see what's going on

        """
        for p in self.game.players:
            self.game.print_player_status(p)
        self.game.print_piles()

class RandomBot(PolychromePlayer):
    """ Polychrome AI player which makes all decisions randomly """
    def __init__(self,name):
        PolychromePlayer.__init__(self,name)
    def get_action(self):
        if random() > 0.5:
            return 'draw'
        else:
            return 'take'

    def decision_take(self):
        """ Randomly decide to take one of the available piles """
        [piles_take,idx_take] = self.game.get_piles_take()
        return sample(idx_take,1)[0]

    def decision_draw(self,new_card):
        """ Randomly decide on which pile to place the drawn card """
        [piles_draw,idx_draw] = self.game.get_piles_draw()
        return sample(idx_draw,1)[0]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Play a game of polychrome')
    parser.add_argument('--debug', action='store_true', default=False, 
                        help='Run with rpdb2 hooks started for connecting via winpdb')
    parser.add_argument('--play', action='store_true', default=False, 
                        help='Start playing as a human player')
    parser.add_argument('--set-ais', dest='AIs', metavar='AI', type=str, nargs='+', default=[],
                        help='A list of AIs to play against')
    parser.add_argument('--scoring', type=str, default='scoring1',
                        help='A list of AIs to play against')
    args = parser.parse_args()

    ## Handle all the argument parsing

    # Start debug if neccessary
    if args.debug:
        # For debugging with winpdb
        try:
            print('Starting rpdb debugger with password \'x\'')
            import rpdb2; rpdb2.start_embedded_debugger('x')
        except ImportError:
            pass

    players = []
    # Add a human player if requested
    if args.play:
        players.append(HumanPlayer('Human'))

    # Run through the list of AIs given and do some fancy introspection to add them
    if len(args.AIs) == 0:
        # If no list of AIs is given, put in a defalt
        players.append(GreedyBot('Greedy'))
        players.append(GreedyBot('Random'))
    else:
        # get a list of all AI classes.  I.e., all classes in the current scope that derive from PolychromePlayer
        scope = locals()
        ais = {}
        for k in list(scope.keys()):
            if isinstance(scope[k], type) and issubclass(scope[k], (PolychromePlayer,)):
                ais[k] = scope[k]
        
        for i,ai in enumerate(args.AIs):
            try:
                players.append(scope[ai]('Player {0}'.format(i)))
            except KeyError as e:
                sys.stderr.write("Unknown AI {0}\n".format(e))

    # Set up the scoring method
    scoring = {'scoring1': scoring1, 'scoring2': scoring2}[args.scoring]


    ## Start the game
    game = PolychromeGame(players, scoring)
    if args.play:
        game.set_log_mode('buffer')
    else:
        game.set_log_mode('print')
    game.play()
