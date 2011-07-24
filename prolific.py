"""
Detect COM ports from connected Prolific Devices

Reads COM information from Windows registry.  Tested against Windows 7 64-bit
and Windows XP 32-bit.

TODO:
- White list detection of USB bus topology not yet implemented.
  Looks like that feature requires querying Windows IOCTL.
"""

from _winreg import OpenKey, QueryValueEx, EnumValue, HKEY_LOCAL_MACHINE
from re import search
from sys import exit

class ProlificPorts:
  """Cross-references Windows COM port numbers from Prolific devices"""
  def __init__(self):
    """"""
    self.squids = []
    SER2PL32 = "SYSTEM\\CurrentControlSet\\Services\\Ser2pl\\Enum"
    SER2PL64 = "SYSTEM\\CurrentControlSet\\Services\\Ser2pl64\\Enum"
    
    try:
      # 32-bit Prolific driver
      self.arch = 32
      self.prolific_path = OpenKey(HKEY_LOCAL_MACHINE, SER2PL32)
      # Have to try Registry instead of platform.architecture, since the
      # latter returns architecture of Python and not of Prolific's driver
    except WindowsError:
      try:
        # 64-bit
        self.arch = 64
        self.prolific_path = OpenKey(HKEY_LOCAL_MACHINE, SER2PL64)
      except WindowsError:
        exit("DriverError: No Ser2pl or Ser2pl64 service found to control "+\
             "Prolific USB-serial COM ports.  Is the Prolific driver"+\
             "installed?")
    self.ports, type = QueryValueEx(self.prolific_path, "Count")
    print "Number of devices using", "Ser2pl" + str(self.arch), \
          "service:", self.ports
    if self.ports is 0:
      exit("No Prolific USB-serial COM ports found")
    self.COM = [0] * self.ports
    self.get_squids()
    self.enumerate_ports()
  
  def get_squids(self):
    squids = self.squids
    try:
      i = 0
      while 1:
        name, string, type = EnumValue(self.prolific_path, i)
        if type == 1: # 1 is for "REG_SZ", "A null-terminated string"
          sn = search('(?<=[\][0-9]&)\w+',string)
          if str(sn.group(0)) not in squids:
            squids.append(str(sn.group(0)))
        i += 1
    except WindowsError:
      pass
  
  def enumerate_ports(self):
    ENUM = "SYSTEM\\CurrentControlSet\\Enum\\"
    try:
      i = 0
      while 1:
        name, string, type = EnumValue(self.prolific_path, i)
        if type == 1: # 1 is for "REG_SZ", "A null-terminated string"
          sn = search('(?<=[\][0-9]&)\w+',string)
          offset = 0;
          
          # Print COMs for each key
          try:
            serint = ENUM + string + "\\Device Parameters"
            serial_path = OpenKey(HKEY_LOCAL_MACHINE,serint)
            port, type = QueryValueEx(serial_path, "PortName")
            self.COM[int(search('[0-9]$',string).group(0)) + 
                     offset*4 - 1] = str(port)
          except WindowsError:
            pass
        i += 1
    except WindowsError:
      pass

if __name__ == '__main__':
  """
  Example Program Output
  ----------------------
  Number of devices using Ser2pl service: 4
  Found Squids: ['3298b0e7']
  Ordered COM ports: ['COM55', 'COM56', 'COM57', 'COM58']
  """
  prolific = ProlificPorts()
  print "Found Squids:", prolific.squids
  print "Ordered COM ports:", prolific.COM