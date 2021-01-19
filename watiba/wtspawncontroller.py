'''
Watiba spawn controller class and exception definitions

Author: Ray Walker
Raythonic@gmail.com
'''

import time
import threading


class WTSpawnException(Exception):
    def __init__(self, promise, message=""):
        self.promise = promise
        self.message = message


class WTSpawnController():
    def __init__(self):
        self.promises = []
        self.args = {"max": 10,  # Max number of threads allowed before slowdown mode
                     "sleep-floor": .125,  # Starting sleep value
                     "sleep-ceiling": 3,  # Maximum sleep value
                     "sleep-increment": .125,  # Incremental sleep value
                     "expire": -1,  # Default: no expiration
                     "error": self.default_error,  # Default error callback,
                     "hosts": ["localhost"]  # Where to run the command. Default locally
                     }

    # clean out any promises that have resolved
    def promises_gc(self):
        self.promises = [p for p in self.promises if not p.resolved()]

    def default_error(self, promise, promise_count):
        print(f"ERROR: Maximum promise/thread count reached: {promise_count}")
        print(f"  Shell command that exceeded max: {promise.command}")
        promise.tree_dump()
        raise WTSpawnException(promise, "Promises not resolved by expiration period")

    # Start a thread belonging to the passed promise
    def start(self, promise, thread_callback, thread_args):
        track_promise = True
        ex_count = self.args["expire"]
        loop_counter = 0
        sleep_value = self.args["sleep-floor"]

        # Clean out any resolved promises, this controller is only for the long running ones
        self.promises_gc()

        # Check to see if we somehow are already tracking this promise (shouldn't happen)
        for p in self.promises:
            if p.resolved():
                track_promise = False

        # Add this promise to our tracking list
        if track_promise:
            self.promises.append(promise)

        # Don't start the new thread until we're below the threshold
        # This is slowdown mode...
        while len(self.promises) > self.args["max"]:
            time.sleep(sleep_value)

            # Expiration countdown.  If set (not -1) and hits zero, call error handling routine
            ex_count -= 1 if ex_count > -1 else 0
            if ex_count == 0:
                return self.args["error"](promise, len(self.promises))

            # Every third cycle, bump the sleep time up 1/8 second  (slowing down the loop incrementally)
            # Once the increment hits the sleep value, stay at sleep value
            if loop_counter > 0 and loop_counter % 3 == 0:
                sleep_value = sleep_value + self.args["sleep-increment"] if sleep_value < self.args[
                    "sleep-ceiling"] else self.args["sleep-ceiling"]

            loop_counter += 1
            self.promises_gc()

        '''
        The "kill switch" is there in case the user's app wants to pre-emptively stop this command from running.
          How the user can access the promise before this start, takes some doing.  But since the promise 
          is inserted into the promise tree before we get here, there is early access to it.  But that requires 
          the user to be walking the tree in an unconventional way.
          
          So, the kill() method was added to the promise to allow sophisticated thread management in the user's app.
        '''
        # Run the command and call the resolver if some other process out there didn't kill it first
        if not promise.killed:
            try:
                promise.thread = threading.Thread(target=thread_callback, args=(promise, thread_args,))
                promise.thread.start()
            except Exception as ex:
                raise ex

    # Merge in parameters settings
    def set_parms(self, parms):
        for k, v in parms.items():
            self.args[k] = v
