# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import math
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

socketio = SocketIO(app)
db = SQLAlchemy(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    city = db.Column(db.String(120))
    avatar = db.Column(db.String(200), default='default.png')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    top_users = User.query.order_by(User.clicks.desc()).limit(10).all()
    place = User.query.filter(User.clicks > user.clicks).count() + 1
    point = user.clicks // 1000
    level = calculate_level(point)
    progress = level_progress(point)
    return render_template('index.html', user=user, top_users=top_users, place=place,
                           level=level, progress=progress, point=point)

def calculate_level(point):
    level = 1
    required = 10
    while point >= required:
        point -= required
        required = int(required * 2.5)
        level += 1
    return level

def level_progress(point):
    level = 1
    required = 10
    while point >= required:
        point -= required
        required = int(required * 2.5)
        level += 1
    return int((point / required) * 100)

@app.route('/click', methods=['POST'])
def click():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user.clicks += 1
        db.session.commit()
        return jsonify({'clicks': user.clicks})
    return jsonify({'error': 'Not logged in'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return 'Username exists'
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    file = request.files['avatar']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        user = User.query.get(session['user_id'])
        point = user.clicks // 1000
        if calculate_level(point) >= 5:
            user.avatar = filename
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()[::-1]
    return render_template('chat.html', user=user, messages=messages)

@socketio.on('send_message')
def handle_message(data):
    user = User.query.get(session['user_id'])
    text = data['text'][:500]
    message = Message(user_id=user.id, text=text)
    db.session.add(message)
    db.session.commit()
    place = User.query.filter(User.clicks > user.clicks).count() + 1
    socketio.emit('receive_message', {
        'username': user.username,
        'avatar': user.avatar,
        'text': text,
        'place': place
    })

if __name__ == '__main__':
    db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000)
