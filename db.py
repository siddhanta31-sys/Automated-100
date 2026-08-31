import json, os, sqlite3, threading
from datetime import datetime, timezone
from config import DB_PATH, DATA_DIR, IMAGE_DIR

_local = threading.local()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def conn():
    c = getattr(_local, 'conn', None)
    if c is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(IMAGE_DIR, exist_ok=True)
        c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('PRAGMA synchronous=NORMAL')
        _local.conn = c
    return c

def init_db():
    c = conn()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS cycles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      started_at TEXT NOT NULL,
      finished_at TEXT,
      status TEXT NOT NULL,
      stage TEXT,
      concepts_discovered INTEGER DEFAULT 0,
      candidates_scored INTEGER DEFAULT 0,
      rendered INTEGER DEFAULT 0,
      visible INTEGER DEFAULT 0,
      rejected INTEGER DEFAULT 0,
      failed INTEGER DEFAULT 0,
      estimated_cost_usd REAL DEFAULT 0,
      note TEXT
    );
    CREATE TABLE IF NOT EXISTS designs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      cycle_id INTEGER,
      created_at TEXT NOT NULL,
      lane TEXT,
      category TEXT,
      concept_family TEXT,
      title TEXT,
      description TEXT,
      materials TEXT,
      target_weight TEXT,
      region_signal TEXT,
      rationale TEXT,
      pre_score REAL,
      visual_score REAL,
      final_score REAL,
      image_path TEXT,
      visible INTEGER DEFAULT 0,
      favorite INTEGER DEFAULT 0,
      fingerprint TEXT UNIQUE,
      status TEXT,
      error TEXT
    );
    CREATE TABLE IF NOT EXISTS research_snapshots (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT NOT NULL,
      summary TEXT,
      source_note TEXT
    );
    CREATE TABLE IF NOT EXISTS app_settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS spend_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT NOT NULL,
      cycle_id INTEGER,
      kind TEXT,
      estimated_usd REAL,
      note TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_designs_visible_score ON designs(visible, final_score DESC);
    CREATE INDEX IF NOT EXISTS idx_designs_created ON designs(created_at DESC);
    ''')
    c.commit()

def execute(sql, params=()):
    c = conn(); cur = c.execute(sql, params); c.commit(); return cur

def query(sql, params=()):
    return [dict(r) for r in conn().execute(sql, params).fetchall()]

def one(sql, params=()):
    r = conn().execute(sql, params).fetchone(); return dict(r) if r else None

def create_cycle():
    cur = execute("INSERT INTO cycles(started_at,status,stage) VALUES(?,?,?)", (now_iso(),'running','research'))
    return cur.lastrowid

def update_cycle(cycle_id, **fields):
    if not fields: return
    sets = ','.join(f'{k}=?' for k in fields)
    execute(f'UPDATE cycles SET {sets} WHERE id=?', tuple(fields.values())+(cycle_id,))

def log_spend(cycle_id, kind, usd, note=''):
    execute('INSERT INTO spend_log(created_at,cycle_id,kind,estimated_usd,note) VALUES(?,?,?,?,?)',
            (now_iso(),cycle_id,kind,float(usd),note))

def today_spend():
    row = one("SELECT COALESCE(SUM(estimated_usd),0) AS total FROM spend_log WHERE date(created_at)=date('now')")
    return float(row['total'] if row else 0)

def get_setting(key, default=None):
    row = one('SELECT value FROM app_settings WHERE key=?', (key,))
    return row['value'] if row else default

def set_setting(key, value):
    execute('INSERT INTO app_settings(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at',
            (key, str(value), now_iso()))

def get_int_setting(key, default):
    try: return int(float(get_setting(key, default)))
    except Exception: return int(default)

def get_bool_setting(key, default):
    raw = str(get_setting(key, '1' if default else '0')).strip().lower()
    return raw in ('1','true','yes','on')
