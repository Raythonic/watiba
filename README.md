# Watiba
Watiba is very light bit of syntactical sugar for Python applications.
  It allows embedded Linux shell commands within any Python 
  statement or expression.

## Usage
Watiba files, suffixed with ".wt", are Python programs containing embedded shell commands.  
Shell commands are expressed within backtick characters emulating BASH's original capture syntax.
They can be placed in any Python statement or expression.  Watiba keeps track of the current working directory after the execution of 
any shell command so that all subsequent shell commands keep context.  For example:

```
#/usr/bin/python

if __name__ == "__main__":
    `cd /tmp`
    for l in 'ls -lrt`.stdout:
        print(l)
```

This loop will display the file list from /tmp. The `ls -lrt` is run in the 
context of previous `cd /tmp`.  

### Directory Context

A prominent Watiba usage point is directory context is kept for dispersed shell commands.
Any command that changes the shell's CWD is discovered and kept by Watiba.  
Watiba achieves this by tagging a `&& echo pwd` to the user's 
command and then locating the result in the command's STDOUT and setting the
Python environment to that CWD with `os.chdir(dir)`.  This is automatic and opaque to the user.  
The user's STDOUT from the command(s) will not contain
the product of the `echo` as this element is removed from the STDOUT array passed
to the user's program.

If the `echo` presents a problem for the user, it can be eliminated by prefixing
the leading escape (backtick) with dash.  Example:  ```for l in -`ls -lrt && pwd`.stdout:```
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