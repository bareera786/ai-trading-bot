import unittest
from app import create_app, db
from app.models import User, AuditLog

class AuditLogTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

            # Create a test admin user
            admin_user = User(username='admin', email='admin@test.com', password_hash='hashed', role='ADMIN')
            db.session.add(admin_user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_audit_log_creation(self):
        with self.app.app_context():
            # Create an audit log entry
            log = AuditLog(user_id=1, action='TEST_ACTION', details='Test details')
            db.session.add(log)
            db.session.commit()

            # Verify the log was created
            logs = AuditLog.query.all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].action, 'TEST_ACTION')

    def test_get_audit_logs(self):
        with self.app.app_context():
            # Add a test log
            log = AuditLog(user_id=1, action='LOGIN', details='User logged in')
            db.session.add(log)
            db.session.commit()

            # Authenticate as admin and fetch logs
            response = self.client.get('/audit/logs', headers={'Authorization': 'Bearer <admin_token>'})
            self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()