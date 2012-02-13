#!/usr/bin/python
# -*- coding: utf-8 -*-
# Created: 30 January 2012, Chee Sing Lee

from __future__ import print_function
from random import shuffle, sample, random
from itertools import combinations_with_replacement
import sys
import copy

if sys.version_info.major == 2:
    input = raw_input

# define scoring schemes
scoring1 = [0,1,3,6,10,15,21,21,21,21]
scoring2 = [0,1,4,8,7,6,5,5,5,5]

CARD_CHAR = '▮'
def wrap_color(string, color, weight='standard'):
    def rgb_to_color(r,g,b):
        return int(r/256.*5*36) + int(g/256.*5*6) + int(b/256.*5) + 16
    weights = { 'standard': '0',
                'bold': '1' }
    colors = { 'orange': '172',  #colors from http://www.mudpedia.org/wiki/Xterm_256_colors
               'blue': '039',
               'brown': '088',
               'yellow': '226',
               'gray': '248',
               'green': '071',
               'pink': '212',
               'wild': '201',
               '+2': '255' }

    #color_start = '\033[{weight};{color}m'.format(color=colors[color], weight=weights[weight])
    color_start = '\x1b[38;5;{color}m'.format(color=colors[color])
    color_end = '\033[0m'
    
    return color_start + string + color_end

class PolychromeGame:
    """ Class for playing Polychrome """
    deck = []
    players = []
    two_player = False
    colors = ['green','blue','brown','yellow','gray','pink','orange']
    piles = []
    piles_taken = []
    scoring = []
    log_dest = ''

    def __init__(self,players,scoring):
        self.two_player = False
        self.initialize_deck()
        self.scoring = scoring
        self.players = players
        self.piles = [list() for p in self.players]

    def initialize_deck(self):
        """ populate the Polychrome deck """

        # 7 colors (if >3 players, 6 if >2 players, else 5 colors), 9 of each
        reduce_colors_by = 2 if len(self.players) == 2 else 1 if len(self.players) == 3 else 0
        self.deck = self.colors[reduce_colors_by:]*9

        # 3 wilds
        self.deck.extend(['wild']*3)

        # 10 bonus "+2" cards
        self.deck.extend(['+2']*10)

        # shuffle
        shuffle(self.deck)

    def play(self):
        """ Play one game of Polychrome
        """
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
            self.piles = [list() for n in range(n_players)]
            # all players are in again
            self.piles_taken = [False]*n_players
            for p in self.players:
                p.out = False
                self.print_player_status(p)
            while not all(self.piles_taken):
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
            # adjust the player index so that the last player to take in this
            # round is the starting player for the next round
            player_idx -= 1
        self.log('\n----Game Over----')
        final_scores = self.compute_scores()
        for p in self.players:
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
            # scoring without wilds
            values = [self.scoring[n] for n in color_counts_no_wild]
            values.sort(reverse=True)
            score = 0
            for n in range(7):
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
                (len(self.piles[0]) == 1 and not self.piles_taken[0]) and
                (len(self.piles[1]) == 2 and not self.piles_taken[1]) and
                (len(self.piles[2]) == 3 and not self.piles_taken[2]))

    def set_log_output(self,dest):
        self.log_dest = dest

    def log(self,s):
        if len(self.log_dest) == 0:
            # log to console
            print(s)
        else:
            try:
                fid = open(s,'a')
                fid.write(s+'\n')
            except:
                print('Error, could not write log to file '+self.log_dest)

    def print_player_status(self,p):
        score = self.score(p.cards)
        cards = list(p.cards)
        cards.sort()

        s = ''.join(wrap_color(CARD_CHAR, color) for color in cards)
        template = '{name}:\t{score} points\nHand: {hand}'.format(name=p.name, score=score, hand=s)
        s = '\x1b\x5b1;31;40m'+template+'\033[0m'

        #template = '{name}:\t{score} points\n\
        #Orange: {n_orange}\tBlue: {n_blue}\tBrown: {n_brown}\n\
        #Yellow: {n_yellow}\tGray: {n_gray}\tGreen: {n_green}\n\
        #Pink  : {n_pink}\tWild: {n_wild}\t+2   : {n_bonus}'
        #s = template.format(name=p.name,score=str(score),
        #                    n_orange=str(cards.count('orange')),
        #                    n_blue=str(cards.count('blue')),
        #                    n_brown=str(cards.count('brown')),
        #                    n_yellow=str(cards.count('yellow')),
        #                    n_gray=str(cards.count('gray')),
        #                    n_green=str(cards.count('green')),
        #                    n_pink=str(cards.count('pink')),
        #                    n_wild=str(cards.count('wild')),
        #                    n_bonus=str(cards.count('+2')))
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
            if not self.two_player:
                if not self.piles_taken[i] and len(p) > 0:
                    idx_take.append(i)
                    piles_take.append(p)
            else:
                if len(p) > i and not self.piles_taken[i]:
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

    def get_action():
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

class BuilderBot(PolychromePlayer):
    """
    BuilderBot will always draw if possible. It places the drawn card in the
    pile which will give the maximum score increase
    """
    def __init__(self,name):
        PolychromePlayer.__init__(self,name)


class HumanPlayer(PolychromePlayer):
    """ Human Polychrome Player

    All decisions are made through input()
    """
    def __init__(self,name):
        PolychromePlayer.__init__(self,name)
    def get_action(self):
        while True:
            action = input('Would you like to [t]ake or [d]raw? [ENTER for status] ').lower()
            if len(action) == 0:
                self.print_status()
            elif action == 't':
                return 'take'
            elif action == 'd':
                return 'draw'
            else:
                print('Please answer "t" or "d"')

    def decision_take(self):
        while True:
            n = input('Enter the number of the pile you would like to pick up: [ENTER for status] ')
            if len(n) == 0:
                self.print_status()
            elif not n.isdigit():
                print('Enter a numerical value')
                continue
            else:
                n = int(n)
                if self.game.piles_taken[n]:
                    print('Pile has already been taken')
                elif len(self.game.piles[n]) == 0:
                    print('Cannot pick up empty pile')
                elif n >= len(self.game.piles):
                    print('Invalid number')
                else:
                    return n

    def decision_draw(self,new_card):
        while True:
            n = input('Enter the number of the pile on which you would like put the new card: [ENTER for status] ')
            if len(n) == 0:
                self.print_status()
            elif not n.isdigit():
                print('Enter a numerical value')
                continue
            else:
                n = int(n)
                if self.game.piles_taken[n]:
                    print('Pile has already been taken')
                elif len(self.game.piles[n]) == 3:
                    print('Pile is already full')
                elif n >= len(self.game.piles):
                    print('Invalid number')
                else:
                    return n

    def print_status(self):
        """ print game status

        reprint the player statuses and pile contents so the human player can
        see what's going on

        """
        for p in self.game.players:
            self.game.print_player_status(p)
        self.game.print_piles()

class RandomPlayer(PolychromePlayer):
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
        n_players = len(self.game.players)
        # available piles are those which have not yet been taken, and which
        # contain cards
        available_piles = [i for i in range(n_players)
                            if not self.game.piles_taken[i] and
                            any(self.game.piles[i])]
        return sample(available_piles,1)[0]

    def decision_draw(self,new_card):
        """ Randomly decide on which pile to place the drawn card """
        n_players = len(self.game.players)
        # valid piles are those which have not yet been taken, and which
        # contain fewer than 3 cards
        valid_piles = [i for i in range(n_players)
                        if not self.game.piles_taken[i] and
                        len(self.game.piles[i]) < 3]
        return sample(valid_piles,1)[0]

if __name__ == "__main__":
    # example game with 3 RandomPlayers and 1 HumanPlayer
    players = []
    for i in range(3):
        players.append(RandomPlayer('Player '+str(i)))
    players.append(GreedyBot('Greedy'))
#    player_name = input('Enter your name: ')
#    players.append(HumanPlayer(player_name))
    game = PolychromeGame(players,scoring1)
    game.play()
