'''
Created on Feb 20, 2013

@author: crisr
'''
from __future__ import division, print_function, unicode_literals, absolute_import
import warnings
warnings.simplefilter('default',DeprecationWarning)

import xml.etree.ElementTree as ET
import os
from Simulation import Simulation
import sys
import matplotlib.pyplot as plt

debug = True

if __name__ == '__main__':
  # Retrieve the framework directory path
  frameworkDir = os.path.dirname(os.path.abspath(sys.argv[0]))
  # open the XML input 
  try:
    if len(sys.argv) == 1:
      inputFile = 'test.xml' 
    else:
      inputFile = sys.argv[1]
  except:
    raise IOError ('input file not provided')
  workingDir = os.getcwd()
  if not os.path.isabs(inputFile):
    inputFile = os.path.join(workingDir,inputFile)
  if not os.path.exists(inputFile):
    print('file not found '+inputFile)
  
  # Try to parse the input => No try statement here otherwise 
  # the parse will not give us information about the eventual errors occurred 
  tree = ET.parse(inputFile)
  if debug: print('opened file '+inputFile)

  root = tree.getroot()

  # generate all the components of the simulation
  simulation = Simulation(inputFile, frameworkDir)
  #Call the function to read and construct each single module of the simulation 
  simulation.XMLread(root)
  # Run the simulation 
  simulation.run()
  
  # TO BE DELETED
  plt.show()

