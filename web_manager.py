import os
import subprocess
import shutil
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
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
    DISPLAY_REQUEST_FILE = f'/home/{sudo_user}/display_request.txt'
else:
    # Fallback for development/local run
    IMAGE_FOLDER = os.path.expanduser('~/images')
    DISPLAY_REQUEST_FILE = os.path.expanduser('~/display_request.txt')

if sudo_user:
    IMAGE_FOLDER = f'/home/{sudo_user}/images'
    DISPLAY_REQUEST_FILE = f'/home/{sudo_user}/display_request.txt'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif', 'heic', 'heif'}

# Storage limits (in GB)
STORAGE_WARNING_THRESHOLD = 0.8  # 80% usage warning
STORAGE_LIMIT = 0.95  # 95% usage limit - prevent uploads

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_disk_usage():
    """Get disk usage statistics for the images folder."""
    stat = shutil.disk_usage(IMAGE_FOLDER)
    total_bytes = stat.total
    used_bytes = stat.used
    free_bytes = stat.free

    # Convert to GB for easier reading
    total_gb = total_bytes / (1024**3)
    used_gb = used_bytes / (1024**3)
    free_gb = free_bytes / (1024**3)

    usage_percent = (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0

    return {
        'total_gb': round(total_gb, 2),
        'used_gb': round(used_gb, 2),
        'free_gb': round(free_gb, 2),
        'usage_percent': round(usage_percent, 1)
    }

def is_storage_full():
    """Check if storage usage exceeds the limit."""
    usage = get_disk_usage()
    return usage['usage_percent'] >= (STORAGE_LIMIT * 100)

def is_storage_warning():
    """Check if storage usage is approaching the limit."""
    usage = get_disk_usage()
    return usage['usage_percent'] >= (STORAGE_WARNING_THRESHOLD * 100)

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
    storage_info = get_disk_usage()

    return render_template('index.html', images=images, storage=storage_info)

@app.route('/api/storage')
def get_storage_info():
    """API endpoint to get current storage information."""
    storage_info = get_disk_usage()
    storage_info['is_full'] = is_storage_full()
    storage_info['is_warning'] = is_storage_warning()
    return jsonify(storage_info)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if this is an AJAX request
    is_ajax = request.headers.get('Content-Type') == 'application/json' or request.is_json

    # Check storage limits first
    if is_storage_full():
        message = 'Storage is full. Please delete some images before uploading new ones.'
        if is_ajax:
            return {'success': False, 'message': message}
        flash(message)
        return redirect(url_for('index'))

    if is_storage_warning():
        message = 'Storage is almost full. Consider deleting some images to free up space.'
        if is_ajax:
            # Still allow upload but warn
            pass
        else:
            flash(message)

    if 'files[]' not in request.files:
        message = 'No file part'
        if is_ajax:
            return {'success': False, 'message': message}
        flash(message)
        return redirect(request.url)

    files = request.files.getlist('files[]')
    uploaded_files = []
    failed_files = []

    for file in files:
        if file.filename == '':
            continue

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()

            try:
                # Convert HEIC to JPG
                if file_ext in ['heic', 'heif']:
                    img = Image.open(file)
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    new_filename = filename.rsplit('.', 1)[0] + '.jpg'
                    save_path = os.path.join(IMAGE_FOLDER, new_filename)
                    img.save(save_path, "JPEG", quality=90)
                    uploaded_files.append(new_filename)
                else:
                    # Save regular images directly
                    file.save(os.path.join(IMAGE_FOLDER, filename))
                    uploaded_files.append(filename)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                failed_files.append(filename)
        else:
            failed_files.append(file.filename)

    # Prepare response
    if is_ajax:
        response = {
            'success': len(uploaded_files) > 0,
            'uploaded': uploaded_files,
            'failed': failed_files,
            'storage_warning': is_storage_warning()
        }
        if uploaded_files:
            response['message'] = f'Successfully uploaded {len(uploaded_files)} image(s)'
            if failed_files:
                response['message'] += f', {len(failed_files)} failed'
        elif failed_files:
            response['message'] = f'Failed to upload {len(failed_files)} image(s)'
        else:
            response['message'] = 'No valid files to upload'

        return response

    # Regular form submission - use flash messages
    if uploaded_files:
        flash(f'Successfully uploaded {len(uploaded_files)} image(s)')
    if failed_files:
        flash(f'Failed to upload {len(failed_files)} file(s): {", ".join(failed_files)}')

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


@app.route('/display/<filename>', methods=['GET', 'POST'])
def display_image(filename):
    success = True
    try:
        # Check if file exists in source directory
        file_path = os.path.join(IMAGE_FOLDER, filename)
        if os.path.exists(file_path):
            with open(DISPLAY_REQUEST_FILE, 'w') as f:
                f.write(filename)
            message = f'Request to display {filename} sent.'
        else:
            message = 'File not found.'
            success = False
    except Exception as e:
        message = f'Error requesting display: {e}'
        success = False

    # Check if this is an AJAX request
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        return {'success': success, 'message': message}

    # Regular request - use flash and redirect
    flash(message)
    return redirect(url_for('index'))

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    # Run on port 80, accessible from network
    # Note: Requires root/sudo to bind to port 80
    app.run(host='0.0.0.0', port=80, debug=False)

