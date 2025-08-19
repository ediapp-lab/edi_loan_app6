import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import uuid
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Initialize database with all mandatory columns
def init_db():
    conn = sqlite3.connect('instance/applications.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 is_admin BOOLEAN DEFAULT 0 NOT NULL,
                 is_approved BOOLEAN DEFAULT 0 NOT NULL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Applications table with ALL mandatory fields
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (id TEXT PRIMARY KEY,
                 collector_email TEXT NOT NULL,
                 collection_date TIMESTAMP NOT NULL,
                 
                 -- Location Information
                 region TEXT NOT NULL,
                 zone TEXT NOT NULL,
                 woreda TEXT NOT NULL,
                 kebele TEXT NOT NULL,
                 batch TEXT NOT NULL,
                 
                 -- Applicant Information
                 first_name TEXT NOT NULL,
                 father_name TEXT NOT NULL,
                 grandfather_name TEXT NOT NULL,
                 dob TEXT NOT NULL,
                 sex TEXT NOT NULL CHECK(sex IN ('M', 'F')),
                 address TEXT NOT NULL,
                 
                 -- Business License Information
                 has_license TEXT NOT NULL CHECK(has_license IN ('Yes', 'No')),
                 trade_license_num TEXT,
                 trade_reg_num TEXT,
                 tin_number TEXT,
                 license_date TEXT,
                 
                 -- Business Information
                 enterprise_size TEXT NOT NULL CHECK(enterprise_size IN ('Micro', 'Small', 'Medium', 'Startup')),
                 ownership_type TEXT NOT NULL CHECK(ownership_type IN ('Sole Proprietorship', 'Partnership', 'PLC')),
                 business_sector TEXT NOT NULL CHECK(business_sector IN ('Manufacturing', 'Construction', 'Agriculture', 'Mining', 'Service', 'Other')),
                 owners_count INTEGER NOT NULL,
                 owners_names TEXT NOT NULL,
                 registered_address TEXT NOT NULL,
                 business_premise TEXT NOT NULL CHECK(business_premise IN ('Rented', 'Applicant Owned', 'Government')),
                 
                 -- Employment Information
                 male_employees INTEGER NOT NULL,
                 female_employees INTEGER NOT NULL,
                 
                 -- Financial Information
                 capital REAL NOT NULL,
                 monthly_revenue REAL NOT NULL,
                 annual_revenue REAL NOT NULL,
                 net_profit REAL NOT NULL,
                 requested_amount REAL NOT NULL,
                 
                 -- Loan Information
                 purpose TEXT NOT NULL,
                 repayment_source TEXT NOT NULL,
                 
                 -- Guarantor Information
                 guaranter_first_name TEXT NOT NULL,
                 guaranter_father_name TEXT NOT NULL,
                 guaranter_grandfather_name TEXT NOT NULL,
                 guaranter_phone TEXT NOT NULL,
                 guaranter_salary REAL NOT NULL,
                 
                 -- Banking Information
                 cbe_account TEXT NOT NULL,
                 branch_name TEXT NOT NULL,
                 city TEXT NOT NULL,
                 finance_mode TEXT NOT NULL CHECK(finance_mode IN ('Conventional', 'IFB')),
                 
                 -- Status and Metadata
                 status TEXT DEFAULT 'Pending' NOT NULL,
                 FOREIGN KEY (collector_email) REFERENCES users(email))''')

    # Insert super admin if not exists
    c.execute("SELECT * FROM users WHERE email = 'natnaelkoyachew1@gmail.com'")
    if not c.fetchone():
        c.execute("INSERT INTO users (email, password, is_admin, is_approved) VALUES (?, ?, 1, 1)",
                  ('natnaelkoyachew1@gmail.com', generate_password_hash('#password321')))
    conn.commit()
    conn.close()

# Initialize Google Sheets
def init_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/drive",
             "https://www.googleapis.com/auth/spreadsheets"]
    
    creds_dict = {
        "type": "service_account",
        "project_id": os.environ.get('PROJECT_ID'),
        "private_key_id": os.environ.get('PRIVATE_KEY_ID'),
        "private_key": os.environ.get('PRIVATE_KEY').replace('\\n', '\n'),
        "client_email": os.environ.get('CLIENT_EMAIL'),
        "client_id": os.environ.get('CLIENT_ID'),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get('CLIENT_CERT_URL')
    }
    
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# Initialize components
init_db()
client = None
try:
    client = gspread.authorize(init_gsheets())
except Exception as e:
    print(f"Google Sheets initialization failed: {e}")

# Application submission route with all mandatory fields
@app.route('/submit-application', methods=['GET', 'POST'])
def submit_application():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Get all mandatory fields from form
            application_data = {
                'id': str(uuid.uuid4()),
                'collector_email': session['email'],
                'collection_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                
                # Location Information
                'region': request.form['region'],
                'zone': request.form['zone'],
                'woreda': request.form['woreda'],
                'kebele': request.form['kebele'],
                'batch': request.form['batch'],
                
                # Applicant Information
                'first_name': request.form['first_name'],
                'father_name': request.form['father_name'],
                'grandfather_name': request.form['grandfather_name'],
                'dob': request.form['dob'],
                'sex': request.form['sex'],
                'address': request.form['address'],
                
                # Business License Information
                'has_license': request.form['has_license'],
                'trade_license_num': request.form.get('trade_license_num', ''),
                'trade_reg_num': request.form.get('trade_reg_num', ''),
                'tin_number': request.form.get('tin_number', ''),
                'license_date': request.form.get('license_date', ''),
                
                # Business Information
                'enterprise_size': request.form['enterprise_size'],
                'ownership_type': request.form['ownership_type'],
                'business_sector': request.form['business_sector'],
                'owners_count': int(request.form['owners_count']),
                'owners_names': request.form['owners_names'],
                'registered_address': request.form['registered_address'],
                'business_premise': request.form['business_premise'],
                
                # Employment Information
                'male_employees': int(request.form['male_employees']),
                'female_employees': int(request.form['female_employees']),
                
                # Financial Information
                'capital': float(request.form['capital']),
                'monthly_revenue': float(request.form['monthly_revenue']),
                'annual_revenue': float(request.form['annual_revenue']),
                'net_profit': float(request.form['net_profit']),
                'requested_amount': float(request.form['requested_amount']),
                
                # Loan Information
                'purpose': request.form['purpose'],
                'repayment_source': request.form['repayment_source'],
                
                # Guarantor Information
                'guaranter_first_name': request.form['guaranter_first_name'],
                'guaranter_father_name': request.form['guaranter_father_name'],
                'guaranter_grandfather_name': request.form['guaranter_grandfather_name'],
                'guaranter_phone': request.form['guaranter_phone'],
                'guaranter_salary': float(request.form['guaranter_salary']),
                
                # Banking Information
                'cbe_account': request.form['cbe_account'],
                'branch_name': request.form['branch_name'],
                'city': request.form['city'],
                'finance_mode': request.form['finance_mode'],
                
                'status': 'Pending'
            }
            
            # Insert into database
            conn = sqlite3.connect('instance/applications.db')
            c = conn.cursor()
            columns = ', '.join(application_data.keys())
            placeholders = ', '.join(['?'] * len(application_data))
            c.execute(f"INSERT INTO applications ({columns}) VALUES ({placeholders})", 
                     list(application_data.values()))
            conn.commit()
            conn.close()
            
            # Update Google Sheets if configured
            if client:
                try:
                    sheet = client.open_by_key(os.environ.get('GOOGLE_SHEET_ID')).sheet1
                    sheet.append_row(list(application_data.values()))
                except Exception as e:
                    print(f"Failed to update Google Sheet: {e}")
            
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error submitting application: {str(e)}', 'danger')
            return redirect(url_for('submit_application'))
    
    # For GET request - show form with dropdown options
    dropdown_options = {
        'sex_options': ['M', 'F'],
        'license_options': ['Yes', 'No'],
        'enterprise_sizes': ['Micro', 'Small', 'Medium', 'Startup'],
        'ownership_types': ['Sole Proprietorship', 'Partnership', 'PLC'],
        'business_sectors': ['Manufacturing', 'Construction', 'Agriculture', 'Mining', 'Service', 'Other'],
        'premise_types': ['Rented', 'Applicant Owned', 'Government'],
        'finance_modes': ['Conventional', 'IFB']
    }
    
    return render_template('application_form.html', **dropdown_options)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
