import sqlite3
from datetime import datetime, timezone

DB = "opportunities.db"

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS opportunities(
        id INTEGER PRIMARY KEY,
        url TEXT UNIQUE NOT NULL,
        project_code TEXT,
        title TEXT,
        organisation TEXT,
        location TEXT,
        activity_dates TEXT,
        activity_type TEXT,
        deadline TEXT,
        participant_countries TEXT,
        algeria_status TEXT,
        profile TEXT,
        description TEXT,
        content_hash TEXT,
        status TEXT,
        match_score INTEGER DEFAULT 0,
        match_reasons TEXT,
        first_seen TEXT,
        last_seen TEXT,
        last_changed TEXT
    )""")
    return c

def upsert(item, digest):
    import json
    now = datetime.now(timezone.utc).isoformat()
    c = connect()
    old = c.execute("SELECT content_hash FROM opportunities WHERE url=?", (item["url"],)).fetchone()
    new_state = "NEW" if not old else ("UPDATED" if old["content_hash"] != digest else "UNCHANGED")
    if not old:
        c.execute("""INSERT INTO opportunities
        (url,project_code,title,organisation,location,activity_dates,activity_type,
        deadline,participant_countries,algeria_status,profile,description,content_hash,
        status,match_score,match_reasons,first_seen,last_seen,last_changed)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (item["url"],item["project_code"],item["title"],item["organisation"],item["location"],
         item["activity_dates"],item["activity_type"],item["deadline"],
         item["participant_countries"],item["algeria_status"],item["profile"],item["description"],
         digest,item["status"],item["match_score"],json.dumps(item["match_reasons"],ensure_ascii=False),
         now,now,now))
    else:
        c.execute("""UPDATE opportunities SET project_code=?,title=?,organisation=?,location=?,
        activity_dates=?,activity_type=?,deadline=?,participant_countries=?,algeria_status=?,
        profile=?,description=?,content_hash=?,status=?,match_score=?,match_reasons=?,
        last_seen=?,last_changed=CASE WHEN content_hash != ? THEN ? ELSE last_changed END
        WHERE url=?""",
        (item["project_code"],item["title"],item["organisation"],item["location"],
         item["activity_dates"],item["activity_type"],item["deadline"],
         item["participant_countries"],item["algeria_status"],item["profile"],item["description"],
         digest,item["status"],item["match_score"],json.dumps(item["match_reasons"],ensure_ascii=False),
         now,digest,now,item["url"]))
    c.commit(); c.close()
    return new_state

def list_open(limit=200):
    c=connect()
    rows=c.execute("""SELECT * FROM opportunities
                     WHERE status!='EXPIRED' AND algeria_status='ELIGIBLE'
                     ORDER BY match_score DESC, id DESC LIMIT ?""",(limit,)).fetchall()
    c.close(); return rows

def stats():
    c=connect()
    out={}
    for label, q in {
        "total":"SELECT COUNT(*) FROM opportunities",
        "eligible":"SELECT COUNT(*) FROM opportunities WHERE algeria_status='ELIGIBLE'",
        "open":"SELECT COUNT(*) FROM opportunities WHERE status='OPEN'",
        "expired":"SELECT COUNT(*) FROM opportunities WHERE status='EXPIRED'",
        "new":"SELECT COUNT(*) FROM opportunities WHERE status='NEW'"
    }.items():
        out[label]=c.execute(q).fetchone()[0]
    c.close(); return out
