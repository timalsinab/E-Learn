import random
import string
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_bcrypt import Bcrypt
from flask_behind_proxy import FlaskBehindProxy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from forms import LoginForm, RegistrationForm
from models import db, User, Course, Module, Lesson
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant
import requests
import os
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '9c7f5ed4fee35fed7a039ddba384397f')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///../instance/site.db')

# Initialize Flask extensions
db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
proxied = FlaskBehindProxy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def generate_token(identity, room_name):
    token = AccessToken(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_API_KEY_SID'),
        os.getenv('TWILIO_API_KEY_SECRET'),
        identity=identity
    )
    video_grant = VideoGrant(room=room_name)
    token.add_grant(video_grant)
    return token.to_jwt()

@app.route("/")
@login_required
def home():
    return render_template('home.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/video_call/<room_name>")
@login_required
def video_call(room_name):
    token = generate_token(current_user.username, room_name)
    return render_template('video_call.html', token=token, room_name=room_name)

# Global matchmaking queue and temporary storage for room assignments
matchmaking_queue = []
room_assignments = {}

lock = threading.Lock()  # Lock to handle concurrent access to matchmaking_queue and room_assignments

@app.route("/join_queue")
@login_required
def join_queue():
    print("Join queue route accessed")

    # Clear room_name from session if present
    if 'room_name' in session:
        print(f"Clearing room_name from session for user {current_user.username}")
        session.pop('room_name', None)

    # Check if the user is already in the matchmaking queue
    with lock:
        if current_user.username in matchmaking_queue:
            print(f"User {current_user.username} is already in the queue")
            return jsonify({'matched': False, 'message': 'You are already in the queue'})

        # Add the user to the queue
        matchmaking_queue.append(current_user.username)
        print(f"User {current_user.username} added to queue. Current queue: {matchmaking_queue}")

        # Check if there are exactly two users in the queue
        if len(matchmaking_queue) >= 2:
            user1 = matchmaking_queue.pop(0)
            user2 = matchmaking_queue.pop(0)
            room_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            room_assignments[user1] = room_name
            room_assignments[user2] = room_name

            print(f"Room {room_name} created with users: {user1} and {user2}")
            print(f"Matchmaking queue: {matchmaking_queue}")

            # Return response with room details for the current user
            session['room_name'] = room_name
            return jsonify({'matched': True, 'room_name': room_name})

    # If not enough users, return waiting message
    print(f"User {current_user.username} waiting for a partner")
    return jsonify({'matched': False, 'message': 'You have been added to the queue and are waiting for a partner'})

@app.route("/check_match")
@login_required
def check_match():
    username = current_user.username
    if username in room_assignments:
        room_name = room_assignments[username]
        session['room_name'] = room_name
        return jsonify({'matched': True, 'room_name': room_name})
    return jsonify({'matched': False})

@app.route("/token")
@login_required
def token():
    room_name = session.get('room_name')
    if not room_name:
        return jsonify({'error': 'No room name found'}), 404
    token = generate_token(current_user.username, room_name)
    return jsonify({'token': token})

# JDoodle API endpoint
@app.route("/compile", methods=['POST'])
def compile_code():
    data = request.json
    payload = {
        'script': data['script'],
        'language': data['language'],
        'stdin': data['stdin'],
        'versionIndex': '0',
        'clientId': os.environ.get('JDOODLE_CLIENT_ID'),
        'clientSecret': os.environ.get('JDOODLE_CLIENT_SECRET')
    }
    response = requests.post('https://api.jdoodle.com/v1/execute', json=payload)
    return jsonify(response.json())

@app.route("/end_call", methods=['POST'])
@login_required
def end_call():
    # Perform any necessary cleanup here, such as updating the database or matchmaking queue
    session.pop('room_name', None)  # Clear the room name from the session
    return jsonify({'message': 'Call ended successfully'}), 200

# Mock Interview route
@app.route("/mock_interview")
@login_required
def mock_interview():
    return render_template('mock_interview.html')

@app.route('/courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_course = Course(title=title, description=description)
        db.session.add(new_course)
        db.session.commit()
        flash('Course added successfully!', 'success')
        return redirect(url_for('manage_courses'))

    courses = Course.query.all()
    return render_template('courses.html', courses=courses)

if __name__ == '__main__':
    app.run(debug=True)
