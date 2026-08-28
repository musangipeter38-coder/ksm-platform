from app import app
from database import db, User, Child

with app.app_context():
    existing_admin = User.query.filter_by(email="peter@ksm.local").first()
    if not existing_admin:
        admin = User(
            full_name="Peter Nzoka Musangi",
            email="peter@ksm.local",
            role="admin"
        )
        admin.set_password("changeme123")
        db.session.add(admin)
        print("Admin account created.")
    else:
        print("Admin account already exists.")

    if Child.query.count() == 0:
        children = [
            Child(name="Grace", age=8, story="Loves singing and helping care for younger children.", monthly_need=2000),
            Child(name="Samuel", age=11, story="Enjoys football and is doing well at Rainbow Academy.", monthly_need=2000),
            Child(name="Faith", age=6, story="Recently joined the home and is settling in well.", monthly_need=2000),
        ]
        db.session.add_all(children)
        print("Sample children added.")
    else:
        print("Children already exist, skipping.")

    db.session.commit()
    print("Done.")