import os
import sys
import sqlalchemy
from sqlalchemy import text

# Add parent dir to path to allow imports if needed (though we use raw sql here)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_training_job_schema():
    print("🔧 FORCE DB FIX: Starting schema repair for TrainingJob...")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL not set")
        sys.exit(1)

    try:
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as conn:
            print("   Connected to database.")
            
            # 1. Check for UUID mismatch (The Root Cause)
            print("   1. Checking for Schema Mismatch (UUID vs Integer)...")
            try:
                # Check column type
                res = conn.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name='training_job' AND column_name='id'"))
                col_type = res.scalar()
                print(f"      Current ID type: {col_type}")
                
                if col_type == 'uuid':
                    print("      ⚠️ MISMATCH DETECTED: DB has UUID, Code wants Integer.")
                    print("      🧨 PROTOCOL: Dropping incompatible table to allow clean rebuild...")
                    conn.execute(text("DROP TABLE training_job CASCADE"))
                    print("      ✅ Table dropped. Recreating from model...")
                    
                    # Recreate logic handled by next step or app/bootstrap
                    # We can force creation here if we import db
                    # But assuming db.create_all() runs after this or we do it manually:
                    conn.execute(text("""
                        CREATE TABLE training_job (
                            id SERIAL PRIMARY KEY,
                            status VARCHAR(20),
                            progress INTEGER,
                            logs TEXT,
                            result_metrics JSON,
                            created_at TIMESTAMP DEFAULT NOW(),
                            completed_at TIMESTAMP
                        )
                    """))
                    print("      ✅ Table recreated with SERIAL ID.")
            except Exception as e:
                print(f"      ⚠️ Mismatch check failed: {e}")

            # 2. Sequence (If we didn't just recreate it)
            print("   2. Forcing ID column default...")
            try:
                conn.execute(text("ALTER TABLE training_job ALTER COLUMN id SET DEFAULT nextval('training_job_id_seq')"))
                print("      ✅ ID default set to nextval('training_job_id_seq').")
            except Exception as e:
                print(f"      ⚠️ ID default set note: {e}")

            # 3. Link Sequence
            print("   3. Linking sequence to column...")
            try:
                conn.execute(text("ALTER SEQUENCE training_job_id_seq OWNED BY training_job.id"))
                print("      ✅ Sequence owned by training_job.id.")
            except Exception as e:
                print(f"      ⚠️ Sequence ownership note: {e}")

            # 4. Sync Sequence Value
            print("   4. Syncing sequence value...")
            try:
                # Get max ID or 0
                result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM training_job"))
                max_id = result.scalar()
                print(f"      Current Max ID: {max_id}")
                
                # Set sequence to max_id + 1
                conn.execute(text(f"SELECT setval('training_job_id_seq', {max_id + 1}, false)"))
                print(f"      ✅ Sequence set to {max_id + 1}")
            except Exception as e:
                print(f"      ❌ Sequence sync failed: {e}")

            # 5. Fix Missing Columns (Comprehensive)
            print("   5. Checking field columns...")
            for table, col, dtype in [
                ("training_job", "created_at", "TIMESTAMP DEFAULT NOW()"),
                ("training_job", "completed_at", "TIMESTAMP"),
                ("training_job", "result_metrics", "JSON DEFAULT '{}'::json"),
                ("ml_model", "symbol", "VARCHAR(20)"),
                ("ml_model", "file_path", "VARCHAR(255)"),
                ("ml_model", "auto_paused", "BOOLEAN DEFAULT FALSE"),
                ("ml_model", "auto_pause_reason", "TEXT"),
                ("ml_model", "health_state", "VARCHAR(20) DEFAULT 'HEALTHY'"),
                ("ml_model", "health_score", "FLOAT DEFAULT 1.0"),
                ("ml_model", "last_health_check", "TIMESTAMP"),
                ("shadow_prediction", "model_id", "INTEGER")
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {dtype}"))
                    print(f"      Checked/Added {table}.{col}")
                except Exception as e:
                    print(f"      ⚠️ Failed check for {table}.{col}: {e}")
            
            conn.commit()
            print("✅ FORCE DB FIX: Complete. Schema should be consistent now.")

    except Exception as e:
        print(f"❌ FORCE DB FIX FAILED: {e}")
        # We don't exit 1 here because we don't want to crash the container loop if DB is temporarily unreachable
        # but in this case, it helps debugging.
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_training_job_schema()
