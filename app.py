from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # лучше заменить на свой

# Конфигурация БД
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'tap.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Инициализация БД и создание админа с новым паролем
with app.app_context():
    db.create_all()
    admin = User.query.filter_by(username='Enot').first()
    if not admin:
        admin = User(
            username='Enot',
            password_hash=generate_password_hash('e365Iopol'),  # Новый пароль
            clicks=0,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# Хелпер для текущего пользователя
def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Главная страница
@app.route('/')
def index():
    user = current_user()
    if not user:
        return redirect(url_for('signin'))

    # Топ-10 по кликам
    users = User.query.order_by(User.clicks.desc()).limit(10).all()

    # Место пользователя в рейтинге
    place = User.query.filter(User.clicks > user.clicks).count() + 1

    return render_template('index.html', user=user, users=users, place=place)

# Обработка клика по кнопке
@app.route('/tap', methods=['POST'])
def tap():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    user.clicks += 1
    db.session.commit()

    win = (user.clicks % 10000 == 0)
    return jsonify({'clicks': user.clicks, 'win': win})

# Сохранение координат пользователя
@app.route('/location', methods=['POST'])
def location():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    user.latitude = data.get('lat')
    user.longitude = data.get('lon')
    db.session.commit()
    return jsonify({'status': 'ok'})

# Регистрация
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return render_template('signup.html', error='Имя уже занято')

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            clicks=0
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('signin'))
    return render_template('signup.html')

# Вход
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return render_template('signin.html', error='Неверное имя или пароль')
    return render_template('signin.html')

# Выход
@app.route('/signout')
def signout():
    session.pop('user_id', None)
    return redirect(url_for('signin'))

# Карта (доступна только для админа Enot)
@app.route('/map')
def locations():
    user = current_user()
    if not user or not user.is_admin:
        abort(403)  # Доступ запрещён

    users = User.query.filter(User.latitude.isnot(None), User.longitude.isnot(None)).all()
    return render_template('map.html', users=users)

# Запуск
if __name__ == '__main__':
    app.run(debug=True)
