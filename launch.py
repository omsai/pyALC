'''
Turn on Andor Laser Launch as a 'dumb' box for Analog control

Andor uses several brands of diode solid-state continuous wave lasers in the
launch.  Rejects serial squids not on the same USB parent branch as the DeVaSys.
'''

from devasys import Microcontroller
from prolific import ProlificPorts
from laser import Cube, Sapphire, Cobolt3, Cobolt4
  
class Launch():
  def __init__(self_):
    TYPE = (
      'CUBE',
      'SAPPHIRE',
    )
    if type not in TYPE:
      if type in ['COBOLTJIVE', 'COBOLTFANDANGO', 'COBOLTMAMBO']:
        type = 'COBOLT3'
      elif type in ['COBOLTJIVE4', 'COBOLTFANDANGO4', 'COBOLTMAMBO4']:
        type = 'COBOLT4'
      else:
        print 'LaserError: Unknown type of laser:', type
        return
    
    