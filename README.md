# serial-repl-pico
This script runs a REPL loop over the UART on a Pi Pico and provides a very basic shell environment.

I wrote this so I could use my Windows CE system to connect to my Pi Pico via the built-in terminal utility. The CE system uses a normal RS-232 serial connection, so I have a conversion board attached to it, but this script just expects a device connected on the UART0 pins. By default, the system operates at 9600 baud, and pauses after newlines to allow time for the slow Windows CE system to redraw the display. The system also provides a set of line-editing functions.

Use ```load_and_patch("name")``` name to access another script. For example, to run the included ezpyle.py, do ```load_and_patch("ezpyle")```, followed by ```ezpyle.main()```. ```load_and_patch``` re-implements print and input to operate over UART0 and may not work for all scripts.
