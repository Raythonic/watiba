# Watiba
Watiba, pronounced wah-TEE-bah, is a lightweight Python pre-compiler for embedding Linux shell 
commands within Python applications.

## Usage
Watiba files, suffixed with ".wt", are Python programs containing embedded shell commands. 
Shell commands are expressed within backtick characters emulating BASH's original capture syntax.
They can be placed in any Python statement or expression.  Watiba keeps track of the current working directory 
after the execution of any shell command so that all subsequent shell commands keep context.  For example:

```
#!/usr/bin/python3

if __name__ == "__main__":
    `cd /tmp`
    for l in `ls -lrt`.stdout:
        print(l)
```

This loop will display the file list from /tmp. The `ls -lrt` is run in the 
context of previous `cd /tmp`.  

Commands can also be Python variables only if the entire command is within the variable. This is denoted by 
prepending a dollar sign on the variable name within backticks. A complete example:

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

#### Commands Expressed as Variables
Commands within backticks can _be_ a variable, but cannot contain snippets of Python code or Python variables. 
The statement within the backticks _must_ be either a pure shell command or a Python variable containing a pure
shell command.  To execute commands in a Python variable, prefix the variable name between backticks with a dollar sign.

A command expressed in a Python variable can be executed like this:
```
# Set the Python variable to the command
touch_cmd = "touch /tmp/blah.txt"

# Execute it
`$touch_cmd`  # Execute the command within Python variable touch_cmd
```
An example of building a command from other variables and then executing it within a print() statement:
```
in_file = "some_file.txt"
my_cmd = "cat {}".format(in_file)
print(`$my_cmd`.stdout)
```

These constructs are not supported:
 ```
file_name = "blah.txt"

# Python variable within backticks
`touch file_name`  # NOT SUPPORTED!

# Attempting to access Python variable with dollar sign
`touch $file_name` # NOT SUPPORTED!

# Mixed shell and Python statements within backticks
`if x not in l: ls -lrt x` # NOT SUPPORTED!
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
of the object returned by Watiba in an object.  Treat the backticked command as a normal
Python object.  Following are its properties:

- stdout - array of output lines from the command normalized for display
- stderr - array of standard error output lines from the command normalized for display
- exit_code - integer exit code value from command
- cwd - current working directory after command was executed


## Asynchronous Spawning and Promises
Shell commands can be executed asynchronously with a defined resolver callback block.
The resolver is a callback block that follows the Watiba _spawn_ expression.  The spawn feature is executed
when a ```spawn `cmd` args: resolver block``` code block is encountered. The 
resolver is passed the results in the promise object. (The promise structure contains the properties 
defined in "Results from Spawned Command" of this README.)  The _spawn_ expression returns a _promise_ object 
that can be used by the outer code to check for resolution.  The promise object is passed to the resolver 
in variable _promise_.  The outer code can check its state with a call to _resolved()_ on 
the *returned* promise object.  Output from the command is found in _promise.output_

_Notes:_
1. Arguments can be passed to the resolver by specifying a trailing variable after the command.  If the arguments
variable is omitted, an empty dictionary, i.e. {}, is passed to the resolver in _args_.
**_Warning!_** Python threading does not deep copy objects passed as arguments to threads.  What you place in ```args```
of the spawn expression will only be shallow copied so if there's references to other objects, it's
to not likely to survive the copy.
2. The resolver must return _True_ to set the promise to resolved, or _False_ to leave it unresolved.
3. The outer code creating the spawned command can synchronize with it by calling the _.join()_ method on the promise
object.
4. A resolver can also set the promise to resolved by calling ```promise.set_resolved()```.  This is handy in cases where
a resolver has spawned another command and doesn't want the outer promise resolved until the inner resolvers are done. 
To resolve an outer, i.e. parent, resolver issue _promise.resolve_parent()_.  Then the parent resolver can return
_False_ at the end of its block so it leaves the resolved determination to the inner resolver block.
This is demonstrated in the examples.


**_Spawn Syntax:_**
```
my_promise = spawn `cmd` [args]:
    resolver block (promise, args)
    args passed in args
    return resolved or unresolved (True or False)
 ```
    
_For spawns within class definitions_:
```
my_promise = self.spawn `cmd` [args]:
    resolver block (promise, args)
    args passed in args
    return resolved or unresolved (True or False)
```
    
_Spawn with resolver arguments omitted_:
```
my_promise = spawn `cmd`:
    resolver block (promise, args)
    return resolved or unresolved (True or False)
```
        
_For spawns within class definitions resolver arguments omitted_:
```
my_promise = self.spawn `cmd`:
    resolver block (promise, args)
    return resolved or unresolved (True or False)
```

_Resolving an outer promise_:
```
p = spawn `ls -lrt`:
    for f in promise.output.stdout:
        cmd = "touch {}".format(f)
        # Spawn command from this resolver and pass our promise
        spawn `$cmd`:
            print("Resolving all promises")
            promise.resolve_parent() # Resolve outer promise
            return True # Resolve inner promise
        return False # Do NOT resolve outer promise here
p.join()  # Wait for ALL promises to be resolved
```

_Expanded example_:
```
#!/usr/bin/python3

# Args dictionary passed to resolver
my_args = {"msg": "tar command completed.  Output follows:"}

# Spawn argment and callback resolver block
my_promise = spawn `tar -zcvf tarball.tar.gz /tmp` my_args:
    # Start of resolver block
    # Get my_args passed to resolver
    print(args["msg"])

    # The command results are found in promise.output
    print("Command stdout: {}".format(promise.output.stdout))

    # Tar's output in STDERR
    for l in promise.output.stderr:
        print(l)

    # Promise resolved
    return True

# Sleep until the promise is resolved
my_promise.join()

# Once the promise is resolved, the command output is available
print("Command exit code: {}".format(my_promise.output.exit_code))
```
### Results from Spawned Command
Spawned commands return their results in the _promise.output_ reference of the _promise_ object passed to
the resolver block, and in the spawn expression if there is an assignment in that spawn expression.  
The result properties can then be accessed as followed:
 
- promise.output.stdout - array of output lines from the command normalized for display
- promise.output.stderr - array of standard error output lines from the command normalized for display
- promise.output.exit_code - integer exit code value from command
- promise.output.cwd - current working directory after command was executed

_Notes:_
1. Watiba backticked commands can exist within the resolver 
2. Other _spawn_ blocks can be embedded within a resolver (recursion allowed)
3. The command within the _spawn_ definition can be a variable
    (The same rules apply as for all backticked shell commands)
4. The leading dash to ignore CWD _cannot_ be used in the _spawn_ command
5. The _promise.output_ object is not available until _promise.resolved()_ returns True

Example of a promise returned in the spawn assignment, to variable _p_, and passed to the resolver in argument
_promise_.
```
dir = "ls -lrt /tmp"
p = spawn `$dir`:
    # Outcome found in argument "promise"
    print(promise.output.stdout)
    return True

# Wait until promise is resolved
while not p.resolved():
    print("Command not finished")
    `sleep 5`

 print("Command completed.")
```

Simple example.  

```
#!/usr/bin/python3

# run "date" command asynchronously 
spawn `date`:
    for l in promise.output.stdout:
        print(l)
    return True

```

Simple example with the shell command as a Python variable:
```
#!/usr/bin/python3

# run "date" command asynchronously 
d = 'date "+%Y/%m/%d"'
spawn `$d`:
    print(promise.output.stdout[0])
    return True

```
Example with shell commands executed within resolver block:
```
#!/usr/bin/python3
import os

print("Running Watiba spawn with wait")
`rm /tmp/done`

# run "ls -lrt" command asynchronously 
spawn `ls -lrt`:
    print("Exit code: {}".format(promise.output.exit_code))
    print("CWD: {}".format(promise.output.cwd))
    print("STDERR: {}".format(promise.output.stderr))
    for l in promise.output.stdout:
        print(l)
    `touch /tmp/done`
    return True

# Pause until spawn command is complete
while not os.path.exists("/tmp/done"):
    `sleep 3`

print("complete")

```

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
If you cloned this from github, you'll still need to install the package with pip, first, for the
watbia module.  Follow these steps to install Watiba locally.
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

# Simple statement utilizing command and results in one statement
print(`cd /tmp`.cwd)

# This will not change the Watiba CWD context, because of the dash prefix, but within 
# the command itself the cd is honored.  file.txt is created in /home/user/blah but
# this does not impact the CWD of any subsequent commands.  They
# are still operating from the previous cd command to /tmp
-`cd /home/user/blah && touch file.txt`

# This will print "/tmp" _not_ /home because of the leading dash on the command
print("CWD is not /home: {}".format(-`cd /home`.cwd))

# This will find text files in /tmp/, not /home/user/blah  (CWD context!)
w=`find . -name '*.txt'`
for l in w.stdout:
    print("File: {}".format(l))


# Embedding commands in print expressions that will print the stderr output, which tar writes to
print(`echo "Some textual comment" > /tmp/blah.txt && tar -zcvf /tmp/blah.tar.gz /tmp`).stdout)

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

# Example of a failed command to see its exit code
xc = `lsvv -lrt`.exit_code
print("Return code: {}".format(xc))

# Example of running a command asynchronously and using the resolver callback code block
spawn `cd /tmp && tar -zxvf tarball.tar.gz`:
    for l in promise.output.stderr:
        print(l)
print("This prints before the tar output.")
`sleep 5`  # Pause for 5 seconds so spawn can complete

# List dirs from CWD, iterate through them, spawn a tar command
# then within the resolver, spawn a move command
# Demonstrates spawns within resolvers
for dir in `ls -d *`.stdout:
    tar = "tar -zcvf {}.tar.gz {}"
    prom = spawn `$tar` {"dir": dir}:
        print("{} tar complete".format(args["dir"]))
        mv = "mv -r {}/* /tmp/.".format(args["dir"])
        spawn `$mv`:
            print("Move done")
            # Resolve outer promise
            promise.resolve_parent()
            return True
        # Do not resolve this promise yet.  Let the inner resolver do it
        return False
    prom.join()
```
