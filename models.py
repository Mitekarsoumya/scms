from datetime import date, datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TeacherProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(30), default="")
    department = db.Column(db.String(40), nullable=False)
    designation = db.Column(db.String(80), default="Teacher")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship(
        "User",
        backref=db.backref("teacher_profile", uselist=False, cascade="all, delete-orphan"),
        single_parent=True,
    )


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), default="")
    department = db.Column(db.String(40), nullable=False)
    semester = db.Column(db.Integer, nullable=False, default=1)
    section = db.Column(db.String(10), nullable=False, default="A")
    face_image = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("student_profile", uselist=False))
    attendance_records = db.relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete-orphan",
    )


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(40), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    teacher = db.relationship("User", foreign_keys=[teacher_id], backref="assigned_subjects")


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject_id = db.Column(db.Integer, nullable=False, default=0)
    attendance_date = db.Column(db.Date, nullable=False, default=date.today)
    period_no = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="Present")
    method = db.Column(db.String(20), nullable=False, default="manual")
    marked_by = db.Column(db.String(80), nullable=False, default="system")
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("Student", back_populates="attendance_records")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "subject_id",
            "attendance_date",
            "period_no",
            name="unique_attendance_once_per_period",
        ),
    )

    @property
    def subject_name(self):
        if not self.subject_id:
            return "General Attendance"
        subject = db.session.get(Subject, self.subject_id)
        return subject.name if subject else "Subject"


class StudyMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    department = db.Column(db.String(40), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.String(80), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    department = db.Column(db.String(40), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
