from app import app
from database import db, SectionPhoto, DirectorInfo
import os

SECTION_UPLOAD_FOLDER = os.path.join("static", "uploads", "sections")
DIRECTOR_UPLOAD_FOLDER = os.path.join("static", "uploads", "director")

SECTIONS = ["home", "childrens_home", "rainbow_academy", "bible_school", "sunbeam_farm"]

with app.app_context():
    # Restore section photos
    if os.path.exists(SECTION_UPLOAD_FOLDER):
        for filename in os.listdir(SECTION_UPLOAD_FOLDER):
            matched_section = None
            for section in SECTIONS:
                if filename.startswith(section + "_"):
                    matched_section = section
                    break
            if matched_section:
                exists = SectionPhoto.query.filter_by(filename=filename).first()
                if not exists:
                    entry = SectionPhoto(section=matched_section, caption="", filename=filename)
                    db.session.add(entry)
                    print(f"Restored: {filename} -> {matched_section}")

    # Restore director photo (keeps the most recent one if multiple exist)
    if os.path.exists(DIRECTOR_UPLOAD_FOLDER):
        director_files = [f for f in os.listdir(DIRECTOR_UPLOAD_FOLDER) if f.startswith("director_")]
        if director_files:
            latest = sorted(director_files)[-1]
            director = DirectorInfo.query.first()
            if not director:
                director = DirectorInfo()
                db.session.add(director)
            director.photo_filename = latest
            print(f"Restored director photo: {latest}")

    db.session.commit()
    print("Done.")