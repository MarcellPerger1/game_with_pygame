import functools
from typing import TypeVar, Callable

CT = TypeVar('CT', bound=Callable)


class TriggerOnce:
    def __init__(self, on_trigger):
        self.triggered = False
        self.fn = on_trigger

    def trigger(self, *args, **kwargs):
        self.triggered = True
        self.fn(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        self.trigger(*args, **kwargs)


def trigger_once(f: CT) -> CT:
    to_obj = TriggerOnce(f)

    @functools.wraps(f)
    def new(*args, **kwargs):
        return to_obj.trigger(*args, **kwargs)

    new.orig_fn = f

    return new
