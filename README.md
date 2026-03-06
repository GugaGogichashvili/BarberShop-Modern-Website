# Luxe Barbershop

A modern barbershop booking website with appointment management and admin dashboard.

## Features

- 📅 Online appointment booking
- 👨‍💼 Manage services, barbers, and appointments
- 🔐 Admin dashboard with password protection
- 📸 Upload barber photos
- 📱 Responsive design

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
python app.py
```

3. Open http://localhost:5000

## Admin Access

- URL: http://localhost:5000/admin
- Password: `Mesopotamia`

## Project Structure

```
barbershop/
├── app.py              # Flask backend
├── barbershop.db      # SQLite database
├── requirements.txt    # Python dependencies
├── public/
│   ├── index.html     # Main website
│   ├── admin.html     # Admin dashboard
│   ├── login.html     # Admin login
│   └── images/        # Images folder
└── .gitignore
```

## Deploying to Render

1. Push to GitHub
2. Create a new Web Service on Render
3. Set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python app.py`
4. Your app will be live!
