from app import app
from database import db, BibleVerse

VERSES = [
    ("So do not fear, for I am with you; do not be dismayed, for I am your God. I will strengthen you and help you; I will uphold you with my righteous right hand.", "Isaiah 41:10"),
    ("For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, plans to give you hope and a future.", "Jeremiah 29:11"),
    ("Religion that God our Father accepts as pure and faultless is this: to look after orphans and widows in their distress.", "James 1:27"),
    ("A father to the fatherless, a defender of widows, is God in his holy dwelling.", "Psalm 68:5"),
    ("Let the little children come to me, and do not hinder them, for the kingdom of heaven belongs to such as these.", "Matthew 19:14"),
    ("Trust in the Lord with all your heart and lean not on your own understanding.", "Proverbs 3:5"),
    ("I can do all things through Christ who strengthens me.", "Philippians 4:13"),
    ("The Lord is close to the brokenhearted and saves those who are crushed in spirit.", "Psalm 34:18"),
    ("Cast all your anxiety on him because he cares for you.", "1 Peter 5:7"),
    ("And we know that in all things God works for the good of those who love him, who have been called according to his purpose.", "Romans 8:28"),
]

with app.app_context():
    if BibleVerse.query.count() == 0:
        for text, ref in VERSES:
            db.session.add(BibleVerse(text=text, reference=ref))
        db.session.commit()
        print("10 verses added.")
    else:
        print("Verses already exist, skipping.")