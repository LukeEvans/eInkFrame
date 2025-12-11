import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from PIL import Image
from pillow_heif import register_heif_opener
from werkzeug.utils import secure_filename

# Register HEIF opener with Pillow
register_heif_opener()

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this for production security

# Configuration
# Get user from environment variable if running as root via sudo/systemd
sudo_user = os.environ.get('SUDO_USER')
if sudo_user:
    IMAGE_FOLDER = f'/home/{sudo_user}/images'
    CONFIG_FILE = f'/home/{sudo_user}/config.txt'
else:
    # Fallback for development/local run
    IMAGE_FOLDER = os.path.expanduser('~/images')
    CONFIG_FILE = os.path.expanduser('~/config.txt')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif', 'heic', 'heif'}

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def restart_service():
    """Restart the e-ink display service to apply changes."""
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', 'epaper.service'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restarting service: {e}")
        return False

@app.route('/')
def index():
    images = [f for f in os.listdir(IMAGE_FOLDER) if allowed_file(f) and not f.startswith('.')]
    
    # Read current refresh time
    refresh_time = 600
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                content = f.read().strip()
                if content.isdigit():
                    refresh_time = int(content)
        except:
            pass
            
    return render_template('index.html', images=images, refresh_time=refresh_time)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    files = request.files.getlist('files[]')
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            
            # Convert HEIC to JPG
            if file_ext in ['heic', 'heif']:
                try:
                    img = Image.open(file)
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    new_filename = filename.rsplit('.', 1)[0] + '.jpg'
                    save_path = os.path.join(IMAGE_FOLDER, new_filename)
                    img.save(save_path, "JPEG", quality=90)
                except Exception as e:
                    print(f"Error converting {filename}: {e}")
                    flash(f'Error converting {filename}')
                    continue
            else:
                # Save regular images directly
                file.save(os.path.join(IMAGE_FOLDER, filename))
                
    return redirect(url_for('index'))

@app.route('/delete/<filename>')
def delete_file(filename):
    try:
        file_path = os.path.join(IMAGE_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f'Deleted {filename}')
        else:
            flash('File not found')
    except Exception as e:
        flash(f'Error deleting file: {e}')
        
    return redirect(url_for('index'))

@app.route('/config', methods=['POST'])
def update_config():
    refresh_time = request.form.get('refresh_time')
    
    if refresh_time and refresh_time.isdigit():
        try:
            with open(CONFIG_FILE, 'w') as f:
                f.write(refresh_time)
            
            # Restart service to apply changes
            if restart_service():
                flash(f'Settings saved and service restarted (Interval: {refresh_time}s)')
            else:
                flash('Settings saved but failed to restart service')
                
        except Exception as e:
            flash(f'Error saving config: {e}')
    else:
        flash('Invalid refresh time')
        
    return redirect(url_for('index'))

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    # Run on port 80, accessible from network
    # Note: Requires root/sudo to bind to port 80
    app.run(host='0.0.0.0', port=80, debug=False)

