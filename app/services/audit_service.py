import logging
from flask import request, has_request_context
from app.extensions import db
from app.models import AuditLog

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def log_event(user_id, action: str, details: str = None, ip: str = None, status: str = "success"):
        """
        Log an auditable event to the database.
        
        Args:
            user_id: ID of the user performing the action (UUID or string)
            action: Short string describing action (e.g. 'user.login', 'config.update')
            details: Optional JSON string or text details
            ip: Optional IP address. If None, attempts to extract from Flask request.
            status: Outcome of the action ('success', 'failure').
        """
        try:
            if ip is None and has_request_context():
                # Extract IP from header (X-Forwarded-For) or remote addr
                if request.headers.getlist("X-Forwarded-For"):
                    ip = request.headers.getlist("X-Forwarded-For")[0]
                else:
                    ip = request.remote_addr

            # Convert user_id to UUID object if it's a string, ensuring compatibility with Uuid column
            if isinstance(user_id, str):
                import uuid
                try:
                    user_id = uuid.UUID(user_id)
                except ValueError:
                    # If invalid UUID string, keep as is or set None to avoid generic crash?
                    # But AuditLog user_id is nullable UUID. 
                    # If invalid, maybe log error but don't crash login.
                    logger.error(f"Invalid UUID string for audit log: {user_id}")
                    # If we don't return here, it will fail insert. 
                    # Best to fallback or skip user_id linkage.
                    user_id = None 

            # Append metadata to details if columns don't exist
            import json
            meta = {"ip": ip, "status": status}
            
            # Combine details
            final_details = details or ""
            try:
                if details and details.startswith("{"):
                     d_json = json.loads(details)
                     d_json.update(meta)
                     final_details = json.dumps(d_json)
                else:
                    final_details = (f"{details} " if details else "") + f"[Meta: {json.dumps(meta)}]"
            except:
                final_details = (f"{details} " if details else "") + f"[Meta: {json.dumps(meta)}]"

            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                details=final_details
            )
            db.session.add(log_entry)
            db.session.commit()
            logger.info(f"AuditLog: {action} ({status}) by {user_id} from {ip}")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            db.session.rollback()

    @staticmethod
    def log_admin_action(admin_user_id, action: str, target: str = None):
        details = f"Target: {target}" if target else None
        AuditService.log_event(admin_user_id, f"admin.{action}", details)
