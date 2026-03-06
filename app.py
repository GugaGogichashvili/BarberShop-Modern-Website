from flask import Flask, jsonify, request, send_from_directory, session
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__, static_folder='public')
app.secret_key = 'luxe-barbershop-secret-key-2026'
app.config['UPLOAD_FOLDER'] = 'public/images/barbers'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

DB_PATH = os.path.join(os.path.dirname(__file__), 'barbershop.db')

# Simple admin password (change this!)
ADMIN_PASSWORD = 'Mesopotamia'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create services table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            duration INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')
    
    # Create barbers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT,
            image TEXT
        )
    ''')
    
    # Create appointments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_email TEXT,
            service_id INTEGER NOT NULL,
            barber_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'confirmed',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (service_id) REFERENCES services(id),
            FOREIGN KEY (barber_id) REFERENCES barbers(id)
        )
    ''')
    
    # Check if services exist
    cursor.execute("SELECT COUNT(*) as count FROM services")
    if cursor.fetchone()[0] == 0:
        services = [
            ('Classic Haircut', 'Traditional cut with clippers and scissors', 30, 35),
            ('Beard Trim', 'Professional beard shaping and trim', 20, 25),
            ('Full Service', 'Haircut + Beard trim + Hot towel', 50, 55),
            ('Buzz Cut', 'Single guard clipper cut', 15, 20),
            ('Kids Cut', 'For children under 12', 25, 25),
            ('Senior Cut', 'Classic styling for gentlemen 60+', 30, 30)
        ]
        cursor.executemany("INSERT INTO services (name, description, duration, price) VALUES (?, ?, ?, ?)", services)
    
    # Check if barbers exist
    cursor.execute("SELECT COUNT(*) as count FROM barbers")
    if cursor.fetchone()[0] == 0:
        barbers = [
            ('James Wilson', 'Master Barber', 'barber1.jpg'),
            ('Michael Chen', 'Style Expert', 'barber2.jpg'),
            ('David Rodriguez', 'Beard Specialist', 'barber3.jpg'),
            ('Alex Thompson', 'Fade Expert', 'barber4.jpg')
        ]
        cursor.executemany("INSERT INTO barbers (name, specialty, image) VALUES (?, ?, ?)", barbers)
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# API Routes

@app.route('/api/services', methods=['GET'])
def get_services():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM services")
    services = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(services)

@app.route('/api/services', methods=['POST'])
@login_required
def create_service():
    data = request.get_json()
    
    required = ['name', 'duration', 'price']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO services (name, description, duration, price) VALUES (?, ?, ?, ?)",
            (data['name'], data.get('description', ''), data['duration'], data['price'])
        )
        conn.commit()
        service_id = cursor.lastrowid
        conn.close()
        return jsonify({'id': service_id, 'message': 'Service created successfully'}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['PUT'])
@login_required
def update_service(service_id):
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE services SET name = ?, description = ?, duration = ?, price = ? WHERE id = ?",
            (data.get('name'), data.get('description', ''), data.get('duration'), data.get('price'), service_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Service updated successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@login_required
def delete_service(service_id):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Service deleted successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/barbers', methods=['GET'])
def get_barbers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM barbers")
    barbers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(barbers)

@app.route('/api/barbers', methods=['POST'])
@login_required
def create_barber():
    data = request.get_json()
    
    required = ['name']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO barbers (name, specialty, image) VALUES (?, ?, ?)",
            (data['name'], data.get('specialty', ''), data.get('image', ''))
        )
        conn.commit()
        barber_id = cursor.lastrowid
        conn.close()
        return jsonify({'id': barber_id, 'message': 'Barber created successfully'}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/barbers/<int:barber_id>', methods=['PUT'])
@login_required
def update_barber(barber_id):
    # Check if request has file upload
    if request.content_type and 'multipart/form-data' in request.content_type:
        name = request.form.get('name')
        specialty = request.form.get('specialty', '')
        image = request.form.get('image', '')
        
        # Handle file upload
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename:
                # Save the file
                filename = f"barber_{barber_id}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image = f"images/barbers/{filename}"
    else:
        data = request.get_json()
        name = data.get('name')
        specialty = data.get('specialty', '')
        image = data.get('image', '')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE barbers SET name = ?, specialty = ?, image = ? WHERE id = ?",
            (name, specialty, image, barber_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Barber updated successfully', 'image': image})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/barbers/<int:barber_id>', methods=['DELETE'])
@login_required
def delete_barber(barber_id):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM barbers WHERE id = ?", (barber_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Barber deleted successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/availability', methods=['GET'])
def get_availability():
    date = request.args.get('date')
    barber_id = request.args.get('barber_id')
    
    if not date or not barber_id:
        return jsonify({'error': 'Date and barber_id are required'}), 400
    
    # Generate all time slots (9 AM to 7 PM)
    all_slots = []
    for hour in range(9, 19):
        all_slots.append(f"{hour:02d}:00")
        all_slots.append(f"{hour:02d}:30")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT time FROM appointments WHERE date = ? AND barber_id = ? AND status != 'cancelled'",
        (date, barber_id)
    )
    booked = [row['time'] for row in cursor.fetchall()]
    conn.close()
    
    available = [slot for slot in all_slots if slot not in booked]
    return jsonify(available)

@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.get_json()
    
    required = ['customer_name', 'customer_phone', 'service_id', 'barber_id', 'date', 'time']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if slot is available
    cursor.execute(
        "SELECT id FROM appointments WHERE date = ? AND time = ? AND barber_id = ? AND status != 'cancelled'",
        (data['date'], data['time'], data['barber_id'])
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'This time slot is already booked'}), 409
    
    try:
        cursor.execute(
            '''INSERT INTO appointments (customer_name, customer_phone, customer_email, service_id, barber_id, date, time)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (data['customer_name'], data['customer_phone'], data.get('customer_email', ''),
             data['service_id'], data['barber_id'], data['date'], data['time'])
        )
        conn.commit()
        appointment_id = cursor.lastrowid
        conn.close()
        return jsonify({'id': appointment_id, 'message': 'Appointment booked successfully'}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    date = request.args.get('date')
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = '''
        SELECT a.*, s.name as service_name, s.duration, s.price, b.name as barber_name 
        FROM appointments a
        JOIN services s ON a.service_id = s.id
        JOIN barbers b ON a.barber_id = b.id
    '''
    
    if date:
        query += " WHERE a.date = ?"
        cursor.execute(query + " ORDER BY a.date, a.time", (date,))
    else:
        query += " ORDER BY a.date, a.time"
        cursor.execute(query)
    
    appointments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(appointments)

@app.route('/api/appointments/<int:appointment_id>', methods=['DELETE'])
@login_required
def cancel_appointment(appointment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Appointment cancelled successfully'})

@app.route('/api/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
def update_appointment(appointment_id):
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """UPDATE appointments SET 
                customer_name = ?, customer_phone = ?, customer_email = ?,
                service_id = ?, barber_id = ?, date = ?, time = ?, status = ?
            WHERE id = ?""",
            (
                data.get('customer_name'),
                data.get('customer_phone'),
                data.get('customer_email', ''),
                data.get('service_id'),
                data.get('barber_id'),
                data.get('date'),
                data.get('time'),
                data.get('status', 'confirmed'),
                appointment_id
            )
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Appointment updated successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments/<int:appointment_id>', methods=['DELETE'])
@login_required
def delete_appointment(appointment_id):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Appointment deleted successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    today = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) as total, SUM(s.price) as revenue FROM appointments a JOIN services s ON a.service_id = s.id WHERE a.date = ? AND a.status != 'cancelled'",
        (today,)
    )
    summary = dict(cursor.fetchone())
    
    cursor.execute(
        "SELECT a.*, s.name as service_name, b.name as barber_name FROM appointments a JOIN services s ON a.service_id = s.id JOIN barbers b ON a.barber_id = b.id WHERE a.date = ? AND a.status != 'cancelled' ORDER BY a.time",
        (today,)
    )
    appointments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'summary': summary, 'appointments': appointments})

# Serve frontend
@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

@app.route('/admin')
def serve_admin():
    # Check if already authenticated
    if session.get('authenticated'):
        return send_from_directory('public', 'admin.html')
    # Show login page
    return send_from_directory('public', 'login.html')

@app.route('/api/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    password = data.get('password', '')
    
    if password == ADMIN_PASSWORD:
        session['authenticated'] = True
        return jsonify({'success': True, 'message': 'Logged in successfully'})
    else:
        return jsonify({'success': False, 'message': 'Invalid password'}), 401

@app.route('/api/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    return jsonify({'authenticated': session.get('authenticated', False)})

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('public', path)

if __name__ == '__main__':
    print("Luxe Barbershop server running on http://localhost:5000")
    app.run(debug=True, port=5000)
