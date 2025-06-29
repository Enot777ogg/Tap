from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Замените на свой секретный ключ!

# Конфигурация базы данных
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Инициализация базы (запусти один раз)
@app.before_first_request
def create_tables():
    db.create_all()
    # Создать админа, если нет
    admin = User.query.filter_by(username='Enot').first()
    if not admin:
        admin = User(username='Enot', is_admin=True)
        admin.set_password('e365Iopol.')
        db.session.add(admin)
        db.session.commit()

# Вспомогательные функции
def current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def get_ranking_place(user):
    users = User.query.order_by(User.clicks.desc()).all()
    for i, u in enumerate(users, 1):
        if u.id == user.id:
            return i
    return None

# Главная страница
@app.route('/')
def index():
    user = current_user()
    if not user:
        return redirect(url_for('signin'))

    users = User.query.order_by(User.clicks.desc()).limit(10).all()
    place = get_ranking_place(user)

    return render_template('index.html', user=user, users=users, place=place)

# Обработка нажатия на кнопку
@app.route('/tap', methods=['POST'])
def tap():
    user = current_user()
    if not user:
        return jsonify({'error': 'Не авторизован'}), 401

    user.clicks += 1
    db.session.commit()
    win = (user.clicks % 10000 == 0)
    return jsonify({'clicks': user.clicks, 'win': win})

# Приём геопозиции
@app.route('/location', methods=['POST'])
def location():
    user = current_user()
    if not user:
        return jsonify({'error': 'Не авторизован'}), 401

    data = request.get_json()
    if data:
        user.latitude = data.get('lat')
        user.longitude = data.get('lon')
        db.session.commit()
    return jsonify({'status': 'ok'})

# Регистрация
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return render_template('signup.html', error='Пользователь уже существует')

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        return redirect(url_for('index'))

    return render_template('signup.html')

# Вход
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return render_template('signin.html', error='Неверный логин или пароль')

    return render_template('signin.html')

# Выход
@app.route('/signout')
def signout():
    session.pop('user_id', None)
    return redirect(url_for('signin'))

# Карта нажатий (только для админа)
@app.route('/locations')
def locations():
    user = current_user()
    if not user or not user.is_admin:
        abort(403)

    users = User.query.filter(User.latitude != None, User.longitude != None).all()
    return render_template('map.html', users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
