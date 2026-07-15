import os
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_db
db = get_db()

def seed_database():
    print("Clearing existing collections...")
    collections = [
        "users", "admins", "bicycles", "bookings", "favorites",
        "carbon_savings", "reviews", "reservation_queue",
        "scheduled_rides", "companion_rides"
    ]
    for col in collections:
        db[col].delete_many({})
        print(f"Cleared collection: {col}")
        
    print("Hashing passwords using Werkzeug...")
    admin_password_hash = generate_password_hash("admin123")
    user_password_hash = generate_password_hash("user123")
    
    # 1. Seed Admin
    print("Seeding admins...")
    admin_data = {
        "email": "admin@gmail.com",
        "password": admin_password_hash,
        "name": "System Admin",
        "role": "admin",
        "created_at": datetime.utcnow()
    }
    db.admins.insert_one(admin_data)
    
    # 2. Seed Rider User
    print("Seeding users...")
    user_data = {
        "email": "user@gmail.com",
        "password": user_password_hash,
        "name": "Jane Doe",
        "phone": "+91 9876543210",
        "role": "user",
        "preferences": {
            "ride_purpose": "Commute",
            "budget": "Medium",
            "distance": "Medium (5-15 km)",
            "terrain": "Paved"
        },
        "created_at": datetime.utcnow()
    }
    user_id = db.users.insert_one(user_data).inserted_id
    
    # 3. Seed Bicycles
    print("Seeding bicycles...")
    bicycles_data = [
        {
            "name": "Apex Mountain Rider",
            "type": "Mountain",
            "hourly_rate": 60,
            "price_per_hour": 60.0,
            "status": "available",
            "image": "/static/images/cycles/mountain_bike.jpg",
            "image_url": "/static/images/cycles/mountain_bike.jpg",
            "description": "Built for rugged trails, rock paths, and unpaved terrains. Features 21-speed gears, full suspension, and heavy-duty knobby tires.",
            "specifications": {
                "gears": "21 Speed Shimano",
                "weight": "14.5 kg",
                "frame": "6061 Aluminum Alloy",
                "brakes": "Hydraulic Disc Brakes"
            },
            "location": "Central Station A",
            "rating": 4.7,
            "average_rating": 4.7,
            "review_count": 3,
            "rating_count": 3
        },
        {
            "name": "Urban Glide Pro",
            "type": "Road",
            "hourly_rate": 40,
            "price_per_hour": 40.0,
            "status": "available",
            "image": "/static/images/cycles/road_bike.jpg",
            "image_url": "/static/images/cycles/road_bike.jpg",
            "description": "Ultra-lightweight frame designed for speed and smooth asphalt commuting. Perfect for fast urban rides and fitness routines.",
            "specifications": {
                "gears": "18 Speed Shimano Claris",
                "weight": "9.8 kg",
                "frame": "Carbon Fiber Fork / Alu Frame",
                "brakes": "Caliper Rim Brakes"
            },
            "location": "North Plaza Terminal",
            "rating": 4.5,
            "average_rating": 4.5,
            "review_count": 2,
            "rating_count": 2
        },
        {
            "name": "EcoVolt Commuter",
            "type": "Electric",
            "hourly_rate": 100,
            "price_per_hour": 100.0,
            "status": "available",
            "image": "/static/images/cycles/electric_bike.jpg",
            "image_url": "/static/images/cycles/electric_bike.jpg",
            "description": "Pedal-assisted electric smart bike with an integrated battery. Ride further and climb hills with absolute ease. Charge lasts up to 60 km.",
            "specifications": {
                "motor": "250W Brushless Motor",
                "battery": "36V 10.4Ah Lithium-ion",
                "weight": "18.2 kg",
                "brakes": "Tektro Mechanical Disc"
            },
            "location": "Central Station A",
            "rating": 4.9,
            "average_rating": 4.9,
            "review_count": 5,
            "rating_count": 5
        },
        {
            "name": "City Explorer Hybrid",
            "type": "Hybrid",
            "hourly_rate": 60,
            "price_per_hour": 60.0,
            "status": "available",
            "image": "/static/images/cycles/hybrid_bike.jpg",
            "image_url": "/static/images/cycles/hybrid_bike.jpg",
            "description": "Combines the speed of a road bike with the durability of a mountain bike. Best suited for daily errands, casual parks, and mixed trails.",
            "specifications": {
                "gears": "7 Speed MicroSHIFT",
                "weight": "12.8 kg",
                "frame": "Hi-Ten Steel Comfort Frame",
                "brakes": "Linear Pull V-Brakes"
            },
            "location": "East Gate Depot",
            "rating": 4.2,
            "average_rating": 4.2,
            "review_count": 4,
            "rating_count": 4
        },
        {
            "name": "Metro Step-Through",
            "type": "City",
            "hourly_rate": 40,
            "price_per_hour": 40.0,
            "status": "available",
            "image": "/static/images/cycles/city_bike.jpg",
            "image_url": "/static/images/cycles/city_bike.jpg",
            "description": "Ergonomic city cruiser with step-through frame, utility front basket, and dual mudguards. Unbeatable comfort for short neighborhood grocery trips.",
            "specifications": {
                "gears": "3 Speed Nexus Hub",
                "weight": "15.0 kg",
                "frame": "Step-Thru Aluminum Comfort",
                "brakes": "Coaster & Front Drum Brakes"
            },
            "location": "West Hills Outpost",
            "rating": 4.6,
            "average_rating": 4.6,
            "review_count": 4,
            "rating_count": 4
        },
        {
            "name": "Mini Sprinter Junior",
            "type": "Kids",
            "hourly_rate": 40,
            "price_per_hour": 40.0,
            "status": "available",
            "image": "/static/images/cycles/kids_bike.jpg",
            "image_url": "/static/images/cycles/kids_bike.jpg",
            "description": "Safety-first kids bicycle with training wheel options, chain guards, and high-visibility decals. Perfect for children aged 5-9.",
            "specifications": {
                "gears": "Single Speed",
                "weight": "8.2 kg",
                "frame": "Steel Kid Frame",
                "brakes": "Coaster & Hand Brakes"
            },
            "location": "North Plaza Terminal",
            "rating": 4.4,
            "average_rating": 4.4,
            "review_count": 1,
            "rating_count": 1
        },
        {
            "name": "Metro Shift 7-Speed",
            "type": "Gear",
            "hourly_rate": 60,
            "price_per_hour": 60.0,
            "status": "available",
            "image": "/static/images/cycles/gear_cycle.jpg",
            "image_url": "/static/images/cycles/gear_cycle.jpg",
            "description": "Classic 7-speed gear cycle engineered for smooth shifting and durable urban utility. Excellent choice for general daily transit.",
            "specifications": {
                "gears": "7 Speed Shimano Tourney",
                "weight": "13.0 kg",
                "frame": "Steel Commuter Frame",
                "brakes": "Rim V-Brakes"
            },
            "location": "East Gate Depot",
            "rating": 4.3,
            "average_rating": 4.3,
            "review_count": 3,
            "rating_count": 3
        },
        {
            "name": "Volt Cruiser Elite",
            "type": "Premium E-Bike",
            "hourly_rate": 120,
            "price_per_hour": 120.0,
            "status": "rented",
            "image": "/static/images/cycles/premium_ebike.jpg",
            "image_url": "/static/images/cycles/premium_ebike.jpg",
            "description": "Premium cruiser-style electric bicycle with leather grips and a plush saddle. Makes long scenic rides along the coast feel like a breeze.",
            "specifications": {
                "motor": "350W Hub Motor",
                "battery": "48V 12Ah Removable Battery",
                "weight": "21.0 kg",
                "brakes": "Hydraulic Disc Brakes"
            },
            "location": "Waterfront Station B",
            "rating": 4.8,
            "average_rating": 4.8,
            "review_count": 8,
            "rating_count": 8
        },
        {
            "name": "Skyline Step-Thru",
            "type": "Women",
            "hourly_rate": 60,
            "price_per_hour": 60.0,
            "status": "available",
            "image": "/static/images/cycles/womens_bike.jpg",
            "image_url": "/static/images/cycles/womens_bike.jpg",
            "description": "Elegant step-through bicycle in beautiful pastel color, featuring high-end comfort grips and a light frame.",
            "specifications": {
                "gears": "6 Speed Shimano",
                "weight": "13.5 kg",
                "frame": "Alloy Step-Thru",
                "brakes": "Tektro V-Brakes"
            },
            "location": "Central Station A",
            "rating": 4.6,
            "average_rating": 4.6,
            "review_count": 2,
            "rating_count": 2
        },
        {
            "name": "Pack & Go Foldable",
            "type": "Folding",
            "hourly_rate": 80,
            "price_per_hour": 80.0,
            "status": "available",
            "image": "/static/images/cycles/folding_bike.jpg",
            "image_url": "/static/images/cycles/folding_bike.jpg",
            "description": "Convenient folding bike designed for multi-modal travel. Folds down in seconds for transit storage or office desks.",
            "specifications": {
                "gears": "7 Speed Shimano",
                "weight": "11.2 kg",
                "frame": "Aluminum Folding Frame",
                "brakes": "Mechanical Disc Brakes"
            },
            "location": "North Plaza Terminal",
            "rating": 4.5,
            "average_rating": 4.5,
            "review_count": 3,
            "rating_count": 3
        },
        {
            "name": "Continental Expedition",
            "type": "Touring",
            "hourly_rate": 100,
            "price_per_hour": 100.0,
            "status": "available",
            "image": "/static/images/cycles/touring_bike.jpg",
            "image_url": "/static/images/cycles/touring_bike.jpg",
            "description": "Ultimate long-distance tourer equipped with front and rear racks, multiple gear ranges, and a super sturdy chassis.",
            "specifications": {
                "gears": "30 Speed Shimano Deore",
                "weight": "14.2 kg",
                "frame": "Chromoly Steel Touring Frame",
                "brakes": "TRP Spyre Mechanical Disc"
            },
            "location": "East Gate Depot",
            "rating": 4.9,
            "average_rating": 4.9,
            "review_count": 4,
            "rating_count": 4
        },
        {
            "name": "Sand & Snow Goliath",
            "type": "Fat Tire",
            "hourly_rate": 150,
            "price_per_hour": 150.0,
            "status": "available",
            "image": "/static/images/cycles/fat_tire_bike.jpg",
            "image_url": "/static/images/cycles/fat_tire_bike.jpg",
            "description": "Oversized fat tires designed to cruise through sand, snow, mud, and loose gravel with maximum stability.",
            "specifications": {
                "gears": "9 Speed Shimano Alivio",
                "weight": "16.5 kg",
                "frame": "6061 Custom Alloy",
                "brakes": "SRAM Level Hydraulic Disc"
            },
            "location": "Waterfront Station B",
            "rating": 4.7,
            "average_rating": 4.7,
            "review_count": 5,
            "rating_count": 5
        },
        {
            "name": "Trail Blazer Gear",
            "type": "Gear",
            "hourly_rate": 55,
            "price_per_hour": 55.0,
            "status": "maintenance",
            "image": "/static/images/cycles/gear_cycle.jpg",
            "image_url": "/static/images/cycles/gear_cycle.jpg",
            "description": "Rugged all-weather gear cycle under periodic maintenance. Optimized for reliability and longevity.",
            "specifications": {
                "gears": "14 Speed Shimano Tourney",
                "weight": "13.5 kg",
                "frame": "Steel Comfort Frame",
                "brakes": "Rim V-Brakes"
            },
            "location": "East Gate Depot",
            "rating": 4.0,
            "average_rating": 4.0,
            "review_count": 1,
            "rating_count": 1
        },
        {
            "name": "E-Volt Cargo",
            "type": "Electric",
            "hourly_rate": 110,
            "price_per_hour": 110.0,
            "status": "rented",
            "image": "/static/images/cycles/electric_bike.jpg",
            "image_url": "/static/images/cycles/electric_bike.jpg",
            "description": "Heavy-duty electric cargo bike with pedal-assist. Built for carrying goods or comfortable long commutes.",
            "specifications": {
                "motor": "500W Mid-drive Motor",
                "battery": "48V 15Ah Battery",
                "weight": "24.0 kg",
                "brakes": "Hydraulic Disc Brakes"
            },
            "location": "Central Station A",
            "rating": 4.8,
            "average_rating": 4.8,
            "review_count": 2,
            "rating_count": 2
        },
        {
            "name": "Cruiser Comfort",
            "type": "City",
            "hourly_rate": 45,
            "price_per_hour": 45.0,
            "status": "available",
            "image": "/static/images/cycles/city_bike.jpg",
            "image_url": "/static/images/cycles/city_bike.jpg",
            "description": "Relaxed-geometry city cruiser for comfortable daily transport and casual leisure rides around town.",
            "specifications": {
                "gears": "Single Speed",
                "weight": "14.0 kg",
                "frame": "Steel Step-Thru Frame",
                "brakes": "Coaster Brakes"
            },
            "location": "West Hills Outpost",
            "rating": 4.4,
            "average_rating": 4.4,
            "review_count": 3,
            "rating_count": 3
        }
    ]
    
    bike_ids = []
    for bike in bicycles_data:
        inserted = db.bicycles.insert_one(bike)
        bike_ids.append(inserted.inserted_id)
        print(f"Inserted bicycle: {bike['name']} ({inserted.inserted_id})")
        
    # 4. Seed Carbon Savings history for Jane Doe (user_id)
    print("Seeding carbon savings statistics...")
    carbon_records = [
        {
            "user_id": user_id,
            "ride_id": "ride_mock_1",
            "distance_km": 12.5,
            "carbon_saved_kg": round(12.5 * 0.12, 2),
            "money_saved": round(12.5 * 4.50, 2),
            "eco_score": 85,
            "timestamp": datetime.utcnow() - timedelta(days=5)
        },
        {
            "user_id": user_id,
            "ride_id": "ride_mock_2",
            "distance_km": 8.2,
            "carbon_saved_kg": round(8.2 * 0.12, 2),
            "money_saved": round(8.2 * 4.50, 2),
            "eco_score": 90,
            "timestamp": datetime.utcnow() - timedelta(days=3)
        },
        {
            "user_id": user_id,
            "ride_id": "ride_mock_3",
            "distance_km": 15.4,
            "carbon_saved_kg": round(15.4 * 0.12, 2),
            "money_saved": round(15.4 * 4.50, 2),
            "eco_score": 95,
            "timestamp": datetime.utcnow() - timedelta(days=1)
        }
    ]
    db.carbon_savings.insert_many(carbon_records)
    
    # 5. Seed Reviews
    print("Seeding reviews...")
    reviews_records = [
        {
            "user_id": user_id,
            "user_name": "Jane Doe",
            "bicycle_id": bike_ids[0],
            "rating": 5,
            "review_text": "Incredible suspension! Took this on the woodland trail and it handled like a dream. Highly recommend.",
            "timestamp": datetime.utcnow() - timedelta(days=4)
        },
        {
            "user_id": user_id,
            "user_name": "Jane Doe",
            "bicycle_id": bike_ids[1],
            "rating": 4,
            "review_text": "Very lightweight and fast on streets. Wish the seat was slightly softer, but otherwise a solid choice.",
            "timestamp": datetime.utcnow() - timedelta(days=2)
        }
    ]
    db.reviews.insert_many(reviews_records)
    
    # 6. Seed Scheduled Rides
    print("Seeding scheduled rides...")
    scheduled_records = [
        {
            "user_id": user_id,
            "bicycle_id": bike_ids[2],
            "bicycle_name": "EcoVolt Commuter",
            "date": (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "start_time": "10:00",
            "duration_hours": 3.0,
            "pickup_location": "Central Station A",
            "status": "pending",
            "created_at": datetime.utcnow()
        }
    ]
    db.scheduled_rides.insert_many(scheduled_records)
    
    # 7. Seed Reservation Queue (one person waiting for Volt Cruiser Elite)
    print("Seeding reservation queue...")
    queue_record = {
        "user_id": user_id,
        "user_name": "Jane Doe",
        "user_email": "user@gmail.com",
        "bicycle_id": bike_ids[7], # Volt Cruiser Elite (index 7)
        "bicycle_name": "Volt Cruiser Elite",
        "joined_at": datetime.utcnow() - timedelta(hours=2),
        "position": 1,
        "status": "waiting"
    }
    db.reservation_queue.insert_one(queue_record)
 
    print("\nDatabase seeded successfully!")
    print(f"Admin Account: admin@gmail.com / admin123")
    print(f"User Account:  user@gmail.com / user123")
 
if __name__ == "__main__":
    seed_database()
