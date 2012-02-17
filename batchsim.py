# -*- coding: utf-8 -*-
#Batch simulator for polychrome
#
#Created: CS Lee 4 Feb. 2012

from polychrome import *
from ui_simulator import *
from PyQt4 import QtCore, QtGui
#from numpy import *

class Simulator(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_Simulator()
        self.game = None
        self.players = []
        self.player_types = []
        self.scoring_schemes = [[0,1,3,6,10,15,21],[0,1,4,8,7,6,5]]
        self.populate_players()
        self.setup_ui()
    
    def setup_ui(self):
        self.ui.setupUi(self)
        # populate the UI combo boxes
        player_names = [t.__name__ for t in self.player_types]
        player_names.insert(0,'None')
        self.boxes = [self.ui.cbo_player1,self.ui.cbo_player2,self.ui.cbo_player3,
                 self.ui.cbo_player4,self.ui.cbo_player5]
        for box in self.boxes:
            box.addItems(player_names)
            if box is not self.ui.cbo_player1:
                box.setEnabled(False)
                
        # populate the scoring schemes
        for s in self.scoring_schemes:
            self.ui.cbo_scoring.addItem(str(s))
            
        # connect UI elements
        self.ui.btn_go.clicked.connect(self.do_simulation)
        for box in self.boxes:
            box.currentIndexChanged.connect(self.validate_checkbox)
        
    def populate_players(self):
        """
        Inform the simulator of known Polychrome Player types
        """
        self.player_types = PolychromePlayer.__subclasses__()
        self.player_types.remove(HumanPlayer)
        
    def do_simulation(self):
        n_runs = self.ui.spin_n_games.value()
        if not n_runs > 0:
            QtGui.QMessageBox.warning(self,"Number of games must be at least 1")
            return
        self.log('#### Starting Batch Simulation ####')
        # create the players
        self.players = []
        n = 0
        for box in self.boxes:
            n += 1
            idx = box.currentIndex()
            if idx > 0:
                player_name = 'Player '+str(n)
                player_class = self.player_types[idx-1]
                self.players.append(player_class(player_name))
        self.log('Players are: '+str([p.__class__.__name__ for p in self.players]))
        
        # get the scoring scheme
        idx_scoring = self.ui.cbo_scoring.currentIndex()
        scoring = self.scoring_schemes[idx_scoring]
        self.log('Scoring is: '+str(scoring))
        
        for n in range(n_runs):
            # reset players
            for p in self.players:
                p.__init__(p.name)
            self.log('\n>>>>>>> Starting Game #'+str(n+1)+'/'+str(n_runs)+' <<<<<<<\n')
            game = PolychromeGame(self.players,scoring)
            game.play()
            self.log(game.flush_log())
            self.ui.progress_bar.setValue(int(100*n+1/n_runs))
                 
    def validate_checkbox(self,idx):
        """
        If the selection is set to 'None', then make sure all subsequent boxes
        are set to 'None' as well and disabled
        """
        box = self.sender()
        idx = self.boxes.index(box)
        if box.currentText() == 'None':
            for i in range(idx+1,5):
                self.boxes[i].setCurrentIndex(0)
                self.boxes[i].setEnabled(False)
        else:
            if idx < 4:
                self.boxes[idx+1].setEnabled(True)
                
    def log(self,msg):
        """
        append a string to the log
        """
        self.ui.txt_log.append(msg)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    main = Simulator()
    main.show()
#    sys.exit(app.exec_())