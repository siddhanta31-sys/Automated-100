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
      note TEXT,
      heartbeat_at TEXT
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
    CREATE TABLE IF NOT EXISTS design_feedback (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      design_id INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      verdict TEXT NOT NULL,
      reason TEXT,
      note TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_feedback_design ON design_feedback(design_id, created_at DESC);
    CREATE TABLE IF NOT EXISTS design_references (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT NOT NULL,
      name TEXT,
      image_path TEXT,
      note TEXT,
      active INTEGER DEFAULT 1,
      profile_name TEXT DEFAULT 'General',
      dna_json TEXT,
      analysis_status TEXT DEFAULT 'pending'
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
    # Forward-compatible migrations.
    for sql in [
        'ALTER TABLE cycles ADD COLUMN heartbeat_at TEXT',
        "ALTER TABLE design_references ADD COLUMN profile_name TEXT DEFAULT 'General'",
        'ALTER TABLE design_references ADD COLUMN dna_json TEXT',
        "ALTER TABLE design_references ADD COLUMN analysis_status TEXT DEFAULT 'pending'",
    ]:
        try:
            c.execute(sql); c.commit()
        except sqlite3.OperationalError:
            pass
    c.execute('''CREATE TABLE IF NOT EXISTS cycle_checkpoints (
      id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id INTEGER NOT NULL, created_at TEXT NOT NULL,
      stage TEXT NOT NULL, payload TEXT, UNIQUE(cycle_id,stage)
    )''')
    c.commit()
    # Forward-compatible migration for richer CAD handoff data.
    try:
        c.execute('ALTER TABLE designs ADD COLUMN cad_brief TEXT')
        c.commit()
    except sqlite3.OperationalError:
        pass

    # Rejection integrity: an owner-rejected design is permanently hidden from all visible libraries.
    # Triggers are deliberately database-level so a UI setting change cannot resurrect it.
    c.executescript('''
    CREATE TRIGGER IF NOT EXISTS trg_feedback_reject_hides_design
    AFTER INSERT ON design_feedback
    WHEN lower(trim(NEW.verdict)) = 'reject'
    BEGIN
      UPDATE designs
      SET visible=0, favorite=0, status='owner_rejected'
      WHERE id=NEW.design_id;
    END;

    CREATE TRIGGER IF NOT EXISTS trg_rejected_design_cannot_be_resurrected
    AFTER UPDATE OF visible, favorite, status ON designs
    WHEN EXISTS (
      SELECT 1 FROM design_feedback f
      WHERE f.design_id=NEW.id AND lower(trim(f.verdict))='reject'
    ) AND (
      COALESCE(NEW.visible,0)<>0 OR COALESCE(NEW.favorite,0)<>0 OR COALESCE(NEW.status,'')<>'owner_rejected'
    )
    BEGIN
      UPDATE designs
      SET visible=0, favorite=0, status='owner_rejected'
      WHERE id=NEW.id;
    END;
    ''')
    c.commit()
    repair_rejection_integrity()

def repair_rejection_integrity():
    """Self-audit and repair contradictory historical records.

    Any design that has ever received an owner 'reject' verdict is terminally hidden.
    The feedback row remains for negative learning, but the design can never re-enter
    an accepted/review library because a threshold or preset changed.
    """
    c = conn()
    cur = c.execute('''
        UPDATE designs
        SET visible=0, favorite=0, status='owner_rejected'
        WHERE EXISTS (
          SELECT 1 FROM design_feedback f
          WHERE f.design_id=designs.id AND lower(trim(f.verdict))='reject'
        )
          AND (
            COALESCE(visible,0)<>0 OR COALESCE(favorite,0)<>0 OR COALESCE(status,'')<>'owner_rejected'
          )
    ''')
    c.commit()
    return cur.rowcount


def is_owner_rejected(design_id):
    return one('''SELECT 1 AS yes FROM design_feedback
                  WHERE design_id=? AND lower(trim(verdict))='reject' LIMIT 1''', (int(design_id),)) is not None


def execute(sql, params=()):
    c = conn(); cur = c.execute(sql, params); c.commit(); return cur

def query(sql, params=()):
    return [dict(r) for r in conn().execute(sql, params).fetchall()]

def one(sql, params=()):
    r = conn().execute(sql, params).fetchone(); return dict(r) if r else None

def create_cycle():
    ts=now_iso(); cur = execute("INSERT INTO cycles(started_at,status,stage,heartbeat_at) VALUES(?,?,?,?)", (ts,'running','research',ts))
    return cur.lastrowid

def update_cycle(cycle_id, **fields):
    if not fields: fields={}
    fields['heartbeat_at']=now_iso()
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

def mark_running_cycles_interrupted(note='Recovered after app/worker restart.'):
    """Close orphaned running rows from a previous process/deploy."""
    c = conn()
    cur = c.execute("UPDATE cycles SET status='interrupted', stage='recovered', finished_at=?, note=? WHERE status='running'", (now_iso(), note))
    c.commit()
    return cur.rowcount

def mark_stale_running_cycles(minutes=75):
    """Close only very old running rows. Safe to call periodically."""
    try:
        mins = max(1, int(minutes))
    except Exception:
        mins = 75
    c = conn()
    cur = c.execute("""
        UPDATE cycles
        SET status='interrupted', stage='stale_recovered', finished_at=?, note='Automatically recovered stale cycle.'
        WHERE status='running'
          AND datetime(COALESCE(heartbeat_at,started_at)) < datetime('now', ?)
    """, (now_iso(), f'-{mins} minutes'))
    c.commit()
    return cur.rowcount

def active_cycle():
    return one("SELECT * FROM cycles WHERE status='running' ORDER BY id DESC LIMIT 1")

def feedback_summary(limit=250):
    rows=query('''SELECT f.verdict,f.reason,f.note,d.lane,d.category,d.concept_family,d.title,d.description,d.materials,d.target_weight,d.final_score
                  FROM design_feedback f JOIN designs d ON d.id=f.design_id ORDER BY f.id DESC LIMIT ?''',(limit,))
    return rows

def add_feedback(design_id, verdict, reason='', note=''):
    """Persist owner feedback atomically. Reject is a terminal visibility decision."""
    did=int(design_id); v=str(verdict or '').strip().lower(); c=conn()
    try:
        c.execute('BEGIN IMMEDIATE')
        c.execute('INSERT INTO design_feedback(design_id,created_at,verdict,reason,note) VALUES(?,?,?,?,?)',
                  (did,now_iso(),v,str(reason or ''),str(note or '')))
        if v=='reject':
            c.execute("UPDATE designs SET visible=0, favorite=0, status='owner_rejected' WHERE id=?",(did,))
        c.commit()
    except Exception:
        c.rollback(); raise


def reference_summary(limit=60):
    return query("SELECT id,name,note,profile_name,dna_json,analysis_status FROM design_references WHERE active=1 ORDER BY id DESC LIMIT ?",(limit,))

def save_checkpoint(cycle_id,stage,payload):
    execute('INSERT INTO cycle_checkpoints(cycle_id,created_at,stage,payload) VALUES(?,?,?,?) ON CONFLICT(cycle_id,stage) DO UPDATE SET created_at=excluded.created_at,payload=excluded.payload',(int(cycle_id),now_iso(),str(stage),json.dumps(payload,ensure_ascii=False)))

def get_checkpoint(cycle_id,stage):
    r=one('SELECT payload FROM cycle_checkpoints WHERE cycle_id=? AND stage=?',(int(cycle_id),str(stage)))
    if not r: return None
    try: return json.loads(r['payload'])
    except Exception: return None
