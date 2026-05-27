"""
mailer.py — EduTrack Pro email sender
Handles login credentials + announcements via SMTP.
"""
import smtplib, ssl, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

SMTP_PRESETS = {
    "gmail":   {"label":"Gmail","smtp_host":"smtp.gmail.com","smtp_port":587,
                "note":"Use an App Password (Google Account → Security → 2-Step → App Passwords)."},
    "outlook": {"label":"Outlook / Hotmail","smtp_host":"smtp.office365.com","smtp_port":587,
                "note":"Use your full Outlook email and regular password."},
    "yahoo":   {"label":"Yahoo Mail","smtp_host":"smtp.mail.yahoo.com","smtp_port":587,
                "note":"Generate an App Password from Yahoo Account Security settings."},
    "zoho":    {"label":"Zoho Mail","smtp_host":"smtp.zoho.in","smtp_port":587,
                "note":"Use your Zoho email and password."},
    "custom":  {"label":"Custom SMTP","smtp_host":"","smtp_port":587,"note":"Enter your own SMTP server details."}
}


def _smtp_send(config, from_addr, to_email, msg_obj):
    smtp_host = config.get("smtp_host","").strip()
    smtp_port = int(config.get("smtp_port", 587))
    smtp_user = config.get("smtp_user","").strip()
    smtp_pass = config.get("smtp_pass","").strip()
    if smtp_port == 465:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=10) as s:
            s.login(smtp_user, smtp_pass)
            s.sendmail(from_addr, to_email, msg_obj.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.ehlo(); s.starttls(context=ssl.create_default_context()); s.ehlo()
            s.login(smtp_user, smtp_pass)
            s.sendmail(from_addr, to_email, msg_obj.as_string())


def build_email_html(student_name, student_class, username, password,
                     school_name="EduTrack Pro", portal_url="http://localhost:5000"):
    year = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><title>Your Login Credentials</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
      <tr><td style="background:linear-gradient(135deg,#1e3a5f,#0f1f3a);border-radius:16px 16px 0 0;padding:32px 40px;text-align:center;">
        <h1 style="color:white;font-size:22px;font-weight:800;margin:0 0 4px;">{school_name}</h1>
        <p style="color:#93b4d9;font-size:13px;margin:0;">Engineering College Management System</p>
      </td></tr>
      <tr><td style="background:#fff;padding:36px 40px;">
        <p style="color:#1e293b;font-size:16px;font-weight:600;margin:0 0 6px;">Hello, {student_name}! 👋</p>
        <p style="color:#64748b;font-size:14px;line-height:1.6;margin:0 0 24px;">
          Welcome to <strong>{school_name}</strong>! Your student portal account is ready.</p>
        <div style="margin-bottom:20px;">
          <span style="background:#dbeafe;color:#1d4ed8;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700;">
            {student_class}
          </span>
        </div>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
          <tr><td style="background:#f8faff;border:2px solid #e0e9ff;border-radius:14px;padding:24px;">
            <p style="color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 16px;">Login Credentials</p>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
              <tr><td style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;">
                <p style="color:#94a3b8;font-size:11px;font-weight:600;text-transform:uppercase;margin:0 0 4px;">Username</p>
                <p style="color:#1e293b;font-size:17px;font-weight:800;font-family:'Courier New',monospace;margin:0;">{username}</p>
              </td></tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr><td style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;">
                <p style="color:#94a3b8;font-size:11px;font-weight:600;text-transform:uppercase;margin:0 0 4px;">Password</p>
                <p style="color:#4f8ef7;font-size:17px;font-weight:800;font-family:'Courier New',monospace;margin:0;letter-spacing:1px;">{password}</p>
              </td></tr>
            </table>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
          <tr><td align="center">
            <a href="{portal_url}" style="display:inline-block;background:linear-gradient(135deg,#4f8ef7,#6366f1);color:white;font-size:15px;font-weight:700;text-decoration:none;padding:13px 32px;border-radius:12px;">
              Login to Student Portal →
            </a>
          </td></tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr><td style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;">
            <p style="color:#92400e;font-size:13px;margin:0;">
              ⚠️ <strong>Keep your credentials safe.</strong> Do not share your password with anyone.
            </p>
          </td></tr>
        </table>
      </td></tr>
      <tr><td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 0 16px 16px;padding:18px 40px;text-align:center;">
        <p style="color:#94a3b8;font-size:12px;margin:0;">© {year} {school_name} · Automated message — do not reply.</p>
      </td></tr>
    </table>
  </td></tr>
</table></body></html>"""


def build_announcement_html(recipient_name, title, body, school_name="EduTrack Pro"):
    year = datetime.now().year
    body_html = body.replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
      <tr><td style="background:linear-gradient(135deg,#1e3a5f,#0f1f3a);border-radius:16px 16px 0 0;padding:28px 40px;text-align:center;">
        <h1 style="color:white;font-size:20px;font-weight:800;margin:0 0 4px;">{school_name}</h1>
        <p style="color:#93b4d9;font-size:12px;margin:0;">📢 Announcement</p>
      </td></tr>
      <tr><td style="background:#fff;padding:36px 40px;">
        <p style="color:#64748b;font-size:14px;margin:0 0 20px;">Dear {recipient_name},</p>
        <h2 style="color:#1e293b;font-size:20px;font-weight:800;margin:0 0 16px;">{title}</h2>
        <div style="color:#475569;font-size:14px;line-height:1.7;border-left:4px solid #4f8ef7;padding-left:16px;">{body_html}</div>
      </td></tr>
      <tr><td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:0 0 16px 16px;padding:16px 40px;text-align:center;">
        <p style="color:#94a3b8;font-size:12px;margin:0;">© {year} {school_name} · Automated message — do not reply.</p>
      </td></tr>
    </table>
  </td></tr>
</table></body></html>"""


def send_credentials_email(to_email, student_name, student_class, username, password,
                            config: dict, qr_path=None, portal_url="http://localhost:5000"):
    if not config.get("enabled"):
        return False, "Email sending is disabled."
    smtp_host   = config.get("smtp_host","").strip()
    smtp_user   = config.get("smtp_user","").strip()
    smtp_pass   = config.get("smtp_pass","").strip()
    sender_name = config.get("sender_name","EduTrack Pro").strip()
    if not smtp_host or not smtp_user or not smtp_pass:
        return False, "SMTP not configured."
    if not to_email or "@" not in to_email:
        return False, f"Invalid email: {to_email}"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎓 Your Portal Credentials — Welcome, {student_name}!"
        msg["From"]    = f"{sender_name} <{smtp_user}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(f"Username: {username}\nPassword: {password}\nLogin: {portal_url}", "plain"))
        msg.attach(MIMEText(build_email_html(student_name, student_class, username, password,
                                              sender_name, portal_url), "html"))
        if qr_path and os.path.exists(qr_path):
            with open(qr_path,"rb") as f:
                qi = MIMEImage(f.read(), name=os.path.basename(qr_path))
                qi.add_header("Content-Disposition","attachment",filename=f"qr_{student_name.replace(' ','_')}.png")
                msg.attach(qi)
        _smtp_send(config, smtp_user, to_email, msg)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Use an App Password for Gmail."
    except smtplib.SMTPConnectError:
        return False, f"Could not connect to {smtp_host}."
    except TimeoutError:
        return False, "Connection timed out."
    except Exception as e:
        return False, str(e)


def send_announcement_email(to_email, recipient_name, title, body, config: dict):
    """Send an announcement email to one recipient."""
    if not config.get("enabled"):
        return False, "Email disabled."
    smtp_user   = config.get("smtp_user","").strip()
    sender_name = config.get("sender_name","EduTrack Pro").strip()
    if not to_email or "@" not in to_email:
        return False, f"Invalid email: {to_email}"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📢 {title}"
        msg["From"]    = f"{sender_name} <{smtp_user}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(f"{title}\n\n{body}", "plain"))
        msg.attach(MIMEText(build_announcement_html(recipient_name, title, body, sender_name), "html"))
        _smtp_send(config, smtp_user, to_email, msg)
        return True, ""
    except Exception as e:
        return False, str(e)


def test_smtp_connection(config: dict):
    smtp_host = config.get("smtp_host","").strip()
    smtp_port = int(config.get("smtp_port", 587))
    smtp_user = config.get("smtp_user","").strip()
    smtp_pass = config.get("smtp_pass","").strip()
    if not smtp_host or not smtp_user or not smtp_pass:
        return False, "Fill in all SMTP fields first."
    try:
        if smtp_port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=8) as s:
                s.login(smtp_user, smtp_pass)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as s:
                s.ehlo(); s.starttls(); s.ehlo()
                s.login(smtp_user, smtp_pass)
        return True, f"Connected to {smtp_host}:{smtp_port} successfully!"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed. Use an App Password for Gmail."
    except Exception as e:
        return False, str(e)
