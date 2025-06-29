from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tap.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'

db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

# Инициализация базы данных при старте
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='Enot').first():
        admin = User(username='Enot', password='admin123')
        db.session.add(admin)
        db.session.commit()

# Страница регистрации
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "Пользователь уже существует"
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('signin'))
    return render_template('signup.html')

# Страница входа
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return "Неверные данные"
    return render_template('signin.html')

# Выход
@app.route('/signout')
def signout():
    session.pop('user_id', None)
    return redirect(url_for('signin'))

# Главная страница с кнопкой
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    user = User.query.get(session['user_id'])
    all_users = User.query.order_by(User.clicks.desc()).all()
    place = [i + 1 for i, u in enumerate(all_users) if u.id == user.id][0]
    return render_template('index.html', user=user, place=place, users=all_users[:10])

# Обработка нажатия
@app.route('/tap', methods=['POST'])
def tap():
    if 'user_id' not in session:
        return "Unauthorized", 401
    user = User.query.get(session['user_id'])
    user.clicks += 1
    db.session.commit()
    win = user.clicks % 10000 == 0
    return jsonify({'clicks': user.clicks, 'win': win})

# Отправка координат
@app.route('/location', methods=['POST'])
def location():
    if 'user_id' not in session:
        return "Unauthorized", 401
    data = request.get_json()
    user = User.query.get(session['user_id'])
    user.latitude = data.get('lat')
    user.longitude = data.get('lon')
    db.session.commit()
    return '', 204

# Карта с координатами (только для Enot)
@app.route('/locations')
def locations():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    user = User.query.get(session['user_id'])
    if user.username != 'Enot':
        return "Доступ запрещён", 403
    users = User.query.filter(User.latitude.isnot(None), User.longitude.isnot(None)).all()
    return render_template('map.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)
