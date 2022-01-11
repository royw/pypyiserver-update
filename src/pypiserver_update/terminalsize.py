#!/usr/bin/env python
# coding=utf-8
"""
Function to get the terminal size.

Used in application_settings adjust the argparse display width to fill the width of the console.

From:  https://gist.github.com/jtriley/1108174

"""
import os
import shlex
import struct
import platform
import subprocess


def get_terminal_size():
    """ getTerminalSize()

     - get width and height of console
     - works on linux,os x,windows,cygwin(windows)

     originally retrieved from:

     http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
    """
    current_os = platform.system()
    tuple_xy = None
    if current_os == 'Windows':
        tuple_xy = _get_terminal_size_windows()
        if tuple_xy is None:
            tuple_xy = _get_terminal_size_tput()
            # needed for window's python in cygwin's xterm!
    if current_os in ['Linux', 'Darwin'] or current_os.startswith('CYGWIN'):
        tuple_xy = _get_terminal_size_linux()
    if tuple_xy is None:
        tuple_xy = (80, 25)  # default value
    return tuple_xy


def _get_terminal_size_windows():
    # noinspection PyBroadException
    try:
        from ctypes import windll, create_string_buffer
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            # noinspection SpellCheckingInspection
            (buf_x, buf_y, cur_x, cur_y, w_attr,
             left, top, right, bottom,
             max_x, max_y) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            size_x_ = right - left + 1
            size_y_ = bottom - top + 1
            return size_x_, size_y_
    except Exception:
        pass


def _get_terminal_size_tput():
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    # noinspection PyBroadException
    try:
        cols = int(subprocess.check_call(shlex.split('tput cols')))
        rows = int(subprocess.check_call(shlex.split('tput lines')))
        return cols, rows
    except Exception:
        pass


# noinspection PyTypeChecker
def _get_terminal_size_linux():
    # noinspection PyPep8Naming,PyDocstring,PyShadowingNames
    def ioctl_GWINSZ(fd):
        # noinspection PyBroadException
        try:
            import fcntl
            import termios

            cr = struct.unpack('hh',
                               fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            return cr
        except Exception:
            pass

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        # noinspection PyBroadException
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except Exception:
            pass
    if not cr:
        # noinspection PyBroadException
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except Exception:
            return None
    return int(cr[1]), int(cr[0])


if __name__ == "__main__":
    size_x, size_y = get_terminal_size()
    print('width =', size_x, 'height =', size_y)
