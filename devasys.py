"""
Control laser safety interlocks and identify lasers installed

Interfaces with Devasys microcontroller:
- I/O controls safety interlocks and shutter
- EEPROM contains information about lasers
- i2c control for front panel LEDs

Known bugs:
- Program should die when sled "hard" interlock is open
- See FIXME
"""

from ctypes import windll, c_ulong, pointer, create_string_buffer
from struct import pack, unpack
from sys import exit

class Usb2i2cio:
  def __init__(self):
    """Instantiate DeVaSys board from library"""
    self.lib = windll.LoadLibrary("usbi2cio.dll")
    # FIXME: handle library not found error
    self.handle = self.lib.DAPI_OpenDeviceInstance("UsbI2cIo", 0)
    if self.handle is -1:
      exit("DeVaSys board not found")
  
  def write_i2c_leds(self,value):
    """Write 2 bytes of LED data indicating laser fault and activity
    Write upper 1 byte to address 0x42
    Write lower 1 byte to address 0x40"""
    h = self.handle
    dvs = self.lib
    byTransType = 0x00  # I2C_TRANS_NOADR
    wCount = 1 # 2 bytes of zeroes, 1 byte of real information
    format = 'BBHB'
    for i in range(255):
      format = format + 'x'
    for (bySlvDevAddr, data) in ((0x42,value>>8), (0x40,value&0x00FF)):
      packed_struct = pack(format,byTransType,bySlvDevAddr,wCount,data)
      i2c_Trans = create_string_buffer(packed_struct, 260)
      p_i2c_Trans = pointer(i2c_Trans)
      length_chk = dvs.DAPI_WriteI2c(h, p_i2c_Trans)
      if (length_chk != wCount):
        print "ERR: WriteI2C(&i2c_Trans) failed,", \
              length_chk, "of", wCount, "bytes written"
  
  def read_EEPROM(self,start,length,save_file=None,BCD=False):
    """Get available lasers by reading EEPROM using i2c"""
    data = ""
    if save_file is not None:
      print "Saving raw data to file:", file
      f = open(save_file,'wb')
    h = self.handle
    dvs = self.lib
    """
    Pack the I2C_TRANS struct with the following:
    - BYTE byTransType
    - BYTE bySlvDevAddr
    - WORD wMemoryAddr
    - WORD wCount
    - BYTE Data[256]
    """
    byTransType = 0x02  # I2C_TRANS_16ADR
    #print "DBG: byTransType =", hex(byTransType), type(byTransType), \
    #      "Read or write 16 bit address cycle"
    bySlvDevAddr = 0xA2 # EEPROM chip
    #print "DBG: bySlvDevAddr =", hex(bySlvDevAddr), type(bySlvDevAddr), \
    #      "i2C address of EEPROM chip"
    wMemoryAddr = start
    #print "DBG: wMemoryAddr =", hex(wMemoryAddr), type(wMemoryAddr), \
    #      "Read address on EEPROM chip"
    increment = 64
    loops = length / increment
    total_loops = loops
    loop_remainder = length % increment
    while (loops + 1):
      if loops == 0:
        wCount = loop_remainder
      else:
        print "DBG: Loop", total_loops - loops + 1, "of", total_loops
        wCount = increment
      loops = loops - 1
      #print "DBG: wCount =", wCount, type(wCount), \
      #      "Number of bytes to read"
      format = 'BBHH'
      for i in range(256):
        format = format + 'x'
      packed_struct = pack(format,byTransType,bySlvDevAddr,wMemoryAddr,wCount)
      i2c_Trans = create_string_buffer(packed_struct, 262)
      p_i2c_Trans = pointer(i2c_Trans)
      length_chk = dvs.DAPI_ReadI2c(h, p_i2c_Trans)
      if (length_chk == wCount):
        #print "DBG: ReadI2C(&i2c_Trans) successful,", length, "bytes read"
        if save_file is not None:
          #print "DBG: Format =", format
          f.write(i2c_Trans[6:increment+6])
        else:
          format = 'BBHH'
          for i in range(wCount):
            if BCD is False:
              format = format + 'c'
            else:
              format = format + 'B'
          for i in range(256 - wCount):
            format = format + 'x'
          hex_data = list(unpack(format, i2c_Trans)[4:])
          try: clip = hex_data.index('\x00')
          except ValueError: clip = -1 # No value to remove
          if clip is not -1:
            hex_data = hex_data[0:clip]
          hex_data = ''.join(str(s) for s in hex_data)
      else:
        print "ERR: ReadI2C(&i2c_Trans) failed,", \
              length_chk, "of", wCount, "bytes read"
      if (loops >= 0):
        wMemoryAddr = wMemoryAddr + increment
        #print "DBG: wMemoryAddr =", hex(wMemoryAddr), type(wMemoryAddr), \
        #      "Read address on EEPROM chip"
    return hex_data

class Microcontroller(Usb2i2cio):
  def __init__(self):
    Usb2i2cio.__init__(self)
    self.read_sled_EEPROM()
    
    self.laser_led = (
      # masks for the 5 front panel LED
      0x0020,
      0x0004,
      0x0800,
      0x0100,
      0x1000,
    )
    
    self.all_ok_leds = 0xDDB6
  
  def set_active_leds(self, *lasers):
    """Set any combination of 5 laser as active.
    e.g. set_leds([2,3])
    Indicates laser  #2 and #3 are on"""
    leds = self.all_ok_leds
    
    for laser in lasers:
      if isinstance(laser, int) and laser >=1 and laser <=5:
        leds = leds - self.laser_led[laser - 1]
    
    print hex(leds)
    self.write_i2c_leds(leds)
  
  def bypass(self):
    """Defeat laser interlocks and open safety shutter"""
    h = self.handle
    dvs = self.lib
    ioconf = c_ulong(0x48000) # B7, C6 = inputs, rest = outputs
    iodata = c_ulong(0x84000) # B6, C7 high, others low
    dvs.DAPI_ConfigIoPorts(h, ioconf)
    iomask = 0x80000 # B6 high only: defeat laser safety interlocks
    dvs.DAPI_WriteIoPorts(h, iodata, iomask)
    iomask = 0x4000  # C7 high only: open safety shutter located after AOTF
    dvs.DAPI_WriteIoPorts(h, iodata, iomask)
  
  def start_laser(self):
    """Start up laser using i2c, e.g. Cobolt Compass 561nm"""
    pass
    
  def read_sled_EEPROM(self,read_file=None):
    h = self.handle
    dvs = self.lib
    LASER_OFFSET = 0x80
    EEPROM_MAPPING = (
      ("EEPROM_VERSION", 0x2815, 1),
      ("SERIAL", 0x283F, 10),
      ("LASERS_BCD", 0x2857, 1),
      ("L1_WAVELENGTH", 0x2890, 3),
      ("L1_POWER", 0x2893, 3),
      ("L1_FAMILY", 0x28A0, 16),
    )
    self.eeprom = {}
    sled = self.eeprom
    if read_file is not None:
      f = open(read_file,'r')
    for property, address, length in EEPROM_MAPPING:
      if read_file is not None:
        f.seek(address)
        data = f.read(length)
      else:
        if property.find("_BCD") is not -1:
          data = self.read_EEPROM(address,length,BCD=True)
        else:
          data = self.read_EEPROM(address,length,BCD=False)
      try:
        data = int(data)
      except ValueError:
        pass # leave as string
      sled[property] = data
    i = 2
    while i <= sled["LASERS_BCD"]:
      for property, address, length in EEPROM_MAPPING:
        if read_file is not None:
          f.seek(address + LASER_OFFSET * (i-1))
          data = f.read(length)
        else:
          data = self.read_EEPROM(address + LASER_OFFSET * (i-1),length)
        if property.find("L1_") is not -1:
          try:
            data = int(data)
          except ValueError:
            pass
          sled["L"+str(i)+property.lstrip("L1")] = data
      i = i + 1
    if read_file is not None:
      f.close()
    return sled

if __name__ == '__main__':
  """
  Example Program Output
  ----------------------
  EEPROM_VERSION : 1
       L1_FAMILY : CUBE
        L1_POWER : 100
   L1_WAVELENGTH : 405
       L2_FAMILY : SAPPHIRE
        L2_POWER : 50
   L2_WAVELENGTH : 488
       L3_FAMILY : COBOLTJIVE4
        L3_POWER : 50
   L3_WAVELENGTH : 561
       L4_FAMILY : CUBE
        L4_POWER : 100
   L4_WAVELENGTH : 640
      LASERS_BCD : 4
          SERIAL : LC-0533
  """
  micro = Microcontroller()
  
  #micro.set_active_leds(2)
  #exit(0)
  
  padding = len(max(sorted(micro.eeprom), key=len))
  for attr in sorted(micro.eeprom):
    print str.rjust(str(attr), padding), ":", micro.eeprom[attr]

"""
* DeVaSys is the brand of development board used in the Andor laser launch,
  and the usb2i2cio model of DeVaSys board is used to control laser safety
  interlocks and LEDs.  The LEDs implement CDRH Class 3B compliance by
  illuminating according to the active laser.
  
* The EEPROM, on older Rev. Bx boards was to primarily store the micro-
  controller firmware which gets loaded into RAM upon reset, serves as
  rewritable memory for Andor to store information about the sled,
  including identification of the lasers installed.  In newer Rev. C
  boards even though no firmware is stored in the EEPROM, Andor stores
  it's metadata at the same offset address.
  
* Total EEPROM size is 16 KB or 0x4000:
  Address Content
  ------- -------
  0x0000  Firmware
  0x2800  Andor Laser sled metadata (ASCII encoded)
  0x3F00  Board Serial number (ASCII encoded)

* Andor Laser sled metadata:
  Address Content
  ------- -------
  0x2801  Static string "Andor Technology"
  0x2815  Version of storage format (only encountered "1")
  0x281F  Model number of laser combiner (can be LC-401, 501 or 601)
  0x2829  Date of Manufacture
  0x2834  Date last modified
  0x283F  Serial number of laser combiner
  0x2857  Number of lasers (0x05 for 5 line, 0x04 for 4 line)
  0x2858  ??? 0x61 (5 line) 0x1B (4 line)
  0x2859  Untouched area 'FF'
  0x2880  Serial number of Laser 1
  0x2890  Wavelength of Laser 1
  0x2893  Power of Laser 1
  0x2897  AOTF MHz of Laser 1 (3 numbers before decimal)
  0x289A  AOTF MHz of Laser 1 (3 numbers after decimal)
  0x289D  AOTF dB of Laser 1 (2 numbers before decimal)
  0x289F  AOTF dB of Laser 1 (1 number after decimal)
  0x28A0  Family of Laser 1 (CUBE, EXTERNAL, MG560, SAPPHIRE, ...)
  0x28B0  Untouched area 'FF'
  0x2900  Model number of Laser 2
  ...
  0x2980  Model number of Laser 3
  ...
  0x3000  Model number of Laser 4
  ...
  0x3080  Model number of Laser 5
  ...
  0x3100  Model number of Laser 6
  ...
"""
