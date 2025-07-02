# email_utils.py
from flask_mail import Message
from flask import current_app
from my_extensions import mail  # ✅ Must be correct import



def send_rejection_email(applicant):
    with current_app.app_context():
        msg = Message('Application Rejected', recipients=[applicant.email])
        msg.body = f"""Dear {applicant.name},

Thank you for applying. We regret to inform you that you were not selected.

Best regards,
HR Team"""
        mail.send(msg)

def send_offer_extended_email(applicant):
    with current_app.app_context():
        msg = Message('Offer Extended - Your Action Needed', recipients=[applicant.email])
        msg.body = f"""Dear {applicant.name},

Congratulations! Based on your interview performance, we are extending a job offer.

Please log in to your account and respond by accepting or rejecting the offer.

Best regards,
HR Team"""
        mail.send(msg)

def send_interview_schedule_email(applicant, job_title, interview):
    with current_app.app_context():
        msg = Message('Interview Scheduled', recipients=[applicant.email])
        msg.body = f"""Interview for {job_title} on {interview.date} at {interview.time} via {interview.mode}.
Location/Link: {interview.location_or_link}"""
        mail.send(msg)

def send_user_accepted_offer_email(applicant):
    with current_app.app_context():
        msg = Message('Offer Letter - Congratulations!', recipients=[applicant.email])
        msg.body = f"""Dear {applicant.name},

Congratulations! You have accepted the offer. We are excited to welcome you.

Best regards,
HR Team"""
        mail.send(msg)

def send_auto_selection_email(applicant):
    with current_app.app_context():
        msg = Message('Offer Letter - Auto Selection!', recipients=[applicant.email])
        msg.body = f"""Dear {applicant.name},

We are pleased to inform you that you have been selected based on your interview feedback and qualifications.

Congratulations!

Best regards,
HR Team"""
        mail.send(msg)
