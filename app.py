import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import datetime
import csv
import uuid
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Initialize database
def init_db():
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 email TEXT UNIQUE,
                 password TEXT,
                 is_admin BOOLEAN DEFAULT 0,
                 is_approved BOOLEAN DEFAULT 0,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (id TEXT PRIMARY KEY,
                 collector_email TEXT,
                 collection_date TIMESTAMP,
                 batch TEXT,
                 region TEXT,
                 zone TEXT,
                 woreda TEXT,
                 kebele TEXT,
                 edi_id TEXT,
                 first_name TEXT,
                 father_name TEXT,
                 grandfather_name TEXT,
                 dob TEXT,
                 sex TEXT,
                 address TEXT,
                 has_license TEXT,
                 trade_license_num TEXT,
                 trade_reg_num TEXT,
                 tin_number TEXT,
                 license_date TEXT,
                 enterprise_size TEXT,
                 ownership_type TEXT,
                 business_sector TEXT,
                 owners_count INTEGER,
                 owners_names TEXT,
                 registered_address TEXT,
                 business_premise TEXT,
                 male_employees INTEGER,
                 female_employees INTEGER,
                 capital REAL,
                 monthly_revenue REAL,
                 annual_revenue REAL,
                 net_profit REAL,
                 requested_amount REAL,
                 purpose TEXT,
                 repayment_source TEXT,
                 guaranter_first_name TEXT,
                 guaranter_father_name TEXT,
                 guaranter_grandfather_name TEXT,
                 guaranter_phone TEXT,
                 guaranter_salary REAL,
                 cbe_account TEXT,
                 branch_name TEXT,
                 city TEXT,
                 finance_mode TEXT,
                 status TEXT,
                 FOREIGN KEY (collector_email) REFERENCES users(email))''')
    
    # Insert super admin if not exists
    c.execute("SELECT * FROM users WHERE email = 'natnaelkoyachew1@gmail.com'")
    if not c.fetchone():
        c.execute("INSERT INTO users (email, password, is_admin, is_approved) VALUES (?, ?, 1, 1)",
                  ('natnaelkoyachew1@gmail.com', generate_password_hash('#password321')))
    
    conn.commit()
    conn.close()

init_db()

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
GOOGLE_SHEET_ID = '14BcNGcLq8DTrxf0w3ft1b15QKbDwztWP'

# Authentication functions
def authenticate(email, password):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute("SELECT password, is_approved FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    return check_password_hash(user[0], password) if user and user[1] == 1 else False

def is_admin(email):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else False

def add_user(email, password, is_admin=False):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)",
                  (email, generate_password_hash(password), 1 if is_admin else 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_users():
    conn = sqlite3.connect('applications.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    return users

def approve_user(user_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def save_application(data):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''INSERT INTO applications VALUES
                 (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (
                  data['id'], data['collector_email'], data['collection_date'],
                  data['batch'], data['region'], data['zone'], data['woreda'], data['kebele'],
                  data['edi_id'], data['first_name'], data['father_name'], data['grandfather_name'],
                  data['dob'], data['sex'], data['address'], data['has_license'], data['trade_license_num'],
                  data['trade_reg_num'], data['tin_number'], data['license_date'], data['enterprise_size'],
                  data['ownership_type'], data['business_sector'], data['owners_count'], data['owners_names'],
                  data['registered_address'], data['business_premise'], data['male_employees'],
                  data['female_employees'], data['capital'], data['monthly_revenue'], data['annual_revenue'],
                  data['net_profit'], data['requested_amount'], data['purpose'], data['repayment_source'],
                  data['guaranter_first_name'], data['guaranter_father_name'], data['guaranter_grandfather_name'],
                  data['guaranter_phone'], data['guaranter_salary'], data['cbe_account'], data['branch_name'],
                  data['city'], data['finance_mode'], data['status']
              ))
    conn.commit()
    conn.close()

def get_applications():
    conn = sqlite3.connect('applications.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM applications ORDER BY collection_date DESC")
    apps = c.fetchall()
    conn.close()
    return apps

def get_application_by_id(app_id):
    conn = sqlite3.connect('applications.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    app = c.fetchone()
    conn.close()
    return app

def update_application(app_id, updates):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(app_id)
    c.execute(f"UPDATE applications SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def update_google_sheet(data):
    try:
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        worksheet = sheet.get_worksheet(0)
        row_data = [
            data['id'], data['batch'], data['collection_date'], data['region'],
            data['zone'], f"{data['woreda']}/{data['kebele']}", data['edi_id'],
            f"{data['first_name']} {data['father_name']} {data['grandfather_name']}",
            data['sex'], data['dob'], data['address'], data['has_license'],
            data['trade_license_num'], data['trade_reg_num'], data['tin_number'],
            data['license_date'], data['enterprise_size'], data['ownership_type'],
            data['business_sector'], data['owners_count'], data['owners_names'],
            data['registered_address'], data['business_premise'], data['male_employees'],
            data['female_employees'], str(int(data['male_employees']) + int(data['female_employees'])),
            data['capital'], data['monthly_revenue'], data['annual_revenue'],
            data['net_profit'], data['requested_amount'], data['purpose'],
            data['repayment_source'],
            f"{data['guaranter_first_name']} {data['guaranter_father_name']} {data['guaranter_grandfather_name']}",
            data['guaranter_phone'], data['guaranter_salary'], data['cbe_account'],
            data['branch_name'], data['city'], data['finance_mode'],
            data['collector_email'], data['status']
        ]
        worksheet.append_row(row_data)
    except Exception as e:
        print(f"Error updating Google Sheet: {e}")

# Routes
@app.route('/')
def home():
    if 'logged_in' in session:
        if is_admin(session['email']):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    if authenticate(email, password):
        session['logged_in'] = True
        session['email'] = email
        session['is_admin'] = is_admin(email)
        session['is_super_admin'] = (email == "natnaelkoyachew1@gmail.com")
        return redirect(url_for('admin_dashboard' if session['is_admin'] else 'dashboard'))
    flash('Invalid credentials!', 'error')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session or session.get('is_admin'):
        return redirect(url_for('home'))
    return render_template('dashboard.html')

@app.route('/application', methods=['GET', 'POST'])
def application():
    if 'logged_in' not in session or session.get('is_admin'):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        app_data = {
            'id': str(uuid.uuid4()),
            'collector_email': session['email'],
            'collection_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'batch': request.form.get('batch'),
            'region': request.form.get('region'),
            'zone': request.form.get('zone'),
            'woreda': request.form.get('woreda'),
            'kebele': request.form.get('kebele'),
            'edi_id': request.form.get('edi_id'),
            'first_name': request.form.get('first_name'),
            'father_name': request.form.get('father_name'),
            'grandfather_name': request.form.get('grandfather_name'),
            'dob': request.form.get('dob'),
            'sex': request.form.get('sex'),
            'address': request.form.get('address'),
            'has_license': request.form.get('has_license'),
            'trade_license_num': request.form.get('trade_license_num', ''),
            'trade_reg_num': request.form.get('trade_reg_num', ''),
            'tin_number': request.form.get('tin_number', ''),
            'license_date': request.form.get('license_date', ''),
            'enterprise_size': request.form.get('enterprise_size'),
            'ownership_type': request.form.get('ownership_type'),
            'business_sector': request.form.get('business_sector'),
            'owners_count': request.form.get('owners_count'),
            'owners_names': request.form.get('owners_names'),
            'registered_address': request.form.get('registered_address'),
            'business_premise': request.form.get('business_premise'),
            'male_employees': request.form.get('male_employees'),
            'female_employees': request.form.get('female_employees'),
            'capital': request.form.get('capital'),
            'monthly_revenue': request.form.get('monthly_revenue'),
            'annual_revenue': request.form.get('annual_revenue'),
            'net_profit': request.form.get('net_profit'),
            'requested_amount': request.form.get('requested_amount'),
            'purpose': request.form.get('purpose'),
            'repayment_source': request.form.get('repayment_source'),
            'guaranter_first_name': request.form.get('guaranter_first_name'),
            'guaranter_father_name': request.form.get('guaranter_father_name'),
            'guaranter_grandfather_name': request.form.get('guaranter_grandfather_name'),
            'guaranter_phone': request.form.get('guaranter_phone'),
            'guaranter_salary': request.form.get('guaranter_salary'),
            'cbe_account': request.form.get('cbe_account'),
            'branch_name': request.form.get('branch_name'),
            'city': request.form.get('city'),
            'finance_mode': request.form.get('finance_mode'),
            'status': 'submitted'
        }
        
        save_application(app_data)
        update_google_sheet(app_data)
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('application.html')

@app.route('/admin')
def admin_dashboard():
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html', applications=get_applications())

@app.route('/admin/users')
def admin_users():
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('home'))
    return render_template('admin_users.html', users=get_users())

@app.route('/admin/approve-user/<user_id>')
def admin_approve_user(user_id):
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('home'))
    approve_user(user_id)
    flash('User approved successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/add-admin', methods=['POST'])
def admin_add_admin():
    if 'logged_in' not in session or not session.get('is_super_admin'):
        return redirect(url_for('home'))
    email = request.form.get('email')
    password = request.form.get('password')
    add_user(email, password, is_admin=True)
    flash('Admin added successfully!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/application/<app_id>')
def admin_view_application(app_id):
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('home'))
    return render_template('admin_application.html', app=get_application_by_id(app_id))

@app.route('/admin/update-application/<app_id>', methods=['POST'])
def admin_update_application(app_id):
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('home'))
    update_application(app_id, request.form.to_dict())
    flash('Application updated successfully!', 'success')
    return redirect(url_for('admin_view_application', app_id=app_id))

@app.route('/admin/export-data')
def admin_export_data():
    if 'logged_in' not in session or not session.get('is_admin'):
        return redirect(url_for('home'))
    
    apps = get_applications()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        "ID", "Batch", "Date Collected", "Region", "Zone", "Woreda/Kebele",
        "EDI ID", "Applicant Full Name", "Sex", "Date of Birth", "Address",
        "Business License", "Trade License No", "Trade Reg No", "TIN No",
        "License Date", "Enterprise Size", "Ownership Type", "Business Sector",
        "Owners Count", "Owners Names", "Registered Address", "Business Premise",
        "Male Employees", "Female Employees", "Total Employees", "Capital (ETB)",
        "Monthly Revenue", "Annual Revenue", "Net Profit/Loss", "Requested Amount",
        "Purpose", "Repayment Source", "Guaranter Name", "Guaranter Phone",
        "Guaranter Salary", "CBE Account", "Branch", "City", "Finance Mode",
        "Collector Email", "Status"
    ])
    
    # Write data
    for app in apps:
        writer.writerow([
            app['id'], app['batch'], app['collection_date'], app['region'],
            app['zone'], f"{app['woreda']}/{app['kebele']}", app['edi_id'],
            f"{app['first_name']} {app['father_name']} {app['grandfather_name']}",
            app['sex'], app['dob'], app['address'], app['has_license'],
            app['trade_license_num'], app['trade_reg_num'], app['tin_number'],
            app['license_date'], app['enterprise_size'], app['ownership_type'],
            app['business_sector'], app['owners_count'], app['owners_names'],
            app['registered_address'], app['business_premise'], app['male_employees'],
            app['female_employees'], int(app['male_employees']) + int(app['female_employees']),
            app['capital'], app['monthly_revenue'], app['annual_revenue'],
            app['net_profit'], app['requested_amount'], app['purpose'],
            app['repayment_source'],
            f"{app['guaranter_first_name']} {app['guaranter_father_name']} {app['guaranter_grandfather_name']}",
            app['guaranter_phone'], app['guaranter_salary'], app['cbe_account'],
            app['branch_name'], app['city'], app['finance_mode'],
            app['collector_email'], app['status']
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name='EDI_Applications.csv',
        mimetype='text/csv'
    )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        add_user(email, password)
        flash('Signup successful! Your account will be activated after admin approval.', 'success')
        return redirect(url_for('home'))
    return render_template('signup.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)