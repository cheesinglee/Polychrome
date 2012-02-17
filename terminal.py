#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

import termios, fcntl, struct, sys, os
import signal
import threading
import time
from collections import Counter

if sys.version_info.major == 3:
    unicode = str

class ColoredString(object):
    def __init__(self, string, foreground=None, background=None):
        self.string = string
        self.foreground = foreground
        self.background = background
    def __len__(self):
        return len(self.string)
    def __str__(self):
        return self.string
    def __repr__(self):
        return '<"{0}" background: {1} foreground: {2}>'.format(self.string, self.background, self.foreground)
    def __getitem__(self, item):
        return ColoredString(self.string[item], self.foreground, self.background)
    def split(self):
        return [self.__getitem__(i) for i in range(len(self.string))]
    def rasterize(self):
        return wrap_in_escaped_color(self.string, self.foreground, self.background)
    @classmethod
    def rasterize_any(cls, string):
        """ returns a raserized version of a string, ColoredString, or a list """
        if type(string) in (str, unicode):
            return string
        if type(string) is ColoredString:
            return string.rasterize()
        if type(string) in (list, tuple):
            return ''.join([ColoredString.rasterize_any(s) for s in string])
        raise ValueError('Unknown type for rasterize_any: {0}'.format(type(string)))

    @classmethod
    def split_any(cls, string):
        """ splits a ColoredString or a list of ColoredString into a list where
        each element is a single character """
        if type(string) in (str, unicode):
            return list(string)
        if type(string) is ColoredString:
            return string.split()
        if type(string) in (list, tuple):
            ret = []
            for s in string:
                ret += ColoredString.split_any(s)
            return ret
        raise ValueError('Unknown type for split_any: {0}'.format(type(string)))

def color(foreground=None, background=None):
    def rgb_to_color(r,g,b):
        return int(r/256.*5*36) + int(g/256.*5*6) + int(b/256.*5) + 16

    colors = { 'black': '000',  #standard xterm colors
               'red': '001',
               'green': '002',
               'yellow': '003',
               'purple': '004',
               'magenta': '005',
               'cyan': '006',
               'gray': '007',

               'orange': '172',  #colors from http://www.mudpedia.org/wiki/Xterm_256_colors
               'blue': '039',
               'brown': '088',
               'yellow': '226',
               'gray': '248',
               'green': '071',
               'pink': '212',
               'wild': '201',
               '+2': '255' }
    
    ret_foreground = ''
    ret_background = ''
    if type(foreground) == str:
        ret_foreground = '\x1b[38;5;{color}m'.format(color=colors[foreground])
        # special exception for wild cards!
        if foreground == 'wild':
            ret_foreground = '\x1b[38;5;{color}m'.format(color=colors['black'])
            ret_foreground = '\x1b[48;5;{color}m'.format(color=colors[foreground])
    elif type(foreground) in (list, tuple):
        ret_foreground = '\x1b[38;5;{color}m'.format(rgb_to_color(*foreground))

    if type(background) == str:
        ret_background = '\x1b[48;5;{color}m'.format(color=colors[background])
    elif type(background) in (list, tuple):
        ret_background = '\x1b[48;5;{color}m'.format(rgb_to_color(*background))
    # if both foreground and background are none, we want the default coloring
    if foreground is None and background is None:
        foreground = '\033[0m'

    return ret_background+ret_foreground

def wrap_in_escaped_color(string, foreground=None, background=None):
    return color(foreground, background) + string + '\033[0m'

def split_display_chars(string):
    """ Returns a list of the chars in string where each character is a character that gets displayed,
    i.e., escape characters count as zero-width """
    tmp_buf = []
    char_buf = []
    i = 0
    while i < len(string):
        char_buf = [string[i]]
        if string[i] == '\033':
            while string[i].lower() not in  ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']:
                i += 1
                char_buf.append(string[i])

        tmp_buf.append(''.join(char_buf))
        i += 1
    #tmp_buf still contains zero-width chars.  We need to collapse all of those
    def eat_char(l, c=''):
        if len(l) == 0:
            return (c, [])
        if len(l[0]) > 1:
            c += l[0]
            return eat_char(l[1:], c)
        c += l[0]
        return (c, l[1:])

    ret = []
    remander = tmp_buf
    while len(remander) > 0:
        c, remander = eat_char(remander)
        ret.append(c)

    return ret

def num_to_subscript(string):
    intab = '0123456789'
    outtab = '₀₁₂₃₄₅₆₇₈₉'
    transtab = dict(zip(intab, outtab))
    ret = []
    for c in string:
        ret.append(transtab[c])
    return ''.join(ret)


class SubWindow(object):
    """ A subwindow of a Terminal. All rendering in the subwindow
    will take place relative to it's x,y coordinates """
    def __init__(self, term, x, y, width, height):
        self.term = term
        self.x, self.y = x, y
        self.width, self.height = width, height
    def add_str(self, x, y, string):
        self.term.add_str(x + self.x, y + self.y, string)
    def erase(self):
        """ Replace every character inside the subwindow with a space """
        for j in range(self.height):
            self.add_str(0,j,' '*self.width)
    def refresh(self):
        self.term.refresh()

class ThreadedInputCallback(threading.Thread):
    """ watches self.stream for keypresses and directs them
        to callback when the occur """
    daemon = True
    def __init__(self, parent, callback):
        threading.Thread.__init__(self)
        self.callback = callback
        self.parent = parent
        self.STOP_THREAD = False
    def run(self):
        # from the standard library...
        fd = self.parent.stream.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

        try:
            while not self.STOP_THREAD:
                try:
                    c = sys.stdin.read(1)
                    command = c
                    if c == '\x1b':
                        # grab all the characters until the end of the escape sequence
                        while c.lower() not in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']:
                            c = sys.stdin.read(1)
                            command += c
                    if len(command) > 0:    #python3 allows empty reads for some reason...
                        self.callback(self.parent, command)
                except IOError: pass
                time.sleep(.1)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

class StringBuffer(object):
    """ Two-dimensional string array used to buffer the terminal
    when it isn't being written to """
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Buffer is initialized to all spaces
        self.lines = [[' ' for i in range(self.width)] for j in range(self.height)]

    def set(self, x, y, char):
        if 0 <= x < self.width and 0 <= y < self.height:
            split = ColoredString.split_any(char)
            for i,c in enumerate(split):
                if x + i < self.width:
                    self.lines[y][x + i] = c
    def erase(self):
        self.lines = [[' ' for i in range(self.width)] for j in range(self.height)]

class Terminal(object):
    def __init__(self, stream):
        self.stream = stream
        self.buffer = StringBuffer(*self.get_size())
        self.queued_refreshes = 0

    def get_size(self):
        width, height = 80, 40
        try:
            s = struct.pack("HHHH", 0, 0, 0, 0)
            fd_stdout = sys.stdout.fileno()
            x = fcntl.ioctl(fd_stdout, termios.TIOCGWINSZ, s)
            height, width = struct.unpack("HHHH", x)[:2]
        except:
            pass
        return (width, height)

    def move_cursor(self, x, y):
        self.stream.write('\033[{0};{1}H'.format(y + 1,x + 1))

    def resize(self, x=-1, y=-1):
        if x < 0  or y < 0:
            self.buffer = StringBuffer(*self.get_size())
        else:
            self.buffer = StringBuffer(x,y)

    def watch_resize(self, callback):
        """ connects callback to the terminal resize event.
        callback takes arguments of the terminal object followed
        by the size of the console """
        signal.signal(signal.SIGWINCH, lambda *x: callback(self, self.get_size()))

    def watch_input(self, callback):
        """ watches self.stream for keypresses and directs them
        to callback when the occur """
        self.input_thread = ThreadedInputCallback(self, callback)
        self.input_thread.start()

    def add_str(self, x, y, string):
        self.buffer.set(x, y, string)
#        self.move_cursor(x,y)
#        self.stream.write(string)
    def erase(self):
        self.stream.write('\033[2J')
    def hide_cursor(self):
        self.stream.write('\033[?25l')
        self.refresh()
    def show_cursor(self):
        self.stream.write('\033[?25h')
        self.refresh()

    def draw_box(self, x, y, width, height):
        for i in range(1, width):
            self.add_str(x + i, y, ColoredString('─', 'pink', background='gray'))
            self.add_str(x + i, y + height, '─')
        for i in range(1, height):
            pass
            self.add_str(x, y + i, '│')
            self.add_str(x + width, y + i, '│')
        self.add_str(x,y, '┌')
        self.add_str(x + width, y, '┐')
        self.add_str(x + width,y + height, '┘')
        self.add_str(x,y + height, '└')
        self.refresh()
    def draw_n_column_layout(self, x,y, width, height, n_cols):
        """ draw a border for a n_column layout """

        # Compute the space given to each column
        col_widths = []
        remaining_width = width - n_cols + 1
        for i in range(n_cols):
            col_width = remaining_width // (n_cols - i)
            remaining_width -= col_width
            col_widths.append(col_width)

        subwindows = []

        # Draw the vertical portion of each column
        offset = 0
        for j in range(1, height - 1):
            self.add_str(x, y + j, '│')
        for i in range(n_cols):
            for j in range(1, height - 1):
                self.add_str(x + offset + col_widths[i], y + j, '│')
            for j in range(1, col_widths[i]):
                self.add_str(x + offset + j, y, '─')
                self.add_str(x + offset + j, y + height - 1, '─')
            # Draw the T-joins
            if i < n_cols - 1:
                self.add_str(x + offset + j + 1, y, '┬')
                self.add_str(x + offset + j + 1, y + height - 1, '┴')
            # Create the subwindow for the current region
            subwindows.append(SubWindow(self, x + offset + 1, y + 1, col_widths[i] - 1, height - 2))
            offset += col_widths[i]
        self.add_str(x,y, '┌')
        self.add_str(x + width - 1, y, '┐')
        self.add_str(x + width - 1,y + height - 1, '┘')
        self.add_str(x,y + height - 1, '└')
        self.refresh()

        return subwindows


    def refresh(self):
        def flush():
            if self.queued_refreshes == 0:
                return
            try:
                for i,line in enumerate(self.buffer.lines):
                    self.move_cursor(0,i)
                    self.stream.write(ColoredString.rasterize_any(line))
                self.stream.flush()
                self.queued_refreshes = 0
            except IOError:
                timer = threading.Timer(.1, flush)
                timer.start()
        # when we get a call to refresh, delay it by .1 secs to amalgomate any other refresh
        # calls
        self.queued_refreshes += 1
        timer = threading.Timer(.1, flush)
        timer.start()


class PolychromeLayout(object):
    """ Manages a two-column layout for a game of polychrome """
    def __init__(self, term):
        self.term = term

        self.resize_callback()

        self.term.watch_input(self.keypress_callback)
        self.term.watch_resize(self.resize_callback)
        self.term.hide_cursor()

        self.piles = Piles(self.left_col, [])
        self.piles.refresh()
        self.message_area.add_str(0,0, "'q' to quit")

        self.blocking = threading.Event()
        self.blocking.clear()
        self.action = { 'action': None }

    def exit(self):
        """ exit the game and clean up the terminal """
        self.term.input_thread.STOP_THREAD = True
        self.term.input_thread.join()
        self.term.show_cursor()
        sys.exit()

    def block_for_input(self):
        self.blocking.clear()
        self.blocking.wait()
        return self.action

    def set_title(self, title):
        self.title_area.erase()
        self.title_area.add_str(0,0, ColoredString(' ' + title, 'red'))

    def draw_columns(self, top_padding = 1, bottom_padding = 1):
        width, height = self.term.get_size()
        self.left_col, self.right_col = self.term.draw_n_column_layout(0, top_padding, width, height - (top_padding + bottom_padding), n_cols=2)
        self.bottom_area = SubWindow(self.term, 0, height - 1, width - 40, 1)
        self.message_area = SubWindow(self.term, width - 40, height - 1, 40, 1)
        self.title_area = SubWindow(self.term, 0, 0, width, 1)
    def print_pile_action(self):
        """ prints the action_text associated with each pile """
        self.bottom_area.erase()
        if 0 <= self.piles.selected < len(self.piles.piles) and 'action_text' in self.piles.piles[self.piles.selected]:
            self.bottom_area.add_str(0,0, self.piles.piles[self.piles.selected]['action_text'])
        self.bottom_area.refresh()

    def keypress_callback(self, term, key):
        if key == '\x1b[A':
            # up
            self.piles.select_previous()
            self.print_pile_action()
        elif key == '\x1b[B':
            # down
            self.piles.select_next()
            self.print_pile_action()
        elif key == '\x1b[C':
            # right
            pass
        elif key == '\x1b[D':
            # left
            pass
        elif key == '\n':
            self.action = self.piles.get_selected()['action_response']
            self.blocking.set()
        elif key == 'q':
            self.action = {'action': 'quit'}
            self.blocking.set()
        else:
            self.bottom_area.add_str(0,0, "I don't understand '{0}'".format(key))

    def resize_callback(self, term=None, size=(0,0)):
        self.term.resize()
        self.draw_columns()
        self.set_title('Polychrome')    # Must be done after draw_columns()
        self.term.refresh()

class Piles(object):
    """ Class to display card piles or player hands """
    def __init__(self, term, piles=None):
        """ @term is the terminal/subwindow where the piles should be rendered,
            @piles is a list of piles to render
        """
        self.term = term
        self.piles = piles if piles is not None else []
        self.selected = -1
    def __len__(self):
        return len(self.piles)
    def select(self, pile):
        """ Draw a selection indicator in front of the pile
        @pile.  -1 means no pile is selected """
        self.selected = pile
        self.refresh()
    def get_selected(self):
        """ Returns the currently selected pile """
        if 0 <= self.selected < len(self.piles):
            return self.piles[self.selected]
        else:
            return None
    def select_first(self):
        """ Select the first pile with the selectable trait """
        try:
            self.selected = [p.get('selectable', True) for p in self.piles].index(True)
        except ValueError:
            self.selected = -1

    def select_next(self):
        selectable = []
        # get a list of all the piles that are selectable or have no selectable property
        for i,p in enumerate(self.piles):
            if p.get('selectable', True):
                selectable.append(i)
        if self.selected in selectable:
            self.selected = selectable[(selectable.index(self.selected) + 1) % len(selectable)]
        else:
            self.selected = selectable[0]
        self.refresh()

    def select_previous(self):
        selectable = []
        # get a list of all the piles that are selectable or have no selectable property
        for i,p in enumerate(self.piles):
            if p.get('selectable', True):
                selectable.append(i)
        if self.selected in selectable:
            self.selected = selectable[(selectable.index(self.selected) - 1) % len(selectable)]
        else:
            self.selected = selectable[-1]
        self.refresh()

    def refresh(self):
        self.term.erase()

        for i,p in enumerate(self.piles):
            card_list = [' ']
            # get a cound of the number of each color of cards so we can
            # display how many there are as a subscript
            counted = Counter(p['cards'])
            
            for c in counted:
                # if there is more than one card of a particular color, display a subscript number of how many cards there are
                card_in_color = ColoredString('▊', c)
                number_of_cards = num_to_subscript(str(counted[c]))
                card_list.append(card_in_color)
                if counted[c] > 1:
                    card_list.append(number_of_cards)
            pile_name = p['name']
            if p.get('pile_taken', False):
                pile_name += ' (Taken)'
            if 'score' in p:
                pile_name += ' Score: {0}'.format(p['score'])
            self.term.add_str(2, i*2, pile_name)
            self.term.add_str(3, i*2 + 1, card_list)
            # draw a selection character if neccessary
            if i == self.selected:
                self.term.add_str(0, i*2 + 1, '>')

        self.term.refresh()
