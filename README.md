# Cyxlix - Smart Cycle Rental Management System

A premium, modern Python Flask & MongoDB Atlas web application for smart cycle rentals. Cyxlix features role-based access control, real-time booking collision guards, a smart budget planner, carbon footprint tracking, an interactive AI Chatbot assistant, live stopwatch companion mode, and a bicycle reservation waitlist.

## Features
- **Clean White Rebranded Interface**: Beautiful, responsive layout with glass-morphic components.
- **Bicycle Management**: Full fleet CRUD for admins with 12 distinct high-quality variants.
- **Smart Budget Planner**: Suggests closest matching cycle variants based on budget, duration, and distance.
- **Companion Safety Mode**: A live stopwatch timer, simulation metrics (speed, distance, CO₂ offset, money saved in INR), and an SOS alert trigger.
- **Reservation Queue**: If a bicycle is currently rented out, users can join the waitlist queue and check their real-time queue position.
- **AI Chatbot**: Fast interactive answers regarding ride rules, rates, and extension help.

## Tech Stack
- Python Flask
- MongoDB Atlas (via PyMongo)
- python-dotenv
- Werkzeug security (password hashing)
- Bootstrap 5, FontAwesome, and Vanilla CSS

---

## Getting Started

### 1. Prerequisites
- **Python 3.8+**
- A **MongoDB Atlas** database cluster (or local MongoDB database)

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
MONGO_URI=mongodb+srv://icykid3399:icykid3399@cluster0.peaq7nk.mongodb.net/cyxlix_db?retryWrites=true&w=majority&appName=Cluster0
SECRET_KEY=cyxlix_secret_key
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed the Database
Before running the server, seed your MongoDB Atlas database with test accounts, 12 real cycle fleets, and mock records:
```bash
python database/seed.py
```

**Seeded Accounts**:
- **Rider (User):** `user@gmail.com` / `user123`
- **Admin:** `admin@gmail.com` / `admin123`

### 5. Run the Server
Start the development server:
```bash
python app.py
```
Open your browser and navigate to: `http://localhost:5000`
