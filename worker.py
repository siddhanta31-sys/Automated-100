import time, traceback
from config import AUTO_INTERVAL_MINUTES, AUTO_RUN_ON_START
from db import init_db
from pipeline import run_cycle

print('[Trend2Sketch][worker] worker booting', flush=True)
init_db()
first=True
while True:
    start=time.time()
    try:
        if AUTO_RUN_ON_START or not first:
            print('[Trend2Sketch][worker] starting scheduled cycle', flush=True)
            cid=run_cycle()
            print(f'[Trend2Sketch][worker] cycle {cid} returned', flush=True)
    except Exception as e:
        print(f'[Trend2Sketch][worker] UNHANDLED {type(e).__name__}: {e}', flush=True)
        print(traceback.format_exc(), flush=True)
    first=False
    elapsed=time.time()-start
    sleep=max(60, AUTO_INTERVAL_MINUTES*60-elapsed)
    print(f'[Trend2Sketch][worker] sleeping {sleep:.0f}s', flush=True)
    time.sleep(sleep)
