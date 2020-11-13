# Watiba
Watiba is a lightweight Python pre-compiler for embedding Linux shell 
commands within Python applications.

## Usage
Watiba files, suffixed with ".wt", are Python programs containing embedded shell commands. 
Shell commands are expressed within backtick characters emulating BASH's original capture syntax.
They can be placed in any Python statement or expression.  Watiba keeps track of the current working directory after the execution of 
any shell command so that all subsequent shell commands keep context.  For example:

```
#/usr/bin/python3

if __name__ == "__main__":
    `cd /tmp`
    for l in 'ls -lrt`.stdout:
        print(l)
```

This loop will display the file list from /tmp. The `ls -lrt` is run in the 
context of previous `cd /tmp`.  

Commands can also be Python variables. This is denoted by prepending a dollar sign on the
variable name within backticks. A complete example:

```
#/usr/bin/python3

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
command and then locating the result in the command's STDOUT and setting the
Python environment to that CWD with `os.chdir(dir)`.  This is automatic and opaque to the user.  The 
user's STDOUT from the command(s) will not contain
the product of the `echo` as this element is removed from the STDOUT array passed
to the user's program.

If the `echo` command suffix presents a problem for the user, it can be eliminated by prefixing
the leading backtick with a dash.  Example:  ```for l in -`ls -lrt && pwd`.stdout:```
Warning: the dash will cause Watiba to lose its directory context should the command
cause a CWD change.

### Command Results
The results of the command issued in backticks are available in the properties
of the object returned by Watiba.  Treat the backticked command as a normal
Python object.  Following are its properties:
 
- stdout - array of output lines from the command normalized for display
- stderr - array of standard error output lines from the command normalized for display
- exit_code - integer exit code value from command
- cwd - current working directory after command was executed

### Examples
```

# Stand alone commands.  One with directory context, one without

# This CWD will be active until a subsequent command changes it
`cd /tmp`

# This will not change the Watiba CWD context, becasue of the dash prefix, but within 
# the command itself the cd is honored.  file.txt is created in /home/user/blah but
# this does not impact the CWD of any subsequent commands.  They
# are still operating from the previous cd command to /tmp
-`cd /home/user/blah && touch file.txt`

# This will find text files in /tmp/, not /home/user/blah  (CWD context!)
w=`find . -name '*.txt'`
for l in w.stdout:
    print("File: {}".format(l))


# Embedding commands in print expressions
print(`echo "BLAH!" > /tmp/blah.txt && tar -zcvf /tmp/blah.tar.gz /tmp/blah.txt`.stderr)
print(-`echo "hello!"`.stdout[0])

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