#!/usr/bin/python3.8
'''
Watiba class wraps the Python subprocess and captures all its outputs in a single object

Author: Ray Walker
Raythonic@gmail.com
'''

from subprocess import Popen, PIPE, STDOUT
import re
import os
import threading
import time
import copy


# The object returned to the caller of _watiba_ for command results
class WTOutput(Exception):
    def __init__(self):
        self.stdout = []
        self.stderr = []
        self.exit_code = 0
        self.cwd = "."


# The object returned for Watbia thread spawns
class WTPromise(Exception):
    def __init__(self, command):
        self.output = WTOutput()
        self.resolution = False
        self.id = time.time()
        self.children = []
        self.parent = None
        self.command = command
        self.state = {True: "Resolved", False: "UNRESOLVED"}

    def resolved(self):
        return self.resolution

    def set_resolved(self):
        self.resolution = True

    # Resolve the parent promise if one exists
    def resolve_parent(self):
        if self.parent:
            self.parent.set_resolved()

    # Count this promise's children
    def child_counter(self, child, count, resolved_only=False):
        # Count 1 if not counting just resolved, otherwise only count it if it's resolved
        count += 1 if not resolved_only or child.resolved() else 0

        # Count these children (descend)
        for c in child.children:
            count = self.child_counter(c, count)

        return count

    # Count promise tree size
    # Set resolved_only to True to only count resolved promises in the tree
    def spawn_count(self, resolved_only=False, start_at_top=True):
        # Start with this promise
        p = self

        # Walk to the top of the tree
        while start_at_top and p.parent:
            p = p.parent

        # Count this promise
        count = 1 if not resolved_only or p.resolved() else 0

        # Now do a descending count down the tree
        for child in p.children:
            count = self.child_counter(child, count, resolved_only)

        return count

    # Count resolve promises in tree
    def resolved_count(self, start_at_top=True):
        # Full tree count?
        return self.spawn_count(True, start_at_top)


    # Check the resolved state of nodes in promise tree.
    # Returns True of all nodes (promises) in tree or a subtree, starting from the position given,
    # are resolved, otherwise False.
    def tree_resolved(self, position_node=None):
        # If we're not given a position in the tree to start from
        #   start at the root promise.
        starting_node = self if not position_node else position_node
        while not position_node and starting_node.parent:
            starting_node = starting_node.parent

        # Start at the tree node we're supposed to
        position_node = starting_node

        # Check the node we're on
        total_resolved = position_node.resolved()

        # Now recursively check the children.  If anyone returns unresolved,
        # then the final result will be unresolved (False)
        for child in position_node.children:
            total_resolved &= self.tree_resolved(child)
        return total_resolved

    # Mostly for debugging.  Will document later if it seems necessary
    def tree_dump(self, p = None, dashes=""):
        def lengthen(d):
            d = d.replace("-", " ").replace("|", " ") + "    "
            return d.replace("    ", "---|", 1)[::-1]

        n = self if not p else p
        while not p and n.parent:
            n = n.parent
        p = n

        print("{}+{} ({})".format(dashes, p.command, "Resolved" if p.resolved() else "Unresolved"))

        for x in range(0,3):

            for child in p.children:
                self.tree_dump(child, lengthen(dashes))


    # Wait until this promise and all its children down the tree are ALL resolved
    def join(self, args={}):
        sleep_time = int(args["sleep"]) if "sleep" in args else .5
        expiration = int(args["expire"]) * sleep_time if "expire" in args else -1

        # Pause until promise or promises resolved
        while not self.tree_resolved(self):
            time.sleep(sleep_time)
            if expiration != -1:
                expiration -= 1
                if expiration == 0:
                    raise Exception("Join expired")

    # Wait on just this promise
    def wait(self, args={}):
        sleep_time = int(args["sleep"]) if "sleep" in args else .5
        expiration = int(args["expire"]) * sleep_time if "expire" in args else -1

        # Pause until promise or promises resolved
        while not self.resolved(s):
            time.sleep(sleep_time)
            if expiration != -1:
                expiration -= 1
                if expiration == 0:
                    raise Exception("Wait expired")


# Singleton object with no side effects
# Executes the command an returns a new WTOutput object
class Watiba(Exception):

    # cmd - command string to execute
    # context = track or not track current dir
    # Returns:
    #   WTOutput object that encapsulates stdout, stderr, exit code, etc.
    def bash(self, cmd, context=True):

        # In order to be thread-safe in the generated code, ALWAYS create a new output object for each command
        #  This is because in the generated code, the object reference, "_watiba_", is global and needs to be in scope
        #  at all levels.  The compiler cannot be scope sensitive with this reference.  Therefore, it must be
        # singleton with no side effects.
        out = WTOutput()

        # Tack on this command to see what the current dir is after the user's command is executed
        ctx = ' && echo "_watiba_cwd_($(pwd))_"' if context else ''
        p = Popen("{}{}".format(cmd, ctx),
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  close_fds=True)
        out.exit_code = p.wait()
        out.stdout = p.stdout.read().decode('utf-8').split('\n')
        out.stderr = p.stderr.read().decode('utf-8').split('\n')

        # Are we supposed to track context?  Yes, then set Python's CWD to where the command took us
        if context:
            # if asked to keep CWD context, find our echo string and remove so the
            # user doesn't see it
            for n, o in enumerate(out.stdout):
                m = re.match(r'^_watiba_cwd_\((\S.*)\)_$', o)
                if m:
                    os.chdir(m.group(1))
                    del out.stdout[n]
        out.cwd = os.getcwd()
        return out

    def spawn(self, command, resolver, spawn_args, parent_locals):
        # Create a new promise object
        l_promise = WTPromise(command)

        # Chain our promise in if we're a child
        if 'promise' in parent_locals and str(type(parent_locals['promise'])).find("WTPromise") >= 0:
            parent_locals['promise'].children.append(l_promise)
            l_promise.parent = parent_locals['promise']

        def run_command(cmd, resolver_func, resolver_promise, args):

            # Execute the command in a new thread
            resolver_promise.output = self.bash(cmd)

            # Call the resolver and use its return value for promise resolution
            # The OR is to ensure we don't override a resolved promise from a race condition!
            # once some thread marks it resolved, it's resolved.
            resolver_promise.resolution |= resolver_func(resolver_promise, copy.copy(args))

        try:
            # Create a new thread
            t = threading.Thread(target=run_command, args=(command, resolver, l_promise, spawn_args))

            # Run the command and call the resolver
            t.start()
        except:
            print("ERROR.  w_async thread execution failed. {}".format(command))

        return l_promise
