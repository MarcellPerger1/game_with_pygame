# correct, not marked as unreachable (fixed by PY-29435)
whatever = False
if whatever:
    print('good...')
elif __debug__:
    print('why not?')

# incorrectly marked as unreachable
if __debug__:
    print('debug enabled')
else:
    print('this is marked as unreachable')
