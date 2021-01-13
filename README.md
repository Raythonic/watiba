# Watiba
Watiba, pronounced wah-TEE-bah, is a lightweight Python pre-compiler for embedding Linux shell 
commands within Python applications.  It is similar to other languages' syntactical enhancements where
XML or HTML is integrated into a language such as JavaScript.  That is the concept applied here but integrating
BASH shell commands with Python.

As you browse this document, you'll find Watiba is rich with features for shell command integration with Python.

Features:
- Shell command integration with Python code
- Current directory context maintained across commands throughout your Python code
- Async/promise support for integrated shell commands
- Remote shell command execution
- Remote shell command chaining and piping


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
