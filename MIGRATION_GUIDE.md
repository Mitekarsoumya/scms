# EduTrack Pro — Complete Migration & Setup Guide

## What Changed (from old SCMS to new EduTrack Pro)

### Renamed Concepts
| Old (School) | New (Engineering College) |
|---|---|
| Class (e.g. "10A") | Department + Semester + Section (e.g. CSE, Sem 3, Section A) |
| Student ID only | USN (University Seat Number) |
| Teacher | Faculty |
| SCMS Pro | EduTrack Pro |

---

## Fresh Installation (Recommended)

```bash
# 1. Replace your files with the new ones
cp app.py      /your/project/app.py
cp database.py /your/project/database.py
cp mailer.py   /your/project/mailer.py

# 2. Copy ALL templates into your templates/ folder
cp templates/* /your/project/templates/

# 3. DELETE the old database (schema changed completely)
rm scms.db

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run
python app.py
```

> ⚠️ The old `scms.db` schema is incompatible. You must delete it. Student data will need to be re-entered or imported via CSV.

---

## Project Structure (Complete)

```
your_project/
├── app.py              ← All Flask routes (updated)
├── database.py         ← All DB operations (completely rewritten)
├── mailer.py           ← Email sender (+ announcement emails)
├── requirements.txt    ← Same dependencies
├── scms.db             ← Auto-created on first run (DELETE old one)
├── qrcodes/            ← Auto-created
├── credentials/        ← Auto-created
└── templates/
    ├── base.html           ← Sidebar + topbar (dark theme)
    ├── login.html          ← Role-selector login page
    ├── dashboard.html      ← Main dashboard with stats
    ├── students.html       ← Student list with filters
    ├── student_detail.html ← Student profile + parents + marks + fees
    ├── attendance.html     ← Subject/period-wise attendance
    ├── timetable.html      ← Weekly timetable grid
    ├── exams.html          ← Exam management
    ├── exam_marks.html     ← Bulk marks entry
    ├── fees.html           ← Fee structure + defaulters
    ├── student_fees.html   ← Per-student fee payment
    ├── reports.html        ← Attendance analytics
    ├── announcements.html  ← Post + auto-email announcements
    ├── student_portal.html ← Student self-service (tabs: attend/marks/tt/fees)
    ├── parent_portal.html  ← Parent view of child's data
    ├── settings.html       ← Subjects, departments, password
    ├── email_settings.html ← SMTP config + log
    ├── import_students.html← CSV bulk import
    ├── qr_scan.html        ← Webcam QR scanner
    ├── print_attendance.html← Printable sheet
    └── 404.html
```

---

## Default Login Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| HOD | `hod` | `hod123` |
| Faculty | `faculty` | `faculty123` |
| Student | auto (their USN lowercase) | random 8-char hex |
| Parent | auto-generated | random 8-char hex |

---

## New Features Summary

### 1. Role-Based Login Page
- 5 role cards on login: Admin, HOD, Faculty, Student, Parent
- Role selection validates against DB — wrong role shows error

### 2. Departments + Semester Structure
- Students belong to: Department (CSE/ECE/etc) + Semester (1-8) + Section (A/B/C)
- All filters (attendance, reports, fees, exams) work by dept/sem/section

### 3. Subject/Period-wise Attendance (`/attendance`)
- Filter by department, semester, section, AND subject
- Each record stores: student, subject, date, period_no, status
- UNIQUE constraint prevents duplicate marking
- Subject-wise % shown per student (with 75% shortage alerts)

### 4. Exam Marks (`/exams`, `/exams/<id>/marks`)
- Create exams: CAT1, CAT2, Mid Sem, End Sem, Assignment, Lab
- Bulk marks entry grid — Tab between cells, auto-grade calculation
- Grade scale: O(≥90%) A+(≥80%) A(≥70%) B+(≥60%) B(≥50%) C(≥40%) D(≥35%) F
- Visible in student detail page, student portal, parent portal

### 5. Fee Tracking (`/fees`, `/fees/student/<id>`)
- Define fee structure per department/semester (Tuition, Lab, Library, Exam, Hostel)
- Record payments: cash, UPI, DD, online — with receipt number
- Defaulter list with one-click email blast to all defaulters + parents
- Fee status visible in student portal and parent portal

### 6. Parent Portal (`/parent`)
- Parents get their own login credentials (created via student detail page)
- See child's: attendance %, subject-wise breakdown, exam marks, fees, announcements
- Admins can add/remove parent accounts from the student detail page

### 7. Announcement Emails (automatic)
- Every announcement posted → automatic background email to matching recipients
- Target: Everyone / Students only / Parents only / Faculty / Specific department
- Uses `send_announcement_email()` in mailer.py

### 8. Semester Filter in Portals
- Student portal has a semester dropdown to switch between Sem 1-8
- Shows subject-wise attendance, marks, and timetable for selected semester

---

## CSV Import Format

```csv
name,department,semester,section,email,phone,parent_email,parent_phone,usn
Priya Sharma,CSE,3,A,priya@email.com,9876543210,dad@email.com,9876543211,1CS22CS001
Rahul Kumar,ECE,1,B,rahul@email.com,,,,
```
- `usn` is optional — auto-generated if blank
- `parent_email`, `parent_phone` are optional

---

## Email Setup (for Announcements + Credentials)

1. Go to **Settings → Email Setup**
2. Select preset (Gmail recommended)
3. For Gmail: use an **App Password** (not your regular password)
   - Google Account → Security → 2-Step Verification → App Passwords
4. Enter your email + App Password
5. Check "Enable email sending"
6. Click "Test Connection" to verify
7. Save

Once enabled:
- New student added → credentials emailed to student
- Announcement posted → emailed to all targeted recipients
- Fee defaulter button → reminders emailed to defaulters + parents

---

## Role Permissions Summary

| Feature | Admin | HOD | Faculty | Student | Parent |
|---|---|---|---|---|---|
| Dashboard | ✅ | ✅ | ✅ | ❌ | ❌ |
| Add/Delete Students | ✅ | ✅ | ✅ | ❌ | ❌ |
| Delete Students | ✅ | ✅ | ❌ | ❌ | ❌ |
| Mark Attendance | ✅ | ✅ | ✅ | ❌ | ❌ |
| Add/Delete Exams | ✅ | ✅ | ✅ | ❌ | ❌ |
| Enter Marks | ✅ | ✅ | ✅ | ❌ | ❌ |
| Fee Structure | ✅ | ✅ | ❌ | ❌ | ❌ |
| Record Payments | ✅ | ✅ | ✅ | ❌ | ❌ |
| Add Parent Accounts | ✅ | ✅ | ❌ | ❌ | ❌ |
| Post Announcements | ✅ | ✅ | ✅ | ❌ | ❌ |
| View Own Portal | ❌ | ❌ | ❌ | ✅ | ✅ |
| Departments/Settings | ✅ | ❌ | ❌ | ❌ | ❌ |
