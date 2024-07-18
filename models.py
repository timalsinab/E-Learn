from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy() 
# Define your models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return True  # Replace with actual logic as per your application

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"
