import os
import sys

def become_daemon():
    sys.stdin = open('/dev/null', 'r')
    sys.stdout= open('/dev/null', 'w')
    sys.stderr= open('/dev/null', 'w')

    pid = os.fork()

    if pid != 0:
        sys.exit(0)

    os.setsid()
