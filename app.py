from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import math
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
socketio = SocketIO(app)
db = SQLAlchemy(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    city = db.Column(db.String(100))
    avatar = db.Column(db.String(120), default='default.png')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    text = db.Column(db.String(300))

# Helpers
def calculate_level(clicks):
    point = clicks // 1000
    level = 1
    threshold = 10
    while point >= threshold:
        level += 1
        point -= threshold
        threshold = int(threshold * 2.5)
    return level

def get_user_rank(user_id):
    all_users = User.query.order_by(User.clicks.desc()).all()
    for i, user in enumerate(all_users, 1):
        if user.id == user_id:
            return i
    return None

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.clicks += 1
        db.session.commit()
        if user.clicks == 10000:
            return jsonify({'winner': True})
        return jsonify({'clicks': user.clicks})

    top_users = User.query.order_by(User.clicks.desc()).limit(10).all()
    level = calculate_level(user.clicks)
    point = user.clicks // 1000
    next_level_threshold = 10
    total = 0
    for _ in range(1, level):
        total += next_level_threshold
        next_level_threshold = int(next_level_threshold * 2.5)
    next_total = total + next_level_threshold

    return render_template('index.html', user=user, top_users=top_users, level=level,
                           point=point, progress=point - total, goal=next_level_threshold,
                           rank=get_user_rank(user.id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session['user_id'] = user.id
            return redirect('/')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if User.query.filter_by(username=u).first():
            return 'User exists'
        user = User(username=u, password=p)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect('/')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    level = calculate_level(user.clicks)
    if level < 5:
        return "Level too low", 403
    file = request.files['avatar']
    if file:
        filename = secure_filename(str(uuid.uuid4()) + "_" + file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        user.avatar = filename
        db.session.commit()
    return redirect('/')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    rank = get_user_rank(user.id)
    return render_template('chat.html', username=user.username, avatar=user.avatar, rank=rank)

@socketio.on('send_message')
def handle_send_message(data):
    username = data['username']
    avatar = data['avatar']
    text = data['text']
    emit('receive_message', {
        'username': username,
        'avatar': avatar,
        'text': text
    }, broadcast=True)

# Main
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000)
