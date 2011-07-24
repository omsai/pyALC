*openALC* is a Python userspace Windows driver for the Andor Laser
Combiner (ALC) from Andor Technology.

.. figure:: http://www.andor.com/images/product_images/microscopy_peripherals_laser_combiner_large.jpg
   :alt: Andor Laser Combiner with Multi-port Unit on front
   
   Andor Laser Combiners supported:
   
   +----------+-------------------------------------+
   | Model    | ALC-401, ALC-501, ALC-601           |
   +----------+-------------------------------------+
   | Platform | Windows XP 32-bit, Windows 7 64-bit |
   +----------+-------------------------------------+

.. contents:: 

Project goal
============
- Implement the Laser Combiners control as a script, which when
  directly called, starts the device without further user interaction.
- Thus turn the combiner into a "dumb" box which responds to Analog
  voltage control.

openALC address these limitations of the Andor's SDK
----------------------------------------------------
1. The Andor driver is hard coded to support the PCIM-DDA06/16_ card
   from Measurement Computing (MCC).  This is a problem because the
   card is not supported in all Bio-imaging softwares, and also the
   interface for this card is a +5V-only 32-bit PCI slot which is
   uncommon on many modern PCs.
2. Closed source library.
3. Not freely available for download.

Why program in Python?
----------------------
- Easy language for non-professional programmers in Life Sciences
  to debug.
- Low barrier to tweak program code since it is a scripting language
  and thus no development enviroment needs setup.
- PySerial module does not lock up COM ports when the program exists
  unexpectedly.
- Builtin ctypes module allows communication with the DeVaSys C
  library.

Installation
============

Windows dependencies (minimum versions)
---------------------------------------
1. Python v2.5, with win32 extensions and PySerial.
   Andor iQOpenSource_ 32-bit packages all of these and lots of
   additional useful tools like the Spyder IDE.  You need to create
   an Andor web account and login to download iQOpenSource.
2. DeVaSys usb2i2cio_ v5.00 (choose x64 for 64-bit, or x86 for 32-bit)
   (Optional) EzIO_ 1.09 to debug if DeVaSys does not work.
3. You must have usbi2cio.dll in your script's Python path.  Simplest
   is to copy the dll from the directory:
   C:\Program Files (x86)\DeVaSys\UsbI2cIo\Library Files\5.00\x64\
   to the same directory where you run this Python script, like:
   C:\spinning disk\python driver\

.. _PCIM-DDA06/16: http://www.mccdaq.com/pci-data-acquisition/PCIM-DDA06-16.aspx
.. _iQOpenSource: https://www.andor.com/download/login.aspx
.. _usb2i2cio: http://www.devasys.net/support/support.html
.. _EzIO: http://www.devasys.com/download/UsbI2cIo/EzIo.zip