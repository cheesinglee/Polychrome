# -*- coding: utf-8 -*-
"""
Created on Tue Feb 28 16:31:24 2012

@author: cheesinglee
"""

import sys
from PyQt4 import QtCore, QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

class QFigure(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.axes = self.fig.add_subplot(111)
        
        # layout stuff
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.canvas)
        self.setLayout(vbox)
        
    def plot(self,*args,**kwargs):
        print(args)
        if kwargs.has_key('plotmethod'):
            method = kwargs['plotmethod']
            del kwargs['plotmethod']
        else:
            method = 'plot'
        getattr(self.axes,method)(*args,**kwargs)
        self.canvas.draw()


if __name__=="__main__":
    import numpy
    app = QtGui.QApplication(sys.argv)    
    main = QFigure()
    main.show()
    x = numpy.arange(-9,10)
    y = numpy.arange(-9,10)
    main.plot(x,y,plotmethod='bar',fc='green')
    sys.exit(app.exec_())
    