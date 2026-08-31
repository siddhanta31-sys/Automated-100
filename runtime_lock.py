import os, time
from contextlib import contextmanager
from config import DATA_DIR

LOCK_PATH = os.path.join(DATA_DIR, 'cycle.lock')

@contextmanager
def cycle_lock(blocking=False):
    """Cross-process single-cycle lock. Uses flock on Linux/Render and releases automatically on crash."""
    os.makedirs(DATA_DIR, exist_ok=True)
    fh = open(LOCK_PATH, 'a+')
    acquired = False
    try:
        try:
            import fcntl
            flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
            fcntl.flock(fh.fileno(), flags)
            acquired = True
            fh.seek(0); fh.truncate()
            fh.write(f'pid={os.getpid()} acquired={time.time()}\n'); fh.flush()
        except BlockingIOError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            try:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        fh.close()
