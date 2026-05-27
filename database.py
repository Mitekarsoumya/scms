import sqlite3
import qrcode
import os
import secrets
from datetime import datetime, date

DB_PATH = "scms.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def connect_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        code TEXT UNIQUE,
        hod_name TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        usn TEXT UNIQUE,
        department TEXT,
        semester INTEGER DEFAULT 1,
        section TEXT DEFAULT 'A',
        email TEXT,
        phone TEXT,
        parent_email TEXT DEFAULT '',
        parent_phone TEXT DEFAULT '',
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        department TEXT,
        semester INTEGER,
        credits INTEGER DEFAULT 3,
        faculty TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject_id INTEGER,
        date TEXT,
        period_no INTEGER DEFAULT 1,
        status TEXT DEFAULT 'Present',
        marked_by TEXT DEFAULT 'manual',
        time TEXT,
        UNIQUE(student_id, subject_id, date, period_no)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT,
        semester INTEGER,
        section TEXT,
        day TEXT,
        period INTEGER,
        subject_id INTEGER,
        subject TEXT,
        faculty TEXT,
        time_start TEXT,
        time_end TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        exam_type TEXT,
        department TEXT,
        semester INTEGER,
        subject_id INTEGER,
        max_marks INTEGER DEFAULT 100,
        exam_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        exam_id INTEGER,
        marks REAL DEFAULT 0,
        grade TEXT DEFAULT '',
        remarks TEXT DEFAULT '',
        entered_by TEXT DEFAULT '',
        entered_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, exam_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS fee_structure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT,
        semester INTEGER,
        fee_type TEXT,
        label TEXT,
        amount REAL,
        due_date TEXT,
        academic_year TEXT DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS fee_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        fee_struct_id INTEGER,
        amount_paid REAL DEFAULT 0,
        payment_date TEXT,
        payment_mode TEXT DEFAULT 'cash',
        receipt_no TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        remarks TEXT DEFAULT '',
        entered_by TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS parents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        student_id INTEGER,
        user_id INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        body TEXT,
        author TEXT,
        target TEXT DEFAULT 'all',
        department TEXT DEFAULT '',
        semester INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        pinned INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        type TEXT DEFAULT 'info',
        read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS email_config (
        id INTEGER PRIMARY KEY CHECK(id=1),
        smtp_host TEXT DEFAULT '',
        smtp_port INTEGER DEFAULT 587,
        smtp_user TEXT DEFAULT '',
        smtp_pass TEXT DEFAULT '',
        sender_name TEXT DEFAULT 'EduTrack Pro',
        enabled INTEGER DEFAULT 0
    )""")
    c.execute("SELECT id FROM email_config WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO email_config VALUES (1,'',587,'','','EduTrack Pro',0)")

    c.execute("""CREATE TABLE IF NOT EXISTS email_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        to_email TEXT,
        status TEXT,
        error TEXT,
        sent_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Default users
    for uname, pwd, role in [("admin","admin123","admin"),("hod","hod123","hod"),("faculty","faculty123","faculty")]:
        c.execute("SELECT id FROM users WHERE username=?", (uname,))
        if not c.fetchone():
            c.execute("INSERT INTO users VALUES (NULL,?,?,?)", (uname, pwd, role))

    # Seed departments
    for dname, dcode in [("Computer Science Engineering","CSE"),("Electronics & Communication","ECE"),
                          ("Mechanical Engineering","MECH"),("Civil Engineering","CIVIL"),("Information Science","ISE")]:
        c.execute("SELECT id FROM departments WHERE code=?", (dcode,))
        if not c.fetchone():
            c.execute("INSERT INTO departments VALUES (NULL,?,?,'')", (dname, dcode))

    # Seed subjects
    for row in [("CS101","Engineering Mathematics I","CSE",1,4,"Dr. Sharma"),
                ("CS102","Programming in C","CSE",1,3,"Prof. Patel"),
                ("CS201","Data Structures","CSE",3,4,"Dr. Iyer"),
                ("CS301","Design & Analysis of Algorithms","CSE",5,4,"Dr. Mehta"),
                ("CS302","Operating Systems","CSE",5,4,"Prof. Khan"),
                ("EC101","Basic Electronics","ECE",1,4,"Dr. Nair"),
                ("EC201","Signals & Systems","ECE",3,4,"Prof. Joshi")]:
        c.execute("SELECT id FROM subjects WHERE code=?", (row[0],))
        if not c.fetchone():
            c.execute("INSERT INTO subjects VALUES (NULL,?,?,?,?,?,?)", row)

    # Seed fee structure
    c.execute("SELECT COUNT(*) as n FROM fee_structure")
    if c.fetchone()["n"] == 0:
        for row in [("CSE",1,"tuition","Tuition Fee",45000,"2025-07-31","2025-26"),
                    ("CSE",1,"lab","Lab Fee",5000,"2025-07-31","2025-26"),
                    ("CSE",1,"library","Library Fee",1500,"2025-07-31","2025-26"),
                    ("CSE",1,"exam","Exam Fee",2000,"2025-09-30","2025-26"),
                    ("ECE",1,"tuition","Tuition Fee",42000,"2025-07-31","2025-26"),
                    ("ECE",1,"lab","Lab Fee",4500,"2025-07-31","2025-26")]:
            c.execute("INSERT INTO fee_structure VALUES (NULL,?,?,?,?,?,?,?)", row)

    os.makedirs("qrcodes", exist_ok=True)
    os.makedirs("credentials", exist_ok=True)
    conn.commit()
    conn.close()


# ── AUTH ──────────────────────────────────────────────────────────────────────
def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, role, username FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

# ── DEPARTMENTS ───────────────────────────────────────────────────────────────
def get_departments():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM departments ORDER BY code")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_department(name, code, hod_name=""):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO departments VALUES (NULL,?,?,?)", (name, code, hod_name))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

def delete_department(dept_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM departments WHERE id=?", (dept_id,))
    conn.commit()
    conn.close()

# ── STUDENTS ──────────────────────────────────────────────────────────────────
def add_student(name, department, semester, section, email="", phone="",
                parent_email="", parent_phone="", usn=""):
    conn = get_db()
    c = conn.cursor()
    if not usn:
        usn = f"{department[:3].upper()}{semester}{section}{datetime.now().strftime('%H%M%S')}"
    username = usn.lower()
    password = secrets.token_hex(4)
    try:
        c.execute("INSERT INTO users VALUES (NULL,?,?,?)", (username, password, "student"))
        user_id = c.lastrowid
        c.execute("INSERT INTO students VALUES (NULL,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                  (name, usn, department, semester, section, email, phone, parent_email, parent_phone, user_id))
        student_id = c.lastrowid
        conn.commit()
        generate_qr(student_id, usn)
        with open(f"credentials/{username}.txt", "w") as f:
            f.write(f"USN: {usn}\nUsername: {username}\nPassword: {password}")
        return student_id, username, password, usn
    except Exception as e:
        conn.rollback()
        return None, None, None, None
    finally:
        conn.close()

def generate_qr(student_id, usn=""):
    data = usn if usn else str(student_id)
    img = qrcode.make(data)
    img.save(f"qrcodes/student_{student_id}.png")

def get_students(dept=None, semester=None, section=None):
    conn = get_db()
    c = conn.cursor()
    q = "SELECT * FROM students WHERE 1=1"
    params = []
    if dept:
        q += " AND department=?"; params.append(dept)
    if semester:
        q += " AND semester=?"; params.append(int(semester))
    if section:
        q += " AND section=?"; params.append(section)
    q += " ORDER BY department, semester, section, name"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_student_by_id(sid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id=?", (sid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_student_by_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_student_with_user(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT s.*, u.username, u.password as raw_password, u.id as user_id
                 FROM students s JOIN users u ON s.user_id=u.id WHERE s.id=?""", (student_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_students_with_credentials(dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    q = """SELECT s.*, u.username, u.password as raw_password, u.id as user_id
           FROM students s JOIN users u ON s.user_id=u.id
           WHERE s.email IS NOT NULL AND s.email != ''"""
    params = []
    if dept:
        q += " AND s.department=?"; params.append(dept)
    if semester:
        q += " AND s.semester=?"; params.append(semester)
    q += " ORDER BY s.department, s.semester, s.name"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def delete_student(student_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT user_id FROM students WHERE id=?", (student_id,))
        res = c.fetchone()
        if res:
            for tbl in ("attendance","marks","fee_payments","parents","students"):
                if tbl == "students":
                    c.execute(f"DELETE FROM students WHERE id=?", (student_id,))
                else:
                    c.execute(f"DELETE FROM {tbl} WHERE student_id=?", (student_id,))
            c.execute("DELETE FROM users WHERE id=?", (res["user_id"],))
            conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()
    qr = f"qrcodes/student_{student_id}.png"
    if os.path.exists(qr):
        os.remove(qr)

def update_student(student_id, **kwargs):
    allowed = {"name","email","phone","parent_email","parent_phone","department","semester","section","usn"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    conn = get_db()
    c = conn.cursor()
    sets = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [student_id]
    c.execute(f"UPDATE students SET {sets} WHERE id=?", values)
    conn.commit()
    conn.close()

def get_classes():
    """Legacy helper."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT department||'-SEM'||semester||'-'||section as cs FROM students ORDER BY cs")
    rows = [r["cs"] for r in c.fetchall()]
    conn.close()
    return rows

# ── SUBJECTS ──────────────────────────────────────────────────────────────────
def get_subjects(dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    q = "SELECT * FROM subjects WHERE 1=1"
    params = []
    if dept:
        q += " AND department=?"; params.append(dept)
    if semester:
        q += " AND semester=?"; params.append(int(semester))
    q += " ORDER BY semester, code"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_subject(code, name, department, semester, credits, faculty=""):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO subjects VALUES (NULL,?,?,?,?,?,?)", (code, name, department, semester, credits, faculty))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_subject(sid):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM subjects WHERE id=?", (sid,))
    conn.commit()
    conn.close()

# ── ATTENDANCE ────────────────────────────────────────────────────────────────
def mark_attendance(student_id, status="Present", marked_by="manual",
                    subject_id=None, period_no=1, att_date=None):
    conn = get_db()
    c = conn.cursor()
    today = att_date or date.today().isoformat()
    now = datetime.now().strftime("%H:%M:%S")
    c.execute("""INSERT INTO attendance(student_id,subject_id,date,period_no,status,marked_by,time)
                 VALUES(?,?,?,?,?,?,?)
                 ON CONFLICT(student_id,subject_id,date,period_no)
                 DO UPDATE SET status=excluded.status,time=excluded.time,marked_by=excluded.marked_by""",
              (student_id, subject_id, today, period_no, status, marked_by, now))
    conn.commit()
    conn.close()
    return True

def get_today_attendance(dept=None, semester=None, section=None, subject_id=None):
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()
    where_a = "a.date=?"
    params_a = [today]
    if subject_id:
        where_a += " AND a.subject_id=?"; params_a.append(subject_id)
    s_where = "1=1"
    s_params = []
    if dept:
        s_where += " AND s.department=?"; s_params.append(dept)
    if semester:
        s_where += " AND s.semester=?"; s_params.append(int(semester))
    if section:
        s_where += " AND s.section=?"; s_params.append(section)
    q = f"""
        SELECT s.id, s.name, s.usn, s.department, s.semester, s.section,
               COALESCE(a.status,'Absent') as status,
               COALESCE(a.time,'') as time,
               COALESCE(a.marked_by,'') as marked_by,
               COALESCE(a.period_no,1) as period_no,
               COALESCE(sub.name,'Overall') as subject_name,
               COALESCE(sub.code,'') as subject_code
        FROM students s
        LEFT JOIN subjects sub ON sub.id=?
        LEFT JOIN attendance a ON s.id=a.student_id AND {where_a}
        WHERE {s_where}
        ORDER BY s.department, s.semester, s.section, s.name
    """
    c.execute(q, [subject_id] + s_params + params_a)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_subject_attendance_summary(student_id, semester=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT department FROM students WHERE id=?", (student_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return []
    dept = row["department"]
    q = """SELECT sub.id, sub.code, sub.name, sub.semester,
                  COUNT(a.id) as total_classes,
                  SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as attended
           FROM subjects sub
           LEFT JOIN attendance a ON a.subject_id=sub.id AND a.student_id=?
           WHERE sub.department=?"""
    params = [student_id, dept]
    if semester:
        q += " AND sub.semester=?"; params.append(int(semester))
    q += " GROUP BY sub.id ORDER BY sub.semester, sub.code"
    c.execute(q, params)
    rows = []
    for r in c.fetchall():
        d = dict(r)
        d["percentage"] = round((d["attended"] / d["total_classes"] * 100), 1) if d["total_classes"] else 0
        d["shortage"] = d["total_classes"] > 0 and d["percentage"] < 75
        rows.append(d)
    conn.close()
    return rows

def get_attendance_report(student_id=None, dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    if student_id:
        c.execute("""SELECT s.id, s.name, s.usn, s.department, s.semester, s.section,
                            COUNT(CASE WHEN a.status='Present' THEN 1 END) as attended,
                            COUNT(a.id) as total_classes
                     FROM students s LEFT JOIN attendance a ON s.id=a.student_id
                     WHERE s.id=? GROUP BY s.id""", (student_id,))
    else:
        q = """SELECT s.id, s.name, s.usn, s.department, s.semester, s.section,
                      COUNT(CASE WHEN a.status='Present' THEN 1 END) as attended,
                      COUNT(a.id) as total_classes
               FROM students s LEFT JOIN attendance a ON s.id=a.student_id
               WHERE 1=1"""
        params = []
        if dept:
            q += " AND s.department=?"; params.append(dept)
        if semester:
            q += " AND s.semester=?"; params.append(int(semester))
        q += " GROUP BY s.id ORDER BY s.department, s.semester, s.name"
        c.execute(q, params)
    rows = []
    for r in c.fetchall():
        d = dict(r)
        d["percentage"] = round((d["attended"] / d["total_classes"] * 100), 1) if d["total_classes"] else 0
        d["shortage"] = d["total_classes"] > 0 and d["percentage"] < 75
        rows.append(d)
    conn.close()
    return rows

def get_student_attendance_history(student_id, subject_id=None):
    conn = get_db()
    c = conn.cursor()
    if subject_id:
        c.execute("""SELECT a.date, a.status, a.time, a.period_no,
                            COALESCE(sub.name,'Overall') as subject_name,
                            COALESCE(sub.code,'') as subject_code
                     FROM attendance a LEFT JOIN subjects sub ON a.subject_id=sub.id
                     WHERE a.student_id=? AND a.subject_id=?
                     ORDER BY a.date DESC, a.period_no DESC LIMIT 60""", (student_id, subject_id))
    else:
        c.execute("""SELECT a.date, a.status, a.time, a.period_no,
                            COALESCE(sub.name,'Overall') as subject_name,
                            COALESCE(sub.code,'') as subject_code
                     FROM attendance a LEFT JOIN subjects sub ON a.subject_id=sub.id
                     WHERE a.student_id=?
                     ORDER BY a.date DESC, a.period_no DESC LIMIT 60""", (student_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_full_attendance_log(dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    q = """SELECT s.name, s.usn, s.department, s.semester, s.section,
                  COALESCE(sub.code,'') as subject_code,
                  COALESCE(sub.name,'Overall') as subject_name,
                  a.date, a.period_no, a.status, a.time, a.marked_by
           FROM attendance a JOIN students s ON a.student_id=s.id
           LEFT JOIN subjects sub ON a.subject_id=sub.id WHERE 1=1"""
    params = []
    if dept:
        q += " AND s.department=?"; params.append(dept)
    if semester:
        q += " AND s.semester=?"; params.append(int(semester))
    q += " ORDER BY a.date DESC, s.name"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
def get_dashboard_stats(dept=None):
    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()
    s_where = "WHERE 1=1"
    params = []
    if dept:
        s_where += " AND department=?"; params.append(dept)
    c.execute(f"SELECT COUNT(*) as n FROM students {s_where}", params)
    total = c.fetchone()["n"]
    c.execute(f"""SELECT COUNT(DISTINCT a.student_id) as n
                  FROM attendance a JOIN students s ON a.student_id=s.id
                  {s_where} AND a.date=? AND a.status='Present'""", params + [today])
    present = c.fetchone()["n"]
    absent = total - present
    pct = round((present / total * 100) if total else 0, 1)
    c.execute(f"""SELECT a.date, COUNT(DISTINCT a.student_id) as cnt
                  FROM attendance a JOIN students s ON a.student_id=s.id
                  {s_where} AND a.status='Present'
                  GROUP BY a.date ORDER BY a.date DESC LIMIT 7""", params)
    weekly = list(reversed([dict(r) for r in c.fetchall()]))
    c.execute("""SELECT s.department, s.semester, s.section,
                        COUNT(DISTINCT s.id) as total,
                        COUNT(DISTINCT CASE WHEN a.status='Present' AND a.date=? THEN s.id END) as present
                 FROM students s LEFT JOIN attendance a ON s.id=a.student_id
                 GROUP BY s.department, s.semester, s.section ORDER BY s.department, s.semester""", (today,))
    class_stats = [dict(r) for r in c.fetchall()]
    c.execute("""SELECT s.name, s.usn, s.department, s.semester,
                        a.time, a.status, a.marked_by, a.date
                 FROM attendance a JOIN students s ON a.student_id=s.id
                 ORDER BY a.date DESC, a.time DESC LIMIT 10""")
    recent = [dict(r) for r in c.fetchall()]
    c.execute("SELECT COUNT(*) as n FROM exams")
    exam_count = c.fetchone()["n"]
    c.execute("SELECT COUNT(*) as n FROM fee_payments WHERE status='pending'")
    pending_fees = c.fetchone()["n"]
    conn.close()
    return {"total": total, "present": present, "absent": absent, "percentage": pct,
            "weekly": weekly, "class_stats": class_stats, "recent": recent,
            "exam_count": exam_count, "pending_fees": pending_fees}

# ── TIMETABLE ─────────────────────────────────────────────────────────────────
def get_timetable(dept=None, semester=None, section=None):
    conn = get_db()
    c = conn.cursor()
    q = "SELECT * FROM timetable WHERE 1=1"
    params = []
    if dept:
        q += " AND department=?"; params.append(dept)
    if semester:
        q += " AND semester=?"; params.append(int(semester))
    if section:
        q += " AND section=?"; params.append(section)
    q += " ORDER BY day, period"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_timetable_entry(dept, semester, section, day, period, subject, faculty, time_start, time_end, subject_id=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM timetable WHERE department=? AND semester=? AND section=? AND day=? AND period=?",
              (dept, int(semester), section, day, int(period)))
    c.execute("INSERT INTO timetable VALUES (NULL,?,?,?,?,?,?,?,?,?,?)",
              (dept, int(semester), section, day, int(period), subject_id, subject, faculty, time_start, time_end))
    conn.commit()
    conn.close()

def delete_timetable_entry(entry_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM timetable WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

# ── EXAMS & MARKS ─────────────────────────────────────────────────────────────
def get_exams(dept=None, semester=None, subject_id=None):
    conn = get_db()
    c = conn.cursor()
    q = """SELECT e.*, sub.name as subject_name, sub.code as subject_code
           FROM exams e LEFT JOIN subjects sub ON e.subject_id=sub.id WHERE 1=1"""
    params = []
    if dept:
        q += " AND e.department=?"; params.append(dept)
    if semester:
        q += " AND e.semester=?"; params.append(int(semester))
    if subject_id:
        q += " AND e.subject_id=?"; params.append(subject_id)
    q += " ORDER BY e.exam_date DESC, e.created_at DESC"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_exam(title, exam_type, dept, semester, subject_id, max_marks, exam_date):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO exams VALUES (NULL,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
              (title, exam_type, dept, int(semester), subject_id, int(max_marks), exam_date))
    eid = c.lastrowid
    conn.commit()
    conn.close()
    return eid

def delete_exam(exam_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM marks WHERE exam_id=?", (exam_id,))
    c.execute("DELETE FROM exams WHERE id=?", (exam_id,))
    conn.commit()
    conn.close()

def get_marks_for_exam(exam_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT m.*, s.name as student_name, s.usn, s.section
                 FROM marks m JOIN students s ON m.student_id=s.id
                 WHERE m.exam_id=? ORDER BY s.section, s.name""", (exam_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def upsert_mark(student_id, exam_id, marks, grade="", remarks="", entered_by=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO marks(student_id,exam_id,marks,grade,remarks,entered_by,entered_at)
                 VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)
                 ON CONFLICT(student_id,exam_id)
                 DO UPDATE SET marks=excluded.marks,grade=excluded.grade,
                                remarks=excluded.remarks,entered_by=excluded.entered_by,
                                entered_at=excluded.entered_at""",
              (student_id, exam_id, marks, grade, remarks, entered_by))
    conn.commit()
    conn.close()

def get_student_marks(student_id, semester=None):
    conn = get_db()
    c = conn.cursor()
    q = """SELECT m.marks, m.grade, m.remarks,
                  e.title, e.exam_type, e.max_marks, e.exam_date,
                  sub.name as subject_name, sub.code as subject_code, sub.semester
           FROM marks m JOIN exams e ON m.exam_id=e.id JOIN subjects sub ON e.subject_id=sub.id
           WHERE m.student_id=?"""
    params = [student_id]
    if semester:
        q += " AND sub.semester=?"; params.append(int(semester))
    q += " ORDER BY sub.semester, sub.code, e.exam_date"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_marks_summary_for_student(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT sub.code, sub.name, sub.semester,
                        SUM(m.marks) as scored, SUM(e.max_marks) as total_max
                 FROM marks m JOIN exams e ON m.exam_id=e.id JOIN subjects sub ON e.subject_id=sub.id
                 WHERE m.student_id=? GROUP BY sub.id ORDER BY sub.semester, sub.code""", (student_id,))
    rows = []
    for r in c.fetchall():
        d = dict(r)
        d["percentage"] = round((d["scored"] / d["total_max"] * 100), 1) if d["total_max"] else 0
        rows.append(d)
    conn.close()
    return rows

# ── FEE TRACKING ──────────────────────────────────────────────────────────────
def get_fee_structure(dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    q = "SELECT * FROM fee_structure WHERE 1=1"
    params = []
    if dept:
        q += " AND department=?"; params.append(dept)
    if semester:
        q += " AND semester=?"; params.append(int(semester))
    q += " ORDER BY semester, fee_type"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_fee_structure(dept, semester, fee_type, label, amount, due_date, academic_year=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO fee_structure VALUES (NULL,?,?,?,?,?,?,?)",
              (dept, int(semester), fee_type, label, amount, due_date, academic_year))
    conn.commit()
    conn.close()

def delete_fee_structure(fsid):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM fee_structure WHERE id=?", (fsid,))
    conn.commit()
    conn.close()

def get_student_fee_status(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT department, semester FROM students WHERE id=?", (student_id,))
    s = c.fetchone()
    if not s:
        conn.close()
        return []
    dept, sem = s["department"], s["semester"]
    c.execute("""SELECT fs.id as fee_struct_id, fs.fee_type, fs.label, fs.amount,
                        fs.due_date, fs.academic_year,
                        COALESCE(fp.amount_paid,0) as amount_paid,
                        COALESCE(fp.status,'pending') as status,
                        COALESCE(fp.payment_date,'') as payment_date,
                        COALESCE(fp.payment_mode,'') as payment_mode,
                        COALESCE(fp.receipt_no,'') as receipt_no,
                        COALESCE(fp.id,0) as payment_id
                 FROM fee_structure fs
                 LEFT JOIN fee_payments fp ON fs.id=fp.fee_struct_id AND fp.student_id=?
                 WHERE fs.department=? AND fs.semester=?
                 ORDER BY fs.fee_type""", (student_id, dept, sem))
    rows = []
    for r in c.fetchall():
        d = dict(r)
        d["balance"] = round(d["amount"] - d["amount_paid"], 2)
        rows.append(d)
    conn.close()
    return rows

def record_fee_payment(student_id, fee_struct_id, amount_paid, payment_date,
                       payment_mode, receipt_no="", status="paid", remarks="", entered_by=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM fee_payments WHERE student_id=? AND fee_struct_id=?", (student_id, fee_struct_id))
    existing = c.fetchone()
    if existing:
        c.execute("""UPDATE fee_payments SET amount_paid=?,payment_date=?,payment_mode=?,
                     receipt_no=?,status=?,remarks=?,entered_by=?
                     WHERE student_id=? AND fee_struct_id=?""",
                  (amount_paid, payment_date, payment_mode, receipt_no, status, remarks, entered_by, student_id, fee_struct_id))
    else:
        c.execute("INSERT INTO fee_payments VALUES(NULL,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                  (student_id, fee_struct_id, amount_paid, payment_date, payment_mode, receipt_no, status, remarks, entered_by))
    conn.commit()
    conn.close()
    return True

def get_fee_summary(dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    q = """SELECT fs.fee_type, fs.label,
                  COUNT(DISTINCT s.id) as student_count,
                  SUM(fs.amount) as total_expected,
                  COALESCE(SUM(fp.amount_paid),0) as total_collected
           FROM fee_structure fs
           JOIN students s ON s.department=fs.department AND s.semester=fs.semester
           LEFT JOIN fee_payments fp ON fp.fee_struct_id=fs.id AND fp.student_id=s.id
           WHERE 1=1"""
    params = []
    if dept:
        q += " AND fs.department=?"; params.append(dept)
    if semester:
        q += " AND fs.semester=?"; params.append(int(semester))
    q += " GROUP BY fs.id ORDER BY fs.fee_type"
    c.execute(q, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_fee_defaulters(dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    q = """SELECT s.id, s.name, s.usn, s.department, s.semester, s.section,
                  s.email, s.parent_email,
                  SUM(fs.amount) as total_due,
                  COALESCE(SUM(fp.amount_paid),0) as total_paid
           FROM students s
           JOIN fee_structure fs ON fs.department=s.department AND fs.semester=s.semester
           LEFT JOIN fee_payments fp ON fp.fee_struct_id=fs.id AND fp.student_id=s.id
           WHERE 1=1"""
    params = []
    if dept:
        q += " AND s.department=?"; params.append(dept)
    if semester:
        q += " AND s.semester=?"; params.append(int(semester))
    q += " GROUP BY s.id HAVING (total_due-total_paid)>0 ORDER BY (total_due-total_paid) DESC"
    c.execute(q, params)
    rows = []
    for r in c.fetchall():
        d = dict(r)
        d["balance"] = round(d["total_due"] - d["total_paid"], 2)
        rows.append(d)
    conn.close()
    return rows

# ── PARENTS ───────────────────────────────────────────────────────────────────
def add_parent(name, email, phone, student_id):
    conn = get_db()
    c = conn.cursor()
    username = f"parent_{student_id}_{datetime.now().strftime('%H%M%S')}"
    password = secrets.token_hex(4)
    try:
        c.execute("INSERT INTO users VALUES (NULL,?,?,?)", (username, password, "parent"))
        uid = c.lastrowid
        c.execute("INSERT INTO parents VALUES (NULL,?,?,?,?,?)", (name, email, phone, student_id, uid))
        conn.commit()
        return uid, username, password
    except Exception:
        conn.rollback()
        return None, None, None
    finally:
        conn.close()

def get_parent_by_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM parents WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_parents_for_student(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM parents WHERE student_id=?", (student_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def delete_parent(parent_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM parents WHERE id=?", (parent_id,))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM parents WHERE id=?", (parent_id,))
        c.execute("DELETE FROM users WHERE id=?", (row["user_id"],))
        conn.commit()
    conn.close()

# ── ANNOUNCEMENTS ─────────────────────────────────────────────────────────────
def get_announcements(target=None, dept=None, semester=None):
    conn = get_db()
    c = conn.cursor()
    if target:
        dept_target = f"dept:{dept}" if dept else "__none__"
        c.execute("""SELECT * FROM announcements
                     WHERE target='all' OR target=? OR target=?
                     ORDER BY pinned DESC, created_at DESC""", (target, dept_target))
    else:
        c.execute("SELECT * FROM announcements ORDER BY pinned DESC, created_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_announcement(title, body, author, target="all", dept="", semester=0, pinned=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO announcements VALUES (NULL,?,?,?,?,?,?,CURRENT_TIMESTAMP,?)",
              (title, body, author, target, dept, int(semester), int(pinned)))
    ann_id = c.lastrowid
    conn.commit()
    conn.close()
    return ann_id

def delete_announcement(ann_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
    conn.commit()
    conn.close()

def toggle_pin(ann_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE announcements SET pinned=1-pinned WHERE id=?", (ann_id,))
    conn.commit()
    conn.close()

def get_announcement_recipients(ann: dict):
    """Return unique (email, name) list for email broadcast."""
    conn = get_db()
    c = conn.cursor()
    target = ann.get("target","all")
    dept   = ann.get("department","")
    emails = []

    def add_by_dept(d=None):
        q = "SELECT name, email FROM students WHERE email!='' AND email IS NOT NULL"
        p = []
        if d:
            q += " AND department=?"; p.append(d)
        c.execute(q, p)
        for r in c.fetchall():
            emails.append((r["email"], r["name"]))
        q2 = "SELECT s.parent_email, s.name FROM students s WHERE s.parent_email!='' AND s.parent_email IS NOT NULL"
        if d:
            q2 += " AND s.department=?"; c.execute(q2, [d])
        else:
            c.execute(q2)
        for r in c.fetchall():
            emails.append((r["parent_email"], r["name"] + " (Parent)"))

    if target == "all":
        add_by_dept()
    elif target == "student":
        add_by_dept(dept if dept else None)
    elif target == "parent":
        c.execute("SELECT email, name FROM parents WHERE email!='' AND email IS NOT NULL")
        for r in c.fetchall():
            emails.append((r["email"], r["name"]))
    elif target.startswith("dept:"):
        add_by_dept(target[5:])

    conn.close()
    seen = set()
    unique = []
    for e, n in emails:
        if e not in seen:
            seen.add(e)
            unique.append((e, n))
    return unique

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
def get_notifications(user_id, unread_only=False):
    conn = get_db()
    c = conn.cursor()
    if unread_only:
        c.execute("SELECT * FROM notifications WHERE user_id=? AND read=0 ORDER BY created_at DESC", (user_id,))
    else:
        c.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_notification(user_id, message, ntype="info"):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO notifications VALUES (NULL,?,?,?,0,CURRENT_TIMESTAMP)", (user_id, message, ntype))
    conn.commit()
    conn.close()

def mark_notifications_read(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE notifications SET read=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unread_count(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as n FROM notifications WHERE user_id=? AND read=0", (user_id,))
    n = c.fetchone()["n"]
    conn.close()
    return n

# ── USER / SETTINGS ───────────────────────────────────────────────────────────
def get_user_by_id(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def change_password(user_id, old_pw, new_pw):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id=? AND password=?", (user_id, old_pw))
    row = c.fetchone()
    if row:
        c.execute("UPDATE users SET password=? WHERE id=?", (new_pw, user_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# ── EMAIL CONFIG / LOG ────────────────────────────────────────────────────────
def get_email_config():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM email_config WHERE id=1")
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def save_email_config(host, port, user, pwd, sender_name, enabled):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE email_config SET smtp_host=?,smtp_port=?,smtp_user=?,smtp_pass=?,sender_name=?,enabled=? WHERE id=1",
              (host, int(port), user, pwd, sender_name, int(enabled)))
    conn.commit()
    conn.close()

def log_email_sent(student_id, to_email, status, error=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO email_log VALUES (NULL,?,?,?,?,CURRENT_TIMESTAMP)", (student_id, to_email, status, error))
    conn.commit()
    conn.close()

def get_email_log(limit=50):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""SELECT el.*, s.name, s.usn, s.department
                     FROM email_log el JOIN students s ON el.student_id=s.id
                     ORDER BY el.sent_at DESC LIMIT ?""", (limit,))
        rows = [dict(r) for r in c.fetchall()]
    except Exception:
        rows = []
    conn.close()
    return rows
