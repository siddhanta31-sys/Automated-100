import subprocess, sys, time

while True:
    p=subprocess.Popen([sys.executable,'worker.py'])
    code=p.wait()
    print(f'worker exited with code {code}; restarting in 10s', flush=True)
    time.sleep(10)
