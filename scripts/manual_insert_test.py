import sys
import os
import datetime

# Ensure proper path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force a local SQLite DB for this test if standard config fails, or use existing config
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///local_test.db"
    print("⚠️ No DATABASE_URL found. Using local SQLite: sqlite:///local_test.db")

from app import create_app, db
from app.models import TrainingJob

def test_insert():
    print("🚀 Starting Manual Insert Verification...")
    app = create_app()
    with app.app_context():
        # Ensure fresh tables for this test
        print(f"📂 Using Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        try:
            db.create_all()
        except Exception as e:
            print(f"⚠️ Create all warning: {e}")

        # Basic Insert
        print("🧪 Attempting Insert...")
        try:
            job = TrainingJob(
                status="pending",
                progress=0,
                logs="Test job insert",
                result_metrics={},
                created_at=datetime.datetime.utcnow(),
                completed_at=None,
            )
            db.session.add(job)
            db.session.commit()
            
            if job.id:
                print(f"✅ SUCCESS: Inserted job ID: {job.id}")
            else:
                print("❌ FAILURE: Job inserted but ID is None/Empty")
                
        except Exception as e:
            print(f"❌ FAILURE: Database Insert Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_insert()
