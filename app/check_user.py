from app import create_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

app = create_app()

with app.app_context():
    # Update password using raw SQL to avoid UUID issues
    new_hash = generate_password_hash("admin123")
    db.session.execute(db.text("UPDATE \"user\" SET password_hash = :hash WHERE username = 'admin'"), {"hash": new_hash})
    db.session.commit()
    print(f"Updated password hash to: {new_hash}")

    # Verify
    result = db.session.execute(db.text("SELECT password_hash FROM \"user\" WHERE username = 'admin'")).fetchone()
    if result:
        check = check_password_hash(result[0], "admin123")
        print(f"Password check after update: {check}")
    else:
        print("User not found")