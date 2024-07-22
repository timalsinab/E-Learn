from flask import Flask, render_template, redirect, url_for, flash, request,jsonify

from flask_bcrypt import Bcrypt
from flask_behind_proxy import FlaskBehindProxy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
from flask_migrate import Migrate
from forms import LoginForm, RegistrationForm
import os
from bot import get_user_response
from models import db , User, Course, Module, Lesson


app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = '9c7f5ed4fee35fed7a039ddba384397f'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/site.db'
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


@app.route("/")
def landing():
    return render_template('landing.html')

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


@app.route('/courses', methods=['GET', 'POST'])
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

@app.route('/courses/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get(course_id)
    if course:
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully!', 'success')
    return redirect(url_for('manage_courses'))

@app.route('/courses/<int:course_id>/modules', methods=['GET', 'POST'])
def manage_modules(course_id):
    course = Course.query.get(course_id)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_module = Module(title=title, description=description, course_id=course_id)
        db.session.add(new_module)
        db.session.commit()
        flash('Module added successfully!', 'success')
        return redirect(url_for('manage_modules', course_id=course_id))
    
    modules = Module.query.filter_by(course_id=course_id).all()
    return render_template('modules.html', course=course, modules=modules)

@app.route('/modules/<int:module_id>/delete', methods=['POST'])
def delete_module(module_id):
    module = Module.query.get(module_id)
    if module:
        db.session.delete(module)
        db.session.commit()
        flash('Module deleted successfully!', 'success')
    return redirect(url_for('manage_modules', course_id=module.course_id))

@app.route('/modules/<int:module_id>/lessons', methods=['GET', 'POST'])
def manage_lessons(module_id):
    module = Module.query.get(module_id)
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_lesson = Lesson(title=title, content=content, module_id=module_id)
        db.session.add(new_lesson)
        db.session.commit()
        flash('Lesson added successfully!', 'success')
        return redirect(url_for('manage_lessons', module_id=module_id))
    
    lessons = Lesson.query.filter_by(module_id=module_id).all()
    return render_template('lessons.html', module=module, lessons=lessons)

@app.route('/lessons/<int:lesson_id>/delete', methods=['POST'])
def delete_lesson(lesson_id):
    lesson = Lesson.query.get(lesson_id)
    if lesson:
        db.session.delete(lesson)
        db.session.commit()
        flash('Lesson deleted successfully!', 'success')
    return redirect(url_for('manage_lessons', module_id=lesson.module_id))

@app.route("/chat")
@login_required
def chat():
    return render_template('chatbot.html')

@app.route("/chat", methods=['POST'])
@login_required
def chatting():
    if request.is_json:
        user_msg = request.json.get('message', '')
        bot_msg = get_user_response(user_msg)
        response = {'message': bot_msg}
        return jsonify(response), 200

if __name__ == '__main__':
    app.run(debug=True)
