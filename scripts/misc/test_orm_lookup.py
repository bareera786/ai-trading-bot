
import sys
import os
import uuid
sys.path.append(os.getcwd())

from app import create_app
from app.models import User
from app.extensions import db

def test_lookup():
    app = create_app()
    with app.app_context():
        # Get the admin user first by username (which we know works)
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("CRITICAL: Admin user not found via username!")
            return

        print(f"Found admin user.")
        print(f"ID from DB model: {admin.id} (Type: {type(admin.id)})")
        
        raw_id_str = str(admin.id)
        uuid_obj = admin.id if isinstance(admin.id, uuid.UUID) else uuid.UUID(str(admin.id))
        
        print(f"Testing lookup with String: '{raw_id_str}'")
        res_str = User.query.filter_by(id=raw_id_str).first()
        print(f"Result via String: {'FOUND' if res_str else 'NOT FOUND'}")
        
        print(f"Testing lookup with UUID Object: {uuid_obj}")
        res_obj = User.query.filter_by(id=uuid_obj).first()
        print(f"Result via UUID Object: {'FOUND' if res_obj else 'NOT FOUND'}")
        
        # Test session.get
        print(f"Testing session.get with UUID Object...")
        res_get = db.session.get(User, uuid_obj)
        print(f"Result via session.get: {'FOUND' if res_get else 'NOT FOUND'}")

if __name__ == "__main__":
    test_lookup()
