from app import app
from database import db

with app.app_context():
    db.session.execute(db.text("ALTER TABLE section_photos ALTER COLUMN caption TYPE TEXT;"))
    db.session.commit()
    print("Caption column updated to TEXT — no more length limit.")