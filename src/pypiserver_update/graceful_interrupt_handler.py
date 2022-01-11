# coding=utf-8

"""
Graceful Interrupt Handler as a context manager.

Can be nested.

From:

* http://stackoverflow.com/a/10972804
* https://gist.github.com/nonZero/2907502
"""

import signal

__docformat__ = 'restructuredtext en'
__all__ = ('GracefulInterruptHandler',)


class GracefulInterruptHandler(object):
    """
    Example Usage::

        with GracefulInterruptHandler() as h1:
            while True:
                print("(1)...")
                time.sleep(1)
                with GracefulInterruptHandler() as h2:
                    while True:
                        print("\t(2)...")
                        time.sleep(1)
                        if h2.interrupted:
                            print("\t(2) interrupted!")
                            time.sleep(2)
                            break
                if h1.interrupted:
                    print("(1) interrupted!")
                    time.sleep(2)
                    break
    """

    def __init__(self, sig=signal.SIGINT):
        self.sig = sig
        self.interrupted = False
        self.released = False
        self.original_handler = None

    def __enter__(self):
        return self.capture()

    def capture(self):
        """
        Capture the signal.  Useful when not using the "with GracefulInterruptHandler" syntax.
        :return: current GracefulInterruptHandler instance
        :rtype: GracefulInterruptHandler
        """
        self.interrupted = False
        self.released = False

        self.original_handler = signal.getsignal(self.sig)

        # noinspection PyUnusedLocal
        def handler(signum, frame):
            """
            signal that an interrupt has occurred.

            :param signum: the signal number
            :param frame: unused
            """
            self.release()
            self.interrupted = True

        signal.signal(self.sig, handler)

        return self

    # noinspection PyUnusedLocal,PyShadowingBuiltins
    def __exit__(self, type, value, tb):
        self.release()

    def release(self):
        """release the signal handler"""
        if self.released:
            return False

        signal.signal(self.sig, self.original_handler)

        self.released = True

        return True
