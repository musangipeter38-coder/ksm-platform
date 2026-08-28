import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-later-to-something-random")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///ksm.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

CHILD_UPLOAD_FOLDER = os.path.join("static", "uploads", "children")
SECTION_UPLOAD_FOLDER = os.path.join("static", "uploads", "sections")
DIRECTOR_UPLOAD_FOLDER = os.path.join("static", "uploads", "director")
SITE_UPLOAD_FOLDER = os.path.join("static", "uploads", "site")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["CHILD_UPLOAD_FOLDER"] = CHILD_UPLOAD_FOLDER
app.config["SECTION_UPLOAD_FOLDER"] = SECTION_UPLOAD_FOLDER
app.config["DIRECTOR_UPLOAD_FOLDER"] = DIRECTOR_UPLOAD_FOLDER
app.config["SITE_UPLOAD_FOLDER"] = SITE_UPLOAD_FOLDER

from database import db, bcrypt, User, Child, Donation, PrayerRequest, SectionPhoto, DirectorInfo, SiteSettings
db.init_app(app)
bcrypt.init_app(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_site_settings():
    settings = SiteSettings.query.first()
    return dict(site_settings=settings)


SECTION_LABELS = {
    "home": "Home Page",
    "childrens_home": "Children's Home",
    "rainbow_academy": "Rainbow Academy",
    "bible_school": "Bible School & Church",
    "sunbeam_farm": "Sunbeam Farm",
}


# ---------- Public pages ----------

@app.route("/")
def home():
    photos = SectionPhoto.query.filter_by(section="home").order_by(SectionPhoto.created_at.desc()).all()
    director = DirectorInfo.query.first()
    return render_template("index.html", photos=photos, director=director)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/about/childrens-home")
def childrens_home():
    photos = SectionPhoto.query.filter_by(section="childrens_home").order_by(SectionPhoto.created_at.desc()).all()
    return render_template("childrens_home.html", photos=photos)

@app.route("/about/rainbow-academy")
def rainbow_academy():
    photos = SectionPhoto.query.filter_by(section="rainbow_academy").order_by(SectionPhoto.created_at.desc()).all()
    return render_template("rainbow_academy.html", photos=photos)

@app.route("/about/bible-school")
def bible_school():
    photos = SectionPhoto.query.filter_by(section="bible_school").order_by(SectionPhoto.created_at.desc()).all()
    return render_template("bible_school.html", photos=photos)

@app.route("/about/sunbeam-farm")
def sunbeam_farm():
    photos = SectionPhoto.query.filter_by(section="sunbeam_farm").order_by(SectionPhoto.created_at.desc()).all()
    return render_template("sunbeam_farm.html", photos=photos)

@app.route("/gallery/<section>")
def gallery(section):
    if section not in SECTION_LABELS:
        return redirect(url_for("home"))
    photos = SectionPhoto.query.filter_by(section=section).order_by(SectionPhoto.created_at.desc()).all()
    return render_template("gallery.html", photos=photos, section_label=SECTION_LABELS[section])

@app.route("/sponsorship")
def sponsorship():
    children = Child.query.all()
    return render_template("sponsorship.html", children=children)


@app.route("/prayer", methods=["GET", "POST"])
def prayer():
    if request.method == "POST":
        name = request.form.get("name", "").strip() or "Anonymous"
        message = request.form.get("message", "").strip()
        is_public = bool(request.form.get("is_public"))

        if message:
            req = PrayerRequest(
                name=name,
                message=message,
                is_public=is_public,
                is_approved=False,
            )
            db.session.add(req)
            db.session.commit()
            flash("Your prayer request has been submitted and will appear once reviewed.")
        else:
            flash("Please write a prayer request before submitting.")

        return redirect(url_for("prayer"))

    prayers = PrayerRequest.query.filter_by(
        is_approved=True, is_public=True
    ).order_by(PrayerRequest.created_at.desc()).all()

    return render_template("prayer.html", prayers=prayers)


@app.route("/give", methods=["GET", "POST"])
def give():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip() or "Anonymous"
        phone = request.form.get("phone", "").strip()
        amount = request.form.get("amount", "").strip()
        purpose = request.form.get("purpose", "general")

        if not phone or not amount:
            flash("Phone number and amount are required.")
            return redirect(url_for("give"))

        try:
            amount_int = int(float(amount))
        except ValueError:
            flash("Please enter a valid amount.")
            return redirect(url_for("give"))

        donation = Donation(
            full_name=full_name,
            phone=phone,
            amount=amount_int,
            purpose=purpose,
            status="pending",
        )
        db.session.add(donation)
        db.session.commit()

        flash("Thank you! Your donation has been recorded. (M-Pesa payment will be connected next.)")
        return redirect(url_for("give"))

    return render_template("give.html")


# ---------- Auth ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not full_name or not email or not password:
            flash("Name, email, and password are required.")
            return redirect(url_for("register"))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with this email already exists. Try logging in instead.")
            return redirect(url_for("register"))

        user = User(full_name=full_name, email=email, phone=phone, role="sponsor")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Welcome to Kenya Sunbeam Ministries!")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


# ---------- Dashboard ----------

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin():
        children = Child.query.all()
        pending_prayers = PrayerRequest.query.filter_by(is_approved=False).all()
        donations = Donation.query.order_by(Donation.created_at.desc()).limit(15).all()
        section_photos = SectionPhoto.query.order_by(SectionPhoto.created_at.desc()).all()
        director = DirectorInfo.query.first()
        settings = SiteSettings.query.first()
        return render_template(
            "dashboard.html",
            children=children,
            pending_prayers=pending_prayers,
            donations=donations,
            section_photos=section_photos,
            section_labels=SECTION_LABELS,
            director=director,
            settings=settings,
        )
    return render_template("dashboard.html")


@app.route("/dashboard/approve-prayer/<int:prayer_id>", methods=["POST"])
@login_required
def approve_prayer(prayer_id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    req = PrayerRequest.query.get_or_404(prayer_id)
    req.is_approved = True
    db.session.commit()
    flash("Prayer request approved.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/delete-prayer/<int:prayer_id>", methods=["POST"])
@login_required
def delete_prayer(prayer_id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    req = PrayerRequest.query.get_or_404(prayer_id)
    db.session.delete(req)
    db.session.commit()
    flash("Prayer request deleted.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/add-child", methods=["POST"])
@login_required
def add_child():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    story = request.form.get("story", "").strip()
    photo = request.files.get("photo")

    photo_filename = None
    if photo and photo.filename and allowed_file(photo.filename):
        photo_filename = secure_filename(f"{name}_{photo.filename}".replace(" ", "_"))
        os.makedirs(app.config["CHILD_UPLOAD_FOLDER"], exist_ok=True)
        photo.save(os.path.join(app.config["CHILD_UPLOAD_FOLDER"], photo_filename))

    if name:
        child = Child(
            name=name,
            age=int(age) if age else None,
            story=story,
            photo_filename=photo_filename,
            monthly_need=2000,
        )
        db.session.add(child)
        db.session.commit()
        flash(f"{name} added.")

    return redirect(url_for("dashboard"))


@app.route("/dashboard/add-section-photo", methods=["POST"])
@login_required
def add_section_photo():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    section = request.form.get("section", "").strip()
    caption = request.form.get("caption", "").strip()
    photo = request.files.get("photo")

    if section in SECTION_LABELS and photo and photo.filename and allowed_file(photo.filename):
        filename = secure_filename(f"{section}_{photo.filename}".replace(" ", "_"))
        os.makedirs(app.config["SECTION_UPLOAD_FOLDER"], exist_ok=True)
        photo.save(os.path.join(app.config["SECTION_UPLOAD_FOLDER"], filename))

        entry = SectionPhoto(section=section, caption=caption, filename=filename)
        db.session.add(entry)
        db.session.commit()
        flash("Photo uploaded.")
    else:
        flash("Please choose a section and a valid photo.")

    return redirect(url_for("dashboard"))


@app.route("/dashboard/edit-caption/<int:photo_id>", methods=["POST"])
@login_required
def edit_caption(photo_id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    photo = SectionPhoto.query.get_or_404(photo_id)
    photo.caption = request.form.get("caption", "").strip()
    db.session.commit()
    flash("Caption updated.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/delete-section-photo/<int:photo_id>", methods=["POST"])
@login_required
def delete_section_photo(photo_id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    photo = SectionPhoto.query.get_or_404(photo_id)
    db.session.delete(photo)
    db.session.commit()
    flash("Photo removed.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/update-director", methods=["POST"])
@login_required
def update_director():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()
    bio = request.form.get("bio", "").strip()
    photo = request.files.get("photo")

    director = DirectorInfo.query.first()
    if not director:
        director = DirectorInfo()
        db.session.add(director)

    if name:
        director.name = name
    if role:
        director.role = role
    director.bio = bio

    if photo and photo.filename and allowed_file(photo.filename):
        filename = secure_filename(f"director_{photo.filename}".replace(" ", "_"))
        os.makedirs(app.config["DIRECTOR_UPLOAD_FOLDER"], exist_ok=True)
        photo.save(os.path.join(app.config["DIRECTOR_UPLOAD_FOLDER"], filename))
        director.photo_filename = filename

    db.session.commit()
    flash("Director info updated.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/update-logo", methods=["POST"])
@login_required
def update_logo():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    photo = request.files.get("logo")
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)

    if photo and photo.filename and allowed_file(photo.filename):
        filename = secure_filename(f"logo_{photo.filename}".replace(" ", "_"))
        os.makedirs(app.config["SITE_UPLOAD_FOLDER"], exist_ok=True)
        photo.save(os.path.join(app.config["SITE_UPLOAD_FOLDER"], filename))
        settings.logo_filename = filename
        db.session.commit()
        flash("Logo updated.")
    else:
        flash("Please choose a valid image.")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)