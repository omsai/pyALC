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
from string import rjust

class Laser:
  '''Serial laser device communication'''
  def __init__(self, port):
    '''Set serial communication defaults and open COM port'''
    self.port = port
    self.BAUD = 19200
    self.COMMAND_DELAY = 0.5    # seconds
    self.TIMEOUT_STABILIZE = 3  # minutes
    self.JUNK_CHARACTERS = '\r\n\x00'
    
    try:
      self.ser = \
      Serial(
        port = port,
        baudrate = self.BAUD,
        bytesize = 8,
        parity='N', stopbits=1, timeout=1
      )
      self.ser.setRTS(level=1)
      self.ser.setDTR(level=1)
      if self.ser.isOpen():
        print '(II) Successfully opened serial port', self.port
      else:
        print '(EE) Failed to open serial port', self.port
        return
    except:
      self.ser.close() # since an exception leaves the COM port open
      raise
  
  def serial_check(self, command_list, expected_output_list=None):
    '''Process multiple serial commands compare against expected output.
    
    Arguments:
    command_list --
      list or tuple of queries to serial device
      e.g. ['>=0', 'L=1']
    
    Keyword Arguments:
    expected_output_list --
      list or tuple of response from serial device
      e.g. [None, 'OK']
    
    A single command will still go through if no expected output is provided.
    This is to account for 'dumb' devices which do not respond, and for testing
    purposes, but otherwise it's bad practise so a warning is printed.  If one
    expects no output for a command, use `None`.
    '''
    verbose=True
    output_list = []
    
    if not (isinstance(command_list,tuple) or isinstance(command_list,list)):
      print '(EE) serial_check(): Expected command_list as list or tuple'
      return None
    
    while len(expected_output_list) < len(command_list):
      # Add `None` till the length matches
      expected_output_list.append(None)
    
    for i in range(0,len(command_list)):
      command = command_list[i]
      expected_output = expected_output_list[i]
      #print 'DEBUG: About to write serial command'
      self.ser.write(command + '\r\n')
      sleep(0.01) # wait 10ms
      output = self.ser.readlines() # takes seconds to read all lines
      
      if verbose:
        print rjust(command,20), ':', output,
      
      if expected_output is None:
        # One should always specify the output but don't make a big deal of it
        print '(WW) serial_check(): Output of', command, ':', output,\
              'but no expected output was stated'
        return output_list.append(output)
      
      if output is None:
        # Laser does not give output.
        # Assume it is 'dumb', so function terminates ok
        output_list.append(None)
        continue
      
      if not isinstance(output,list): # readlines always returns a list
        # Output should always be a list
        print '(EE) serial_check(): Output of', command, ':', output,\
              'but cannot parse since it is not a list'
        output_list.append(output)
       
      output_found = 0
      
      for string in output:
        # first assume number of expected outputs to check is just 1
        i = 1
        expected_output_item = expected_output
        
        # if multiple outputs are possible for this command,
        #   increase the expected_output list iteration
        if isinstance(expected_output,list) or\
           isinstance(expected_output,tuple):
          i = len(expected_output)
          expected_output_item = str(expected_output[0])
        
        while i > 0 and not output_found:
          stripped_output = string.strip(self.JUNK_CHARACTERS)
          if stripped_output == expected_output_item:
            output_found = 1
            output_list.append(stripped_output)
            print '-OK'
            i = 1
          i -= 1
          if i > 0:
            expected_output_item = str(expected_output[i])
      
      if not output_found:
        # FIXME: Return value of `False` is difficult handle.
        #   This would be better if there was a `tries` variable for the
        #   serial_check function to attempt to get the value it wants.
        #   default could be 3?
        print '-Expected output not found'
        print '(WW) serial_check(): Expected', expected_output_item,\
              'but got', output
        output_list.append(False)
    
    return output_list
  
  def run(self, loop=False):
    '''Loop the laser state machine until it reaches '''
    # States
    S = {
      's0': 'Unknown laser state',
      's1': 'Interlock open',
      's2': 'Warming up',
      's3': 'Power locked',
      's4': 'Error',
    }
    
    # Initial state
    self.serial_check(self.INIT, ['>=0', 'L=1'])
    machine_state = 's0'
    state_history = []
    machine_input = self.serial_check(self.CHECK_STATUS,
                                      [self.list_to_str(range(1,7))])
    state_history.append(S[machine_state])
    
    i = 100 # FIXME: timeout
    
    while(i > 0):
      print machine_state, ':', machine_input
      
      try:
        machine_state, expected_state, next_command = \
          self.TRANSITION_MATRIX[machine_state, tuple(machine_input)]
      except TypeError:
        print 'Variables values:'
        print 'machine_state', machine_state
        print 'machine_input', machine_input
        raise
      
      state_history.append(S[machine_state])
      try:
        if state_history[-1] == state_history[-2]:
          state_history.pop()
      except IndexError:
        # Ignore duplicate states if there are fewer than 2 items
        pass
      
      if not expected_state:
        # FIXME: Handle errors
        print '(EE) Broke out of state machine. State History:'
        print state_history
        break
      
      if machine_state == 's3':
        print '(II) State machine completed successfully'
        break
        
      if next_command is not None:
        machine_input = self.serial_check(next_command,
                                          next_command)
        machine_input = self.serial_check(self.CHECK_STATUS,
                                          [self.list_to_str(range(1,7))])
        
        if machine_input == [False]:
          # Laser has glitched or does not produce sane output
          # FIXME: This should be fixed in serial_check
          machine_input = self.serial_check(self.CHECK_STATUS,
                                            [self.list_to_str(range(1,7))])
        #print 'Machine input:', machine_input
      
      i -= 1
    
    print '(II) run() ended'
    
  def stop(self):
    # FIXME: Implement this
    pass
    
  def bin_expand(binary):
    '''Returns binary permutations from a string of 1, 0 and x (don't care)
    
    Example:
    >>> bin_expand('0x11')
    [
      '0b0011',
      '0b0111',
    ]
    '''
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
  
  def transition_expand(self,shorthand):
    expanded = {}
    for key, value in shorthand.iteritems():
      state = key[0]
      inputs = key[1]
      for input in inputs:
        expanded[(state, (input,))] = value
    return expanded
  
  def list_to_str(self, number_list):
    list_of_strings = []
    for number in number_list:
      list_of_strings.append(str(number))
    return tuple(list_of_strings)


class Sapphire(Laser):
  '''Laser control of Coherent Sapphire'''
  def __init__(self, port):
    # Laser commands and definitions
    self.INIT = ['>=0', 'L=1']
    self.ON = ['L=1']
    self.OFF = ['L=0']
    self.CHECK_STATUS = ['?STA']
    self.CHECK_ERROR = ['?F']
    self.ERROR = {
      '1': 'Interlock',
    }
    # State transition table, grouping state inputs in 'shorthand'
    TRANSITION_SHORTHAND = {
      ('s0', ('6',)): ('s1', 1, self.INIT),
      ('s0', self.list_to_str(range(1,5))): ('s2', 1, self.ON),
      ('s0', ('5',)): ('s3', 1, None),
      ('s1', self.list_to_str(range(1,5))): ('s2', 1, self.ON),
      ('s1', ('5',)): ('s3', 1, None),
      ('s1', ('6',)): ('s4', 0, None),
      ('s2', ('5',)): ('s3', 1, None),
      ('s2', self.list_to_str(range(1,5))): ('s2', 1, self.ON),
      ('s2', ('6',)): ('s2', 0, None),
      ('s3', ('5',)): ('s3', 1, None),
      ('s3', ('6',)): ('s3', 0, None),
      ('s3', self.list_to_str(range(1,5))): ('s3', 0, None),
    }    
    self.TRANSITION_MATRIX = self.transition_expand(TRANSITION_SHORTHAND)
    
    # Boilerplate for running the laser
    Laser.__init__(self, port)


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
    
    # State transition table, grouping state inputs in 'shorthand'
    ex = self.bin_expand
    TRANSITION_SHORTHAND = {
      ('s0', ex('0xxx')): ('s1', 1, self.INIT),
      ('s0', ex('11xx')): ('s2', 1, None),
      ('s0', ex('10xx')): ('s3', 1, None),
      ('s1', ex('11xx')): ('s2', 1, self.ON),
      ('s1', ex('10xx')): ('s2', 1, None),
      ('s1', ex('00xx')): ('s4', 0, None),
      ('s2', ex('10xx')): ('s3', 1, None),
      ('s2', ex('11xx')): ('s2', 1, None),
      ('s2', ex('0xxx')): ('s4', 0, None),
      ('s3', ex('10xx')): ('s3', 1, None),
      ('s3', ex('11xx')): ('s4', 0, None),
      ('s3', ex('0xxx')): ('s4', 0, None),
    }    
    self.TRANSITION_MATRIX = self.transition_expand(TRANSITION_SHORTHAND)
  
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

if __name__ == '__main__':
  laser2 = Sapphire('COM202')
  laser2.run()
