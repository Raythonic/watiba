# Watiba
#### Version:  **0.6.6**
#### Date: 2021/01/24

Watiba, pronounced wah-TEE-bah, is a lightweight Python pre-compiler for embedding Linux shell 
commands within Python applications.  It is similar to other languages' syntactical enhancements where
XML or HTML is integrated into a language such as JavaScript.  That is the concept applied here but integrating
BASH shell commands with Python.

As you browse this document, you'll find Watiba is rich with features for shell command integration with Python.

Features:
- Shell command integration with Python code
- In-line access to shell command results
- Current directory context maintained across commands throughout your Python code
- Async/promise support for integrated shell commands
- Remote shell command execution
- Remote shell command chaining and piping

## Table of Contents
1. [Usage](#usage)
2. [Directory Context](#directory-context)
3. [Commands as Variables](#commands-as-variables)
4. [Command Results](#command-results)
5. [Asynchronous Spawning and Promises](#async-spawing-and-promises)
    1. [Useful Properties in Promise](#useful-properties-in-promise)
    2. [Spawn Controller](#spawn-controller)
    3. [Join, Wait or Watch](#join-wait-watch)
    4. [The Promise Tree](#promise-tree)
    5. [Threads](#threads)
6. [Remote Execution](#remote-execution)
    1. [Change SSH port for remote execution](#change-ssh-port)
7. [Command Chaining](#command-chaining)
8. [Command Chain Piping (Experimental)](#piping-output)
9. [Installation](#installation)
10. [Pre-compiling](#pre-compiling)
11. [Code Examples](#code-examples)

<div id="usage"/>

## Usage
Watiba files, suffixed with ".wt", are Python programs containing embedded shell commands. 
Shell commands are expressed within backtick characters emulating BASH's original capture syntax.
They can be placed in any Python statement or expression.  Watiba keeps track of the current working directory 
after the execution of any shell command so that all subsequent shell commands keep context.  For example:

Basic example of embedded commands:
```
#!/usr/bin/python3

# Typical Python program

if __name__ == "__main__":

    # Change directory context
    `cd /tmp`
    
    # Directory context maintained
    for file in `ls -lrt`.stdout:  # In-line access to command results
        print(f"File in /tmp: {file}")
```

This loop will display the file list from /tmp. The `ls -lrt` is run in the 
context of previous `cd /tmp`.  

<div id="commands-as-variables"/>

#### Commands Expressed as Variables
Commands within backticks can _be_ a variable, but cannot contain snippets of Python code or Python variables. 
The statement within the backticks _must_ be either a pure shell command or a Python variable containing a pure
shell command.  To execute commands in a Python variable, prefix the variable name between backticks with a dollar sign.

_A command variable is denoted by prepending a dollar sign on the variable name within backticks_:
```
# Set the Python variable to the command
cmdA = 'echo "This is a line of output" > /tmp/blah.txt'
cmdB = 'cat /tmp/blah.txt'

# Execute first command
`$cmdA`  # Execute the command within Python variable cmdA

# Execute second command
for line in `$cmdB`.stdout:
    print(line)
```

_This example demonstrates keeping dir context and executing a command by variable_:
```
#!/usr/bin/python3

if __name__ == "__main__":
    # Change CWD to /tmp
    `cd /tmp`
    
    # Set a command string
    my_cmd = "tar -zxvf tmp.tar.gz"
    
    # Execute that command and save the command results in variable "w"
    w = `$my_cmd`
    if w.exit_code == 0:
        for l in w.stderr:
            print(l)
```

_These constructs are **not** supported_:
 ```
file_name = "blah.txt"

# Python variable within backticks
`touch file_name`  # NOT SUPPORTED!

# Attempting to access Python variable with dollar sign
`touch $file_name` # NOT SUPPORTED!

# Python within backticks is NOT SUPPORTED!
`if x not in l: ls -lrt x`
```
<div id="directory-context"/>

## Directory Context

An important Watiba usage point is directory context is kept for dispersed shell commands.
Any command that changes the shell's CWD is discovered and kept by Watiba.  Watiba achieves 
this by tagging a `&& echo pwd` to the user's command, locating the result in the command's STDOUT, 
and finally setting the Python environment to that CWD with `os.chdir(dir)`.  This is automatic and 
opaque to the user.  The user will not see the results of the generated suffix.  If the `echo` 
suffix presents a problem for the user, it can be eliminated by prefixing the leading backtick with a
dash.  The dash turns off the context track, by not suffixing the command, and so causes Watiba to
lose its context.  However, the context is maintained _within_ the set of commands in the backticks just not
when it returns.  For example, **out = -\`cd /tmp && ls -lrt\`** honors the ```cd``` within the scope
of that execution line, but not for any backticked commands that follow later in your code.

**_Warning!_** The dash will cause Watiba to lose its directory context should the command
cause a CWD change either explicitly or implicitly.

_Example_:
```
`cd /tmp`  # Context will be kept

# This will print from /home/user, but context is NOT kept  
for line in -`cd /home/user && ls -lrt`.stdout:
    print(line) 

# This will print from /tmp, not /home/user
for line in `ls -lrt`.stdout:
    print(line)
```

<div id="command-results"/>

## Command Results
The results of the command issued in backticks are available in the properties
of the object returned by Watiba.  Following are those properties:

<table>
    <th>Property</th><th>Data Type</th><th>Description</th>
    <tr></tr>
    <td>stdout</td><td>List</td><td>STDOUT lines from the command normalized for display</td>
    <tr></tr>
    <td>stderr</td><td>List</td><td>STDERR lines from the command normalized for display</td>
    <tr></tr>
    <td>exit_code</td><td>Integer</td><td>Exit code value from command</td>
    <tr></tr>
    <td>cwd</td><td>String</td><td>Current working directory <i>after</i> command was executed</td>
</table>

Technically, the returned object for any shell command is defined in the WTOutput class.

<div id="async-spawing-and-promises"/>

## Asynchronous Spawning and Promises
Shell commands can be executed asynchronously with a defined resolver callback block.  Each _spawn_ expression creates
and runs a new OS thread. The resolver is a callback block that follows the Watiba _spawn_ expression.  The spawn 
feature is executed when a ```spawn `cmd` args: resolver block``` code block is encountered. The 
resolver is passed the results in the promise object. (The promise structure contains the properties 
defined in section ["Results from Spawned Commands"](#spawn-results)  The _spawn_ expression also returns a _promise_ object 
to the caller of _spawn_.  The promise object is passed to the _resolver block_ in argument _promise_.  The 
outer code can check its state with a call to _resolved()_ on the *returned* promise object.  Output from the command
is found in _promise.output_.  The examples throughout this README and in the _examples.wt_ file make this clear.

<div id="useful-properties-in-promise"/>

##### Useful properties in promise structure 
A promise is either returned in assignment from outermost spawn, or passed to child spawns in argument "promise".

  <table>
      <th>Property</th>
      <th>Data Type</th>
      <th>Description</th>
      <tr></tr>
      <td>host</td><td>String</td><td>Host name on which spawned command ran</td>
      <tr></tr>
      <td>children</td><td>List</td><td>Children promises for this promise node</td>
      <tr></tr>
      <td>parent</td><td>Reference</td><td>Parent promise node of child promise. None if root promise.</td>
      <tr></tr>
      <td>command</td><td>String</td><td>Shell command issued for this promise</td>
      <tr></tr>
      <td>resolved()</td><td>Method</td><td>Call to find out if this promise is resolved</td>
      <tr></tr>
      <td>resolve_parent()</td><td>Method</td><td>Call inside resolver block to resolve parent promise</td>
      <tr></tr>
      <td>tree_dump()</td><td>Method</td><td>Call to show the promise tree.  Takes subtree argument otherwise it defaults to the root promise</td>
      <tr></tr>
      <td>join()</td><td>Method</td><td>Call to wait on on promise and all its children</td>
      <tr></tr>
      <td>wait()</td><td>Method</td><td>Call to wait on just this promise</td>
      <tr></tr>
      <td>watch()</td><td>Method</td><td>Call to create watcher on this promise</td>
      <tr></tr>
      <td>start_time</td><td>Time</td><td>Time that spawned command started</td>
      <tr></tr>
      <td>end_time</td><td>Time</td><td>Time that promise resolved</td>
  </table>

_Example of simple spawn_:
```buildoutcfg
prom = spawn `tar -zcvf big_file.tar.gz some_dir/*`:
    # Resolver block to which "promise" and "args" is passed...
    print(f"{promise.command} completed.")
    return True  # Resolve promise

# Do other things while tar is running
# Finally wait for tar promise to resolve
prom.join()
```

<div id="spawn-controller"/>

#### Spawn Controller
All spawned threads are managed by Watiba's Spawn Controller.  The controller watches for too many threads and
incrementally slows down each thread start when that threshold is exceeded until either all the promises in the tree
resolve, or an expiration count is reached, at which time an exception is thrown on the last spawned command.  
This exception is raised by the default error method. This method as well as other spawn controlling parameters 
can be overridden.  The controller's purpose is to not allow run away threads and provide signaling of possible
hung threads.

_spawn-ctl_ example:
```buildoutcfg
# Only allow 20 spawns max, 
# and increase slowdown by 1/2 second each 3rd cycle
...python code...
spawn-ctl {"max":20, "sleep-increment":.500}  
```

Spawn control parameters:

<table>
    <th>Key Name</th>
    <th>Data Type</th>
    <th>Description</th>
    <th>Default</th>
    <tr></tr>
    <td>max</td><td>Integer</td><td>The maximum number of spawned commands allowed before the controller enters slowdown mode</td><td>10</td>
    <tr></tr>
    <td>sleep-floor</td><td>Integer</td><td>Seconds of <i>starting</i> 
sleep value when the controller enters slowdown mode</td><td>.125 (start at 1/8th second pause)</td>
    <tr></tr>
    <td>sleep-increment</td><td>Integer</td><td>Seconds the <i>amount</i> of seconds sleep will increase every 3rd cycle when in slowdown 
      mode</td><td>.125 (Increase pause 1/8th second every 3rd cycle)</td>
    <tr></tr>
    <td>sleep-ceiling</td><td>Integer</td><td>Seconds the <i>highest</i> length sleep value allowed when in slowdown mode  
      (As slow as it will get)</td><td>3 (won't get slower than 3 second pauses)</td>
    <tr></tr>
    <td>expire</td><td>Integer</td><td>Total number of slowdown cycles allowed before the error method is called</td><td>No expiration</td>
    <tr></tr>
    <td>error</td><td>Method</td><td>
    Callback method invoked when slowdown mode expires. Use this to catch hung commands.
            This method is passed 2 arguments:
    
- **promise** - The promise attempting execution at the time of expiration
- **count** - The thread count (unresolved promises) at the time of expiration
    </td><td>Generic error handler.  Just throws <i>WTSpawnException</i> that hold properties <i>promise</i> and <i>message</i></td></td>
</table>
    
_spawn-ctl_ only overrides the values it sets and does not affect values not specified.  _spawn-ctl_ statements can
set whichever values it wants, can be dispersed throughout your code (i.e. multiple _spawn-ctl_ statements) and 
only affects subsequent spawn expressions.

_Notes:_
1. Arguments can be passed to the resolver by specifying a trailing variable after the command.  If the arguments
variable is omitted, an empty dictionary, i.e. {}, is passed to the resolver in _args_.
**_Warning!_** Python threading does not deep copy objects passed as arguments to threads.  What you place in ```args```
of the spawn expression will only be shallow copied so if there are references to other objects, it's not likely to 
   survive the copy.
2. The resolver must return _True_ to set the promise to resolved, or _False_ to leave it unresolved.
3. A resolver can also set the promise to resolved by calling ```promise.set_resolved()```.  This is handy in cases where
a resolver has spawned another command and doesn't want the outer promise resolved until the inner resolvers are done. 
To resolve an outer, i.e. parent, resolver issue _promise.resolve_parent()_.  Then the parent resolver can return
_False_ at the end of its block so it leaves the resolved determination to the inner resolver block.
4. Each promise object holds its OS thread object in property _thread_ and its thread id in property _thread_id_. This
can be useful for controlling the thread directly.  For example, to signal a kill. 
5. _spawn-ctl_ has no affect on _join_, _wait_, or _watch_.  This is because _spawn-ctl_ establishes an upper end
throttle on the overall spawning process.  When the number of spawns hits the max value, throttling (i.e. slowdown 
   mode) takes affect and will expire if none of the promises resolve.  Conversely, the arguments used by _join_, 
   _wait_ and _watch_ control the sleep cycle and expiration of just those calls, not the spawned threads as a whole. When
   an expiration is set for, say, _join_, then that join will expire at that time.  When an expiration is set in
   _spawn-ctl_, then if all the spawned threads as a whole don't resolve in time then an expiration function is called.


**_Spawn Syntax:_**
```
my_promise = spawn `cmd` [args]:
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

_Simple spawn example_:
```buildoutcfg
p = spawn `tar -zcvf /tmp/file.tar.gz /home/user/dir`:
    # Resolver block to which "promise" and "args" are passed
    # Resolver block is called when spawned command has completed
    for line in promise.output.stderr:
        print(line)
    
    # This marks the promise resolved
    return True
    
# Wait for spawned command to resolve (not merely complete)
try:
    p.join({"expire": 3})
    print("tar resolved")
except Exception as ex:
    print(ex.args)
```

_Example of file that overrides spawn controller parameters_:
```
#!/usr/bin/python3
def spawn_expired(promise, count):
    print("I do nothing just to demonstrate the error callback.")
    print(f"This command failed {promise.command} at this threshold {count}")
    
    raise Exception("Too many threads.")
    
if __name__ == "__main__":
    # Example showing default values
    parms = {"max": 10, # Max number of threads allowed before slowdown mode
         "sleep-floor": .125,  # Starting sleep value
         "sleep-ceiling": 3,  # Maximum sleep value
         "sleep-increment": .125,  # Incremental sleep value
         "expire": -1,  # Default: no expiration
         "error": spawn_expired  # Method called upon slowdown expiration
    }
     
    # Set spawn controller parameter values
    spawn-ctl parms
```

<div id="join-wait-watch"/>

#### Join, Wait, or Watch

Once commands are spawned, the caller can wait for _all_ promises, including inner or child promises, to complete, or
the caller can wait for just a specific promise to complete.  To wait for all _child_ promises including
the promise on which you're calling this method, call _join()_.  It will wait for that promise and all its children. To 
wait for just one specific promise, call _wait()_ on the promise of interest.  To wait for _all_ promises in 
the promise tree, call _join()_ on the root promise.

_join_ and _wait_ can be controlled through parameters.  Each are iterators paused with a sleep method and will throw
an expiration exception should you set a limit for iterations.  If an expiration value is not set,
no exception will be thrown and the cycle will run only until the promise(s) are resolved.  _join_ and _wait_ are not
affected by _spawn-ctl_.

_watch_ is called to establish a separate asynchronous thread that will call back a function of your choosing should
the command the promise is attached to time out.  This is different than _join_ and _wait_ in that _watch_ is not synchronous 
and does not pause.  This is used to keep an eye on a spawned command and take action should it hang.  Your watcher
function is passed the promise on which the watcher was attached, and the arguments, if any, from the spawn expression.
If your command does not time out (i.e. hangs and expires), the watcher thread will quietly go away when the promise
is resolved.  _watch_ expiration is expressed in **seconds**, unlike _join_ and _wait_ which are expressed as total
_iterations_ paused at the sleep value.  _watch_'s polling cycle pause is .250 seconds, so the expiration value is
multiplied by 4.  The default expiration is 15 seconds.

Examples:
```
# Spawn a thread running this command
p = spawn `ls -lrt`:
    ## resolver block ##
    return True
    
# Wait for promises, pause for 1/4 second each iteration, and throw an exception after 4 iterations 
(1 second)
try:
    p.join({"sleep": .250, "expire": 4})
except Exception as ex:
    print(ex.args)

# Wait for this promise, pause for 1 second each iteration, and throw an exception after 5 iterations 
(5 seconds)
try:
    p.wait({"sleep": 1, "expire": 5})
except Exception as ex:
    print(ex.args)
 
# My watcher function (called if spawned command never resolves by its experation period)
def watcher(promise, args):
    print(f"This promise is likely hung: {promise.command}")
    print(f"and I still have the spawn expression's args: {args}")

p = spawn `echo "hello" && sleep 5` args:
    print(f"Args passed to me: {args}")
    return True

# Attach a watcher to this thread.  It will be called upon experation.
p.watch(watcher)
print("watch() does not pause like join or wait")

# Attach a watcher that will expire in 5 seconds
p.watch(watcher, {"expire": 5})
```

**_join_ syntax**
```
promise.join({optional args})
Where args is a Python dictionary with the following options:
    "sleep" - seconds of sleep for each iteration (fractions such as .5 are honored)
        default: .5 seconds
    "expire" - number of sleep iterations until an excpetions is raised
        default: no expiration
Note: "args" is optional and can be omitted
```

_Example of joining parent and children promises_:
```
p = spawn `ls *.txt`:
    for f in promise.output.stdout:
        cmd = f"tar -zcvf {f}.tar.gz {f}"
        spawn `$cmd` {"file":f}:
            print(f"{f} completed")
            promise.resolve_parent()
            return True
    return False

# Wait for all commands to complete
try:
    p.join({"sleep":1, "expire":20})
except Exception as ex:
    print(ex.args)
```

**_wait_ syntax**
```
promise.wait({optional args})
Where args is a Python dictionary with the following options:
    "sleep" - seconds of sleep for each iteration (fractions such as .5 are honored)
        default: .5 seconds
    "expire" - number of sleep iterations until an excpetions is raised
        default: no expiration
Note: "args" is optional and can be omitted
```

_Example of waiting on just the parent promise_:
```
p = spawn `ls *.txt`:
    for f in promise.output.stdout:
        cmd = f"tar -zcvf {f}.tar.gz {}"
        spawn `$cmd` {"file":f}:
            print(f"{f} completed")
            promise.resolve_parent() # Wait completes here
            return True
    return False

# Wait for just the parent promise to complete
try:
    p.wait({"sleep":1, "expire":20})
except Exception as ex:
    print(ex.args)
```

**_watch_ syntax**
```
promise.watch(callback, {optional args})
Where args is a Python dictionary with the following options:
    "sleep" - seconds of sleep for each iteration (fractions such as .5 are honored)
        default: .5 seconds
    "expire" - number of sleep iterations until an excpetions is raised
        default: no expiration
Note: "args" is optional and can be omitted
```

_Example of creating a watcher_:
```buildoutcfg
# Define watcher method.  Called if command times out (i.e. expires)
def time_out(promise, args):
    print(f"Command {promise.command} timed out.")

# Spawn a thread running some command that hangs
p = spawn `long-running.sh`:
    print("Finally completed.  Watcher method won't be called.")
    return True
 
p.watch(time_out)  # Does not wait.  Calls method "time_out" if this promise expires (i.e. command hangs)
 
# Do other things...
 
```

<div id="promise-tree"/>

#### The Promise Tree
Each _spawn_ issued inserts its promise object into the promise tree.  The outermost _spawn_ will generate the root
promise and each inner _spawn_ will be among its children.  There's no limit to how far it can nest.  _wait_ only applies
to the promise on which it is called and is how it is different than _join_.  _wait_ does not consider any other
promise state but the one it's called for, whereas _join_ considers the one it's called for **and** anything below it
in the tree.

The promise tree can be printed with the ```dump_tree()``` method on the promise.  This method is intended for
diagnostic purposes where it must be determined why spawned commands hung.  ```dump_tree(subtree)``` accepts
a subtree promise as an argument.  If no arguments are passed, ```dump_tree()``` dumps from the root promise on down.
```
# Simple example with no child promises
p = spawn `date`:
    return True
    
p.tree_dump()  # Dump tree from root
# or
p.tree_dump(subtree_promise)  # Dump tree from node in argument
```

Example dumping tree from subtree node:
```buildoutcfg
# Complex example with child and grandchild promises
# Demonstrates how to dump the promise tree from various points within it
p = spawn `date`:
    # Spawn child command (child promise)
    spawn `pwd`:
        # Spawn a grandchild to the parent promise
        spawn `python --version`:
            promise.tree_dump(promise)  # Dump the subtree from this point down
            return False
    # Spawn another child
     spawn `echo "blah"`:
         # Resolve parent promise
         promise.resolve_parent()
         # Resolve child promise
        return True
    # Do NOT resolve parent promise, let child do that
    return False
    
p.join()
p.tree_dump(p.children[0])  # Dump subtree from first child on down
p.tree_dump(p.children[1])  # Dump subtree from the second child
p.tree_dump(p.children[0].children[0]) # Dump subtree from the grandchild 

# Dump all children
for c in p.children:
    p.tree_dump(c)
```

_Parent and child joins shown in these two examples_:

``` 
root_promise = spawn `ls -lr`:
    for file in promise.stdout:
        t = f"touch {file}"
        spawn `$t` {"file" file}:  # This promise is a child of root
            print(f"{file} updated".)
            spawn `echo "done" > /tmp/done"`:  # Another child promise (root's grandchild)
                print("Complete")
                promise.resolve_parent()
                return True
            promise.resolve_parent()
            return False
    return False

root_promise.join()  # Wait on the root promise and all its children.  Thus, waiting for everything.
```

``` 
root_promise = spawn `ls -lr`:
    for file in promise.output.stdout:
        t = f"touch {file}"
        spawn `$t` {"file" file}:  # This promise is a child of root
            print(f"{promise.args['file'])} updated")
            promise.join() # Wait for this promise and its children but not its parent (root)
            spawn `echo "done" > /tmp/done"`:
                print("Complete")
```



_Resolving a parent promise_:
```
p = spawn `ls -lrt`:
    for f in promise.output.stdout:
        cmd = f"touch {f}"
        # Spawn command from this resolver and pass our promise
        spawn `$cmd`:
            print("Resolving all promises")
            promise.resolve_parent() # Resolve parent promise here
            return True # Resolve child promise
        return False # Do NOT resolve parent promise here
p.join()  # Wait for ALL promises to be resolved
```

<div id="spawn-results"/>

### Results from Spawned Commands
Spawned commands return their results in the _promise.output_ property of the _promise_ object passed to
the resolver block, and in the spawn expression if there is an assignment in that spawn expression.

The result properties can then be accessed as followed:

<table>
    <th>Property</th><th>Data Type</th><th>Description</th>
    <tr></tr>
    <td>promise.output.stdout</td><td>List</td><td>STDOUT lines from the command normalized for display</td>
    <tr></tr>
    <td>promise.output.stderr</td><td>List</td><td>STDERR lines from the command normalized for display</td>
    <tr></tr>
    <td>promise.output.exit_code</td><td>Integer</td><td>Exit code value from command</td>
    <tr></tr>
    <td>promise.output.cwd</td><td>String</td><td>Current working directory <i>after</i> command was executed</td>
</table>


_Notes:_
1. Watiba backticked commands can exist within the resolver 
2. Other _spawn_ blocks can be embedded within a resolver (recursion allowed)
3. The command within the _spawn_ definition can be a variable
    (The same rules apply as for all backticked shell commands.  This means the variable must contain
   pure shell commands.)
4. The leading dash to ignore CWD _cannot_ be used in the _spawn_ expression
5. The _promise.output_ object is not available until _promise.resolved()_ returns True

_Simple example with the shell command as a Python variable_:
```
#!/usr/bin/python3

# run "date" command asynchronously 
d = 'date "+%Y/%m/%d"'
spawn `$d`:
    print(promise.output.stdout[0])
    return True

```

_Example with shell commands executed within resolver block_:
```
#!/usr/bin/python3

print("Running Watiba spawn with wait")
`rm /tmp/done`

# run "ls -lrt" command asynchronously 
p = spawn `ls -lrt`:
    print(f"Exit code: {promise.output.exit_code}")
    print(f"CWD: {promise.output.cwd}")
    print(f"STDERR: {promise.output.stderr}")

    # Loop through STDOUT from command
    for l in promise.output.stdout:
        print(l)
    `echo "Done" > /tmp/done`

    # Resolve promise
    return True

# Pause until spawn command is complete
p.wait()
print("complete")

```

<div id="threads"/>

### Threads
Each promise produced from a _spawn_ expression results in one OS thread.  To access the 
number of threads your code has spawned collectively, you can do the following:
``` 
num_of_spawns = promise.spawn_count()  # Returns number of nodes in the promise tree
num_of_resolved_promises = promise.resolved_count() # Returns the number of promises resolved in tree
``` 
<div id="remote-execution"/>

## Remote Execution
Shell commands can be executed remotely.  This is achieved though the SSH command, issued by Watiba, and has the 
following requirements:
- OpenSSH is installed on the local and remote hosts
- The local SSH key is in the remote's _authorized_keys_ file.  _The details of this
  process is beyond the scope of this README.  For those instructions, consult www.ssh.com_
  
- Make sure that SSH'ing to the target host does not cause any prompts.  
  
Test that your SSH environment is setup first by manually entering: 
```
ssh {user}@{host} "ls -lrt"

# For example
ssh rwalk@walkubu "ls -lrt"

# If SSH prompts you, then Watiba remote execution cannot function. 
```

To execute a command remotely, a _@host_ parameter is suffixed to the backticked command.  The host name can be a
literal or a variable.  To employ a variable, prepend a _$_ to the name following _@_ such as _@$var_.

<div id="change-ssh-port"/>

#### Change SSH port for remote execution
To change the default SSH port 22 to a custom value, add to your Watiba code:  ```watiba-ctl {"ssh-port": custom port}```
Example:
```buildoutcfg
watiba-ctl {"ssh-port": 2233}
```
Examples:
```buildoutcfg
p = spawn `ls -lrt`@remoteserver {parms}:
    for line in promise.output.stdout:
        print(line)
    return True
     
```  
```buildoutcfg
remotename = "serverB"
p = spawn `ls -lrt`@$remotename {parms}:
    for line in p.output.stdout:
        print(line)
    return True
```
```buildoutcfg
out = `ls -lrt`@remoteserver
for line in out.stdout:
    print(line)
```
```buildoutcfg
remotename = "serverB"
out = `ls -lrt`@$remotename
for line in out.stdout:
    print(line)
```

<div id="command-chaining"/>

## Command Chaining
Watiba extends its remote command execution to chaining commands across multiple remote hosts.  This is achieved
by the _chain_ expression.  This expression will execute the backticked command across a list of hosts, passed by
the user, sequentially, synchronously until the hosts list is exhausted, or the command fails.  _chain_ returns a
Python dictionary where the keys are the host names and the values the WTOutput from the command run on that host.

#### Chain Exception
The _chain_ expression raises a WTChainException on the first failed command.  The exception raised
has the following properties:

_WTChainException_:
<table>
<th>Property</th><th>Data Type</th><th>Description</th>
<tr></tr>
<td>command</td><td>String</td><td>Command that failed</td>
<tr></tr>
<td>host</td><td>String</td><td>Host where command failed</td>
<tr></tr>
<td>message</td><td>String</td><td>Error message</td>
<tr></tr>
<td>output</td><td>WTOutput structure:

- stdout
- stderr
- exit_code
- cwd</td><td>Output from command</td>
</table>

Import this exception to catch it:
```buildoutcfg
from watiba import WTChainException
```


Examples:
```
from watiba import WTChainException

try:
    out = chain `tar -zcvf backup/file.tar.gz dir/*` {"hosts", ["serverA", "serverB"]}
    for host,output in out.items():
        print(f'{host} exit code: {output.exit_code}')
        for line in output.stderr:
            print(line)
 except WTChainException(ex):
    print(f"Error: {ex.message}")
    print(f"  host: {ex.host} exit code: {ex.output.exit_code} command: {ex.command})
            
```

<div id="piping-output"/>

## Command Chain Piping (Experimental)
The _chain_ expression supports piping STDOUT and/or STDERR to other commands executed on remote servers.  Complex
arrangements can be constructed through the Python dictionary passed to the _chain_ expression.  The dictionary
contents function as follows:
- "hosts": [server, server, ...]   This entry instructions _chain_ on which hosts the backticked command will run.
    This is a required entry.
    
- "stdout": {server:command, server:command, ...}
    This is an optional entry.
  
- "stderr": {server:command, server:command, ...}
    This is an optional entry.

Just like a _chain_ expression that does not pipe output, the return object is a dictionary of WTOutput object keyed
by the host name from the _hosts_ list and *not* from the commands recieving the piped output.

If any command fails, a WTChainException is raised.  Import this exception to catch it:
```buildoutcfg
from watiba import WTChainException
```

_Note_: _The piping feature is experimental as of this release, and a better design will eventually
supercede it._

Examples:  
```
from watiba import WTChainException

# This is a simple chain with no piping
try:
    args = {"hosts": ["serverA", "serverB", "serverC"]}
    out = chain `ls -lrt dir/` args
    for host, output in out.items():
        print(f'{host} exit code: {output.exit_code}')
except WTChainException as ex:
    print(f'ERROR: {ex.message}, {ex.host}, {ex.command}, {ex.output.stderr}')
```
```
# This is a more complex chain that runs the "ls -lrt" command on each server listed in "hosts"
# and pipes the STDOUT output from serverC to serverV and serverD, to those commands, and serverB's STDERR
# to serverX and its command
try:
    args = {"hosts": ["serverA", "serverB", "serverC"],
                "stdout": {"serverC":{"serverV": "grep something", "serverD":"grep somethingelse"}},
                "stderr": {"serverB":{"serverX": "cat >> /tmp/serverC.err"}}
           }
    out = chain `ls -lrt dir/` args
    for host, output in out.items():
        print(f'{host} exit code: {output.exit_code}')
except WTChainException as ex:
    print(f'ERROR: {ex.message}, {ex.host}, {ex.command}, {ex.output.stderr}')
```

####How does this work?
Watiba will run the backticked command in the expression on each host listed in _hosts_, in sequence and synchronously.
If there is a "stdout" found in the arguments, then it will name the source host as the key, i.e. the host from which
STDOUT will be read, and fed to each host and command listed under that host.  This is true for STDERR as well.

The method in which Watiba feeds the piped output is through a an _echo_ command shell piped to the command to be run
on that host.  So, "stdout": {"serverC":{"serverV": "grep something"}} causes Watiba to read each line of STDOUT from
serverC and issue ```echo "$line" | grep something``` on serverV.  It is piping from serverC to serverV.

<div id="installation"/>

## Installation
### PIP
If you installed this as a Python package, e.g. pip, then the pre-compiler, _watiba-c_,
will be placed in your system's PATH by PIP.

### GITHUB
If you cloned this from github, you'll still need to install the package with pip, first, for the
watbia module.  Follow these steps to install Watiba locally.
```
# Watiba package required
python3 -m pip install watiba
```


<div id="pre-compiling"/>

## Pre-compiling
Test that the pre-compiler functions in your environment:
```
watiba-c version
```
For example:
```buildoutcfg
rwalk@walkubu:~$ watiba-c version
Watiba 0.3.26
```

To pre-compile a .wt file:
```
watiba-c my_file.wt > my_file.py
chmod +x my_file.py
./my_file.py
```

Where _my_file.wt_ is your Watiba code.

<div id="code-examples"/>

## Code Examples

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
print(f"CWD is not /home: {-`cd /home`.cwd)}"

# This will find text files in /tmp/, not /home/user/blah  (CWD context!)
w=`find . -name '*.txt'`
for l in w.stdout:
    print(f"File: {l}")


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
print(f"Return code: {xc}")

# Example of running a command asynchronously and resolving promise
spawn `cd /tmp && tar -zxvf tarball.tar.gz`:
    for l in promise.output.stderr:
        print(l)
    return True  # Mark promise resolved


# List dirs from CWD, iterate through them, spawn a tar command
# then within the resolver, spawn a move command
# Demonstrates spawns within resolvers
for dir in `ls -d *`.stdout:
    tar = "tar -zcvf {}.tar.gz {}"
    prom = spawn `$tar` {"dir": dir}:
        print(f"{}args['dir'] tar complete")
        mv = f"mv -r {args['dir']}/* /tmp/."
        spawn `$mv`:
            print("Move done")
            # Resolve outer promise
            promise.resolve_parent()
            return True
        # Do not resolve this promise yet.  Let the inner resolver do it
        return False
    prom.join()
```
