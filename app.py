import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ksm-super-secret-key-2026-change-later')

# Configure database
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///ksm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Helper function for image uploads
def upload_image_to_cloudinary(file_storage, folder_name):
    if not file_storage or file_storage.filename == '':
        return None
    try:
        response = cloudinary.uploader.upload(file_storage, folder=f"ksm/{folder_name}")
        return response.get('secure_url')
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None

# Import models
from database import User, Child, Donation, PrayerRequest, SectionPhoto, DirectorInfo, SiteSettings

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_site_settings():
    settings = SiteSettings.query.first()
    return dict(site_settings=settings)

# Public Routes
@app.route('/')
def home():
    photos = SectionPhoto.query.filter_by(section='home').order_by(SectionPhoto.id.desc()).all()
    director = DirectorInfo.query.first()
    return render_template('index.html', photos=photos, director=director)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/childrens-home')
def childrens_home():
    photos = SectionPhoto.query.filter_by(section='childrens_home').order_by(SectionPhoto.id.desc()).all()
    return render_template('childrens_home.html', photos=photos)

@app.route('/rainbow-academy')
def rainbow_academy():
    photos = SectionPhoto.query.filter_by(section='rainbow_academy').order_by(SectionPhoto.id.desc()).all()
    return render_template('rainbow_academy.html', photos=photos)

@app.route('/bible-school')
def bible_school():
    photos = SectionPhoto.query.filter_by(section='bible_school').order_by(SectionPhoto.id.desc()).all()
    return render_template('bible_school.html', photos=photos)

@app.route('/sunbeam-farm')
def sunbeam_farm():
    photos = SectionPhoto.query.filter_by(section='sunbeam_farm').order_by(SectionPhoto.id.desc()).all()
    return render_template('sunbeam_farm.html', photos=photos)

@app.route('/sponsorship')
def sponsorship():
    children = Child.query.all()
    return render_template('sponsorship.html', children=children)

@app.route('/prayer', methods=['GET', 'POST'])
def prayer():
    if request.method == 'POST':
        name = request.form.get('name', 'Anonymous')
        request_text = request.form.get('request_text')
        is_private = True if request.form.get('is_private') else False
        
        if request_text:
            new_prayer = PrayerRequest(
                name=name,
                request_text=request_text,
                is_private=is_private,
                status='pending'
            )
            db.session.add(new_prayer)
            db.session.commit()
            flash('Your prayer request has been submitted for review. Thank you!', 'success')
            return redirect(url_for('prayer'))
            
    prayers = PrayerRequest.query.filter_by(status='approved', is_private=False).order_by(PrayerRequest.id.desc()).all()
    return render_template('prayer.html', prayers=prayers)

@app.route('/give', methods=['GET', 'POST'])
def give():
    if request.method == 'POST':
        donor_name = request.form.get('donor_name')
        donor_email = request.form.get('donor_email')
        amount = request.form.get('amount')
        phone = request.form.get('phone')
        
        new_donation = Donation(
            donor_name=donor_name,
            donor_email=donor_email,
            amount=amount,
            phone=phone,
            status='pending'
        )
        db.session.add(new_donation)
        db.session.commit()
        flash('Thank you for initiating your donation!', 'success')
        return redirect(url_for('give'))
        
    return render_template('give.html')

@app.route('/gallery/<section>')
def gallery(section):
    valid_sections = ['home', 'childrens_home', 'rainbow_academy', 'bible_school', 'sunbeam_farm']
    if section not in valid_sections:
        flash('Invalid section.', 'danger')
        return redirect(url_for('home'))
    
    photos = SectionPhoto.query.filter_by(section=section).order_by(SectionPhoto.id.desc()).all()
    return render_template('gallery.html', section=section, photos=photos)

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
            
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password_hash=hashed_pw, name=name, role='sponsor')
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

# Admin Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Admin access required.', 'danger')
        return redirect(url_for('home'))
        
    children = Child.query.all()
    prayers = PrayerRequest.query.order_by(PrayerRequest.id.desc()).all()
    donations = Donation.query.order_by(Donation.id.desc()).all()
    photos = SectionPhoto.query.order_by(SectionPhoto.id.desc()).all()
    director = DirectorInfo.query.first()
    
    return render_template(
        'dashboard.html', 
        children=children, 
        prayers=prayers, 
        donations=donations, 
        photos=photos, 
        director=director
    )

# Admin Action Routes
@app.route('/admin/add-child', methods=['POST'])
@login_required
def add_child():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    name = request.form.get('name')
    age = request.form.get('age')
    story = request.form.get('story')
    file = request.files.get('photo')
    
    photo_url = upload_image_to_cloudinary(file, 'children')
    
    new_child = Child(name=name, age=age, story=story, photo_filename=photo_url)
    db.session.add(new_child)
    db.session.commit()
    flash('Child record added.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/add-photo', methods=['POST'])
@login_required
def add_photo():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    section = request.form.get('section')
    caption = request.form.get('caption')
    file = request.files.get('photo')
    
    photo_url = upload_image_to_cloudinary(file, 'sections')
    
    if photo_url:
        new_photo = SectionPhoto(section=section, filename=photo_url, caption=caption)
        db.session.add(new_photo)
        db.session.commit()
        flash('Photo uploaded successfully.', 'success')
    else:
        flash('Failed to upload photo.', 'danger')
        
    return redirect(url_for('dashboard'))

@app.route('/admin/delete-photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    photo = SectionPhoto.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/admin/update-caption/<int:photo_id>', methods=['POST'])
@login_required
def update_caption(photo_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    photo = SectionPhoto.query.get_or_404(photo_id)
    photo.caption = request.form.get('caption')
    db.session.commit()
    flash('Caption updated.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/update-director', methods=['POST'])
@login_required
def update_director():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    director = DirectorInfo.query.first()
    if not director:
        director = DirectorInfo()
        db.session.add(director)
        
    director.name = request.form.get('name')
    director.role = request.form.get('role')
    director.bio = request.form.get('bio')
    
    file = request.files.get('photo')
    photo_url = upload_image_to_cloudinary(file, 'director')
    if photo_url:
        director.photo_filename = photo_url
        
    db.session.commit()
    flash('Director details updated.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/update-logo', methods=['POST'])
@login_required
def update_logo():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        
    file = request.files.get('logo')
    logo_url = upload_image_to_cloudinary(file, 'site')
    if logo_url:
        settings.logo_filename = logo_url
        db.session.commit()
        flash('Site logo updated.', 'success')
    else:
        flash('No file selected or upload failed.', 'danger')
        
    return redirect(url_for('dashboard'))

@app.route('/admin/prayer/<int:prayer_id>/<action>', methods=['POST'])
@login_required
def moderate_prayer(prayer_id, action):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
        
    prayer = PrayerRequest.query.get_or_404(prayer_id)
    if action == 'approve':
        prayer.status = 'approved'
    elif action == 'delete':
        db.session.delete(prayer)
    db.session.commit()
    flash('Prayer request updated.', 'info')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)