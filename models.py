from datetime import datetime
from werkzeug.security import generate_password_hash
from my_extensions import db
import PyPDF2
import docx
import re
from google.generativeai import GenerativeModel
from dotenv import load_dotenv

load_dotenv()

class Admi(db.Model):
    __tablename__ = 'admi'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Job1(db.Model):
    __tablename__ = 'job1'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.Float)
    deadline = db.Column(db.Date)
    posted_on = db.Column(db.DateTime, default=datetime.utcnow)
    applicants = db.relationship('Applicant1', backref='job', lazy=True)

class Applicant1(db.Model):
    __tablename__ = 'applicant1'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    age = db.Column(db.Integer, nullable=False)
    qualification = db.Column(db.String(100), nullable=False)
    resume_filename = db.Column(db.String(255), nullable=False)
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
    job_id = db.Column(db.Integer, db.ForeignKey('job1.id'), nullable=False)
    ats_score = db.Column(db.Float)
    status = db.Column(db.String(20), default=None)
    final_status = db.Column(db.String(20), default=None)
    user_response = db.Column(db.String(20), default=None)
    offer_extended_on = db.Column(db.DateTime)

class UserApplied(db.Model):
    __tablename__ = 'user_applied'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_email = db.Column(db.String(120), nullable=False, index=True)
    job_id = db.Column(db.Integer, nullable=False)
    job_title = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(50), default='Pending')
    user_response = db.Column(db.String(50), default=None)
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant1.id'))

    applicant = db.relationship('Applicant1', backref='user_application')
    user = db.relationship('User')

class Interview1(db.Model):
    __tablename__ = 'interview1'
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant1.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    mode = db.Column(db.String(50), nullable=False)
    location_or_link = db.Column(db.String(255), nullable=False)
    scheduled_on = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Scheduled')
    applicant = db.relationship('Applicant1', backref='interviews')

class Feedback1(db.Model):
    __tablename__ = 'feedback1'
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview1.id'), nullable=False)
    feedback_text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    submitted_on = db.Column(db.DateTime, default=datetime.utcnow)
    interview = db.relationship('Interview1', backref='feedback')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx'}

def extract_text_from_file(filepath):
    if filepath.endswith('.pdf'):
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join([page.extract_text() or '' for page in reader.pages])
    elif filepath.endswith('.docx') or filepath.endswith('.doc'):
        try:
            doc = docx.Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        except:
            return ""
    else:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

def calculate_ats_score(resume_text, job_description):
    try:
        model = GenerativeModel(model_name='gemini-1.5-flash')
        prompt = f"""
        Analyze the following resume and job description. Provide an ATS compatibility score (0 to 100).
        Only return the numeric score.

        Job Description:
        {job_description}

        Resume:
        {resume_text[:8000]}
        """
        response = model.generate_content(prompt)
        match = re.search(r'\d+(\.\d+)?', response.text.strip())
        return float(match.group(0)) if match else 0.5
    except Exception as e:
        print("[Gemini Error]", e)
        return 0.5

def initialize_database(app):
    with app.app_context():
        db.create_all()
        if not Admi.query.first():
            admin = Admi(username='admin', password=generate_password_hash('admin123'))
            db.session.add(admin)
            db.session.commit()
