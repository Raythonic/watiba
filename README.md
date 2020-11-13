# Watiba
Watiba is a lightweight Python pre-compiler for embedding Linux shell 
commands within Python applications.

## Usage
Watiba files, suffixed with ".wt", are Python programs containing embedded shell commands. 
Shell commands are expressed within backtick characters emulating BASH's original capture syntax.
They can be placed in any Python statement or expression.  Watiba keeps track of the current working directory after the execution of 
any shell command so that all subsequent shell commands keep context.  For example:

```
#!/usr/bin/python3

if __name__ == "__main__":
    `cd /tmp`
    for l in `ls -lrt`.stdout:
        print(l)
```

This loop will display the file list from /tmp. The `ls -lrt` is run in the 
context of previous `cd /tmp`.  

Commands can also be Python variables. This is denoted by prepending a dollar sign on the
variable name within backticks. A complete example:

```
#!/usr/bin/python3

if __name__ == "__main__":
    # Change CWD to /tmp
    `cd /tmp`
    
    # Set a command string
    my_cmd = "tar -zxvf blah.tar.gz"
    
    # Execute that command and save the result object in variable "w"
    w = `$my_cmd`
    if w.exit_code == 0:
        for l in w.stderr:
            print(l)
```

### Directory Context

An important Watiba usage point is directory context is kept for dispersed shell commands.
Any command that changes the shell's CWD is discovered and kept by Watiba.  Watiba achieves 
this by tagging a `&& echo pwd` to the user's 
command, locating the result in the command's STDOUT, and finally setting the
Python environment to that CWD with `os.chdir(dir)`.  This is automatic and opaque to the user.  The 
user's STDOUT from the command(s) will not contain
the product of the inserted `echo` as this element is removed from the STDOUT array passed
to the user's program.

If the `echo` command suffix presents a problem for the user, it can be eliminated by prefixing
the leading backtick with a dash.  

_Warning_: the dash will cause Watiba to lose its directory context should the command
cause a CWD change.


Example:  ```for l in -`cd /home/user && ls -lrt && pwd`.stdout: print(l)``` will list the files
for /home/user and ```pwd``` output, but it will not change the current working directory for 
subsequent commands.


### Command Results
The results of the command issued in backticks are available in the properties
of the object returned by Watiba.  Treat the backticked command as a normal
Python object.  Following are its properties:
 
- stdout - array of output lines from the command normalized for display
- stderr - array of standard error output lines from the command normalized for display
- exit_code - integer exit code value from command
- cwd - current working directory after command was executed


# Installation
## PIP
If you installed this as a Python package, e.g. pip, then the pre-compiler can be found
where the package was installed.  For example:
```
/home/{user}/.local/lib/python3.8/site-packages/watiba/watiba-c.py
```
This file can be copied to any directory in your PATH.  It is stand-alone and can be copied
anywhere you need.

## GITHUB
If you cloned this from github, you'll still need to install the package with pip for the
watbia module first then you'll need to modify and run the makefile.
```

# Must install Watiba package
pip3 install watiba

# Now edit makefile and run make
cd {to where you git cloned watiba}/watiba

# 1. Edit makefile
# 2. Change the top two variables to your target destinations
# 3. venv = /home/rwalk/Projects/python3/venv/lib64/python3.8/site-packages/
#    bin = /home/rwalk/bin/watiba-c
#        -- CHANGE TO --
#    venv = {your Python venv environment}
#    bin = {your bin directory and file name}

# Execute command
make

```

# Pre-compiling
Once you've installed watiba-c.py into your path, you can execute it to pre-compile
your .wt (Watiba) code.  Output will be written to STDOUT, so you'll need to redirect
it to your final Python file.  Example follows:
```
watiba-c.py my_file.wt > my_file.py
chmod +x my_file.py
./my_file.py
```
To show the Watiba version of your pre-compiler, enter:
```
watiba-c.py version
```

### Examples

**my_file.wt**

```
#!/usr/bin/python3

# Stand alone commands.  One with directory context, one without

# This CWD will be active until a subsequent command changes it
`cd /tmp`

# This will not change the Watiba CWD context, because of the dash prefix, but within 
# the command itself the cd is honored.  file.txt is created in /home/user/blah but
# this does not impact the CWD of any subsequent commands.  They
# are still operating from the previous cd command to /tmp
-`cd /home/user/blah && touch file.txt`

# This will find text files in /tmp/, not /home/user/blah  (CWD context!)
w=`find . -name '*.txt'`
for l in w.stdout:
    print("File: {}".format(l))


# Embedding commands in print expressions that will print the stderr output, which tar writes to
print(`echo "BLAH!" > /tmp/blah.txt && tar -zcvf /tmp/blah.tar.gz /tmp/blah.txt`.stderr)
# This will print the first line of stdout from the echo
print(`echo "hello!"`.stdout[0])

# Example of more than one command in a statement line
if len(`ls -lrt`.stdout) > 0 or len(-`cd /tmp`.stdout) > 0:
    print("You have stdout or stderr messages")


# Example of a command as a Python varible and
#  receiving a Watiba object
cmd = "tar -zcvf /tmp/watiba_test.tar.gz /mnt/data/git/watiba/src"
cmd_results = `$cmd`
if cmd_results.exit_code == 0:
    for l in cmd_results.stderr:
        print(l)

# Simple reading of command output
#  Iterate on the stdout property
for l in `cat blah.txt`.stdout:
    print(l)

# example of a failed command to see its exit code
xc = `lsvv -lrt`.exit_code
print("Return code: {}".format(xc))
```
