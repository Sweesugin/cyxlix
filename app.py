import os
import sys
import requests
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cyxlix_secret_key")

# Get MongoDB database instance using the robust fallback client
from database.db import get_db
db = get_db()

# --- Decorators for Route Protection ---

def login_required(f):
    """Requires user (rider) authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if 'admin_id' in session:
                return redirect(url_for('admin_dashboard'))
            flash("Please login or signup to view this feature.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Requires admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            if 'user_id' in session:
                return redirect(url_for('user_dashboard'))
            flash("Please login or signup to view this feature.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# --- Helpers & AI Logic Engines ---

def get_recommendations(user_pref):
    """
    Ranks and matches bicycles based on rider preferences:
    ride_purpose, budget, terrain.
    """
    bicycles = list(db.bicycles.find({"status": "available"}))
    scored_bikes = []

    purpose = user_pref.get("ride_purpose", "")
    budget = user_pref.get("budget", "")
    terrain = user_pref.get("terrain", "")

    for bike in bicycles:
        score = 50 # base score
        rate = bike.get("hourly_rate", bike.get("price_per_hour", 0.0))
        
        # 1. Match Ride Purpose
        if purpose == "Mountain Trails" and bike["type"] == "Mountain":
            score += 30
        elif purpose == "Fitness" and bike["type"] == "Road":
            score += 30
        elif purpose == "Commute" and bike["type"] in ["Electric", "Hybrid", "City"]:
            score += 30
        elif purpose == "Leisure" and bike["type"] in ["Hybrid", "City", "Electric"]:
            score += 25

        # 2. Match Budget Limit (hourly rate comparison)
        if budget == "Low" and rate <= 40:
            score += 20
        elif budget == "Medium" and 40 < rate <= 80:
            score += 20
        elif budget == "High" and rate > 80:
            score += 20
        else:
            score -= 10 # penalty for out of budget

        # 3. Match Terrain
        bike_type = bike["type"]
        if terrain == "Paved" and bike_type in ["Road", "Hybrid", "City"]:
            score += 20
        elif terrain == "Unpaved" and bike_type in ["Mountain", "Fat Tire"]:
            score += 20
        elif terrain == "Mixed" and bike_type in ["Hybrid", "Mountain", "Touring"]:
            score += 15

        bike["match_score"] = min(99, max(40, score))
        scored_bikes.append(bike)

    scored_bikes.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_bikes[:3] # return top 3 matches


def check_overlap(bicycle_id, start_time, duration_hours):
    """
    Checks for interval overlaps with scheduled rides and active bookings to prevent double bookings.
    Condition: Start_1 < End_2 and Start_2 < End_1
    """
    end_time = start_time + timedelta(hours=duration_hours)
    
    # 1. Check scheduled rides
    schedules = db.scheduled_rides.find({
        "bicycle_id": ObjectId(bicycle_id),
        "status": "pending"
    })
    for s in schedules:
        try:
            s_start = datetime.strptime(f"{s['date']} {s['start_time']}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        s_end = s_start + timedelta(hours=float(s["duration_hours"]))
        
        # Overlap check: Start1 < End2 and Start2 < End1
        if start_time < s_end and s_start < end_time:
            return True # Overlap exists
            
    # 2. Check active bookings
    active_rentals = db.bookings.find({
        "bicycle_id": ObjectId(bicycle_id),
        "status": "active"
    })
    for r in active_rentals:
        r_start = r["created_at"]
        r_end = r_start + timedelta(hours=float(r["duration_hours"]))
        
        # Overlap check
        if start_time < r_end and r_start < end_time:
            return True # Overlap exists
            
    return False


def get_carbon_aggregates(user_id):
    """Aggregates carbon savings history entries for a specific rider."""
    records = list(db.carbon_savings.find({"user_id": ObjectId(user_id)}))
    
    total_co2 = 0.0
    total_money = 0.0
    total_distance = 0.0
    scores = []
    
    for r in records:
        total_co2 += r.get("carbon_saved_kg", 0.0)
        total_money += r.get("money_saved", 0.0)
        total_distance += r.get("distance_km", 0.0)
        scores.append(r.get("eco_score", 70))
        
    eco_score = int(sum(scores) / len(scores)) if scores else 70
    
    return {
        "total_co2": round(total_co2, 2),
        "total_money": round(total_money, 2),
        "total_distance": round(total_distance, 1),
        "eco_score": min(100, eco_score)
    }


# --- General Pages / Routes ---

@app.route("/")
def home():
    return render_template("home.html")


# --- Authentication System ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard'))
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "user")

        if role == "admin":
            admin = db.admins.find_one({"email": email})
            if admin and check_password_hash(admin["password"], password):
                session['admin_id'] = str(admin["_id"])
                session['admin_name'] = admin["name"]
                flash("Admin authenticated successfully.", "success")
                return redirect(url_for('admin_dashboard'))
        else:
            user = db.users.find_one({"email": email})
            if user and check_password_hash(user["password"], password):
                session['user_id'] = str(user["_id"])
                session['user_name'] = user["name"]
                session['user_email'] = user["email"]
                flash("Welcome back to Cyxlix!", "success")
                return redirect(url_for('user_dashboard'))

        flash("Invalid email address or credentials.", "error")
        return redirect(url_for('login'))

    return render_template("login.html", active_tab="user")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    if 'user_id' in session:
        return redirect(url_for('user_dashboard'))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        admin = db.admins.find_one({"email": email})
        if admin and check_password_hash(admin["password"], password):
            session['admin_id'] = str(admin["_id"])
            session['admin_name'] = admin["name"]
            flash("Admin authenticated successfully.", "success")
            return redirect(url_for('admin_dashboard'))

        flash("Invalid email address or credentials.", "error")
        return redirect(url_for('admin_login'))

    return render_template("login.html", active_tab="admin")


@app.route("/register", methods=["GET", "POST"])
def register():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard'))
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        # Rider Preferences
        ride_purpose = request.form.get("ride_purpose", "Commute")
        budget = request.form.get("budget", "Medium")
        distance = request.form.get("distance", "Medium (5-15 km)")
        terrain = request.form.get("terrain", "Paved")

        if not name or not email or not phone or not password or not confirm_password:
            flash("All fields are required.", "error")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register'))

        if db.users.find_one({"email": email}) or db.admins.find_one({"email": email}):
            flash("Account with this email already exists.", "error")
            return redirect(url_for('register'))

        # Hash password
        hashed_password = generate_password_hash(password)

        new_user = {
            "name": name,
            "email": email,
            "phone": phone,
            "password": hashed_password,
            "role": "user",
            "preferences": {
                "ride_purpose": ride_purpose,
                "budget": budget,
                "distance": distance,
                "terrain": terrain
            },
            "created_at": datetime.utcnow()
        }

        db.users.insert_one(new_user)
        flash("Rider account registered successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Successfully signed out.", "success")
    return redirect(url_for('login'))


# --- Rider Dashboard ---

@app.route("/dashboard")
@login_required
def user_dashboard():
    user_id = session['user_id']
    user = db.users.find_one({"_id": ObjectId(user_id)})
    
    # 1. Fetch statistics
    carbon_stats = get_carbon_aggregates(user_id)
    
    # 2. Fetch Active Bookings
    active_bookings = list(db.bookings.find({
        "user_id": ObjectId(user_id),
        "status": "active"
    }))
    
    # 3. Fetch Upcoming Scheduled Rides
    scheduled_rides = list(db.scheduled_rides.find({
        "user_id": ObjectId(user_id),
        "status": "pending"
    }))
    
    # 4. Fetch AI Recommended Bicycles
    recommended_bikes = get_recommendations(user.get("preferences", {}))
    
    # 5. Fetch Favorites
    fav_ids = [f["bicycle_id"] for f in db.favorites.find({"user_id": ObjectId(user_id)})]
    favorites = list(db.bicycles.find({"_id": {"$in": fav_ids}}))
    
    return render_template(
        "dashboard.html",
        carbon_stats=carbon_stats,
        active_bookings=active_bookings,
        scheduled_rides=scheduled_rides,
        recommended_bikes=recommended_bikes,
        favorites=favorites
    )


# --- Bicycles Fleet & Details ---

@app.route("/bicycles")
@login_required
def bicycles_list():
    search = request.args.get("search", "").strip()
    bike_type = request.args.get("type", "").strip()
    status = request.args.get("status", "").strip()
    sort_by = request.args.get("sort_by", "default")
    
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if bike_type:
        query["type"] = {"$regex": f"^{bike_type}$", "$options": "i"}
    if status:
        query["status"] = {"$regex": f"^{status}$", "$options": "i"}
        
    bicycles = list(db.bicycles.find(query))
    
    # Standardize keys in lists
    for b in bicycles:
        b["hourly_rate"] = b.get("hourly_rate", b.get("price_per_hour", 0.0))
        b["price_per_hour"] = b["hourly_rate"]
        b["image"] = b.get("image", b.get("image_url"))
        b["image_url"] = b["image"]
        b["rating"] = b.get("rating", b.get("average_rating", 5.0))
        b["average_rating"] = b["rating"]
        b["review_count"] = b.get("review_count", b.get("rating_count", 0))
        b["rating_count"] = b["review_count"]
    
    # Sorting logic
    if sort_by == "price_asc":
        bicycles.sort(key=lambda x: x["hourly_rate"])
    elif sort_by == "price_desc":
        bicycles.sort(key=lambda x: x["hourly_rate"], reverse=True)
    elif sort_by == "rating":
        bicycles.sort(key=lambda x: x["rating"], reverse=True)
        
    user_favorites = []
    if 'user_id' in session:
        favs = db.favorites.find({"user_id": ObjectId(session['user_id'])})
        user_favorites = [str(f["bicycle_id"]) for f in favs]
        
    filters = {"search": search, "type": bike_type, "status": status, "sort_by": sort_by}
    return render_template("bicycles.html", bicycles=bicycles, user_favorites=user_favorites, filters=filters)


@app.route("/bicycles/<bike_id>")
@login_required
def bicycle_detail(bike_id):
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike:
        flash("Bicycle record not found.", "error")
        return redirect(url_for('bicycles_list'))
        
    # Standardize keys
    bike["hourly_rate"] = bike.get("hourly_rate", bike.get("price_per_hour", 0.0))
    bike["price_per_hour"] = bike["hourly_rate"]
    bike["image"] = bike.get("image", bike.get("image_url"))
    bike["image_url"] = bike["image"]
    bike["rating"] = bike.get("rating", bike.get("average_rating", 5.0))
    bike["average_rating"] = bike["rating"]
    bike["review_count"] = bike.get("review_count", bike.get("rating_count", 0))
    bike["rating_count"] = bike["review_count"]

    # Get reviews for this bike
    reviews = list(db.reviews.find({"bicycle_id": ObjectId(bike_id)}).sort("timestamp", -1))
    
    # Get queue list count
    queue_count = db.reservation_queue.count_documents({
        "bicycle_id": ObjectId(bike_id),
        "status": "waiting"
    })
    
    min_date = datetime.utcnow().strftime("%Y-%m-%d")
    
    return render_template(
        "bicycle_detail.html",
        bike=bike,
        reviews=reviews,
        queue_count=queue_count,
        min_date=min_date
    )


# --- Favorites Logic ---

@app.route("/favorites")
@login_required
def favorites_page():
    user_id = session['user_id']
    favs = db.favorites.find({"user_id": ObjectId(user_id)})
    bike_ids = [f["bicycle_id"] for f in favs]
    bicycles = list(db.bicycles.find({"_id": {"$in": bike_ids}}))
    
    for b in bicycles:
        b["hourly_rate"] = b.get("hourly_rate", b.get("price_per_hour", 0.0))
        b["price_per_hour"] = b["hourly_rate"]
        b["image"] = b.get("image", b.get("image_url"))
        b["image_url"] = b["image"]
        b["rating"] = b.get("rating", b.get("average_rating", 5.0))
        b["average_rating"] = b["rating"]
        b["review_count"] = b.get("review_count", b.get("rating_count", 0))
        b["rating_count"] = b["review_count"]

    return render_template("favorites.html", bicycles=bicycles)


@app.route("/favorites/toggle/<bike_id>", methods=["POST"])
@login_required
def toggle_favorite(bike_id):
    user_id = session['user_id']
    redirect_to = request.form.get("redirect_to", "bicycles")
    
    existing = db.favorites.find_one({
        "user_id": ObjectId(user_id),
        "bicycle_id": ObjectId(bike_id)
    })
    
    if existing:
        db.favorites.delete_one({"_id": existing["_id"]})
        flash("Removed from favorites list.", "success")
    else:
        db.favorites.insert_one({
            "user_id": ObjectId(user_id),
            "bicycle_id": ObjectId(bike_id),
            "created_at": datetime.utcnow()
        })
        flash("Added to favorites list!", "success")
        
    if redirect_to == "favorites":
        return redirect(url_for('favorites_page'))
    return redirect(url_for('bicycles_list'))


# --- Immediate Rentals (Bookings) ---

@app.route("/book/<bike_id>")
@login_required
def book_bicycle(bike_id):
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike or bike["status"] != "available":
        flash("Bicycle is not available for rental right now.", "error")
        return redirect(url_for('bicycle_detail', bike_id=bike_id))
        
    bike["hourly_rate"] = bike.get("hourly_rate", bike.get("price_per_hour", 0.0))
    bike["price_per_hour"] = bike["hourly_rate"]
    bike["image"] = bike.get("image", bike.get("image_url"))
    bike["image_url"] = bike["image"]
    return render_template("booking.html", bike=bike)


@app.route("/book/confirm/<bike_id>", methods=["POST"])
@login_required
def confirm_booking(bike_id):
    user_id = session['user_id']
    duration = float(request.form.get("duration", 1.0))
    
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike or bike["status"] != "available":
        flash("Bicycle is no longer available.", "error")
        return redirect(url_for('bicycles_list'))
        
    # Prevent Double Booking
    now = datetime.utcnow()
    if check_overlap(bike_id, now, duration):
        flash("This cycle is already booked or scheduled during the requested time.", "error")
        return redirect(url_for('bicycle_detail', bike_id=bike_id))
        
    rate = bike.get("hourly_rate", bike.get("price_per_hour", 0.0))
    total_cost = round(duration * rate, 2)
    
    # Save booking record
    booking_data = {
        "user_id": ObjectId(user_id),
        "user_email": session['user_email'],
        "bicycle_id": ObjectId(bike_id),
        "bicycle_name": bike["name"],
        "duration_hours": duration,
        "rental_cost": total_cost,
        "status": "active",
        "created_at": now
    }
    db.bookings.insert_one(booking_data)
    
    # Update bicycle status to rented
    db.bicycles.update_one(
        {"_id": ObjectId(bike_id)},
        {"$set": {"status": "rented"}}
    )
    
    flash("Booking successful!", "success")
    return redirect(url_for('user_dashboard'))


@app.route("/bookings/end/<booking_id>")
@login_required
def end_rental(booking_id):
    booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking or booking["status"] != "active":
        flash("No active booking found.", "error")
        return redirect(url_for('user_dashboard'))
        
    # Mark booking completed
    db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "completed"}}
    )
    
    # Update bicycle status to available
    db.bicycles.update_one(
        {"_id": booking["bicycle_id"]},
        {"$set": {"status": "available"}}
    )
    
    flash("Bicycle returned successfully! Please rate your riding experience.", "success")
    return redirect(url_for('rate_bicycle_page', bike_id=str(booking["bicycle_id"])))


# --- Ride Scheduler ---

@app.route("/schedule/<bike_id>")
@login_required
def schedule_ride(bike_id):
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike:
        flash("Bicycle record not found.", "error")
        return redirect(url_for('bicycles_list'))
        
    bike["hourly_rate"] = bike.get("hourly_rate", bike.get("price_per_hour", 0.0))
    bike["price_per_hour"] = bike["hourly_rate"]
    bike["image"] = bike.get("image", bike.get("image_url"))
    bike["image_url"] = bike["image"]

    busy_slots = list(db.scheduled_rides.find({
        "bicycle_id": ObjectId(bike_id),
        "status": "pending"
    }))
    
    min_date = datetime.utcnow().strftime("%Y-%m-%d")
    return render_template("scheduler.html", bike=bike, busy_schedules=busy_slots, min_date=min_date)


@app.route("/schedule/confirm/<bike_id>", methods=["POST"])
@login_required
def confirm_schedule(bike_id):
    user_id = session['user_id']
    date_str = request.form.get("date")
    time_str = request.form.get("start_time")
    duration = float(request.form.get("duration", 1.0))
    pickup_location = request.form.get("pickup_location")
    
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike:
        flash("Bicycle not found.", "error")
        return redirect(url_for('bicycles_list'))
        
    try:
        proposed_start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        flash("Invalid date or time format.", "error")
        return redirect(url_for('schedule_ride', bike_id=bike_id))

    # Prevent Double Booking
    if check_overlap(bike_id, proposed_start, duration):
        flash("This cycle is already scheduled or booked during the requested time. Please select another slot.", "error")
        return redirect(url_for('schedule_ride', bike_id=bike_id))
        
    # Save schedule
    schedule_data = {
        "user_id": ObjectId(user_id),
        "user_email": session['user_email'],
        "bicycle_id": ObjectId(bike_id),
        "bicycle_name": bike["name"],
        "date": date_str,
        "start_time": time_str,
        "duration_hours": duration,
        "pickup_location": pickup_location,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    db.scheduled_rides.insert_one(schedule_data)
    
    flash(f"Successfully scheduled {bike['name']} on {date_str} at {time_str}!", "success")
    return redirect(url_for('user_dashboard'))


@app.route("/schedule/cancel/<schedule_id>")
@login_required
def cancel_schedule(schedule_id):
    db.scheduled_rides.update_one(
        {"_id": ObjectId(schedule_id)},
        {"$set": {"status": "cancelled"}}
    )
    flash("Scheduled ride cancelled.", "success")
    return redirect(url_for('user_dashboard'))


# --- Carbon Savings Dashboard ---

@app.route("/carbon")
@login_required
def carbon_savings():
    user_id = session['user_id']
    stats = get_carbon_aggregates(user_id)
    history = list(db.carbon_savings.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1))
    return render_template("carbon.html", carbon_stats=stats, history=history)


# --- Budget Planner ---

@app.route("/budget", methods=["GET", "POST"])
@login_required
def budget_planner():
    suggestions = None
    search_params = {}
    
    if request.method == "POST":
        budget_limit = float(request.form.get("budget_limit", 60.0))
        hours = float(request.form.get("hours", 2.0))
        distance_km = float(request.form.get("distance_km", 10.0))
        ride_purpose = request.form.get("ride_purpose", "Leisure")
        
        search_params = {
            "budget_limit": budget_limit,
            "hours": hours,
            "distance_km": distance_km,
            "ride_purpose": ride_purpose
        }
        
        # Get all available bicycles from MongoDB
        all_bikes = list(db.bicycles.find({"status": "available"}))
        if not all_bikes:
            all_bikes = list(db.bicycles.find({}))
            
        suggestions = []
        is_nearest_fallback = False
        message = ""
        
        # Calculate estimated cost for each bike
        for bike in all_bikes:
            rate = bike.get("hourly_rate", bike.get("price_per_hour", 0.0))
            bike["hourly_rate"] = rate
            bike["price_per_hour"] = rate
            bike["estimated_cost"] = rate * hours
            bike["image"] = bike.get("image", bike.get("image_url"))
            bike["image_url"] = bike["image"]

        # Filter eligible bikes where estimated_cost <= budget_limit
        eligible_bikes = [b for b in all_bikes if b["estimated_cost"] <= budget_limit]
        
        if eligible_bikes:
            # Show all that match, sorted by estimated_cost descending (closest to budget first)
            eligible_bikes.sort(key=lambda x: x["estimated_cost"], reverse=True)
            selected_bikes = eligible_bikes
            is_nearest_fallback = False
        else:
            # Budget is too low. Show the cheapest cycle as fallback.
            all_bikes.sort(key=lambda x: x["estimated_cost"])
            selected_bikes = [all_bikes[0]] if all_bikes else []
            is_nearest_fallback = True
            message = "This is the nearest option to your budget."
            
        for bike in selected_bikes:
            carbon = distance_km * 0.12 # 0.12 kg/km
            savings = distance_km * 4.50 # ₹4.50/km
            
            suggestions.append({
                "bike": bike,
                "estimated_cost": bike["estimated_cost"],
                "carbon_saved": carbon,
                "money_saved": savings,
                "is_nearest_fallback": is_nearest_fallback,
                "message": message if is_nearest_fallback else ""
            })
            
    return render_template("budget.html", suggestions=suggestions, search_params=search_params)


# --- AI Chatbot NLP API ---

@app.route("/chatbot")
@login_required
def chatbot_page():
    return render_template("chatbot.html")


@app.route("/chatbot/send", methods=["POST"])
@login_required
def chatbot_message():
    data = request.get_json() or {}
    message = data.get("message", "").lower().strip()
    
    # Keyword response logic
    if any(k in message for k in ["price", "cost", "how much", "rate"]):
        response = (
            "Our cycle plans are highly competitive!\n"
            "• Kids balance: ₹40/hour\n"
            "• Road bicycles: ₹40 - ₹80/hour\n"
            "• Hybrid/City/Gear: ₹40 - ₹60/hour\n"
            "• Premium E-Bikes: ₹120/hour."
        )
    elif any(k in message for k in ["book", "rent", "reserve", "schedule"]):
        response = (
            "Booking is simple!\n"
            "1. Browse our catalog under the 'Bicycles' page.\n"
            "2. Select a bicycle to view specifications.\n"
            "3. Choose 'Rent Immediately' or 'Schedule Future Ride' if logged in."
        )
    elif any(k in message for k in ["available", "availability", "fleet"]):
        avail = db.bicycles.count_documents({"status": "available"})
        rented = db.bicycles.count_documents({"status": "rented"})
        maint = db.bicycles.count_documents({"status": "maintenance"})
        response = (
            f"Currently in our fleet:\n"
            f"• Available cycles: {avail}\n"
            f"• Out on leases: {rented}\n"
            f"• Undergoing maintenance: {maint}"
        )
    elif any(k in message for k in ["carbon", "co2", "savings", "eco", "green"]):
        response = (
            "Every kilometer cycled saves approximately 0.12 kg of CO₂ emissions "
            "compared to standard passenger cars. Additionally, you save roughly ₹4.50/km in fuel/cabs "
            "while increasing your personal Eco Score statistics!"
        )
    elif any(k in message for k in ["weather", "forecast", "rain", "storm"]):
        response = (
            "We recommend checking your local weather forecast before riding. "
            "Always wear a helmet and ride slowly if the pavement is wet."
        )
    elif any(k in message for k in ["rule", "helmet", "safety", "speed"]):
        response = (
            "Critical Safety Guidelines:\n"
            "1. Wear a certified helmet at all times.\n"
            "2. Observe local street regulations and stay in bike lanes.\n"
            "3. Inspect brakes and tire inflation levels before departure.\n"
            "4. Lock your cycle using smart locks when parked."
        )
    elif any(k in message for k in ["queue", "waitlist", "wait"]):
        response = (
            "If a bicycle is currently rented out, click 'Join Reservation Queue' "
            "on its detail sheet. The system will hold your place and alert you in order when "
            "the bicycle is returned by the previous rider."
        )
    else:
        response = (
            "I'm here to assist you! You can ask questions about: "
            "pricing & costs, booking/scheduling procedures, cycle availability counts, "
            "carbon offsets, or riding safety rules."
        )
        
    return jsonify({"response": response})


# --- Smart Companion Mode ---

@app.route("/companion")
@login_required
def companion_mode():
    last_ride_stats = session.pop('last_ride_stats', None)
    return render_template("companion.html", last_ride_stats=last_ride_stats)


@app.route("/companion/save", methods=["POST"])
@login_required
def save_companion_ride():
    user_id = session['user_id']
    duration_sec = int(request.form.get("duration_seconds", 0))
    distance_km = float(request.form.get("distance_km", 0.0))
    
    co2_saved = round(distance_km * 0.12, 2)
    money_saved = round(distance_km * 4.50, 2)
    eco_score = min(100, int(distance_km * 5 + 75)) if distance_km > 0 else 70
    
    # Save companion ride
    ride_id = "ride_comp_" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
    ride_data = {
        "user_id": ObjectId(user_id),
        "ride_id": ride_id,
        "bicycle_name": "Companion Ride",
        "duration_seconds": duration_sec,
        "distance_km": distance_km,
        "co2_saved": co2_saved,
        "money_saved": money_saved,
        "eco_score": eco_score,
        "created_at": datetime.utcnow()
    }
    db.companion_rides.insert_one(ride_data)
    
    # Insert Carbon savings entry
    carbon_data = {
        "user_id": ObjectId(user_id),
        "user_email": session['user_email'],
        "ride_id": ride_id,
        "distance_km": distance_km,
        "carbon_saved_kg": co2_saved,
        "money_saved": money_saved,
        "eco_score": eco_score,
        "timestamp": datetime.utcnow()
    }
    db.carbon_savings.insert_one(carbon_data)
    
    session['last_ride_stats'] = {
        "distance": distance_km,
        "co2_saved": co2_saved,
        "money_saved": money_saved,
        "eco_score": eco_score
    }
    
    flash(f"Journey completed successfully! Logged {distance_km:.2f} km, saving {co2_saved:.2f} kg CO₂.", "success")
    return redirect(url_for('companion_mode'))


# --- Rating & Reviews ---

@app.route("/reviews/rate/<bike_id>")
@app.route("/review/<bike_id>")
@login_required
def rate_bicycle_page(bike_id):
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike:
        flash("Bicycle record not found.", "error")
        return redirect(url_for('user_dashboard'))
    return render_template("review.html", bike=bike)


@app.route("/reviews/submit", methods=["POST"])
@login_required
def submit_review():
    user_id = session['user_id']
    user_name = session['user_name']
    bike_id = request.form.get("bicycle_id")
    rating = int(request.form.get("rating", 5))
    review_text = request.form.get("review_text", "").strip()
    
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike:
        flash("Bicycle not found.", "error")
        return redirect(url_for('user_dashboard'))
        
    # Save review
    review_data = {
        "user_id": ObjectId(user_id),
        "user_name": user_name,
        "bicycle_id": ObjectId(bike_id),
        "bicycle_name": bike["name"],
        "rating": rating,
        "review_text": review_text,
        "timestamp": datetime.utcnow()
    }
    db.reviews.insert_one(review_data)
    
    # Re-calculate averages for this bike
    all_reviews = list(db.reviews.find({"bicycle_id": ObjectId(bike_id)}))
    count = len(all_reviews)
    avg = sum([r["rating"] for r in all_reviews]) / count if count > 0 else 5.0
    
    db.bicycles.update_one(
        {"_id": ObjectId(bike_id)},
        {"$set": {
            "average_rating": round(avg, 1),
            "rating": round(avg, 1),
            "rating_count": count,
            "review_count": count
        }}
    )
    
    flash("Thank you for your rating & review!", "success")
    return redirect(url_for('user_dashboard'))


# --- Reservation Queue ---

@app.route("/reservation-queue")
@login_required
def reservation_queue():
    user_id = session['user_id']
    queue_items = list(db.reservation_queue.find({"user_id": ObjectId(user_id)}).sort("joined_at", -1))
    
    for item in queue_items:
        bike = db.bicycles.find_one({"_id": item["bicycle_id"]})
        if bike:
            item["bike_image"] = bike.get("image", bike.get("image_url"))
            item["bike_status"] = bike.get("status")
            item["bike_rate"] = bike.get("hourly_rate", bike.get("price_per_hour"))
            
    return render_template("queue.html", queue_items=queue_items)


@app.route("/queue/join/<bike_id>", methods=["POST"])
@login_required
def join_queue(bike_id):
    user_id = session['user_id']
    user_name = session['user_name']
    user_email = session['user_email']
    
    bike = db.bicycles.find_one({"_id": ObjectId(bike_id)})
    if not bike:
        flash("Bicycle not found.", "error")
        return redirect(url_for('bicycles_list'))
        
    # Check if user is already in queue
    existing = db.reservation_queue.find_one({
        "user_id": ObjectId(user_id),
        "bicycle_id": ObjectId(bike_id),
        "status": "waiting"
    })
    
    if existing:
        flash("You are already in the reservation queue for this bicycle.", "info")
        return redirect(url_for('bicycle_detail', bike_id=bike_id))
        
    # Get current queue length to set position
    current_waiting = db.reservation_queue.count_documents({
        "bicycle_id": ObjectId(bike_id),
        "status": "waiting"
    })
    
    queue_record = {
        "user_id": ObjectId(user_id),
        "user_name": user_name,
        "user_email": user_email,
        "bicycle_id": ObjectId(bike_id),
        "bicycle_name": bike["name"],
        "joined_at": datetime.utcnow(),
        "position": current_waiting + 1,
        "status": "waiting"
    }
    db.reservation_queue.insert_one(queue_record)
    
    flash(f"Joined queue successfully! Your waitlist position is #{current_waiting + 1}.", "success")
    return redirect(url_for('bicycle_detail', bike_id=bike_id))


@app.route("/queue/leave/<queue_id>", methods=["POST"])
@login_required
def leave_queue(queue_id):
    user_id = session['user_id']
    queue_item = db.reservation_queue.find_one({"_id": ObjectId(queue_id), "user_id": ObjectId(user_id)})
    if queue_item:
        db.reservation_queue.delete_one({"_id": ObjectId(queue_id)})
        db.reservation_queue.update_many(
            {
                "bicycle_id": queue_item["bicycle_id"],
                "position": {"$gt": queue_item["position"]}
            },
            {"$inc": {"position": -1}}
        )
        flash("You have left the reservation waitlist.", "success")
    else:
        flash("Waitlist entry not found.", "error")
    return redirect(url_for('reservation_queue'))


# --- Admin Actions & Dashboard ---

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    # 1. Fetch real metrics from MongoDB
    total_bikes = db.bicycles.count_documents({})
    total_users = db.users.count_documents({})
    total_bookings = db.bookings.count_documents({})
    total_scheduled_rides = db.scheduled_rides.count_documents({})
    total_reviews = db.reviews.count_documents({})
    
    # Calculate total revenue in INR
    bookings = list(db.bookings.find({}))
    total_revenue = sum([b.get("rental_cost", 0.0) for b in bookings])

    carbon_records = list(db.carbon_savings.find({}))
    total_co2_saved = sum([c.get("carbon_saved_kg", 0.0) for c in carbon_records])
    total_distance = sum([c.get("distance_km", 0.0) for c in carbon_records])
    total_money_saved = sum([c.get("money_saved", 0.0) for c in carbon_records])

    stats = {
        "total_bikes": total_bikes,
        "total_users": total_users,
        "total_bookings": total_bookings,
        "total_scheduled_rides": total_scheduled_rides,
        "total_reviews": total_reviews,
        "total_revenue": round(total_revenue, 2),
        "total_distance": round(total_distance, 1),
        "total_co2_saved": round(total_co2_saved, 2),
        "total_money_saved": round(total_money_saved, 2)
    }

    # 2. Fetch full lists for tables
    bicycles = list(db.bicycles.find({}))
    users = list(db.users.find({}))
    scheduled_rides = list(db.scheduled_rides.find({}))
    reservation_queue = list(db.reservation_queue.find({}))
    reviews = list(db.reviews.find({}))

    # Standardize keys in templates
    for b in bicycles:
        b["hourly_rate"] = b.get("hourly_rate", b.get("price_per_hour", 0.0))
        b["price_per_hour"] = b["hourly_rate"]
        b["image"] = b.get("image", b.get("image_url"))
        b["image_url"] = b["image"]
        b["rating"] = b.get("rating", b.get("average_rating", 5.0))
        b["average_rating"] = b["rating"]

    data = {
        "bicycles": bicycles,
        "users": users,
        "bookings": bookings,
        "scheduled_rides": scheduled_rides,
        "reservation_queue": reservation_queue,
        "reviews": reviews
    }

    return render_template("admin_dashboard.html", stats=stats, data=data, hide_nav=True)


@app.route("/admin/bicycles/add", methods=["POST"])
@admin_required
def admin_add_bike():
    name = request.form.get("name")
    type_ = request.form.get("type")
    price = float(request.form.get("hourly_rate", 40.0))
    location = request.form.get("location")
    status = request.form.get("status", "available")
    image_url = request.form.get("image_url")
    description = request.form.get("description")
    
    gears = request.form.get("spec_gears")
    weight = request.form.get("spec_weight")
    frame = request.form.get("spec_frame")
    brakes = request.form.get("spec_brakes")
    
    specs = {
        "frame": frame,
        "weight": weight,
        "brakes": brakes
    }
    if type_ == "Electric Bike" or type_ == "Premium E-Bike":
        specs["motor"] = gears
        specs["battery"] = "36V 10Ah Lithium-ion"
    else:
        specs["gears"] = gears

    new_bike = {
        "name": name,
        "type": type_,
        "hourly_rate": price,
        "price_per_hour": price,
        "status": status,
        "image": image_url,
        "image_url": image_url,
        "description": description,
        "specifications": specs,
        "location": location,
        "rating": 5.0,
        "average_rating": 5.0,
        "review_count": 0,
        "rating_count": 0
    }
    
    db.bicycles.insert_one(new_bike)
    flash(f"Successfully added bicycle {name} to catalog.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/bicycles/edit/<bike_id>", methods=["POST"])
@admin_required
def admin_edit_bike(bike_id):
    name = request.form.get("name")
    type_ = request.form.get("type")
    price = float(request.form.get("hourly_rate"))
    location = request.form.get("location")
    status = request.form.get("status")
    image_url = request.form.get("image_url")
    description = request.form.get("description")
    
    db.bicycles.update_one(
        {"_id": ObjectId(bike_id)},
        {"$set": {
            "name": name,
            "type": type_,
            "hourly_rate": price,
            "price_per_hour": price,
            "location": location,
            "status": status,
            "image": image_url,
            "image_url": image_url,
            "description": description
        }}
    )
    flash(f"Successfully updated bicycle {name}.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/bicycles/delete/<bike_id>", methods=["POST"])
@admin_required
def admin_delete_bike(bike_id):
    db.bicycles.delete_one({"_id": ObjectId(bike_id)})
    flash("Bicycle removed from fleet catalog.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/users/delete/<user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    db.users.delete_one({"_id": ObjectId(user_id)})
    flash("User account deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/reviews/delete/<review_id>", methods=["POST"])
@admin_required
def admin_delete_review(review_id):
    review = db.reviews.find_one({"_id": ObjectId(review_id)})
    if review:
        db.reviews.delete_one({"_id": ObjectId(review_id)})
        
        bike_id = review["bicycle_id"]
        all_reviews = list(db.reviews.find({"bicycle_id": bike_id}))
        count = len(all_reviews)
        avg = sum([r["rating"] for r in all_reviews]) / count if count > 0 else 5.0
        
        db.bicycles.update_one(
            {"_id": bike_id},
            {"$set": {
                "average_rating": round(avg, 1),
                "rating": round(avg, 1),
                "rating_count": count,
                "review_count": count
            }}
        )
        flash("Review deleted and cycle statistics recalculated.", "success")
        
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/queue/notify/<queue_id>", methods=["POST"])
@admin_required
def admin_notify_queue(queue_id):
    db.reservation_queue.update_one(
        {"_id": ObjectId(queue_id)},
        {"$set": {"status": "notified"}}
    )
    flash("Waitlist user notified via system alert.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/queue/remove/<queue_id>", methods=["POST"])
@admin_required
def admin_remove_queue(queue_id):
    queue_item = db.reservation_queue.find_one({"_id": ObjectId(queue_id)})
    if queue_item:
        db.reservation_queue.delete_one({"_id": ObjectId(queue_id)})
        
        db.reservation_queue.update_many(
            {
                "bicycle_id": queue_item["bicycle_id"],
                "position": {"$gt": queue_item["position"]}
            },
            {"$inc": {"position": -1}}
        )
        flash("User removed from reservation waitlist.", "success")
        
    return redirect(url_for('admin_dashboard'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "error.html",
        error_title="Page Not Found",
        error_code=404,
        error_description="The page you are looking for does not exist or has been moved."
    ), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template(
        "error.html",
        error_title="Internal Server Error",
        error_code=500,
        error_description="An unexpected error occurred on our server. Please try again later."
    ), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

