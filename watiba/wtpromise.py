'''
Watiba promise class and exception definitions

Author: Ray Walker
Raythonic@gmail.com
'''

import sys
import time
import threading
from watiba.wtoutput import WTOutput


class WTWaitException(Exception):
    def __init__(self, promise, message=""):
        self.promise = promise
        self.message = message


class WTKillException(Exception):
    def __init__(self, promise, message=""):
        self.promise = promise
        self.message = message


# The object returned for Watbia thread spawns
class WTPromise(Exception):
    def __init__(self, command, host="localhost"):
        self.output = None
        self.host = host
        self.resolution = False
        self.start_time = time.time()
        self.end_time = None
        self.thread = None
        self.thread_id = None
        self.killed = False
        self.watcher = None
        self.children = []
        self.parent = None
        self.command = command
        self.depth = 0
        self.__WTPROMISE_STAMP__ = True

    # Getter to check promise state
    def resolved(self):
        return self.resolution

    # Set promise to resolved state
    def set_resolved(self):
        self.end_time = time.time()
        self.set_resolution(True)

    # Set resolution state from resolver
    # The OR is to ensure we don't override a resolved promise from a race condition!
    # once some thread marks it resolved, it's resolved.
    def set_resolution(self, resolution):
        self.resolution |= resolution

    ####################################################################################################################
    # kill() here just in case it's needed.  Not documenting right now.
    # This would only work in some rare case where you issue kill() BEFORE any thread on this promise starts.
    # This prevents a thread from starting, it does not kill a running thread.  Since the caller under normal
    # circumstances cannot access the promise until the thread is started, it's not likely to be useful.
    # So why have it?  Because a promise is inserted in the promise tree before the thread is started, so there
    # remains a slim window when the user's code has access to a promise before any thread executes-and they may
    # just want to stop it first.  So, making that possible.  You're welcome.
    def kill(self):
        if not self.resolved() and self.thread:
            self.killed = True
        else:
            raise WTKillException(self, f'Kill failed.  Command {"running" if not self.resolved() else "completed"}.')

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
            count = self.child_counter(c, count, resolved_only)

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
        return self.spawn_count(resolved_only=True, start_at_top=True)

    # Encapsulate setting relating parent/child promises
    def relate(self, parent_promise):
        # Link child to parent
        self.parent = parent_promise
        self.depth = self.parent.depth + 1
        self.parent.children.append(self)

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
    def tree_dump(self, p=None, dashes="", header=True):
        if header:
            print("Dumping promise tree", file=sys.stderr)
            header = False

        def indent(d):
            d = d.replace("-", " ").replace("|", " ") + "    "
            # Replace just the first 4 spaces with line, then reverse it so line is on right side
            return d.replace("    ", "---|", 1)[::-1]

        # If not given a starting point, set up to start at root
        n = self if not p else p

        # If position in tree not passed, find root promise
        while not p and n.parent:
            n = n.parent

        # Set out starting position
        p = n

        # Calculate the execution time of the command related to this promise
        execution_time = round(p.end_time - p.start_time, 4) if p.end_time else round(time.time() - p.start_time, 4)

        # Print dump output
        print("{}+ {}: `{}` ({}, {}, {})".format(dashes,
                                             "root" if p.depth < 1 else p.depth,
                                             p.command,
                                             "Resolved" if p.resolved() else "Unresolved",
                                             f"Execution time: {execution_time} seconds",
                                             f"Thread id: {p.thread_id}"
                                             ), file=sys.stderr)

        for child in p.children:
            self.tree_dump(child, indent(dashes), header)

    # Wait until this promise and all its children down the tree are ALL resolved
    def join(self, args={}):
        sleep_time = int(args["sleep"]) if "sleep" in args else .5
        expiration = int(args["expire"]) if "expire" in args else -1

        # Pause until promise or promises resolved
        while not self.tree_resolved(self):
            time.sleep(sleep_time)
            if expiration != -1:
                expiration -= 1
                if expiration == 0:
                    self.tree_dump()
                    raise WTWaitException(self, "Join exceeded expiration period")

    # Wait on just this promise
    def wait(self, args={}):
        sleep_time = int(args["sleep"]) if "sleep" in args else .5
        expiration = int(args["expire"]) if "expire" in args else -1

        # Pause until promise or promises resolved
        while not self.resolved():
            time.sleep(sleep_time)
            if expiration != -1:
                expiration -= 1
                if expiration == 0:
                    self.tree_dump()
                    raise WTWaitException(self, "Join exceeded expiration period")

    # Establish a watcher thread for this promise
    # Does not pause like join or wait.
    #  Calls back user's method, specified in "notify" argument, if promise hasn't completed in time
    def watch(self, watcher_method, args={}):
        # Thread function.  Wraps watcher notification method.
        def watcher(promise, watcher_method, args):
            expire = args["expire"] * 4 if "expire" in args else 60

            # Sleep in 1 second chunks so if resolved we end quickly
            while expire > 0 and not promise.resolved():
                time.sleep(.250)
                expire -= 1

            # Call the user's watcher if promise still not resolved
            if not self.resolved():
                watcher_method(promise, args)

        # Spawn a watcher thread
        self.watcher = threading.Thread(target=watcher, args=(self, watcher_method, args))
        self.watcher.start()
