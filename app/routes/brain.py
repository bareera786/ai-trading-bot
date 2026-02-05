from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import requires_role, RoleEnum, MLModel, TrainingJob, Strategy
from app.services import BrainService, ModelPromotionService
from app.extensions import db

brain_bp = Blueprint('brain', __name__, url_prefix='/api/brain')

# Phase 6: Register performance governance routes
from app.routes.brain_phase6 import register_phase6_routes
register_phase6_routes(brain_bp)

@brain_bp.before_request
def enforce_admin():
    # Allow DB Fix without login (Critical for fresh install healing)
    if request.endpoint == 'brain.fix_database_schema':
        return

    # Manual Auth Check for everything else
    if not current_user.is_authenticated:
        from flask_login import login_required
        # Trigger standard unauthorized behavior
        return login_required(lambda: None)()
        
    # Validates role if logged in
    if current_user.role != RoleEnum.ADMIN.value:
         return jsonify({"error": "Admin required"}), 403

@brain_bp.route('/fix_db', methods=['GET'])
def fix_database_schema():
    """Manually trigger DB schema fix for TrainingJob ID."""
    from sqlalchemy import text
    log = []
    
    try:
        log.append("🔧 Starting schema repair...")
        with db.engine.connect() as conn:
            # 1. Check for UUID Mismatch (Nuclear Fix)
            try:
                res = conn.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name='training_job' AND column_name='id'"))
                col_type = res.scalar()
                
                if col_type == 'uuid':
                    log.append("⚠️ Found UUID column (Mismatch). Dropping table...")
                    conn.execute(text("DROP TABLE training_job CASCADE"))
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
                    log.append("✅ Table recreated with Serial Integer ID")
            except Exception as e:
                log.append(f"⚠️ Mismatch check: {e}")

            # 2. Sequence (Standard Repair)
            try:
                conn.execute(text("CREATE SEQUENCE IF NOT EXISTS training_job_id_seq"))
                log.append("✅ Sequence training_job_id_seq ready")
            except Exception as e:
                # Ignore if sequence exists or handled by SERIAL above
                log.append(f"ℹ️ Sequence note: {e}")

            # 3. Default
            try:
                conn.execute(text("ALTER TABLE training_job ALTER COLUMN id SET DEFAULT nextval('training_job_id_seq')"))
                log.append("✅ ID default set to nextval")
            except Exception as e:
                 # Likely already set by SERIAL
                log.append(f"ℹ️ ID Default note: {e}")

            # 4. Ownership
            try:
                conn.execute(text("ALTER SEQUENCE training_job_id_seq OWNED BY training_job.id"))
                log.append("✅ Sequence ownership linked")
            except Exception as e:
                log.append(f"ℹ️ Ownership note: {e}")

            # 5. Sync
            try:
                result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM training_job"))
                max_id = result.scalar()
                conn.execute(text(f"SELECT setval('training_job_id_seq', {max_id + 1}, false)"))
                log.append(f"✅ Sequence synced to {max_id + 1}")
            except Exception as e:
                log.append(f"❌ Sync failed: {e}")
                
            conn.commit()
            
        return jsonify({"status": "success", "log": log})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "log": log}), 500

@brain_bp.route('/models/rollback', methods=['POST'])
def rollback_model():
    """Emergency rollback to previous model."""
    success, msg = BrainService.rollback_model()
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 400

@brain_bp.route('/models/<int:model_id>/status', methods=['POST'])
def set_model_status(model_id):
    """Set model lifecycle status (e.g. deprecated)."""
    data = request.json or {}
    status = data.get("status")
    if status not in ["shadow", "archived", "deprecated"]:
        return jsonify({"error": "Invalid status"}), 400
        
    success, msg = BrainService.set_model_status(model_id, status)
    if success:
         return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 400

@brain_bp.route('/status', methods=['GET'])
def get_status():
    """Get Brain heartbeat and active model info."""
    status = BrainService.get_brain_status()
    # Add rollback availability info
    from app.models import SystemSetting
    prev = SystemSetting.get_value("brain_previous_active_model_id")
    status["can_rollback"] = bool(prev)
    return jsonify(status)

@brain_bp.route('/train', methods=['POST'])
def spawn_training():
    """Spawn a background training job."""
    try:
        data = request.json or {}
        job_id = BrainService.start_training_job(data)
        return jsonify({"job_id": job_id, "status": "pending"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@brain_bp.route('/jobs/active', methods=['GET'])
def get_active_jobs():
    """Get all active and recent training jobs for status tracking."""
    from app.models import TrainingJob
    # Get jobs from last 24 hours, ordered by most recent
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    jobs = TrainingJob.query.filter(
        TrainingJob.created_at >= cutoff
    ).order_by(TrainingJob.created_at.desc()).limit(10).all()
    
    return jsonify({
        "active_jobs": [
            {
                "job_id": str(job.id),
                "status": job.status,
                "progress": job.progress or 0,
                "logs": job.logs or "",
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "result_metrics": job.result_metrics or {}
            }
            for job in jobs
        ]
    })


@brain_bp.route('/pause', methods=['POST'])
def pause_signals():
    """Emergency Kill Switch."""
    data = request.json or {}
    paused = data.get("paused", True)
    BrainService.pause_brain(paused)
    return jsonify({"status": "PAUSED" if paused else "ACTIVE"})

@brain_bp.route('/models', methods=['GET'])
def list_models():
    """List all models."""
    models = MLModel.query.order_by(MLModel.created_at.desc()).all()
    return jsonify([m.to_dict() for m in models])

@brain_bp.route('/models/activate/<int:model_id>', methods=['POST'])
def activate_model(model_id):
    """Atomic swap of active model with confirmation (Phase 6)."""
    from flask_login import current_user
    
    # Get admin user ID (use string representation for audit)
    admin_user_id = str(current_user.id) if current_user.is_authenticated else "system"
    
    # Use Phase 6 Promotion Service
    success, message = ModelPromotionService.execute_promotion(model_id, admin_user_id)
    
    if success:
        return jsonify({"status": "success", "active_model_id": model_id, "message": message})
    return jsonify({"error": message}), 400

@brain_bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    """Get recent audit logs."""
    from app.models import AuditLog
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "action": log.action,
            "timestamp": log.timestamp.isoformat(),
            "user_id": str(log.user_id) if log.user_id else "system",
            "details": log.details
        })
    return jsonify(results)

@brain_bp.route('/models/archive/<int:model_id>', methods=['POST'])
def archive_model(model_id):
    """Archive a model."""
    success = BrainService.archive_model(model_id)
    if success:
        return jsonify({"status": "success", "archived_model_id": model_id})
    return jsonify({"error": "Model not found or currently active"}), 400

@brain_bp.route('/train/status/<job_id>', methods=['GET'])
def get_training_status(job_id):
    """Get status of a specific training job."""
    job = TrainingJob.query.get(job_id)
    if not job:
        # Try casting to int if string lookup failed
        try:
             job = TrainingJob.query.get(int(job_id))
        except:
             pass
             
    if not job:
        return jsonify({"error": "Job not found"}), 404
        
    # Return full logs + progress
    return jsonify({
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "logs": job.logs,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "result_metrics": job.result_metrics
    })

@brain_bp.route('/models/deactivate/<int:model_id>', methods=['POST'])
def deactivate_model(model_id):
    """Force deactivate (archive) an active model."""
    success, msg = BrainService.deactivate_model(model_id)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 400

@brain_bp.route('/models/<int:model_id>', methods=['DELETE'])
def delete_model_route(model_id):
    """Permanently delete a model."""
    success, msg = BrainService.delete_model(model_id)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"error": msg}), 400

@brain_bp.route('/shadow/stats', methods=['GET'])
def get_shadow_stats():
    """Get Shadow vs Active comparison stats."""
    from app.services.shadow_service import ShadowService
    return jsonify(ShadowService.get_comparison_stats())

@brain_bp.route('/simulate', methods=['POST'])
def run_simulation():
    """Run a historical backtest."""
    data = request.json or {}
    result = BrainService.run_backtest(data)
    return jsonify(result)

# --- Phase 5: Strategy Management ---

@brain_bp.route('/strategies', methods=['GET'])
def list_strategies():
    """List all strategies."""
    strats = Strategy.query.all()
    return jsonify([s.to_dict() for s in strats])

@brain_bp.route('/strategies', methods=['POST'])
def create_strategy():
    """Create a new strategy."""
    data = request.json or {}
    name = data.get("name")
    if not name: return jsonify({"error": "Name required"}), 400
    
    if Strategy.query.filter_by(name=name).first():
        return jsonify({"error": "Strategy exists"}), 400
        
    s = Strategy(
        name=name,
        type=data.get("type", "directional"),
        risk_profile=data.get("risk_profile", "balanced")
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict())

@brain_bp.route('/strategies/<int:sid>/allocation', methods=['POST'])
def update_allocation(sid):
    """Update capital allocation weight."""
    s = Strategy.query.get(sid)
    if not s: return jsonify({"error": "Not found"}), 404
    
    data = request.json or {}
    try:
        weight = float(data.get("weight", 0.0))
        s.capital_weight = weight
        db.session.commit()
        return jsonify(s.to_dict())
    except:
        return jsonify({"error": "Invalid weight"}), 400

@brain_bp.route('/strategies/<int:sid>/resume', methods=['POST'])
def resume_strategy(sid):
    """Resume a paused strategy."""
    BrainService.resume_strategy(sid)
    return jsonify({"status": "resumed"})

