'''
Watiba spawn controller class and exception definitions

Author: Ray Walker
Raythonic@gmail.com
'''

import time


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
                     "error": self.default_error  # Default error callback
                     }

    # clean out any promises that have resolved
    def promises_gc(self):
        self.promises = [p for p in self.promises if not p.resolved()]

    def default_error(self, promise, promise_count):
        print("ERROR: Maximum promise/thread count reached: {}".format(promise_count))
        print("  Shell command that exceeded max: {}".format(promise.command))
        promise.tree_dump()
        raise WTSpawnException(promise, "Promises not resolved by expiration period")

    # Start a thread belonging to the passed promise
    def start(self, promise):
        promise_exists = False
        ex_count = self.args["expire"]
        loop_counter = 0
        sleep_value = self.args["sleep-floor"]

        # Clean out any resolved promises, this controller is only for the long running ones
        self.promises_gc()

        # Check to see if we somehow are already tracking this promise (shouldn't happen)
        for p in self.promises:
            if p.thread_id == promise.thread_id and p.command == promise.command:
                promise_exists = True

        # Add this promise to our tracking list
        if not promise_exists:
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

        # Run the command and call the resolver
        promise.thread.start()

    # Merge in parameters settings
    def set_parms(self, parms):
        for k, v in parms.items():
            self.args[k] = v
