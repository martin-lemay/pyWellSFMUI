pyWellSFM - Stratigraphic Forward Modeling
===========================================

QUICK START
-----------
1. Double-click install.exe
   - Requires Python 3.13+ installed on your system
   - Requires internet connection (downloads dependencies)
   - Wait for "Installation complete" message

2. Double-click pyWellSFM.exe
   - Opens the application in your default browser
   - Keep the console window open while using the app
   - Close the console window to stop the application

CONFIGURATION
-------------
Edit config.ini to change settings:
  port = 5006    (change if port 5006 is already in use)

TROUBLESHOOTING
---------------
- "Could not find Python 3.13+":
  Install Python 3.13 or later from https://python.org
  Make sure to check "Add Python to PATH" during install.

- "Installation failed":
  Check your internet connection and try again.

- "Port already in use":
  Close any other instance of pyWellSFM, or change the
  port number in config.ini.

- Antivirus warning:
  PyInstaller-built executables may be flagged by some
  antivirus software. This is a false positive. You can
  safely add an exception for install.exe and pyWellSFM.exe.

- To reinstall:
  Run install.exe again. It will remove the previous
  installation and create a fresh one.
