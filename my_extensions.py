# my_extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

db = SQLAlchemy()
mail = Mail()

print("✅ my_extensions.py loaded successfully")
