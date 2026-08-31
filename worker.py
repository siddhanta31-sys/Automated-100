import time, traceback
from config import AUTO_INTERVAL_MINUTES, AUTO_RUN_ON_START, CYCLE_STALE_MINUTES
from db import init_db, mark_running_cycles_interrupted, mark_stale_running_cycles
from pipeline import run_cycle

print('[Trend2Sketch][worker] hardened worker booting',flush=True)
init_db()
recovered=mark_running_cycles_interrupted('Recovered automatically when hardened worker started after deploy/restart.')
if recovered: print(f'[Trend2Sketch][worker] recovered {recovered} orphaned running cycle(s)',flush=True)
first=True
while True:
    start=time.time()
    try:
        mark_stale_running_cycles(CYCLE_STALE_MINUTES)
        if AUTO_RUN_ON_START or not first:
            print('[Trend2Sketch][worker] requesting scheduled cycle',flush=True)
            cid=run_cycle(); print(f'[Trend2Sketch][worker] scheduled cycle result={cid}',flush=True)
    except Exception as e:
        print(f'[Trend2Sketch][worker] UNHANDLED {type(e).__name__}: {e}',flush=True); print(traceback.format_exc(),flush=True)
    first=False
    elapsed=time.time()-start; sleep=max(60,AUTO_INTERVAL_MINUTES*60-elapsed)
    print(f'[Trend2Sketch][worker] sleeping {sleep:.0f}s',flush=True); time.sleep(sleep)
