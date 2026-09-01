import subprocess, sys, time

print('[Trend2Sketch][supervisor] resilient worker supervisor starting', flush=True)
backoff=5
while True:
    started=time.time()
    p=subprocess.Popen([sys.executable,'-u','worker.py'])
    code=p.wait()
    lived=time.time()-started
    if lived>300: backoff=5
    else: backoff=min(60,max(5,backoff*2))
    print(f'[Trend2Sketch][supervisor] worker exited code={code}; auto-restart in {backoff}s', flush=True)
    time.sleep(backoff)
