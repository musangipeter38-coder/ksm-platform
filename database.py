from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="sponsor")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password):
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def is_admin(self):
        return self.role == "admin"


class Child(db.Model):
    __tablename__ = "children"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    story = db.Column(db.Text)
    photo_filename = db.Column(db.String(200))
    is_sponsored = db.Column(db.Boolean, default=False)
    monthly_need = db.Column(db.Integer, default=2000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.String(50), default="general")
    status = db.Column(db.String(20), default="pending")
    mpesa_receipt = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PrayerRequest(db.Model):
    __tablename__ = "prayer_requests"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="Anonymous")
    message = db.Column(db.Text, nullable=False)
    is_public = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SectionPhoto(db.Model):
    __tablename__ = "section_photos"

    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(50), nullable=False)
    caption = db.Column(db.Text)
    filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DirectorInfo(db.Model):
    __tablename__ = "director_info"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="Ellen Allison")
    role = db.Column(db.String(200), default="Founder & Missionary — Kenya Sunbeam Ministries")
    bio = db.Column(db.Text)
    photo_filename = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SiteSettings(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    logo_filename = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)