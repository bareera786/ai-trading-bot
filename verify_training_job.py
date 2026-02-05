import os
import sys
from datetime import datetime

# Force development env
os.environ["FLASK_ENV"] = "development"
os.environ["FLASK_DEBUG"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///test_verification.db"

try:
    from app import create_app
    from app.extensions import db
    from app.models import TrainingJob
except ImportError as e:
    print(f"❌ Setup Error: {e}")
    print("Ensure you are running in the virtual environment with 'source .venv/bin/activate'")
    sys.exit(1)

def verify_fix():
    print("🚀 Starting Headless Verification...")
    
    app = create_app()
    with app.app_context():
        # 1. Reset Test DB
        print("🔄 recreating temporary database...")
        db.drop_all()
        db.create_all()
        
        # 2. Verify Schema by Insertion
        print("🧪 Testing TrainingJob creation...")
        try:
            job = TrainingJob(
                status="pending",
                logs="Test log",
                result_metrics={"test": True},
                created_at=datetime.utcnow()
            )
            db.session.add(job)
            db.session.commit()
            
            # 3. Retrieve and Check
            saved_job = db.session.get(TrainingJob, job.id)
            if saved_job and saved_job.created_at:
                print(f"✅ SUCCESS: TrainingJob created with ID {saved_job.id}")
                print(f"   created_at: {saved_job.created_at}")
                print(f"   completed_at: {saved_job.completed_at}")
            else:
                print("❌ FAILURE: Job saved but created_at is missing!")
                
        except Exception as e:
            print(f"❌ FAILURE: Database operation failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify_fix()
    # Cleanup
    if os.path.exists("test_verification.db"):
        os.remove("test_verification.db")
