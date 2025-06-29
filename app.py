from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tap.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

@app.before_first_request
def create_tables():
    db.create_all()
    # Создаем Enot, если нет
    if not User.query.filter_by(username='Enot').first():
        admin = User(username='Enot', password='admin123', clicks=0)
        db.session.add(admin)
        db.session.commit()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            return "Пользователь существует"
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('signin'))
    return render_template('signup.html')

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

@app.route('/signout')
def signout():
    session.pop('user_id', None)
    return redirect(url_for('signin'))

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    user = User.query.get(session['user_id'])
    return render_template('index.html', user=user)

@app.route('/tap', methods=['POST'])
def tap():
    if 'user_id' not in session:
        return "Unauthorized", 401
    user = User.query.get(session['user_id'])
    user.clicks += 1
    db.session.commit()
    win = False
    if user.clicks % 10000 == 0:
        win = True
    return {'clicks': user.clicks, 'win': win}

@app.route('/locations')
def locations():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    user = User.query.get(session['user_id'])
    if user.username != 'Enot':
        return "Доступ запрещён", 403
    users = User.query.filter(User.latitude != None, User.longitude != None).all()
    return render_template('map.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)
