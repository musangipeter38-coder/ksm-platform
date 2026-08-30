import os
from dotenv import load_dotenv
load_dotenv()

import cloudinary
import cloudinary.uploader

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from mpesa import stk_push, normalize_phone

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-later-to-something-random")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///ksm.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["MPESA_ENV"] = os.environ.get("MPESA_ENV", "sandbox")
app.config["MPESA_CONSUMER_KEY"] = os.environ.get("MPESA_CONSUMER_KEY")
app.config["MPESA_CONSUMER_SECRET"] = os.environ.get("MPESA_CONSUMER_SECRET")
app.config["MPESA_SHORTCODE"] = os.environ.get("MPESA_SHORTCODE")
app.config["MPESA_PASSKEY"] = os.environ.get("MPESA_PASSKEY")
app.config["MPESA_CALLBACK_URL"] = os.environ.get("MPESA_CALLBACK_URL")

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

from database import db, bcrypt, User, Child, Donation, PrayerRequest, SectionPhoto, DirectorInfo, SiteSettings, BibleVerse
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


def upload_to_cloudinary(file, folder):
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    result = cloudinary.uploader.upload(file, folder=f"ksm/{folder}")
    return result.get("secure_url")


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
    verses = BibleVerse.query.order_by(BibleVerse.created_at.desc()).all()
    return render_template("about.html", verses=verses)

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


# ---------- Giving / M-Pesa ----------

@app.route("/give", methods=["GET", "POST"])
def give():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip() or "Anonymous"
        phone_raw = request.form.get("phone", "").strip()
        amount = request.form.get("amount", "").strip()
        purpose = request.form.get("purpose", "general")

        if not phone_raw or not amount:
            flash("Phone number and amount are required.")
            return redirect(url_for("give"))

        try:
            amount_int = int(float(amount))
        except ValueError:
            flash("Please enter a valid amount.")
            return redirect(url_for("give"))

        phone = normalize_phone(phone_raw)

        donation = Donation(
            full_name=full_name,
            phone=phone,
            amount=amount_int,
            purpose=purpose,
            status="pending",
        )
        db.session.add(donation)
        db.session.commit()

        try:
            result = stk_push(
                phone_number=phone,
                amount=amount_int,
                account_reference=f"KSM{donation.id}",
                description="KSM Donation",
            )
            checkout_id = result.get("CheckoutRequestID")
            donation.mpesa_receipt = checkout_id
            db.session.commit()

            if result.get("ResponseCode") == "0":
                flash("Check your phone — enter your M-Pesa PIN to complete the donation.")
            else:
                flash(f"Could not start payment: {result.get('errorMessage', 'Unknown error')}")
        except Exception as exc:
            donation.status = "failed"
            db.session.commit()
            flash(f"Payment could not be started: {exc}")

        return redirect(url_for("give"))

    return render_template("give.html")


@app.route("/mpesa/callback", methods=["POST"])
def mpesa_callback():
    data = request.get_json(force=True, silent=True) or {}
    result = data.get("Body", {}).get("stkCallback", {})
    checkout_id = result.get("CheckoutRequestID")
    result_code = result.get("ResultCode")

    donation = Donation.query.filter_by(mpesa_receipt=checkout_id).first()
    if donation:
        if result_code == 0:
            donation.status = "completed"
            items = result.get("CallbackMetadata", {}).get("Item", [])
            for item in items:
                if item.get("Name") == "MpesaReceiptNumber":
                    donation.mpesa_receipt = item.get("Value")
        else:
            donation.status = "failed"
        db.session.commit()

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


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
        verses = BibleVerse.query.order_by(BibleVerse.created_at.desc()).all()
        return render_template(
            "dashboard.html",
            children=children,
            pending_prayers=pending_prayers,
            donations=donations,
            section_photos=section_photos,
            section_labels=SECTION_LABELS,
            director=director,
            settings=settings,
            verses=verses,
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
    photo_url = upload_to_cloudinary(photo, "children")

    if name:
        child = Child(
            name=name,
            age=int(age) if age else None,
            story=story,
            photo_filename=photo_url,
            monthly_need=2000,
        )
        db.session.add(child)
        db.session.commit()
        flash(f"{name} added.")

    return redirect(url_for("dashboard"))


@app.route("/dashboard/edit-child/<int:child_id>", methods=["POST"])
@login_required
def edit_child(child_id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    child = Child.query.get_or_404(child_id)

    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    story = request.form.get("story", "").strip()
    monthly_need = request.form.get("monthly_need", "").strip()
    photo = request.files.get("photo")

    if name:
        child.name = name
    if age:
        child.age = int(age)
    child.story = story
    if monthly_need:
        child.monthly_need = int(monthly_need)

    photo_url = upload_to_cloudinary(photo, "children")
    if photo_url:
        child.photo_filename = photo_url

    db.session.commit()
    flash(f"{child.name} updated.")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/add-section-photo", methods=["POST"])
@login_required
def add_section_photo():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    section = request.form.get("section", "").strip()
    caption = request.form.get("caption", "").strip()
    photo = request.files.get("photo")
    photo_url = upload_to_cloudinary(photo, "sections")

    if section in SECTION_LABELS and photo_url:
        entry = SectionPhoto(section=section, caption=caption, filename=photo_url)
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

    photo_url = upload_to_cloudinary(photo, "director")
    if photo_url:
        director.photo_filename = photo_url

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

    photo_url = upload_to_cloudinary(photo, "site")
    if photo_url:
        settings.logo_filename = photo_url
        db.session.commit()
        flash("Logo updated.")
    else:
        flash("Please choose a valid image.")

    return redirect(url_for("dashboard"))


@app.route("/dashboard/add-verse", methods=["POST"])
@login_required
def add_verse():
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))

    text = request.form.get("text", "").strip()
    reference = request.form.get("reference", "").strip()

    if text and reference:
        verse = BibleVerse(text=text, reference=reference)
        db.session.add(verse)
        db.session.commit()
        flash("Bible verse added.")
    else:
        flash("Please fill in both the verse and its reference.")

    return redirect(url_for("dashboard"))


@app.route("/dashboard/delete-verse/<int:verse_id>", methods=["POST"])
@login_required
def delete_verse(verse_id):
    if not current_user.is_admin():
        return redirect(url_for("dashboard"))
    verse = BibleVerse.query.get_or_404(verse_id)
    db.session.delete(verse)
    db.session.commit()
    flash("Verse removed.")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)