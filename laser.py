'''
Power up Diode and DPSS laser models reading back fault and status conditions

Supported-
Coherent: Cube, Sapphire
Cobolt: Generation 3, Generation 4

Not tested or supported-
Cobolt: Compass, Calypso
Melles Griot: 560
'''

from serial import Serial
from time import sleep

class Laser:
  '''Serial laser device communication'''
  def __init__(self, port):
    self.BAUD = 19200
    self.COMMAND_DELAY = 0.5    # seconds
    self.TIMEOUT_STABILIZE = 3  # minutes
    self.JUNK_CHARACTERS = '\r\n\x00'
    
    try:
      self.ser = Serial(
                   port = port,
                   baudrate = self.BAUD,
                   bytesize = 8,
                   parity='N', stopbits=1, timeout=1
                 )
      self.ser.setRTS(level=1)
      self.ser.setDTR(level=1)
      if self.ser.isOpen():
        print 'Successfully opened', self.port
      else:
        print 'Failed to open', self.port
        return
    except:
      self.ser.close() # since an exception leaves the COM port open
      raise
  
  def serial_check(self, command, expected_output=None):
    self.ser.write(command + '\r\n')
    sleep(0.01) # wait 10ms
    output = self.ser.readlines() # takes seconds to read all lines
    if output is not None:
      if isinstance(output,list): # readlines always returns a list
        for string in output:
          if string.strip(self.JUNK_CHARACTERS) == expected_output:
            return True
        #print 'DEBUG: Expected', expected_output, 'but got', output
        return False
    else:
      return True
  
  def run(self):
    pass

class Sapphire(Laser):
  '''Laser control of Coherent Sapphire'''
  def __init__(self, port):
    self.INIT = ['>=0', 'L=1']
    self.ON = ['L=1']
    self.OFF = ['L=0']
    self.CHECK_STATUS = ['?STA']
    self.CHECK_ERROR = ['?F']
    self.ERROR = {
      1: 'Interlock',
    }
    
    Laser.__init__(self, port)
    
    # State transition table
    T = {
      ('s0', [6]): ('s1', 1, self.INIT),
      ('s0', range(1,5)): ('s2', 1, self.ON),
      ('s0', [5]): ('s3', 1, None),
      ('s1', range(1,5)): ('s2', 1, self.ON),
      ('s1', [5]): ('s3', 1, None),
      ('s1', [6]): ('s4', 0, None),
      ('s2', [5]): ('s3', 1, None),
      ('s2', range(1,5)): ('s2', 1, self.ON),
      ('s2', [6]): ('s2', 0, None),
      ('s3', [5]): ('s3', 1, None),
      ('s3', [6]): ('s3', 0, None),
      ('s3', range(1,5)): ('s3', 0, None),
    }

class Cobolt4(Laser):
  '''Laser control of Cobolt Generation 4'''
  def __init__(self, port):
    self.INIT = ['cf']
    self.ON = ['lten1', 'xten1', '@cob 1', 'l1']
    self.OFF = ['l0']
    self.CHECK_STATUS = ['leds?']
    self.CHECK_ERROR = ['f?']
    self.ERROR = {
      3: 'Interlock',
    }
    
    Laser.__init__(self, port)
    
    def expand(binary):
      '''Returns binary permutations from a string of 1, 0 and x (don't care)'''
      result = []
      for n in binary:
        if n == 'x':
          if len(result) == 0:
            result = ['0b1','0b']
          else:
            i = 0
            length = len(result)
            while i < length:
              result[i] = result[i] + '0'
              result.append(result[i] + '1')
              i += 1
        else:
          if len(result) == 0:
            result = ['0b' + n]
          else:
            i = 0
            while i < len(result):
              result[i] = result[i] + n
      return result
    
    # State transition table
    T = {
      ('s0', expand('0xxx')): ('s1', 1, self.INIT),
      ('s0', expand('11xx')): ('s2', 1, None),
      ('s0', expand('10xx')): ('s3', 1, None),
      ('s1', expand('11xx')): ('s2', 1, self.ON),
      ('s1', expand('10xx')): ('s2', 1, None),
      ('s1', expand('00xx')): ('s4', 0, None),
      ('s2', expand('10xx')): ('s3', 1, None),
      ('s2', expand('11xx')): ('s2', 1, None),
      ('s2', expand('0xxx')): ('s4', 0, None),
      ('s3', expand('10xx')): ('s3', 1, None),
      ('s3', expand('11xx')): ('s4', 0, None),
      ('s3', expand('0xxx')): ('s4', 0, None),
    }

  '''
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
  '''