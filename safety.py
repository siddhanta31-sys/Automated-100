import os, shutil
import psutil
from config import DATA_DIR, MIN_FREE_DISK_GB, MAX_MEMORY_PERCENT, GENERATION_CONCURRENCY


def system_health():
    os.makedirs(DATA_DIR, exist_ok=True)
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage(DATA_DIR)
    free_gb = disk.free / (1024**3)
    return {
        'memory_percent': vm.percent,
        'memory_available_gb': vm.available/(1024**3),
        'disk_free_gb': free_gb,
        'ok': vm.percent < MAX_MEMORY_PERCENT and free_gb > MIN_FREE_DISK_GB,
    }

def adaptive_concurrency():
    h = system_health()
    if h['memory_percent'] >= MAX_MEMORY_PERCENT or h['disk_free_gb'] <= MIN_FREE_DISK_GB:
        return 0
    if h['memory_percent'] > 72:
        return 1
    if h['memory_percent'] > 60:
        return min(2, GENERATION_CONCURRENCY)
    return max(1, min(GENERATION_CONCURRENCY, 5))
