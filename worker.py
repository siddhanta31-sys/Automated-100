import time
from config import AUTO_INTERVAL_MINUTES, AUTO_RUN_ON_START
from db import init_db
from pipeline import run_cycle

init_db()
first=True
while True:
    start=time.time()
    if AUTO_RUN_ON_START or not first:
        run_cycle()
    first=False
    elapsed=time.time()-start
    sleep=max(60, AUTO_INTERVAL_MINUTES*60-elapsed)
    time.sleep(sleep)
