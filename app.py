import os
import zipfile
import shutil
import time
from flask import Flask, request, render_template, send_file, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
import numpy as np
from waitress import serve

# Initialize Flask app
app = Flask(__name__)

# Configuration settings
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output_images'
app.config['STATIC_IMAGES'] = os.path.join('static', 'images')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB upload limit
app.secret_key = 'supersecretkey'

# Create required folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_IMAGES'], exist_ok=True)

# Function to extract images from ZIP file
def extract_images(zip_path, extract_to):
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return [os.path.join(extract_to, f) for f in os.listdir(extract_to) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

# Function to load and resize images
def load_images(image_paths):
    images = []
    for path in image_paths:
        try:
            img = Image.open(path).convert('L')
            img = img.resize((256, 256))
            images.append(np.array(img, dtype=np.uint8))
        except UnidentifiedImageError:
            print(f"Warning: Could not identify image {path}")
    return images

# Function to compute global average brightness
def compute_global_avg(images):
    all_pixels = np.concatenate([img.flatten() for img in images])
    return np.mean(all_pixels)

# Function to normalize images
def normalize_images(images, global_avg):
    normalized = []
    for img in images:
        img_mean = np.mean(img)
        scale = global_avg / img_mean if img_mean != 0 else 1.0
        adjusted = np.clip(img * scale, 0, 255).astype(np.uint8)
        normalized.append(adjusted)
    return normalized

# Function to save images to disk
def save_images(images, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    image_paths = []
    for idx, img in enumerate(images):
        path = os.path.join(save_dir, f"normalized_image{idx+1}.png")
        Image.fromarray(img).save(path)
        image_paths.append(path)
    return image_paths

# Function to validate images
def validate_images(images, global_avg):
    correct = 0
    for i, img in enumerate(images, 1):
        avg = np.mean(img)
        if abs(avg - global_avg) <= 1:
            correct += 1
    return correct

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Input route
@app.route('/input', methods=['GET', 'POST'])
def input_page():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded.')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.')
            return redirect(request.url)
        if file and file.filename.endswith('.zip'):
            filename = secure_filename(file.filename)
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(zip_path)

            try:
                start = time.time()

                extract_folder = 'input_images'
                try:
                    image_paths = extract_images(zip_path, extract_folder)
                except zipfile.BadZipFile:
                    flash('Invalid ZIP file format.')
                    return redirect(request.url)

                images = load_images(image_paths)

                if not images:
                    flash('No valid images found in the ZIP file.')
                    return redirect(request.url)

                global_avg = compute_global_avg(images)
                normalized = normalize_images(images, global_avg)
                output_paths = save_images(normalized, app.config['OUTPUT_FOLDER'])
                score = validate_images(normalized, global_avg)

                for path in output_paths:
                    static_path = os.path.join(app.config['STATIC_IMAGES'], os.path.basename(path))
                    shutil.copy(path, static_path)

                processing_time = time.time() - start

                output_zip = 'normalized_images.zip'
                with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for path in output_paths:
                        zipf.write(path, os.path.basename(path))

                session['results'] = {
                    'global_avg': global_avg,
                    'score': score,
                    'total_images': len(images),
                    'processing_time': processing_time,
                    'image_urls': [url_for('static', filename=f'images/{os.path.basename(path)}') for path in output_paths],
                    'download_zip': output_zip
                }

                return redirect(url_for('output_page'))

            except Exception as e:
                flash(f'Processing failed: {str(e)}')
                return redirect(request.url)

            finally:
                if os.path.exists(extract_folder):
                    shutil.rmtree(extract_folder)
                if os.path.exists(zip_path):
                    os.remove(zip_path)
        else:
            flash('Please upload a valid ZIP file.')
            return redirect(request.url)

    return render_template('input.html')

# Output route
@app.route('/output')
def output_page():
    results = session.get('results')
    if not results:
        flash('No results available. Please upload a ZIP file first.')
        return redirect(url_for('input_page'))
    return render_template('output.html', **results)

# About route
@app.route('/about')
def about_page():
    return render_template('about.html')

# Download route
@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = filename
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading file: {str(e)}')
        return redirect(url_for('output_page'))

# Ping route
@app.route('/ping')
def ping():
    return 'Pong!'

# Run the app with Waitress
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8000)
