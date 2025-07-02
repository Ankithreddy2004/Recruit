from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import uuid
from my_extensions import db, mail
from email_utils import send_user_accepted_offer_email, send_auto_selection_email

from models import (
    initialize_database, allowed_file, extract_text_from_file, calculate_ats_score,
    Admi, User, Job1, Applicant1, UserApplied, Interview1, Feedback1
)

from email_utils import (
    send_rejection_email,
    send_offer_extended_email,
    send_interview_schedule_email,
    send_user_accepted_offer_email,
    send_auto_selection_email
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.permanent_session_lifetime = timedelta(minutes=30)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize extensions
db.init_app(app)
mail.init_app(app)

# Initialize database
initialize_database(app)


@app.before_request
def before_request():
    public_endpoints = [
        'mainhome', 'login', 'signup', 'signup_user', 'login_user',
        'apply', 'job_listings', 'job_detail', 'serve_resume',
        'uploaded_file', 'static'
    ]
    if request.endpoint and request.endpoint not in public_endpoints:
        if 'admin' not in session and 'user' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login_user'))


@app.route('/')
def mainhome():
    session.pop('admin', None)
    return render_template('mainhome.html')

@app.route('/home')
def home():
    return render_template('home.html', username=session.get('admin'))

@app.route('/userhome')
def user_home():
    if 'user' not in session:
        flash('Please login to access this page', 'warning')
        return redirect(url_for('login_user'))
    return render_template('user_homepage.html', username=session['user'])

@app.route('/signupuser', methods=['GET', 'POST'])
def signup_user():
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pass')

        if not username or not password:
            flash('Both fields are required', 'warning')
            return redirect(url_for('signup_user'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('signup_user'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        session['user'] = username
        flash('Signup successful!', 'success')
        return redirect(url_for('job_listings'))

    return render_template('signup_user.html')

@app.route('/loginuser', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pass')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('user_home'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login_user.html')

@app.route('/logoutuser')
def logout_user():
    session.pop('user', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('mainhome'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin' in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = request.form.get('uname')
        password = request.form.get('pass')
        admin = Admi.query.filter_by(username=user).first()
        if admin and check_password_hash(admin.password, password):
            session['admin'] = admin.username
            session.permanent = True
            return redirect(url_for('home'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('uname')
        password = generate_password_hash(request.form.get('pass'))
        if Admi.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('signup'))
        db.session.add(Admi(username=username, password=password))
        db.session.commit()
        session['admin'] = username
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Logged out', 'info')
    return redirect(url_for('mainhome'))

@app.route('/admin/post-job', methods=['GET', 'POST'])
def post_job():
    if request.method == 'POST':
        try:
            job = Job1(
                title=request.form.get('title'),
                description=request.form.get('description'),
                location=request.form.get('location'),
                salary=float(request.form.get('salary')) if request.form.get('salary') else None,
                deadline=datetime.strptime(request.form.get('deadline'), '%Y-%m-%d').date()
            )
            db.session.add(job)
            db.session.commit()
            flash('Job posted!', 'success')
            return redirect(url_for('job_listings'))
        except Exception as e:
            db.session.rollback()
            flash(str(e), 'danger')
    return render_template('post_job.html')

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login_user'))

    jobs = Job1.query.all()
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            age = request.form.get('age')
            qualification = request.form.get('qualification')
            job_id = request.form.get('job_id')
            resume = request.files.get('resume')

            if not all([name, email, age, qualification, job_id, resume]):
                flash("All fields are required", "danger")
                return redirect(request.url)

            if resume.filename == '' or not allowed_file(resume.filename):
                flash("Invalid resume file", "danger")
                return redirect(request.url)

            filename = f"{uuid.uuid4().hex}_{secure_filename(resume.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(filepath)

            job = Job1.query.get(job_id)
            if not job:
                flash("Selected job does not exist.", "danger")
                return redirect(request.url)

            resume_text = extract_text_from_file(filepath)
            ats_score = calculate_ats_score(resume_text, job.description)

            applicant = Applicant1(
                name=name,
                email=email,
                age=int(age),
                qualification=qualification,
                resume_filename=filename,
                job_id=int(job_id),
                ats_score=ats_score
            )
            db.session.add(applicant)
            db.session.flush()

            current_user = User.query.filter_by(username=session['user']).first()
            if current_user:
                user_applied = UserApplied(
                    user_id=current_user.id,
                    user_email=email,
                    job_id=job.id,
                    job_title=job.title,
                    company_name="Our Company",
                    status='Pending',
                    applicant_id=applicant.id
                )
                db.session.add(user_applied)

            db.session.commit()
            flash(f"Applied successfully! ATS Score: {ats_score:.1f}", "success")
            return redirect(url_for('mainhome'))

        except Exception as e:
            db.session.rollback()
            flash(f"Application failed: {str(e)}", "danger")

    return render_template('apply.html', jobs=jobs)


#user applied details


@app.route('/user/offer-response/<int:applicant_id>', methods=['POST'])
def user_offer_response(applicant_id):
    if 'user' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login_user'))

    response = request.form.get('response')  # 'Accepted' or 'Rejected'
    applicant = Applicant1.query.get_or_404(applicant_id)
    user_applied = UserApplied.query.filter_by(applicant_id=applicant_id).first()

    if not user_applied or user_applied.status != 'Offer Extended':
        flash('Invalid action.', 'danger')
        return redirect(url_for('user_applied_details'))

    try:
        applicant.user_response = response
        user_applied.user_response = response

        if response == 'Accepted':
            applicant.final_decision = 'Accepted'
            user_applied.status = 'Offer Accepted'
            send_user_accepted_offer_email(applicant)

        elif response == 'Rejected':
            applicant.final_decision = 'Rejected'
            user_applied.status = 'Rejected'
            send_rejection_email(applicant)

            db.session.commit()  

            #  to select next best candidate
            #  to select next best candidate
            current_interview = Interview1.query.filter_by(applicant_id=applicant_id).first()
            if current_interview:
                job_id = applicant.job_id
                next_best = (
                    Feedback1.query
                    .join(Interview1)
                    .join(Applicant1)
                    .filter(Applicant1.job_id == job_id)
                    .filter(Applicant1.final_decision.is_(None))
                    .filter(Applicant1.id != applicant_id)
                    .order_by(Feedback1.rating.desc())
                    .first()
                )

                if next_best:
                    next_applicant = next_best.interview.applicant
                    next_applicant.final_decision = 'Accepted'

                    next_user_applied = UserApplied.query.filter_by(applicant_id=next_applicant.id).first()
                    if next_user_applied:
                        next_user_applied.status = 'Offer Extended'

                    send_auto_selection_email(next_applicant)
                db.session.commit()  # commit again for auto-selection

        #  Always commit at the end unless it was committed inside Rejected flow
        if response == 'Accepted':
            db.session.commit()

        flash(f"You have {response} the offer.", "info")

    except Exception as e:
        db.session.rollback()
        flash(f"Something went wrong: {str(e)}", "danger")

    return redirect(url_for('user_applied_details'))




@app.route('/user/applied-details')
def user_applied_details():
    if 'user' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login_user'))

    user = User.query.filter_by(username=session['user']).first()
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('user_home'))

    applications = UserApplied.query.filter_by(user_id=user.id)\
                                    .order_by(UserApplied.applied_on.desc()).all()

    application_data = []
    for app in applications:
        applicant = Applicant1.query.get(app.applicant_id) if app.applicant_id else None
        application_data.append({
            'id': app.id,
            'job_id': app.job_id,
            'job_title': app.job_title,
            'company_name': app.company_name,
            'applied_on': app.applied_on,
            'status': app.status,
            'user_response': app.user_response,
            'ats_score': applicant.ats_score if applicant else None,
            'resume_filename': applicant.resume_filename if applicant else None,
            'final_status': applicant.final_status if applicant else None,
            'applicant_id': app.applicant_id 
        })

    

    return render_template('user_applied_details.html', applications=application_data)



@app.route('/resumes/<filename>')
def serve_resume(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin/applicants')
def view_applicants():
    applicants = Applicant1.query.order_by(
        Applicant1.ats_score.desc(),
        Applicant1.applied_on.desc()
    ).all()
    return render_template('applicants.html', applicants=applicants)


@app.route('/admin/applicants/accept/<int:applicant_id>', methods=['POST'])
def accept_applicant(applicant_id):
    applicant = Applicant1.query.get_or_404(applicant_id)
    applicant.status = 'Accepted'
    db.session.commit()
    flash('Applicant accepted. Schedule interview.', 'success')
    return redirect(url_for('schedule_interview', applicant_id=applicant_id))

@app.route('/admin/applicants/reject/<int:applicant_id>', methods=['POST'])
def reject_applicant(applicant_id):
    applicant = Applicant1.query.get_or_404(applicant_id)
    try:
        applicant.status = 'Rejected'

        user_applied = UserApplied.query.filter_by(applicant_id=applicant_id).first()
        if user_applied:
            user_applied.status = 'Rejected'

        Interview1.query.filter_by(applicant_id=applicant_id).delete()

        send_rejection_email(applicant)

        db.session.commit()
        flash('Rejected and notified', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')

    return redirect(url_for('view_applicants'))

@app.route('/jobs')
def job_listings():
    jobs = Job1.query.order_by(Job1.posted_on.desc()).all()
    return render_template('job_listings.html', jobs=jobs)

@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    job = Job1.query.get_or_404(job_id)
    return render_template('job_detail.html', job=job)

@app.route('/schedule/<int:applicant_id>', methods=['GET', 'POST'])
def schedule_interview(applicant_id):
    applicant = Applicant1.query.get_or_404(applicant_id)
    job = Job1.query.get(applicant.job_id) if applicant.job_id else None
    if request.method == 'POST':
        try:
            interview = Interview1(
                applicant_id=applicant.id,
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
                time=datetime.strptime(request.form.get('time'), '%H:%M').time(),
                mode=request.form.get('mode'),
                location_or_link=request.form.get('location_or_link')
            )
            db.session.add(interview)
            db.session.commit()

            send_interview_schedule_email(applicant, job.title, interview)

            flash('Interview scheduled', 'success')
            return redirect(url_for('view_applicants'))

        except Exception as e:
            db.session.rollback()
            flash(str(e), 'danger')
    return render_template('schedule_interview.html', applicant=applicant, job=job)

@app.route('/admin/accepted-list')
def accepted_list():
    interviews = Interview1.query.filter_by(status='Scheduled').all()
    return render_template('accepted_list.html', interviews=interviews)

@app.route('/feedback/<int:interview_id>', methods=['GET', 'POST'])
def give_feedback(interview_id):
    interview = Interview1.query.get_or_404(interview_id)
    applicant = interview.applicant
    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        rating = int(request.form.get('rating'))
        feedback = Feedback1(interview_id=interview.id, feedback_text=feedback_text, rating=rating)
        db.session.add(feedback)
        db.session.commit()
        flash('Interview feedback submitted successfully!', 'success')
        return redirect(url_for('accepted_list'))
    return render_template('feedback.html', applicant=applicant, interview=interview)

@app.route('/admin/final-list')
def final_list():
    feedbacks = Feedback1.query.join(Interview1).join(Applicant1)\
                .order_by(Feedback1.rating.desc()).all()
    return render_template('final_list.html', feedbacks=feedbacks)


@app.route('/admin/final-list/accept/<int:applicant_id>', methods=['POST'])
def final_accept(applicant_id):
    applicant = Applicant1.query.get_or_404(applicant_id)
    try:
        applicant.final_status = 'Accepted'
        applicant.user_response = None
        applicant.offer_extended_on = datetime.utcnow()

        user_applied = UserApplied.query.filter_by(applicant_id=applicant_id).first()
        if user_applied:
            user_applied.status = 'Offer Extended'
            user_applied.user_response = None

        db.session.commit()
        send_offer_extended_email(applicant)

        flash(f'Offer extended to {applicant.name}. Awaiting user response.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Failed to extend offer: {str(e)}", "danger")

    return redirect(url_for('final_list'))

@app.route('/admin/final-list/reject/<int:applicant_id>', methods=['POST'])
def final_reject(applicant_id):
    applicant = Applicant1.query.get_or_404(applicant_id)
    try:
        applicant.final_status = 'Rejected'
        
        user_applied = UserApplied.query.filter_by(applicant_id=applicant_id).first()
        if user_applied:
            user_applied.status = 'Rejected'
        
        db.session.commit()
        send_rejection_email(applicant)

        flash(f'Final decision: {applicant.name} Rejected. Notification sent!', 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f"Failed to send rejection email: {str(e)}", "danger")

    return redirect(url_for('final_list'))


if __name__ == '__main__':
    app.run(debug=True)
