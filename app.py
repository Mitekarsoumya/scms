import os
import threading
import time
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from uuid import uuid4

import cv2
from sqlalchemy import and_, or_, text
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    Response,
    send_from_directory,
    stream_with_context,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from face_service import FaceRecognitionService
from models import Assignment, Attendance, Student, StudyMaterial, Subject, TeacherProfile, User, db


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
FACE_FOLDER = UPLOAD_FOLDER / "faces"
MATERIAL_FOLDER = UPLOAD_FOLDER / "materials"
ALLOWED_IMAGES = {"jpg", "jpeg", "png"}
ALLOWED_MATERIALS = {"pdf", "doc", "docx", "ppt", "pptx", "txt"}


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "college-project-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'smart_classroom.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
face_service = FaceRecognitionService()


attendance_lock = threading.Lock()
attendance_session = {
    "active": False,
    "started_by": "",
    "started_at": "",
    "department": "",
    "semester": "",
    "section": "",
    "subject_id": 0,
    "period_no": 1,
    "marked": {},
}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def create_required_folders():
    FACE_FOLDER.mkdir(parents=True, exist_ok=True)
    MATERIAL_FOLDER.mkdir(parents=True, exist_ok=True)


def extension_allowed(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_upload(file_storage, subfolder, allowed_extensions):
    if not file_storage or not file_storage.filename:
        return None
    if not extension_allowed(file_storage.filename, allowed_extensions):
        raise ValueError("Unsupported file type")

    folder = UPLOAD_FOLDER / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    original_name = secure_filename(file_storage.filename)
    filename = f"{uuid4().hex}_{original_name}"
    file_storage.save(folder / filename)
    return f"{subfolder}/{filename}"


def redirect_for_role(user):
    if user.role in {"admin", "teacher"}:
        return redirect(url_for("dashboard"))
    return redirect(url_for("student_dashboard"))


def seed_database():
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", full_name="System Admin", role="admin")
        admin.password_hash = generate_password_hash("admin123")
        teacher = User(username="teacher", full_name="Class Teacher", role="teacher")
        teacher.password_hash = generate_password_hash("teacher123")
        student_user = User(username="student", full_name="Demo Student", role="student")
        student_user.password_hash = generate_password_hash("student123")
        db.session.add_all([admin, teacher, student_user])
        db.session.flush()
        db.session.add(
            TeacherProfile(
                employee_id="TCH001",
                email="teacher@example.com",
                phone="",
                department="CSE",
                designation="Assistant Professor",
                user_id=teacher.id,
            )
        )

        db.session.add(
            Student(
                roll_number="CSE001",
                name="Demo Student",
                email="student@example.com",
                department="CSE",
                semester=5,
                section="A",
                user_id=student_user.id,
            )
        )

    if Subject.query.count() == 0:
        teacher = User.query.filter_by(username="teacher", role="teacher").first()
        db.session.add_all(
            [
                Subject(code="CS501", name="Computer Networks", department="CSE", semester=5, teacher_id=teacher.id if teacher else None),
                Subject(code="CS502", name="Database Management Systems", department="CSE", semester=5, teacher_id=teacher.id if teacher else None),
                Subject(code="CS503", name="Machine Learning", department="CSE", semester=5, teacher_id=teacher.id if teacher else None),
                Subject(code="EC301", name="Digital Electronics", department="ECE", semester=3),
            ]
        )

    teacher = User.query.filter_by(username="teacher", role="teacher").first()
    if teacher and not teacher.teacher_profile:
        db.session.add(
            TeacherProfile(
                employee_id="TCH001",
                email="teacher@example.com",
                department="CSE",
                designation="Assistant Professor",
                user_id=teacher.id,
            )
        )
    if teacher:
        for subject in Subject.query.filter_by(teacher_id=None, department="CSE").all():
            subject.teacher_id = teacher.id

    db.session.commit()


def migrate_database():
    subject_columns = [
        row[1] for row in db.session.execute(text("PRAGMA table_info(subject)")).fetchall()
    ]
    if "teacher_id" not in subject_columns:
        db.session.execute(text("ALTER TABLE subject ADD COLUMN teacher_id INTEGER"))
        db.session.commit()


def init_app_database():
    create_required_folders()
    with app.app_context():
        db.create_all()
        migrate_database()
        seed_database()


def filtered_students_query(department="", semester="", section=""):
    query = Student.query
    if department:
        query = query.filter_by(department=department)
    if semester:
        query = query.filter_by(semester=int(semester))
    if section:
        query = query.filter_by(section=section.upper())
    return query.order_by(Student.department, Student.semester, Student.section, Student.name)


def teacher_users():
    return User.query.filter_by(role="teacher").order_by(User.full_name).all()


def assigned_subject_ids():
    if current_user.role != "teacher":
        return None
    return [subject.id for subject in current_user.assigned_subjects]


def subject_options():
    query = Subject.query
    if current_user.is_authenticated and current_user.role == "teacher":
        query = query.filter_by(teacher_id=current_user.id)
    return query.order_by(Subject.department, Subject.semester, Subject.code).all()


def can_use_subject(subject_id):
    subject_id = int(subject_id or 0)
    if current_user.role == "admin":
        return True
    if not subject_id:
        return False
    return Subject.query.filter_by(id=subject_id, teacher_id=current_user.id).first() is not None


def mark_attendance_if_new(student_id, subject_id, period_no, marked_by, method, status="Present"):
    today = date.today()
    subject_id = int(subject_id or 0)
    period_no = int(period_no or 1)
    existing = Attendance.query.filter_by(
        student_id=student_id,
        subject_id=subject_id,
        attendance_date=today,
        period_no=period_no,
    ).first()

    if existing:
        return existing, False

    record = Attendance(
        student_id=student_id,
        subject_id=subject_id,
        attendance_date=today,
        period_no=period_no,
        status=status,
        method=method,
        marked_by=marked_by,
    )
    db.session.add(record)
    db.session.commit()
    return record, True


def student_matches_session(student):
    with attendance_lock:
        department = attendance_session["department"]
        semester = attendance_session["semester"]
        section = attendance_session["section"]

    if department and student.department != department:
        return False
    if semester and student.semester != int(semester):
        return False
    if section and student.section != section:
        return False
    return True


def session_snapshot():
    with attendance_lock:
        snapshot = dict(attendance_session)
        snapshot["marked"] = list(attendance_session["marked"].values())
        return snapshot


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect_for_role(current_user)
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            if role and role != user.role:
                flash("Please select the correct role for this account.", "danger")
                return render_template("login.html")
            login_user(user)
            return redirect_for_role(user)

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
@roles_required("admin", "teacher")
def dashboard():
    today = date.today()
    subject_ids = assigned_subject_ids()
    if subject_ids is None:
        total_students = Student.query.count()
        today_query = db.session.query(Attendance.student_id).filter(
            Attendance.attendance_date == today,
            Attendance.status == "Present",
        )
        recent_query = Attendance.query
    else:
        assigned_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
        class_filters = [
            and_(Student.department == subject.department, Student.semester == subject.semester)
            for subject in assigned_subjects
        ]
        total_students = Student.query.filter(or_(*class_filters)).count() if class_filters else 0
        today_query = db.session.query(Attendance.student_id).filter(
            Attendance.attendance_date == today,
            Attendance.status == "Present",
            Attendance.subject_id.in_(subject_ids or [-1]),
        )
        recent_query = Attendance.query.filter(Attendance.subject_id.in_(subject_ids or [-1]))
    today_present = today_query.distinct().count()
    total_materials = StudyMaterial.query.count()
    total_assignments = Assignment.query.count()
    recent_attendance = (
        recent_query.order_by(Attendance.marked_at.desc())
        .limit(8)
        .all()
    )
    return render_template(
        "dashboard.html",
        total_students=total_students,
        today_present=today_present,
        total_materials=total_materials,
        total_assignments=total_assignments,
        recent_attendance=recent_attendance,
    )


@app.route("/student-dashboard")
@login_required
@roles_required("student")
def student_dashboard():
    student = current_user.student_profile
    if not student:
        abort(404)

    total = Attendance.query.filter_by(student_id=student.id).count()
    attended = Attendance.query.filter_by(student_id=student.id, status="Present").count()
    percentage = round((attended / total) * 100, 1) if total else 0
    materials = (
        StudyMaterial.query.filter_by(department=student.department, semester=student.semester)
        .order_by(StudyMaterial.uploaded_at.desc())
        .all()
    )
    assignments = (
        Assignment.query.filter_by(department=student.department, semester=student.semester)
        .order_by(Assignment.due_date.asc())
        .all()
    )
    history = (
        Attendance.query.filter_by(student_id=student.id)
        .order_by(Attendance.attendance_date.desc(), Attendance.marked_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "student_dashboard.html",
        student=student,
        total=total,
        attended=attended,
        percentage=percentage,
        materials=materials,
        assignments=assignments,
        history=history,
    )


@app.route("/students", methods=["GET", "POST"])
@login_required
@roles_required("admin", "teacher")
def students():
    if request.method == "POST":
        try:
            roll_number = request.form.get("roll_number", "").strip().upper()
            username = request.form.get("username", "").strip() or roll_number.lower()
            password = request.form.get("password", "").strip() or "student123"

            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "danger")
                return redirect(url_for("students"))
            if Student.query.filter_by(roll_number=roll_number).first():
                flash("Roll number already exists.", "danger")
                return redirect(url_for("students"))

            user = User(
                username=username,
                full_name=request.form.get("name", "").strip(),
                role="student",
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.flush()

            face_image = save_upload(request.files.get("face_image"), "faces", ALLOWED_IMAGES)
            student = Student(
                roll_number=roll_number,
                name=request.form.get("name", "").strip(),
                email=request.form.get("email", "").strip(),
                department=request.form.get("department", "").strip().upper(),
                semester=int(request.form.get("semester", 1)),
                section=request.form.get("section", "A").strip().upper(),
                face_image=face_image,
                user_id=user.id,
            )
            db.session.add(student)
            db.session.commit()
            flash(f"Student added. Login: {username} / {password}", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(url_for("students"))

    department = request.args.get("department", "")
    semester = request.args.get("semester", "")
    section = request.args.get("section", "")
    student_rows = filtered_students_query(department, semester, section).all()
    return render_template(
        "students.html",
        students=student_rows,
        department=department,
        semester=semester,
        section=section,
    )


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin", "teacher")
def edit_student(student_id):
    student = db.session.get(Student, student_id) or abort(404)
    if request.method == "POST":
        try:
            student.roll_number = request.form.get("roll_number", "").strip().upper()
            student.name = request.form.get("name", "").strip()
            student.email = request.form.get("email", "").strip()
            student.department = request.form.get("department", "").strip().upper()
            student.semester = int(request.form.get("semester", 1))
            student.section = request.form.get("section", "A").strip().upper()
            if student.user:
                student.user.full_name = student.name
            face_image = save_upload(request.files.get("face_image"), "faces", ALLOWED_IMAGES)
            if face_image:
                student.face_image = face_image
            db.session.commit()
            flash("Student updated successfully.", "success")
            return redirect(url_for("students"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")

    return render_template("student_form.html", student=student)


@app.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_student(student_id):
    student = db.session.get(Student, student_id) or abort(404)
    user = student.user
    db.session.delete(student)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash("Student deleted.", "success")
    return redirect(url_for("students"))


@app.route("/teachers", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def teachers():
    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip().upper()
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip() or "teacher123"

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("teachers"))
        if TeacherProfile.query.filter_by(employee_id=employee_id).first():
            flash("Employee ID already exists.", "danger")
            return redirect(url_for("teachers"))

        teacher = User(
            username=username,
            full_name=full_name,
            role="teacher",
            password_hash=generate_password_hash(password),
        )
        db.session.add(teacher)
        db.session.flush()
        db.session.add(
            TeacherProfile(
                employee_id=employee_id,
                email=request.form.get("email", "").strip(),
                phone=request.form.get("phone", "").strip(),
                department=request.form.get("department", "").strip().upper(),
                designation=request.form.get("designation", "Teacher").strip() or "Teacher",
                user_id=teacher.id,
            )
        )
        db.session.commit()
        flash(f"Teacher added. Login: {username} / {password}", "success")
        return redirect(url_for("teachers"))

    teacher_rows = teacher_users()
    return render_template("teachers.html", teachers=teacher_rows)


@app.route("/teachers/<int:teacher_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_teacher(teacher_id):
    teacher = db.session.get(User, teacher_id) or abort(404)
    if teacher.role != "teacher" or teacher.id == current_user.id:
        abort(403)

    Subject.query.filter_by(teacher_id=teacher.id).update({"teacher_id": None})
    db.session.delete(teacher)
    db.session.commit()
    flash("Teacher removed and assigned subjects were unassigned.", "success")
    return redirect(url_for("teachers"))


@app.route("/subjects", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def subjects():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        if Subject.query.filter_by(code=code).first():
            flash("Subject code already exists.", "danger")
            return redirect(url_for("subjects"))

        teacher_id = int(request.form.get("teacher_id", 0) or 0) or None
        if teacher_id and not User.query.filter_by(id=teacher_id, role="teacher").first():
            flash("Selected teacher was not found.", "danger")
            return redirect(url_for("subjects"))

        db.session.add(
            Subject(
                code=code,
                name=request.form.get("name", "").strip(),
                department=request.form.get("department", "").strip().upper(),
                semester=int(request.form.get("semester", 1)),
                teacher_id=teacher_id,
            )
        )
        db.session.commit()
        flash("Subject added and assigned.", "success")
        return redirect(url_for("subjects"))

    subject_rows = Subject.query.order_by(Subject.department, Subject.semester, Subject.code).all()
    return render_template("subjects.html", subjects=subject_rows, teachers=teacher_users())


@app.route("/subjects/<int:subject_id>/assign", methods=["POST"])
@login_required
@roles_required("admin")
def assign_subject(subject_id):
    subject = db.session.get(Subject, subject_id) or abort(404)
    teacher_id = int(request.form.get("teacher_id", 0) or 0) or None
    if teacher_id and not User.query.filter_by(id=teacher_id, role="teacher").first():
        flash("Selected teacher was not found.", "danger")
        return redirect(url_for("subjects"))
    subject.teacher_id = teacher_id
    db.session.commit()
    flash("Subject assignment updated.", "success")
    return redirect(url_for("subjects"))


@app.route("/subjects/<int:subject_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def delete_subject(subject_id):
    subject = db.session.get(Subject, subject_id) or abort(404)
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted.", "success")
    return redirect(url_for("subjects"))


@app.route("/attendance")
@login_required
@roles_required("admin", "teacher")
def attendance():
    department = request.args.get("department", "").strip().upper()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip().upper()
    subject_id = int(request.args.get("subject_id", 0) or 0)
    subjects = subject_options()
    if current_user.role == "teacher":
        if not subjects:
            student_rows = []
            latest_by_student = {}
            return render_template(
                "attendance.html",
                students=student_rows,
                latest_by_student=latest_by_student,
                subjects=subjects,
                department=department,
                semester=semester,
                section=section,
                subject_id=subject_id,
                session_data=session_snapshot(),
                can_use_general=False,
            )
        if not subject_id:
            subject_id = subjects[0].id
        selected_subject = Subject.query.filter_by(id=subject_id, teacher_id=current_user.id).first()
        if not selected_subject:
            abort(403)
        department = selected_subject.department
        semester = str(selected_subject.semester)

    today = date.today()
    student_rows = filtered_students_query(department, semester, section).all()
    ids = [student.id for student in student_rows]
    records = []
    if ids:
        records = (
            Attendance.query.filter(
                Attendance.attendance_date == today,
                Attendance.student_id.in_(ids),
            )
            .order_by(Attendance.marked_at.desc())
            .all()
        )

    latest_by_student = {}
    for record in records:
        if subject_id and record.subject_id != subject_id:
            continue
        latest_by_student.setdefault(record.student_id, record)

    return render_template(
        "attendance.html",
        students=student_rows,
        latest_by_student=latest_by_student,
        subjects=subjects,
        department=department,
        semester=semester,
        section=section,
        subject_id=subject_id,
        session_data=session_snapshot(),
        can_use_general=current_user.role == "admin",
    )


@app.route("/attendance/manual", methods=["POST"])
@login_required
@roles_required("admin", "teacher")
def manual_attendance():
    payload = request.get_json() or {}
    student_id = int(payload.get("student_id"))
    subject_id = int(payload.get("subject_id", 0) or 0)
    if not can_use_subject(subject_id):
        return jsonify({"success": False, "error": "Teacher is not assigned to this subject."}), 403
    period_no = int(payload.get("period_no", 1) or 1)
    status = payload.get("status", "Present")
    record, created = mark_attendance_if_new(
        student_id,
        subject_id,
        period_no,
        current_user.username,
        "manual",
        status=status,
    )
    if not created:
        record.status = status
        record.method = "manual"
        record.marked_by = current_user.username
        record.marked_at = datetime.utcnow()
        db.session.commit()
    return jsonify({"success": True, "created": created})


@app.route("/attendance/start", methods=["POST"])
@login_required
@roles_required("admin", "teacher")
def start_face_attendance():
    payload = request.get_json() or request.form
    subject_id = int(payload.get("subject_id", 0) or 0)
    if not can_use_subject(subject_id):
        return jsonify({"success": False, "error": "Teacher is not assigned to this subject."}), 403

    selected_subject = db.session.get(Subject, subject_id) if subject_id else None
    department = payload.get("department", "").strip().upper()
    semester = payload.get("semester", "").strip()
    if current_user.role == "teacher" and selected_subject:
        department = selected_subject.department
        semester = str(selected_subject.semester)

    with attendance_lock:
        attendance_session.update(
            {
                "active": True,
                "started_by": current_user.username,
                "started_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                "department": department,
                "semester": semester,
                "section": payload.get("section", "").strip().upper(),
                "subject_id": subject_id,
                "period_no": int(payload.get("period_no", 1) or 1),
                "marked": {},
            }
        )
    return jsonify({"success": True, "session": session_snapshot()})


@app.route("/attendance/stop", methods=["POST"])
@login_required
@roles_required("admin", "teacher")
def stop_face_attendance():
    with attendance_lock:
        attendance_session["active"] = False
    return jsonify({"success": True, "session": session_snapshot()})


@app.route("/attendance/live")
@login_required
@roles_required("admin", "teacher")
def attendance_live():
    return Response(
        stream_with_context(generate_attendance_frames()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


def generate_attendance_frames():
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        while session_snapshot()["active"]:
            yield face_service.placeholder_response("Webcam not available")
            time.sleep(1)
        return

    last_reload = 0
    try:
        while session_snapshot()["active"]:
            success, frame = camera.read()
            if not success:
                yield face_service.placeholder_response("Could not read webcam frame")
                time.sleep(1)
                continue

            if time.time() - last_reload > 5:
                students_with_faces = Student.query.filter(Student.face_image.isnot(None)).all()
                known_faces = [
                    (student.id, student.name, str(UPLOAD_FOLDER / student.face_image))
                    for student in students_with_faces
                    if student.face_image
                ]
                face_service.load_known_faces(known_faces)
                last_reload = time.time()

            matches, annotated_frame = face_service.recognize_frame(frame)
            for match in matches:
                student = db.session.get(Student, match.student_id)
                if not student or not student_matches_session(student):
                    continue

                snapshot = session_snapshot()
                record, created = mark_attendance_if_new(
                    student.id,
                    snapshot["subject_id"],
                    snapshot["period_no"],
                    snapshot["started_by"],
                    "face",
                )
                if created:
                    with attendance_lock:
                        attendance_session["marked"][student.id] = {
                            "id": student.id,
                            "name": student.name,
                            "roll_number": student.roll_number,
                            "time": record.marked_at.strftime("%H:%M:%S"),
                        }

            yield face_service.frame_response(annotated_frame)
    finally:
        camera.release()


@app.route("/api/attendance/session")
@login_required
@roles_required("admin", "teacher")
def attendance_session_api():
    return jsonify(session_snapshot())


@app.route("/reports")
@login_required
@roles_required("admin", "teacher")
def reports():
    selected_date = request.args.get("date", date.today().isoformat())
    report_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    subject_ids = assigned_subject_ids()
    daily_query = Attendance.query.filter_by(attendance_date=report_date)
    if subject_ids is not None:
        daily_query = daily_query.filter(Attendance.subject_id.in_(subject_ids or [-1]))
    daily_records = daily_query.order_by(Attendance.marked_at.desc()).all()

    student_reports = []
    students_query = Student.query
    if subject_ids is not None:
        assigned_subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all() if subject_ids else []
        class_filters = [
            and_(Student.department == subject.department, Student.semester == subject.semester)
            for subject in assigned_subjects
        ]
        students_query = students_query.filter(or_(*class_filters)) if class_filters else students_query.filter(False)
    for student in students_query.order_by(Student.department, Student.semester, Student.name).all():
        total_query = Attendance.query.filter_by(student_id=student.id)
        present_query = Attendance.query.filter_by(student_id=student.id, status="Present")
        if subject_ids is not None:
            total_query = total_query.filter(Attendance.subject_id.in_(subject_ids or [-1]))
            present_query = present_query.filter(Attendance.subject_id.in_(subject_ids or [-1]))
        total = total_query.count()
        present = present_query.count()
        student_reports.append(
            {
                "student": student,
                "total": total,
                "present": present,
                "percentage": round((present / total) * 100, 1) if total else 0,
            }
        )

    return render_template(
        "reports.html",
        selected_date=selected_date,
        daily_records=daily_records,
        student_reports=student_reports,
    )


@app.route("/materials", methods=["GET", "POST"])
@login_required
def materials():
    if request.method == "POST":
        if current_user.role not in {"admin", "teacher"}:
            abort(403)
        try:
            material_file = save_upload(request.files.get("material_file"), "materials", ALLOWED_MATERIALS)
            if not material_file:
                flash("Please choose a file to upload.", "danger")
                return redirect(url_for("materials"))
            db.session.add(
                StudyMaterial(
                    title=request.form.get("title", "").strip(),
                    description=request.form.get("description", "").strip(),
                    department=request.form.get("department", "").strip().upper(),
                    semester=int(request.form.get("semester", 1)),
                    file_path=material_file,
                    uploaded_by=current_user.username,
                )
            )
            db.session.commit()
            flash("Study material uploaded.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("materials"))

    query = StudyMaterial.query
    if current_user.role == "student" and current_user.student_profile:
        student = current_user.student_profile
        query = query.filter_by(department=student.department, semester=student.semester)
    material_rows = query.order_by(StudyMaterial.uploaded_at.desc()).all()
    return render_template("materials.html", materials=material_rows)


@app.route("/materials/<int:material_id>/download")
@login_required
def download_material(material_id):
    material = db.session.get(StudyMaterial, material_id) or abort(404)
    return send_from_directory(UPLOAD_FOLDER, material.file_path, as_attachment=True)


@app.route("/assignments", methods=["GET", "POST"])
@login_required
def assignments():
    if request.method == "POST":
        if current_user.role not in {"admin", "teacher"}:
            abort(403)
        due_date_value = request.form.get("due_date") or date.today().isoformat()
        db.session.add(
            Assignment(
                title=request.form.get("title", "").strip(),
                description=request.form.get("description", "").strip(),
                department=request.form.get("department", "").strip().upper(),
                semester=int(request.form.get("semester", 1)),
                due_date=datetime.strptime(due_date_value, "%Y-%m-%d").date(),
                created_by=current_user.username,
            )
        )
        db.session.commit()
        flash("Assignment created.", "success")
        return redirect(url_for("assignments"))

    query = Assignment.query
    if current_user.role == "student" and current_user.student_profile:
        student = current_user.student_profile
        query = query.filter_by(department=student.department, semester=student.semester)
    assignment_rows = query.order_by(Assignment.due_date.asc()).all()
    return render_template("assignments.html", assignments=assignment_rows)


@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="You do not have access to this page."), 403


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="The page you requested was not found."), 404


init_app_database()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, threaded=True, port=int(os.environ.get("PORT", 5000)))
