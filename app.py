from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User, Task
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

# Login Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if db.session.execute(db.select(User).filter_by(username=username)).scalar():
            flash('Username already exists!')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = db.session.execute(db.select(User).filter_by(username=request.form['username'])).scalar()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid Login!')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    search_query = request.args.get('search')
    if search_query:
        tasks = db.session.execute(db.select(Task).filter(Task.user_id == current_user.id, Task.content.contains(search_query))).scalars().all()
    else:
        tasks = current_user.tasks
    return render_template('dashboard.html', tasks=tasks)

@app.route('/add', methods=['POST'])
@login_required
def add():
    content = request.form['content']
    priority = request.form.get('priority')
    due_date_str = request.form.get('due_date')
    
    due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
    
    new_task = Task(content=content, priority=priority, due_date=due_date, owner=current_user)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    task = db.session.get(Task, id)
    if task and task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/toggle/<int:id>')
@login_required
def toggle(id):
    task = db.session.get(Task, id)
    if task and task.user_id == current_user.id:
        task.is_completed = not task.is_completed
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/clear_all')
@login_required
def clear_all():
    db.session.execute(db.delete(Task).where(Task.user_id == current_user.id))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    task = db.get_or_404(Task, id)
    if task.user_id != current_user.id:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        task.content = request.form['content']
        task.priority = request.form.get('priority')
        due_date_str = request.form.get('due_date')
        if due_date_str:
            task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        else:
            task.due_date = None
            
        db.session.commit()
        return redirect(url_for('dashboard'))
        
    return render_template('update.html', task=task)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Creates the database file
    app.run(debug=True)