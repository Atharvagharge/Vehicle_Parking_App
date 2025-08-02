from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import os
from models import init_db, get_db_connection

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Initialize database on startup
def create_tables():
    init_db()

# Create tables when app starts
with app.app_context():
    create_tables()

# Helper function to check if user is admin
def is_admin():
    return session.get('user_type') == 'admin'

# Helper function to check if user is logged in
def is_logged_in():
    return 'user_id' in session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form['user_type']
        
        conn = get_db_connection()
        
        if user_type == 'admin':
            # Check admin credentials (default: admin/admin)
            if username == 'admin' and password == 'admin':
                session['user_id'] = 1
                session['username'] = 'admin'
                session['user_type'] = 'admin'
                flash('Welcome Admin!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials', 'error')
        else:
            # Check user credentials
            user = conn.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_type'] = 'user'
                flash(f'Welcome {user["username"]}!', 'success')
                conn.close()
                return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        conn.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        
        conn = get_db_connection()
        
        # Check if username already exists
        existing_user = conn.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if existing_user:
            flash('Username already exists', 'error')
        else:
            # Create new user
            hashed_password = generate_password_hash(password)
            conn.execute(
                'INSERT INTO users (username, email, password, phone) VALUES (?, ?, ?, ?)',
                (username, email, hashed_password, phone)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            conn.close()
            return redirect(url_for('login'))
        
        conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Admin Routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get parking lots with spot counts
    lots = conn.execute('''
        SELECT pl.*, 
               COUNT(ps.id) as total_spots,
               SUM(CASE WHEN ps.status = 'A' THEN 1 ELSE 0 END) as available_spots,
               SUM(CASE WHEN ps.status = 'O' THEN 1 ELSE 0 END) as occupied_spots
        FROM parking_lots pl
        LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
        GROUP BY pl.id
    ''').fetchall()
    
    # Get recent bookings
    recent_bookings = conn.execute('''
        SELECT r.*, u.username, pl.prime_location_name, ps.id as spot_number
        FROM reservations r
        JOIN users u ON r.user_id = u.id
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.leaving_timestamp IS NULL
        ORDER BY r.parking_timestamp DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/dashboard.html', lots=lots, recent_bookings=recent_bookings)

@app.route('/admin/create_lot', methods=['GET', 'POST'])
def create_lot():
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        address = request.form['address']
        pincode = request.form['pincode']
        max_spots = int(request.form['max_spots'])
        
        conn = get_db_connection()
        
        # Create parking lot
        cursor = conn.execute(
            'INSERT INTO parking_lots (prime_location_name, price, address, pincode, maximum_number_of_spots) VALUES (?, ?, ?, ?, ?)',
            (name, price, address, pincode, max_spots)
        )
        lot_id = cursor.lastrowid
        
        # Create parking spots
        for i in range(max_spots):
            conn.execute(
                'INSERT INTO parking_spots (lot_id, status) VALUES (?, ?)',
                (lot_id, 'A')
            )
        
        conn.commit()
        conn.close()
        
        flash(f'Parking lot "{name}" created successfully with {max_spots} spots!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/create_lot.html')

@app.route('/admin/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        address = request.form['address']
        pincode = request.form['pincode']
        max_spots = int(request.form['max_spots'])
        
        # Get current spot count
        current_spots = conn.execute(
            'SELECT COUNT(*) as count FROM parking_spots WHERE lot_id = ?', (lot_id,)
        ).fetchone()['count']
        
        # Update parking lot
        conn.execute(
            'UPDATE parking_lots SET prime_location_name = ?, price = ?, address = ?, pincode = ?, maximum_number_of_spots = ? WHERE id = ?',
            (name, price, address, pincode, max_spots, lot_id)
        )
        
        # Adjust parking spots
        if max_spots > current_spots:
            # Add new spots
            for i in range(max_spots - current_spots):
                conn.execute(
                    'INSERT INTO parking_spots (lot_id, status) VALUES (?, ?)',
                    (lot_id, 'A')
                )
        elif max_spots < current_spots:
            # Remove excess spots (only available ones)
            spots_to_remove = current_spots - max_spots
            conn.execute(
                'DELETE FROM parking_spots WHERE lot_id = ? AND status = "A" LIMIT ?',
                (lot_id, spots_to_remove)
            )
        
        conn.commit()
        conn.close()
        
        flash('Parking lot updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # GET request - show edit form
    lot = conn.execute(
        'SELECT * FROM parking_lots WHERE id = ?', (lot_id,)
    ).fetchone()
    
    conn.close()
    
    if not lot:
        flash('Parking lot not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_lot.html', lot=lot)

@app.route('/admin/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Check if all spots are available
    occupied_spots = conn.execute(
        'SELECT COUNT(*) as count FROM parking_spots WHERE lot_id = ? AND status = "O"',
        (lot_id,)
    ).fetchone()['count']
    
    if occupied_spots > 0:
        flash('Cannot delete parking lot with occupied spots', 'error')
    else:
        # Delete reservations first
        conn.execute('DELETE FROM reservations WHERE spot_id IN (SELECT id FROM parking_spots WHERE lot_id = ?)', (lot_id,))
        # Delete parking spots
        conn.execute('DELETE FROM parking_spots WHERE lot_id = ?', (lot_id,))
        # Delete parking lot
        conn.execute('DELETE FROM parking_lots WHERE id = ?', (lot_id,))
        conn.commit()
        flash('Parking lot deleted successfully!', 'success')
    
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
def admin_users():
    if not is_logged_in() or not is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('admin/users.html', users=users)

# User Routes
@app.route('/user/dashboard')
def user_dashboard():
    if not is_logged_in() or is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get user's current and past bookings
    bookings = conn.execute('''
        SELECT r.*, pl.prime_location_name, pl.price, ps.id as spot_number
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.user_id = ?
        ORDER BY r.parking_timestamp DESC
    ''', (session['user_id'],)).fetchall()
    
    # Get available parking lots
    lots = conn.execute('''
        SELECT pl.*, 
               COUNT(ps.id) as total_spots,
               SUM(CASE WHEN ps.status = 'A' THEN 1 ELSE 0 END) as available_spots
        FROM parking_lots pl
        LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
        GROUP BY pl.id
        HAVING available_spots > 0
    ''').fetchall()
    
    conn.close()
    
    return render_template('user/dashboard.html', bookings=bookings, lots=lots)

@app.route('/user/book_spot/<int:lot_id>')
def book_spot(lot_id):
    if not is_logged_in() or is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Check if user has an active booking
    active_booking = conn.execute(
        'SELECT * FROM reservations WHERE user_id = ? AND leaving_timestamp IS NULL',
        (session['user_id'],)
    ).fetchone()
    
    if active_booking:
        flash('You already have an active parking reservation', 'error')
        conn.close()
        return redirect(url_for('user_dashboard'))
    
    # Find first available spot
    available_spot = conn.execute(
        'SELECT * FROM parking_spots WHERE lot_id = ? AND status = "A" LIMIT 1',
        (lot_id,)
    ).fetchone()
    
    if not available_spot:
        flash('No available spots in this parking lot', 'error')
        conn.close()
        return redirect(url_for('user_dashboard'))
    
    # Book the spot
    spot_id = available_spot['id']
    parking_timestamp = datetime.now()
    
    # Update spot status
    conn.execute(
        'UPDATE parking_spots SET status = "O" WHERE id = ?',
        (spot_id,)
    )
    
    # Create reservation
    conn.execute(
        'INSERT INTO reservations (spot_id, user_id, parking_timestamp) VALUES (?, ?, ?)',
        (spot_id, session['user_id'], parking_timestamp)
    )
    
    conn.commit()
    conn.close()
    
    flash(f'Parking spot {spot_id} booked successfully!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/release_spot/<int:reservation_id>')
def release_spot(reservation_id):
    if not is_logged_in() or is_admin():
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get reservation details
    reservation = conn.execute(
        'SELECT * FROM reservations WHERE id = ? AND user_id = ?',
        (reservation_id, session['user_id'])
    ).fetchone()
    
    if not reservation:
        flash('Reservation not found', 'error')
        conn.close()
        return redirect(url_for('user_dashboard'))
    
    if reservation['leaving_timestamp']:
        flash('Spot already released', 'error')
        conn.close()
        return redirect(url_for('user_dashboard'))
    
    # Calculate parking cost
    leaving_timestamp = datetime.now()
    parking_duration = leaving_timestamp - datetime.fromisoformat(reservation['parking_timestamp'])
    hours = max(1, int(parking_duration.total_seconds() / 3600))  # Minimum 1 hour
    
    # Get lot price
    lot_price = conn.execute('''
        SELECT pl.price FROM parking_lots pl
        JOIN parking_spots ps ON pl.id = ps.lot_id
        WHERE ps.id = ?
    ''', (reservation['spot_id'],)).fetchone()['price']
    
    total_cost = hours * lot_price
    
    # Update reservation
    conn.execute(
        'UPDATE reservations SET leaving_timestamp = ?, parking_cost = ? WHERE id = ?',
        (leaving_timestamp, total_cost, reservation_id)
    )
    
    # Update spot status
    conn.execute(
        'UPDATE parking_spots SET status = "A" WHERE id = ?',
        (reservation['spot_id'],)
    )
    
    conn.commit()
    conn.close()
    
    flash(f'Parking spot released successfully! Total cost: ₹{total_cost}', 'success')
    return redirect(url_for('user_dashboard'))

# API Routes (Optional)
@app.route('/api/lots')
def api_lots():
    conn = get_db_connection()
    lots = conn.execute('''
        SELECT pl.*, 
               COUNT(ps.id) as total_spots,
               SUM(CASE WHEN ps.status = 'A' THEN 1 ELSE 0 END) as available_spots
        FROM parking_lots pl
        LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
        GROUP BY pl.id
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(lot) for lot in lots])

@app.route('/api/lot/<int:lot_id>/spots')
def api_lot_spots(lot_id):
    conn = get_db_connection()
    spots = conn.execute(
        'SELECT * FROM parking_spots WHERE lot_id = ?', (lot_id,)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(spot) for spot in spots])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)