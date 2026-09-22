"""Shared helpers for the Merino data generator. Everything is deterministic (seeded).
All dates are RELATIVE to the as-of day, which defaults to TODAY (override: --asof YYYY-MM-DD or env MER_ASOF), so
re-running the generator before a demo makes the whole dataset current without changing any id or story."""
import os
import random
import sys
from datetime import datetime, timedelta

from .config import SEED, HISTORY_DAYS, FORWARD_DAYS, ASOF_HOUR, ASOF_MIN


def _asof():
    v = None
    for i, a in enumerate(sys.argv):
        if a == "--asof" and i + 1 < len(sys.argv):
            v = sys.argv[i + 1]
        elif a.startswith("--asof="):
            v = a.split("=", 1)[1]
    v = v or os.environ.get("MER_ASOF")
    d = datetime.strptime(v, "%Y-%m-%d") if v else datetime.now()
    return d.replace(hour=ASOF_HOUR, minute=ASOF_MIN, second=0, microsecond=0)


R = random.Random(SEED)
ASOF = _asof()
DAY0 = ASOF.replace(hour=0, minute=0)
BASE = DAY0 - timedelta(days=HISTORY_DAYS)            # history starts here (minute 0 of the engine)
END = DAY0 + timedelta(days=FORWARD_DAYS)             # forward plan ends here
ASOF_MINUTE = int((ASOF - BASE).total_seconds() // 60)
END_MINUTE = int((END - BASE).total_seconds() // 60)


def at(days, hour=0, minute=0):
    """datetime at an offset in days from the as-of day (0 = as-of day) with a time of day"""
    return DAY0 + timedelta(days=days, hours=hour, minutes=minute)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%S") if d else None


def dstr(d):
    return d.strftime("%Y-%m-%d")


def minute_of(d):
    return int((d - BASE).total_seconds() // 60)


def pick(seq):
    return R.choice(seq)


def wpick(pairs):
    """weighted pick from [(item, weight), ...] or {item: weight}"""
    items = list(pairs.items()) if isinstance(pairs, dict) else list(pairs)
    tot = sum(w for _, w in items)
    x = R.random() * tot
    for it, w in items:
        x -= w
        if x <= 0:
            return it
    return items[-1][0]


def between(a, b):
    return a + (b - a) * R.random()


def rint(a, b):
    return R.randint(a, b)


def shift_of(d):
    hr = d.hour
    return "A" if 6 <= hr < 14 else "B" if 14 <= hr < 22 else "C"
