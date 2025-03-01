from flask import Flask, redirect, url_for, render_template, request, flash
from flask_login import current_user, login_user, login_required, logout_user, LoginManager, UserMixin
import os
from werkzeug.utils import secure_filename
from PIL import Image
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import save_metadata_to_db, Base, session, Metadata
import json  # Add this import at the top

app = Flask(__name__)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Specify the login view
login_manager.login_message = None  # Remove the default message

@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    metadata_info = None
    filename = None
    
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename:
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                metadata_info = extract_metadata(filepath)
                if metadata_info:  # Make sure metadata is not None
                    metadata_json = json.dumps(metadata_info)
                    new_metadata = Metadata(
                        filename=filename,
                        metadata_info=metadata_json,
                        user_id=current_user.id
                    )
                    
                    session.add(new_metadata)
                    session.commit()
                    
                    flash('Image successfully uploaded and analyzed!', 'success')
                    #flash(filepath)
                    return render_template('index.html', metadata_info=metadata_info, filename=filename)
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
                session.rollback()
    
    return render_template('index.html', metadata_info=None, filename=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # First check if user exists
        user = session.query(User).filter_by(username=username).first()
        if not user:
            flash('User not registered. Please register first.', 'error')
            return render_template('login.html')
        
        # Then check password
        if user.password == password:
            login_user(user)
            session.pop('_flashes', None)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password', 'error')
    
    session.pop('_flashes', None)
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 6
    
    total = session.query(Metadata).filter_by(user_id=current_user.id).count()
    offset = (page - 1) * per_page
    
    metadata = session.query(Metadata).filter_by(user_id=current_user.id)\
        .order_by(Metadata.id.desc())\
        .offset(offset).limit(per_page).all()
    
    # Convert JSON strings back to dictionaries
    for item in metadata:
        if item.metadata_info:
            try:
                item.metadata_info = json.loads(item.metadata_info)
            except:
                item.metadata_info = None
    
    return render_template('history.html', 
                         metadata=metadata,
                         page=page,
                         total=total,
                         per_page=per_page)

def extract_metadata(filepath):
    try:
        with Image.open(filepath) as img:
            exif = img._getexif()
            
            if not exif:
                return {
                    'camera_model': 'Not available',
                    'exposure_time': 'Not available',
                    'gps_info': 'Not available',
                    'date_time': 'Not available'
                }
            
            metadata = {
                'camera_model': exif.get(0x0110, 'Not available'),
                'exposure_time': exif.get(0x829A, 'Not available'),
                'gps_info': exif.get(0x8825, 'Not available'),
                'date_time': exif.get(0x9003, 'Not available')
            }
            
            print(f"Extracted EXIF data: {metadata}")  # Debug print
            return metadata
            
    except Exception as e:
        print(f"Error extracting metadata: {str(e)}")  # Debug print
        return {
            'camera_model': 'Error',
            'exposure_time': 'Error',
            'gps_info': 'Error',
            'date_time': 'Error'
        }

# Make sure your User model inherits from UserMixin
class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)
    # ... other fields ...

app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

if __name__ == '__main__':
    app.run(debug=True) 