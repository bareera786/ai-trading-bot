import unittest
import json
from ai_ml_auto_bot_final import app, db, User

class UserManagementTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        with app.app_context():
            db.drop_all()
            db.create_all()
            # Create admin user
            admin = User(username='admin', email='admin@example.com', is_admin=True)
            admin.set_password('adminpass')
            db.session.add(admin)
            # Create normal user
            user = User(username='user1', email='user1@example.com', is_admin=False)
            user.set_password('userpass')
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_admin_login_logout(self):
        response = self.login('admin', 'adminpass')
        # Should redirect to dashboard (status code 200)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<title>', response.data)  # HTML page
        response = self.logout()
        # Should redirect to login page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<form', response.data)

    def test_user_login_logout(self):
        response = self.login('user1', 'userpass')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<title>', response.data)
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<form', response.data)

    def test_admin_add_delete_user(self):
        self.login('admin', 'adminpass')
        # Add user
        response = self.app.post('/api/users',
            data=json.dumps({
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'newpass',
                'is_admin': False,
                'is_active': True
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'newuser')
        # Delete user
        response = self.app.delete('/api/users/newuser')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('deleted successfully', data['message'])

if __name__ == '__main__':
    unittest.main()
