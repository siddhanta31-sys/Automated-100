
import os, time, traceback
from datetime import datetime
from pathlib import Path
from autonomous_core import create_batch, DATA_DIR

INTERVAL=int(os.getenv("AUTO_INTERVAL_MINUTES","30"))*60
LOCK=DATA_DIR/"worker.lock"

def log(msg):
    print(f"[Trend2Sketch worker {datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)

def acquire_lock():
    # Single-container deployment assumption; stale lock is overwritten after restart.
    try:
        LOCK.write_text(str(os.getpid()))
    except Exception:
        pass

def main():
    acquire_lock()
    log(f"Autonomous generation enabled. Interval={INTERVAL//60} minutes.")
    run_immediately=os.getenv("AUTO_RUN_ON_START","true").lower() in ("1","true","yes")
    first=True
    while True:
        if run_immediately or not first:
            started=time.time()
            try:
                batch_id,results,errors,email_status=create_batch()
                log(f"Batch #{batch_id}: {len(results)} generated, {len(errors)} failed. {email_status}")
            except Exception:
                log("Batch failed:\n"+traceback.format_exc())
            elapsed=time.time()-started
            sleep_for=max(60,INTERVAL-elapsed)
        else:
            sleep_for=INTERVAL
        first=False
        log(f"Sleeping {int(sleep_for)} seconds.")
        time.sleep(sleep_for)

if __name__=="__main__":
    main()
