# Smart Classroom Management System

A simple Flask college project with role-based dashboards, SQLite storage, SQLAlchemy models, Flask-Login authentication, study material uploads, assignments, reports, and OpenCV face-recognition attendance.

## Tech Stack

- Python Flask
- SQLite
- Flask-SQLAlchemy
- Flask-Login
- OpenCV
- Bootstrap 5

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Demo Logins

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| Teacher | `teacher` | `teacher123` |
| Student | `student` | `student123` |

The app creates a new SQLite database named `smart_classroom.db` automatically. The old extracted `scms.db` is not used.

## Face Recognition Attendance Logic

1. Admin or teacher adds students and uploads one clear face image per student.
2. Teacher opens **Face Attendance** and selects department, semester, section, subject, and period.
3. Clicking **Start** opens the webcam stream from `/attendance/live`.
4. OpenCV detects faces using Haar Cascade.
5. If `opencv-contrib-python` is installed, the app trains an LBPH recognizer from uploaded student photos.
6. If LBPH is unavailable, the app uses a simple normalized face-template comparison fallback.
7. When a student is recognized, attendance is saved in SQLite.
8. A unique database rule prevents duplicate attendance for the same student, subject, date, and period.

## Main Project Structure

```text
scms_web/
  app.py                  Flask routes, auth, dashboards, attendance session
  models.py               SQLAlchemy database models
  face_service.py         OpenCV face detection and recognition logic
  smart_classroom.db      Auto-created SQLite database
  uploads/
    faces/                Uploaded student face images
    materials/            Uploaded study materials
  static/css/style.css    Blue and white professional theme
  templates/
    base.html
    login.html
    dashboard.html
    students.html
    attendance.html
    reports.html
    materials.html
    assignments.html
    student_dashboard.html
```

## Notes

- Run on the same machine that has the webcam.
- For best recognition, upload front-facing, well-lit images.
- If webcam permission is blocked, the video panel shows a camera unavailable message.
