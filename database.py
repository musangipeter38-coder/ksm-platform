from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "user"
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default="sponsor")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Child(db.Model):
    __tablename__ = "child"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    story = db.Column(db.Text, nullable=False)
    photo_filename = db.Column(db.String(200))
    is_sponsored = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Donation(db.Model):
    __tablename__ = "donation"
    
    id = db.Column(db.Integer, primary_key=True)
    donor_name = db.Column(db.String(100), nullable=False)
    donor_email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default="pending")
    mpesa_receipt = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PrayerRequest(db.Model):
    __tablename__ = "prayer_request"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Anonymous")
    request_text = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SectionPhoto(db.Model):
    __tablename__ = "section_photo"
    
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DirectorInfo(db.Model):
    __tablename__ = "director_info"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Ellen Allison")
    role = db.Column(db.String(200), default="Founder & Missionary — Kenya Sunbeam Ministries")
    bio = db.Column(db.Text)
    photo_filename = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SiteSettings(db.Model):
    __tablename__ = "site_settings"
    
    id = db.Column(db.Integer, primary_key=True)
    logo_filename = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)