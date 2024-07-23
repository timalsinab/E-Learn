import unittest
from app import app, db, bcrypt, User, Course, Module

class BasicTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()

        with app.app_context():
            db.create_all()

            # Create a test user with hashed password
            hashed_password = bcrypt.generate_password_hash('password').decode('utf-8')
            self.test_user = User(username='testuser', email='testuser@example.com', password=hashed_password)
            db.session.add(self.test_user)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, email, password):
        return self.app.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_home_page(self):
        # Log in the test user
        self.login('testuser@example.com', 'password')

        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Home', response.data)

    def test_register(self):
        response = self.app.post('/register', data=dict(
            username='newuser',
            email='newuser@example.com',
            password='newpassword',
            confirm_password='newpassword'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your account has been created!', response.data)

    def test_login(self):
        response = self.login('testuser@example.com', 'password')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Home', response.data)

    def test_logout(self):
        self.login('testuser@example.com', 'password')
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_protected_route(self):
        response = self.app.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_add_course(self):
        self.login('testuser@example.com', 'password')
        response = self.app.post('/courses', data=dict(
            title='Test Course',
            description='This is a test course.'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Course added successfully!', response.data)

    def test_delete_course(self):
        self.login('testuser@example.com', 'password')
        with app.app_context():
            # Add a course to delete
            self.app.post('/courses', data=dict(
                title='Test Course',
                description='This is a test course.'
            ), follow_redirects=True)
            course = Course.query.filter_by(title='Test Course').first()
        response = self.app.post(f'/courses/{course.id}/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Course deleted successfully!', response.data)

    def test_add_module(self):
        self.login('testuser@example.com', 'password')
        with app.app_context():
            # Add a course to which we can add a module
            self.app.post('/courses', data=dict(
                title='Test Course',
                description='This is a test course.'
            ), follow_redirects=True)
            course = Course.query.filter_by(title='Test Course').first()
        response = self.app.post(f'/courses/{course.id}/modules', data=dict(
            title='Test Module',
            description='This is a test module.'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Module added successfully!', response.data)

    def test_delete_module(self):
        self.login('testuser@example.com', 'password')
        with app.app_context():
            # Add a course and module to delete
            self.app.post('/courses', data=dict(
                title='Test Course',
                description='This is a test course.'
            ), follow_redirects=True)
            course = Course.query.filter_by(title='Test Course').first()
            self.app.post(f'/courses/{course.id}/modules', data=dict(
                title='Test Module',
                description='This is a test module.'
            ), follow_redirects=True)
            module = Module.query.filter_by(title='Test Module').first()
        response = self.app.post(f'/modules/{module.id}/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Module deleted successfully!', response.data)

if __name__ == "__main__":
    unittest.main()
