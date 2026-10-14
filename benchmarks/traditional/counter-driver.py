import sys
from counter import advance, counter

for line in sys.stdin:
    index, amount = map(int, line.split())
    try:
        advance(index, amount)
        status = "ok"
    except IndexError:
        status = "bounds"
    print(status, *counter)
