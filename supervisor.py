import subprocess, sys, time

print('[Trend2Sketch][supervisor] starting worker supervisor', flush=True)
while True:
    p=subprocess.Popen([sys.executable,'-u','worker.py'])
    code=p.wait()
    print(f'[Trend2Sketch][supervisor] worker exited with code {code}; restarting in 10s', flush=True)
    time.sleep(10)
