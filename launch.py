"""
Power up various DPSS laser models and read back fault and status conditions

* Andor uses several brands of diode solid-state continuous wave lasers in the
  launch.
  Supported:
  - Coherent Cube, Sapphire
  - Cobolt Generation 3, Generation 4
  - External gas laser
  Not yet supported:
  - Cobolt Compass, Calypso
  - Melles Griot
  - Guess method for >4 laser line ALC not implemented yet
"""

import devasys
import prolific

class Laser:
  """Serial laser device"""
  type = (
    "EXTERNAL",
    "CUBE",
    "SAPPHIRE",
    "MG560",
    ("COBOLTJIVE", "COBOLTFANDANGO", "COBOLTMAMBO"),
    ("COBOLTJIVE4", "COBOLTFANDANGO4", "COBOLTMAMBO4"),
  )
  
  def __init__(self, port):
    pass
  
  """
  Each laser needs the following:
  
  Communication
  - Baudrate
  
  Delays
  - Each command
  - Time-out to stabilize
  
  Command strings:
  - Initialize
  - Turn on
  - Turn off
  - Status condition
  - Error condition
  
  Tertiary commands
  - Power rating
  - Regex to confirm identity of laser if unknown
  
  Return strings
  - Status
    * Power locked
    * Warming up
  - Error
    * Serious fault
    * Needs recalibration service
  """