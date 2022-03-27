"""
serial_repl.py -- a particularly dirty, hacky thing designed to run a repl loop over the UART on my Pi Pico.
(C) 2022 B.M.Deeal
distributed under the ISC license, see <https://opensource.org/licenses/ISC> for details

This was mostly intended so I could attach my Pico to my Windows CE systems over serial.
There is almost certainly a better way to do this (probably involving a recompiled micropython binary), but this was fun to write.

Configure your device to emit only CR for enter, and ^H for backspace.
Pressing ^J will emit a newline, which will allow you to add multiple lines to anything input.
patch_target monkey-patches the print/input functions for any scripts you want to load and run.
"""

from machine import UART, Pin
import time
import os
import sys
uart0 = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
led = Pin(25, Pin.OUT)

debug=False #mostly enables some debug info on stdout

def out_chr(n):
    """write a character index to the attached terminal"""
    uart0.write(chr(n))

def out_str(s=""):
    """write a string, no newline, to the attached terminal"""
    uart0.write(str(s))

def out_nl():
    """write a newline to the attached terminal"""
    uart0.write("\r\n")
    time.sleep_ms(200)

def out_line(s="", *args, **kwargs):
    """write a full line to the attached terminal"""
    #args and kwargs are ignored and are there only for compatibility with print()
    out_str(s)
    out_nl()

def in_line(txt=""):
    """read a line from the attached terminal"""
    #TODO: a way to erase the whole line?
    #TODO: a way to add newlines?
    line=[]
    out_str(txt)
    while True:
        #check if any data is to be read
        led.off()
        if uart0.any()>0:
            for ch in uart0.read():
                led.on()
                #accept entry
                if ch==13: #enter/carriage return -- my device doesn't do \n, just \r
                    #join everything into a final result
                    result=bytes(line).decode("ascii")
                    led.off()
                    if debug:
                        print(f"sent '{result}'")
                    out_nl()
                    return result
                #debug print info
                if debug:
                    print(f"{ch}='{chr(ch)}'")
                #accept a newline as something you can enter
                if ch==10:
                    out_line("\\") #emit a character to indicate
                    line.append(ch)
                #echo typed valid characters (so, don't use local echo)
                if (ch>=32 and ch<=126): #printable characters
                    out_chr(ch) #uart0.write(chr(ch))
                    line.append(ch)
                #we don't bother with real tabs
                if ch==9: #tab
                    out_str("    ")
                    line.append(ch)
                #clear buffer
                if ch==21: #NAK, generated by ^U
                    line=[]
                    out_line("...erased\\")
                #backspace -- mostly does the right thing visually, breaks on my terminal if the text crosses to a newline
                if ch==8 and len(line)>0:
                    prev_ch=line.pop()
                    #undo the last 4 spaces for tab
                    if prev_ch==9:
                        out_chr(8)
                        out_chr(8)
                        out_chr(8)
                        out_chr(8)
                        #forces the cursor to update
                        out_chr(32)
                        out_chr(8)
                    #any single-character, we can go back, clear, go back
                    else:
                        out_chr(8)
                        out_chr(32)
                        out_chr(8)
                    

def input_test():
    """for testing whether things work"""
    out_nl()
    uart0.write("test data: ")
    in_line()

def show_help():
    """display some commands and keys"""
    out_line("serial_repl.py -- connect a dumb terminal to the Pi Pico")
    out_line("by B.M.Deeal.")
    out_line("Use patch_target('name') to load a program.")
    out_line("sys.exit() will return to the USB REPL.")
    out_line("os.listdir() will show a dir listing.")
    out_line("^M will submit input.")
    out_line("^J will add a newline to the buffer.")
    out_line("^H will backspace a character from the buffer.")
    out_line("^U will clear the input buffer.")

def repl():
    """main read-eval-print loop"""
    out_nl()
    out_nl()
    out_line("Type show_help() to view help.")
    out_line("^M will submit input.")
    out_line("REPL ready.")
    user_input=""
    result=""
    while True:
        #read and evaluate input
        try:
            out_str(">>>")
            user_input=in_line()
            result=eval(user_input)
            if result is not None:
                out_line(result)
        #we try to emit the result if we can, so we have to switch between eval and exec
        #if exec returned a value, none of this would be needed
        except SyntaxError:
            try:
                exec(user_input)
            #real syntax error
            except Exception as ex2:
                out_line(ex2)
        #could not parse
        except Exception as ex:
            out_line(ex)

def main():
    """run the program"""
    time.sleep_ms(900) #the pico spews a bit of garbage, so we wait abit
    repl()

def patch_target(s):
    """monkey-patch other scripts so they output over serial -- this is NOT robust at all"""
    exec(f"import {s}\n{s}.input=in_line\n{s}.print=out_line")


if __name__=="__main__":
    main()