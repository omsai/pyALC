openALC is a Python userspace Windows driver for the Andor Laser
Combiner (ALC) from Andor Technology.

   
.. contents:: Table of Contents
   :depth: 3

Project goal
============
- Implement the Laser Combiners control as a script, which when
  directly called, starts the device without further user interaction.
- Thus turn the combiner into a "dumb" box which responds to Analog
  voltage control.

.. figure:: http://www.andor.com/images/product_images/microscopy_peripherals_laser_combiner_large.jpg
   :alt: Andor Laser Combiner with Multi-port Unit on front
   :align: right
   
   Andor Laser Combiners supported:
   
   :ALC Models:  401, 501
   :Windows Platforms:  XP 32bit, 7 64bit

openALC address these limitations of the Andor's SDK
----------------------------------------------------
1. The Andor driver is hard coded to support the `PCIM-DDA06/16`_ card
   from Measurement Computing (MCC).  This is a problem because the
   card is not supported in all Bio-imaging softwares, and also the
   interface for this card is a +5V-only 32-bit PCI slot which is
   uncommon on many modern PCs.
2. Closed source library.
3. Not freely available for download.

.. _`PCIM-DDA06/16`: http://www.mccdaq.com/pci-data-acquisition/PCIM-DDA06-16.aspx

Installation
============
Windows dependencies (minimum versions)
---------------------------------------
1. Python v2.5, with win32 extensions and PySerial.
   Andor iQOpenSource_ 32-bit packages all of these and lots of
   additional useful tools like the Spyder IDE.  You need to create
   an Andor web account and login to download iQOpenSource.
2. DeVaSys usb2i2cio_ v5.00.  Choose x64 for 64-bit, or x86 for 32-bit.
3. You must have usbi2cio.dll in your script's Python path.  Simplest
   is to copy the dll from the directory::
   
       C:/Program Files (x86)/DeVaSys/UsbI2cIo/Library Files/5.00/x64/
   
   to the same directory where you run this Python script, like::
   
       C:/spinning disk/python driver/

4. (Optional) EzIO_ 1.09 to debug if DeVaSys does not work.

.. _iQOpenSource: https://www.andor.com/download/login.aspx
.. _usb2i2cio: http://www.devasys.net/support/support.html
.. _EzIO: http://www.devasys.com/download/UsbI2cIo/EzIo.zip

Implementation
==============
System Overview
---------------
.. figure:: docs/system_overview.png
   :align: center


Laser control using State Machines
----------------------------------
Each laser is itself a finite state machine.  We need a Mealy State 
machine to monitor the laser's state progression and with the input as 
the laser state, and the output to indicate if this is normal or if
some error handling needs to be applied.

Outputs:
  1 = System OK
  0 = Error occured

State Definitions:
  S0 = Unknown laser state
  S1 = Interlock
  S2 = Warmup (or Seeking power lock)
  S3 = Lock (Laser power stable)
  S4 = Error

.. figure:: docs/laser_flowchart.png
   :align: center

.. figure:: docs/laser_statemachine.png
   :align: center

Coherent Sapphire
~~~~~~~~~~~~~~~~~
Inputs (result of `?STA` command):
  1 = St
  2 = Warm up
  3 = Stand by
  4 = Laser on
  5 = Laser ready
  6 = Interlock Error

=====  =====  =========  ======  ========
State  Input  New State  Output  Action
=====  =====  =========  ======  ========
S0     6      S1         1       L=1
S0     1-4    S2         1       L=1
S0     5      S3         1       
S1     1-4    S2         1       L=1
S1     5      S3         1       
S1     6      S4         0       
S2     5      S3         1       
S2     1-4    S2         1       L=1 [*]_
S2     6      S4         0       
S3     5      S3         1       
S3     6      S4         0       
S3     1-4    S4         0       
=====  =====  =========  ======  ========

.. [*] S4 if >5 min in this state

Cobolt Generation 4
~~~~~~~~~~~~~~~~~~~
Inputs (result of `leds?` command):
  0b0111 or 7  = Interlock Error
  0b1111 or 15 = Stabilizing Temperature
  0b1101 or 13 = Starting Laser
  0b1100 or 12 = Warm up
  0b1000 or 8  = Output power locked

=====  =====  =========  ======  ========================
State  Input  New State  Output  Action
=====  =====  =========  ======  ========================
S0     0xxx   S1         1       cf
S0     11xx   S2         1
S0     10xx   S3         1
S1     11xx   S2         1       lten1, xten1, @cob 1, l1
S1     10xx   S3         1
S1     0xxx   S4         0
S2     10xx   S3         1
S2     11xx   S2         1       [*]_
S2     0xxx   S4         0
S3     10xx   S3         1
S3     0xxx   S4         0
S3     11xx   S4         0
=====  =====  =========  ======  ========================

.. [*] S4 if >3 min in this state


DeVaSys microcontroller
-----------------------
DeVaSys is the brand of development board used in the Andor laser
launch, and the usb2i2cio model of DeVaSys board is used to control 
laser safety interlocks and LEDs.  The LEDs implement CDRH Class 3B
compliance by illuminating according to the active laser.

EEPROM
~~~~~~
- The EEPROM, on older Rev. Bx boards was to primarily store the micro-
  controller firmware which gets loaded into RAM upon reset, serves as
  rewritable memory for Andor to store information about the sled,
  including identification of the lasers installed.  In newer Rev. C
  boards even though no firmware is stored in the EEPROM, Andor stores
  it's metadata at the same offset address.
  
- Total EEPROM size is 16 KB or 0x4000:

=======  =========================================
Address  Content
=======  =========================================
0x0000   Firmware
0x2800   Andor Laser sled metadata (ASCII encoded)
0x3F00   Board Serial number (ASCII encoded)
=======  =========================================

- Andor Laser sled metadata reverse engineered from EEPROM:

=======  =========================================================
Address  Content
=======  =========================================================
0x2801   Static string 'Andor Technology'
0x2815   Version of storage format (only encountered '1')
0x281F   Model number of laser combiner (can be LC-401, 501 or 601)
0x2829   Date of Manufacture
0x2834   Date last modified
0x283F   Serial number of laser combiner
0x2857   Number of lasers (0x05 for 5 line, 0x04 for 4 line)
0x2858   ??? 0x61 (5 line) 0x1B (4 line)
0x2859   Untouched area 'FF'
0x2880   Model number of Laser 1
0x2890   Wavelength of Laser 1
0x2893   Power of Laser 1
0x2897   AOTF MHz of Laser 1 (3 numbers before decimal)
0x289A   AOTF MHz of Laser 1 (3 numbers after decimal)
0x289D   AOTF dB of Laser 1 (2 numbers before decimal)
0x289F   AOTF dB of Laser 1 (1 number after decimal)
0x28A0   Family of Laser 1 (CUBE, EXTERNAL, MG560, SAPPHIRE, ...)
0x28B0   Untouched area 'FF'
0x2900   Model number of Laser 2
...
0x2980   Model number of Laser 3
...
0x3000   Model number of Laser 4
...
0x3080   Model number of Laser 5
...
0x3100   Model number of Laser 6
...
=======  =========================================================

I/O for global interlocks and physical safety shutter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Configure:
  B7, C6 = inputs
  Rest of I/O = outputs
- Set:
  B6 high = close interlocks to allow laser startup
  C7 high = oopen physical safety shutter
  Leave rest low

LED front panel control
~~~~~~~~~~~~~~~~~~~~~~~

===========  =====  =====
i2c address  &0x40  &0x42
===========  =====  =====
All off      0xB6   0xDD
LED 1 on     0x96   0xDD
LED 2 on     0xB2   0xDD
LED 3 on     0xB6   0xDD
LED 4 on     0xB6   0xDC
LED 5 on     0xB6   0xCD
===========  =====  =====


Programming in Python
---------------------
- Easy language for non-professional programmers in Life Sciences
  to debug.
- Low barrier to tweak program code since it is a scripting language
  and thus no development enviroment needs setup.
- PySerial module does not lock up COM ports when the program exists
  unexpectedly.
- Builtin ctypes module allows communication with the DeVaSys C
  library.