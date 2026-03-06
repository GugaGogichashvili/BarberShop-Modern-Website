const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

// Database setup
const db = new sqlite3.Database('./barbershop.db', (err) => {
    if (err) console.error('Database connection error:', err.message);
    else console.log('Connected to SQLite database');
});

// Create tables
db.serialize(() => {
    // Services table
    db.run(`CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        duration INTEGER NOT NULL,
        price REAL NOT NULL
    )`);

    // Barbers table
    db.run(`CREATE TABLE IF NOT EXISTS barbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialty TEXT,
        image TEXT
    )`);

    // Appointments table
    db.run(`CREATE TABLE IF NOT EXISTS appointments (
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
    )`);

    // Insert default data if tables are empty
    db.get("SELECT COUNT(*) as count FROM services", (err, row) => {
        if (row.count === 0) {
            // Insert services
            const services = [
                ['Classic Haircut', 'Traditional cut with clippers and scissors', 30, 35],
                ['Beard Trim', 'Professional beard shaping and trim', 20, 25],
                ['Full Service', 'Haircut + Beard trim + Hot towel', 50, 55],
                ['Buzz Cut', 'Single guard clipper cut', 15, 20],
                ['Kids Cut', 'For children under 12', 25, 25],
                ['Senior Cut', 'Classic styling for gentlemen 60+', 30, 30]
            ];
            
            services.forEach(s => {
                db.run("INSERT INTO services (name, description, duration, price) VALUES (?, ?, ?, ?)", s);
            });
        }
    });

    db.get("SELECT COUNT(*) as count FROM barbers", (err, row) => {
        if (row.count === 0) {
            const barbers = [
                ['James Wilson', 'Master Barber', 'barber1.jpg'],
                ['Michael Chen', 'Style Expert', 'barber2.jpg'],
                ['David Rodriguez', 'Beard Specialist', 'barber3.jpg'],
                ['Alex Thompson', 'Fade Expert', 'barber4.jpg']
            ];
            
            barbers.forEach(b => {
                db.run("INSERT INTO barbers (name, specialty, image) VALUES (?, ?, ?)", b);
            });
        }
    });
});

// API Routes

// Get all services
app.get('/api/services', (req, res) => {
    db.all("SELECT * FROM services", [], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

// Get all barbers
app.get('/api/barbers', (req, res) => {
    db.all("SELECT * FROM barbers", [], (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

// Get available time slots for a specific date and barber
app.get('/api/availability', (req, res) => {
    const { date, barber_id } = req.query;
    
    if (!date || !barber_id) {
        return res.status(400).json({ error: 'Date and barber_id are required' });
    }

    // Working hours: 9 AM to 7 PM
    const allSlots = [];
    for (let hour = 9; hour < 19; hour++) {
        allSlots.push(`${hour.toString().padStart(2, '0')}:00`);
        allSlots.push(`${hour.toString().padStart(2, '0')}:30`);
    }

    // Get booked appointments for this date and barber
    db.all(
        "SELECT time FROM appointments WHERE date = ? AND barber_id = ? AND status != 'cancelled'",
        [date, barber_id],
        (err, rows) => {
            if (err) return res.status(500).json({ error: err.message });
            
            const bookedSlots = rows.map(r => r.time);
            const availableSlots = allSlots.filter(slot => !bookedSlots.includes(slot));
            
            res.json(availableSlots);
        }
    );
});

// Create appointment
app.post('/api/appointments', (req, res) => {
    const { customer_name, customer_phone, customer_email, service_id, barber_id, date, time } = req.body;

    if (!customer_name || !customer_phone || !service_id || !barber_id || !date || !time) {
        return res.status(400).json({ error: 'All fields are required' });
    }

    // Check if slot is available
    db.get(
        "SELECT id FROM appointments WHERE date = ? AND time = ? AND barber_id = ? AND status != 'cancelled'",
        [date, time, barber_id],
        (err, row) => {
            if (err) return res.status(500).json({ error: err.message });
            if (row) return res.status(409).json({ error: 'This time slot is already booked' });

            // Create appointment
            db.run(
                `INSERT INTO appointments (customer_name, customer_phone, customer_email, service_id, barber_id, date, time) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)`,
                [customer_name, customer_phone, customer_email || '', service_id, barber_id, date, time],
                function(err) {
                    if (err) return res.status(500).json({ error: err.message });
                    res.json({ id: this.lastID, message: 'Appointment booked successfully' });
                }
            );
        }
    );
});

// Get all appointments (for admin/view)
app.get('/api/appointments', (req, res) => {
    const { date } = req.query;
    
    let query = `
        SELECT a.*, s.name as service_name, s.duration, s.price, b.name as barber_name 
        FROM appointments a
        JOIN services s ON a.service_id = s.id
        JOIN barbers b ON a.barber_id = b.id
    `;
    
    const params = [];
    if (date) {
        query += " WHERE a.date = ?";
        params.push(date);
    }
    
    query += " ORDER BY a.date, a.time";
    
    db.all(query, params, (err, rows) => {
        if (err) return res.status(500).json({ error: err.message });
        res.json(rows);
    });
});

// Cancel appointment
app.delete('/api/appointments/:id', (req, res) => {
    const { id } = req.params;
    
    db.run("UPDATE appointments SET status = 'cancelled' WHERE id = ?", [id], function(err) {
        if (err) return res.status(500).json({ error: err.message });
        res.json({ message: 'Appointment cancelled successfully' });
    });
});

// Get today's appointments summary
app.get('/api/dashboard', (req, res) => {
    const today = new Date().toISOString().split('T')[0];
    
    db.get(
        "SELECT COUNT(*) as total, SUM(s.price) as revenue FROM appointments a JOIN services s ON a.service_id = s.id WHERE a.date = ? AND a.status != 'cancelled'",
        [today],
        (err, row) => {
            if (err) return res.status(500).json({ error: err.message });
            
            db.all(
                "SELECT a.*, s.name as service_name, b.name as barber_name FROM appointments a JOIN services s ON a.service_id = s.id JOIN barbers b ON a.barber_id = b.id WHERE a.date = ? AND a.status != 'cancelled' ORDER BY a.time",
                [today],
                (err, appointments) => {
                    if (err) return res.status(500).json({ error: err.message });
                    res.json({ summary: row, appointments });
                }
            );
        }
    );
});

// Serve frontend
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
    console.log(`Luxe Barbershop server running on http://localhost:${PORT}`);
});
