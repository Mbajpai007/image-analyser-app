from flask import Flask, request, render_template, redirect, url_for, flash, session as flask_session
from werkzeug.utils import secure_filename
import os
import exifread
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, insert, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import send_from_directory

app = Flask(__name__)
#app.config['UPLOAD_FOLDER'] = 'uploads/'
#app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')

# Add static folder configuration
app.config['STATIC_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static')

app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a real secret key

# Database setup
engine = create_engine('sqlite:///metadata.db')
Base = declarative_base()

# Define User model
class User(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    analyses = relationship('Metadata', back_populates='user')

# Define Metadata model
class Metadata(Base):
    __tablename__ = 'metadata'
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    camera_model = Column(String)
    exposure_time = Column(String)
    gps_info = Column(String)
    date_time = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='analyses')

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(int(user_id))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if session.query(User).filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password)
        session.add(new_user)
        session.commit()
        flash('Registration successful')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = session.query(User).filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    metadata_info = None
    filename = None
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            metadata_info = extract_metadata(filepath)
            save_metadata_to_db(filename, metadata_info, current_user.id)
            flash('Image uploaded and metadata saved successfully!', 'success')
          #  return redirect(url_for('index'))
    return render_template('index.html', metadata_info=metadata_info, filename=filename,fold=app.config['UPLOAD_FOLDER'])

def extract_metadata(filepath):
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f)
    metadata_info = {
        'camera_model': tags.get('Image Model', 'N/A'),
        'exposure_time': tags.get('EXIF ExposureTime', 'N/A'),
        'gps_info': tags.get('GPS GPSLatitude', 'N/A'),
        'date_time': tags.get('EXIF DateTimeOriginal', 'N/A')
    }
    return metadata_info

def save_metadata_to_db(filename, metadata_info, user_id):
    camera_model = str(metadata_info.get('camera_model', 'N/A'))
    exposure_time = str(metadata_info.get('exposure_time', 'N/A'))
    gps_info = str(metadata_info.get('gps_info', 'N/A'))
    date_time = str(metadata_info.get('date_time', 'N/A'))

    new_entry = Metadata(
        filename=filename,
        camera_model=camera_model,
        exposure_time=exposure_time,
        gps_info=gps_info,
        date_time=date_time,
        user_id=user_id
    )

    session.add(new_entry)
    session.commit()

# Add this function to handle pagination
def get_paginated_items(query, page, per_page=5):
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total

@app.route('/history', methods=['GET'])
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page
    user_metadata_query = session.query(Metadata).filter_by(user_id=current_user.id)
    user_metadata, total = get_paginated_items(user_metadata_query, page, per_page)
    return render_template('history.html', metadata=user_metadata, page=page, total=total, per_page=per_page)

if __name__ == '__main__':
    app.run(debug=True) 