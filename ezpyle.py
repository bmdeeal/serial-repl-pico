#!/usr/bin/env python3
#This particular version of ezpyle has been modified for use on the Pi Pico.
#This has been tested with MicroPython v1.17 on a Pi Pico with an RP2040.

import sys
import os
import machine
IOError=OSError

#version string
#this changed significantly, but I've been standardizing them now
#X.Y-release will always be newer than X.Y-beta
#2.9 will always be earlier than 2.10
ezpyle_major_version=2
ezpyle_minor_version=0
ezpyle_extra_version="beta 6 (pico release)"
ezpyle_version=f"v{ezpyle_major_version}.{ezpyle_minor_version}-{ezpyle_extra_version}"

"""
    ezpyle -- a friendly line editor written in Python

    (C) 2021, 2022 B.M.Deeal
    Distributed under the ISC license, see the provided isc-license.txt or
    visit <https://opensource.org/licenses/ISC> for details.

    This was written entirely so I could edit text with my old Windows CE
    system while hooked up to a raspi over serial, while using a nicer,
    more user friendly editor than ed or ex. The VT100 emulation on the
    system doesn't play nicely with nano or vi or anything much.
    At some point, I might consider porting this to C or C++, so it can
    be used on systems without Python 3.x.

    This has been used at the astonishingly low rate of 1200 baud. In
    fact, not merely used, but comfortably used. At least, as comfortably
    as one might expect a line editor to be.

    This particular release has been modified for the Pi Pico environment,
    under MicroPython. In particular, it has been altered for use with my
    serial_repl.py script, to allow on-device file editing. In addition,
    it may have bugs and features that are not present in mainline ezpyle.
    
    As usual, I hope this is useful to you.
    --B.M.Deeal
"""


class Filedata:
    """
    Holds the data for a text file.
    """

    def clear(self):
        """
        Reset the file to be empty.
        """
        self.dirty=False
        self.name=""
        self.data=[]
        self.line=0

    def loadfile(self, filename):
        """
        Read a file from disk.
        Complains if the file cannot be read.
        """
        try:
            #expand ~, and this even works on Windows
            loadpath=filename #os.path.expanduser(filename)
            #read and split lines
            #we don't use readlines becuase we don't want a trailing \n
            with open(loadpath, "r") as f:
                self.clear()
                self.data=f.read().splitlines()
                self.line=len(self.data)
                self.name=filename
                print(f"Loaded {len(self.data)} lines from disk.")
        except IOError:
            print("error: could not load file!")

    def writefile(self, filename):
        """
        Write the file to disk.
        Complains if the file cannot be written.
        """
        try:
            #expand ~, and this even works on Windows apparently
            savepath=filename #os.path.expanduser(filename)
            #write each line; I think this automagically adds a newline to
            #the last line of the file, as is proper
            with open(savepath, "w") as f:
                for line in self.data:
                    f.write(line)
                    f.write("\n")
                print(f"Saved {len(self.data)} lines to disk.")
                self.name=filename
                self.dirty=False
        except IOError:
            print("error: could not write file!")

    def __init__(self):
        """
        Initialize the file, just clears it out.
        """
        self.clear()

    def showfile(self, start=0):
        """
        Displays the file to the screen, starting at a given line.
        """
        if start<0:
            start=0
        view=c_file.data[start:]
        #display whole file
        #may or may not be useful depending on your device
        #on a real paper TTY, this would be dead useful
        #check if file isn't empty
        if len(view)==0:
            print("Nothing to show.")
            return
        #display file
        num=0
        for line in view:
            marker=":"
            #indicate current line
            if num+start==c_file.line:
                marker="*"
            print(f"{num+start+1}{marker} {line}")
            #pause every few lines
            #TODO: probably should be a configurable option
            if num%10 == 9:
                #confirm=input("Show more? [y]/n? > ").lower()
                #if confirm in ("n", "no"):
                confirm=ynprompt('y', "Show more?")
                if not confirm:
                    break
            num=num+1

c_file=Filedata() #current file


def helptext():
    """Show help to the user."""
    #TODO: display this in pages, like if the user used list
    print("commands:")
    print("* new, newfile - start a new, empty file")
    print("* st, stats, info - show file statistics") #TODO: incomplete
    print("* i, ins, insert - insert a line before the current")
    print("* a, app, append - insert a line after the current")
    #print("* add, atch, attach - add text before/after the current line") #TODO
    print("* j, jmp, jump - jump to a given line")
    print("* p, [, prev, previous - go back one line")
    print("* n, ], next - go forward one line")
    #print("* s, search, find - locate a string in the file") #TODO
    print("* r, replace - replace a string in this line with another")
    print("* jn, join, cat - join line with the next")
    print("* sp, split - split a line into two")
    print("* mv, move - move a line")
    print("* dd, delete - delete the current line")
    print("* wf, write, save - write the file to disk")
    print("* lf, load, open - load a file from disk")
    print("* l, ls, list - show a given amount of lines")
    print("* sl, showline, ll - show the current line between quotes")
    print("* la, al, als, listall - show the entire file")
    print("* qq, quit, exit - exit program")
    print()
    print("All commands must be on their own lines.")
    print("Commands will prompt for data as needed.")
    print()

#TODO: replace all prompts with this
#TODO: might add a way to cancel?
#Current design is that operations are always canceled at the end...
#...but that's a bit clunky.
def ynprompt(default=None, message=""):
    """
    Ask a yes/no question.
    Returns True for yes, False for no.
    message is any text to show at the prompt.
    """
    #handle defaults
    if default in ("y", "yes"):
        default=True
        prompt="[y]/n"
    elif default in ("n", "no"):
        default=False
        prompt="y/[n]"
    else:
        default=None
        prompt="y/n"
    #add a space for the message if present
    if message!="":
        message=f"{message} "
    #loop until a valid result is given
    while True:
        result_orig=input(f"{message}{prompt} > ")
        result=result_orig.lower().strip()
        #normal y/n + aliases
        if result in ("y", "yes"):
            return True
        elif result in ("n", "no"):
            return False
        #empty string with no default
        elif result=="" and default!=None:
            return default
        #show message, loop again
        print(f"error: could not understand '{result_orig}'!")
        print("Valid options are yes or no.")

def main():
    """
    Show the intro, handle arguments, and then start accepting commands.
    """
    #show intro, clear file data
    c_file.clear()
    print(f"Welcome to ezpyle {ezpyle_version}.")
    print("(C) 2021, 2022 B.M.Deeal.")
    print("Type ? for help.")
    #load a file passed on the command line
    #TODO: any kind of real argument handling
    if len(sys.argv) > 1:
        print (f"Opening file '{sys.argv[1]}'...")
        c_file.loadfile(sys.argv[1])
    #run the main loop, deal with ^C/^D
    while True:
        try:
            mainloop()
        #TODO: better handling of this
        #also, no command should depend on ^C to escape!
        except KeyboardInterrupt:
            print("\nKeyboard interrupt. Type qq to quit.")
        except EOFError:
            print("\nEnd of file detected. Type qq to quit.")

def cmd_quit():
    """
    Quit command.
    """
    #check dirty file indicator, prompt to quit if dirty
    if c_file.dirty:
        print("File not saved! Quit anyway?")
        confirm=ynprompt('n')
        if not confirm:
            print("Did not quit.")
            return
    print("a: Exit program or b: reset machine?")
    result=input("[a]/b > ").strip().lower()
    if result=="b":
        machine.reset()
    sys.exit()

def cmd_replace(thisline):
    """
    Text replace command.
    Currently only replaces the first found on the line.
    Doesn't search the whole file, only the current line.
    (both are TODO, naturally -- might be added to a different command)
    """
    #bounds check
    if thisline<0:
        print("Nothing to replace.")
        return
    #ask for what to replace
    print("Replacing in line:")
    print(f"{thisline+1}* {c_file.data[thisline]}") #TODO: this should be a method of c_file, need to refactor there
    target=input("String to be replaced? (case-sensitive) > ")
    #abort if it can't be found
    if c_file.data[thisline].find(target) < 0:
        print(f"Could not find '{target}'.")
        print("Did not replace.")
        return
    #target replacement
    replacement=input("String to replace with? > ")
    templine=c_file.data[thisline].replace(target, replacement, 1)
    #ask to confirm
    print("The resulting line is as follows:")
    print(f"{thisline+1}* {templine}")
    print("Is this okay?")
    confirm=ynprompt('n')
    if not confirm:
        print("Did not replace.")
        return
    #apply the replacement
    c_file.data[thisline]=templine
    print(f"Replaced '{target}' with '{replacement}'.")
    c_file.dirty=True

def mainloop():
    """
    Main loop for program.
    """
    #TODO: refactor each operation into a function! (in progress)
    #like, any new commands I add should get their own function
    #TODO: possibly add a system to parse arguments to commands
    #so the user doesn't need to type them separately?
    #show user prompt
    dirtymark="."
    if c_file.dirty:
        dirtymark="!"
    cmd=input(f"({c_file.line+1}|{dirtymark}) Command? > ")
    thisline=c_file.line
    #bounds checking
    if thisline>=len(c_file.data):
        thisline=len(c_file.data)-1
    #exit program
    if cmd in ("qq", "quit", "exit"):
        cmd_quit()
    elif cmd in ("r", "repl", "replace"):
        cmd_replace(thisline)
    #show single line
    elif cmd in ("sl", "showline", "ll"):
        if len(c_file.data) > 0:
            print(f"'{c_file.data[thisline]}'")
        else:
            print("Nothing to show.")
    #get file stats
    #TODO: word count (would we just count spaces?)
    elif cmd in ("st", "stats", "info"):
        #add up each character, show results
        chnum=0
        for line in c_file.data:
            #I bet it was 4am when I wrote this:
            #for ch in line:
            #	chnum=chnum+1
            chnum+=len(line)+1
        print("This file has:")
        print(f" * {len(c_file.data)} lines")
        print(f" * {chnum} characters")
    #move lines
    #TODO: something is up
    elif cmd in ("mv", "move"):
        #this should only happen when the file is empty
        if thisline<0:
            print("Nothing to move.")
            return
        print("warning: possible bugs, beware")
        #prompt to move, get input, validate inputs
        print("Moving line:")
        print(f"{thisline+1}* {c_file.data[thisline]}")
        target=input("Line number to move to? > ")
        try:
            target_num=int(target)-1
        except ValueError:
            if target!="":
                print("error: could not parse number!")
            print("Did not move line.")
            return
        #same line
        if target_num==thisline:
            print("error: current and target line are the same!")
            print("Did not move line.")
            return
        #out of bounds targets are treated as okay
        if target_num<0:
            target_num=0
        if target_num>=len(c_file.data):
            target_num=len(c_file.data)-1;
        #same line
        if target_num==thisline:
            print("Did not move line.")
            return
        #ask to confirm, show context lines (this might be bugged)
        linedata=c_file.data[thisline]
        print("The line will be moved as follows:")
        #show some context; this is ugly and has issues
        #TODO: fix
        if target_num-1>=0: #line before
            print(f"{target_num}: {c_file.data[target_num-1]}")
        print(f"{target_num+1}= {linedata}") #newly moved line
        if target_num<len(c_file.data): #line after
            print(f"{target_num+2}: {c_file.data[target_num]}")
        #ask to confirm
        print("Is this okay?")
        confirm=ynprompt('n')
        if not confirm:
            print("Did not move line.")
            return
        #actually move the line
        #TODO: investigate behavior, something is up
        del c_file.data[thisline]
        c_file.data.insert(target_num, linedata)
        c_file.dirty=True
        print("Moved line.")
    #split lines
    elif cmd in ("sp", "split"):
        if thisline<0:
            print("Nothing to split.")
            return
        print("Splitting line:")
        print(f"{thisline+1}* {c_file.data[thisline]}")
        #ask for where, we do a search for the string and split there
        print("Type the characters you want to split at.")
        search_str=input(" > ")
        last_find=-1
        results=[]
        #get a list of where a string was found
        #I'm incredibly surprised that this isn't a builtin
        #TODO: double check if there's a builtin for this
        #it really does feel wrong that there isn't
        while True: #this would be a do..while in any other language
            last_find=c_file.data[thisline].find(search_str,last_find+1)
            if last_find==-1:
                break
            results.append(last_find)
        #found nothing
        if len(results)==0:
            print(f"Could not find '{search_str}'.")
            print("Did not split line.")
            return
        #which item to split at
        item_num=0
        if len(results)>1:
            print(f"'{search_str}' was found more than once. Which one to split at?")
            try:
                item_num=int(input(f"[1]..{len(results)} > "))-1
            except ValueError:
                print("error: could not parse number!")
                print("Did not split line.")
                return
            if item_num<0 or item_num>=len(results):
                print("error: number out of range!")
                print("Did not split line.")
                return
        #preliminary split
        prelim1=c_file.data[thisline][:results[item_num]]
        prelim2=c_file.data[thisline][results[item_num]:]
        #ask to strip any space between the results
        print("Strip spaces from split?")
        #confirm=input("[y]/n > ").lower()
        #if confirm not in ("n", "no"):
        confirm=ynprompt("y")
        if confirm:
            prelim1=prelim1.rstrip()
            prelim2=prelim2.lstrip()
        #ask if results are okay
        print("The string has been split into:")
        print(f" '{prelim1}'")
        print(f" '{prelim2}'")
        print("Is this okay?")
        confirm=ynprompt('n')
        if not confirm:
            print("Did not split line.")
            return
        #apply the split
        c_file.data[thisline]=prelim1
        c_file.data.insert(thisline+1,prelim2)
        c_file.dirty=True
        print("Split line.")
    #join lines
    elif cmd in ("jn", "join", "cat"):
        #check if there's a line after to join
        if c_file.line+1 >= len(c_file.data):
            print("No line after to join.")
            return
        #show lines to join
        print("Joining lines:")
        print(f"{c_file.line+1}* {c_file.data[c_file.line]}")
        print(f"{c_file.line+2}: {c_file.data[c_file.line+1]}")
        #ask to add a space or not (default yes)
        print("Add space between joined lines?")
        spacer=" "
        confirm=ynprompt("y")
        if not confirm:
            spacer=""
        #generate result, ask if okay (default no)
        joined=c_file.data[c_file.line] + spacer + c_file.data[c_file.line+1]
        print("Is this okay?")
        print(f"{c_file.line+1}* {joined}")
        confirm=ynprompt('n')
        if not confirm:
            print("Did not join lines.")
            return
        #insert result, delete the one after
        c_file.data[c_file.line]=joined
        del c_file.data[c_file.line+1]
        c_file.dirty=True
        print("Joined lines.")
    #go forward a single line
    elif cmd in ("n", "]", "next"):
        #go forward one line, fix it after
        c_file.line+=1
        #bounds check
        if c_file.line>len(c_file.data):
            c_file.line=len(c_file.data)
    #go back a single line
    elif cmd in ("p", "[", "prev", "previous"):
        #go back one line, fix it after
        c_file.line-=1
        #bounds check
        if c_file.line<0:
            c_file.line=0
    #jump to line
    elif cmd in ("j", "jmp", "jump"):
        target=input("Jump to what line? > ")
        #cancel if empty
        if target=="":
            print("Did not jump.")
            return
        #handle bounds checking, jump to the line
        try:
            targetnum=int(target)-1
            if targetnum>len(c_file.data):
                targetnum=len(c_file.data)
            if targetnum<0:
                targetnum=0
            c_file.line=targetnum
        except ValueError:
            print("error: could not parse number!")
            print("Did not jump.")
    #load files
    elif cmd in ("lf", "load", "open"):
        #ask whether to load if there's unsaved data
        if c_file.dirty:
            print("File not saved! Load new file anyway?")
            confirm=ynprompt('n')
            if not confirm:
                print("Did not load a file.")
                return
        fname=input("File to load? > ")
        #cancel if empty
        if fname == "":
            print("Did not load a file.")
            return
        c_file.loadfile(fname)
    #write files
    elif cmd in ("wf", "write", "save"):
        #if we're editing an existing file, confirm saving to it
        if c_file.name!="":
            print(f"Current filename is '{c_file.name}'.")
            print("Save to this file?")
            if ynprompt('y'):
                c_file.writefile(c_file.name)
                return
        #either no name yet, or saving under a new name
        print("Filename to save as? Leave blank to cancel.")
        fname=input(" > ")
        #cancel if empty, otherwise do the save
        if fname == "":
            print("Did not save the file.")
            return
        c_file.writefile(fname)
    #append a line after the current one
    elif cmd in ("a", "app", "append"):
        print(f"Appending after line {c_file.line+1}:")
        line=input(" > ")
        c_file.data.insert(c_file.line+1,line)
        c_file.dirty=True
        c_file.line+=1
    #delete current line
    elif cmd in ("dd", "del", "delete"):
        #the current line can be after the end of the text
        #so, bounds checking
        if thisline>=len(c_file.data):
            thisline=len(c_file.data)-1
        #this should only happen when the file is empty
        if thisline<0:
            print("Nothing to delete.")
            return
        #ask to delete, then delete
        print("Delete line?")
        print(f"{thisline+1}* {c_file.data[thisline]}")
        confirm=ynprompt('n')
        if confirm:
            del c_file.data[thisline]
            c_file.line=thisline
            c_file.dirty=True
            print("Deleted line.")
        else:
            print("Did not delete.")
    #insert line before current
    elif cmd in ("i", "ins", "insert"):
        print(f"Inserting at line {c_file.line+1}:")
        line=input(" > ")
        c_file.data.insert(c_file.line,line)
        c_file.dirty=True
        c_file.line+=1
    #display some lines
    elif cmd in ("l", "ls", "list"):
        c_file.showfile(c_file.line-5)
    #display whole file from the top
    elif cmd in ("la", "al", "als", "listall"):
        c_file.showfile()
    #new file
    elif cmd in ("new", "newfile"):
        #prompt if file was modified
        if c_file.dirty:
            print("File not saved! Start new file anyway?")
            confirm=ynprompt('n')
            if not confirm:
                print("Did not start new file.")
                return
        #clear everything
        c_file.clear()
        print("New file created.")
    #get help
    elif cmd in ("?", "help"):
        helptext()
    #don't complain on blank string
    elif cmd=="":
        return
    #tell user to confirm their quit attempt with qq
    #since it's way easier to just hit q when you don't want to quit
    elif cmd=="q":
        print("Type qq to quit. Type ? for help.")
    #give up, try again
    else:
        print("Unknown command. Type ? for help.")


#entry point
if __name__ == "__main__":
    main()

