from flask import Flask
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'elavalasaiankithreddy@gmail.com'
app.config['MAIL_PASSWORD'] = 'jeww ydmg wlny vjvu'
app.config['MAIL_DEFAULT_SENDER'] = 'elavalasaiankithreddy@gmail.com'

mail = Mail(app)

@app.route('/')
def send_test_email():
    try:
        msg = Message("Test Email", recipients=["your_other_email@gmail.com"], body="This is a test.")
        mail.send(msg)
        return " Mail sent successfully!"
    except Exception as e:
        return f" Failed to send mail: {e}"

if __name__ == '__main__':
    app.run(debug=True)
