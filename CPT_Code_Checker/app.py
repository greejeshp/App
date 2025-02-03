from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key
app.config['UPLOAD_FOLDER'] = 'data/'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limit to 50MB

# Admin login credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

# Placeholder for CPT code rules
cpt_code_rules = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return render_template('admin_panel.html')
        else:
            return "Invalid credentials", 403
    return render_template('admin_login.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        load_cpt_code_rules(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('home'))

def load_cpt_code_rules(file_path):
    global cpt_code_rules
    with open(file_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        headers = next(reader)  # Read the header row
        for row in reader:
            if len(row) < 2:  # Check if there are at least two columns
                print(f"Skipping row: {row} - not enough columns")  # Debugging output
                continue  # Skip empty or malformed rows
            rule_data = {headers[i]: row[i] for i in range(len(headers))}
            cpt_code_rules[rule_data.get('CPT_Code', 'Unknown')] = rule_data
            print(f"Loaded rule for CPT code: {rule_data.get('CPT_Code', 'Unknown')}")  # Debugging output

@app.route('/check-codes', methods=['POST'])
def check_codes():
    cpt_codes = request.form['cpt_codes'].split(',')
    results = {}
    for code in cpt_codes:
        code = code.strip()
        result = cpt_code_rules.get(code, "No rule found")
        results[code] = result
        print(f"Checking code: {code}, Result: {result}")  # Debugging output
    return render_template('index.html', result=results)

if __name__ == '__main__':
    app.run(debug=True)
