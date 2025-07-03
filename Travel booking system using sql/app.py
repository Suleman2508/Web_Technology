import pymysql
from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='Abuibu123',
        database='TravelBookingSystem',
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as total_bookings FROM Bookings')
    total_bookings = cursor.fetchone()['total_bookings']

    cursor.execute('SELECT SUM(Amount) as total_revenue FROM Payments')
    result = cursor.fetchone()
    total_revenue = result['total_revenue'] if result['total_revenue'] is not None else 0

    cursor.execute('''
        SELECT d.City, COUNT(*) as booking_count 
        FROM Bookings b
        JOIN TravelPackages p ON b.PackageID = p.PackageID
        JOIN Destinations d ON p.DestinationID = d.DestinationID
        GROUP BY d.City
        ORDER BY booking_count DESC
        LIMIT 1
    ''')
    top_destination = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('index.html', 
                           total_bookings=total_bookings, 
                           total_revenue=total_revenue, 
                           top_destination=top_destination)

@app.route('/add-booking', methods=['GET', 'POST'])
def add_booking():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        customer_id = request.form['customer_id']
        package_id = request.form['package_id']
        travel_date = request.form['travel_date']
        persons = request.form['persons']
        amount = request.form['amount']

        # Insert into Bookings
        cursor.execute('''
            INSERT INTO Bookings (CustomerID, PackageID, TravelDate, NumberOfPersons)
            VALUES (%s, %s, %s, %s)
        ''', (customer_id, package_id, travel_date, persons))

        # Get booking id
        booking_id = cursor.lastrowid

        # Insert payment
        cursor.execute('''
            INSERT INTO Payments (BookingID, Amount)
            VALUES (%s, %s)
        ''', (booking_id, amount))

        conn.commit()
        cursor.close()
        conn.close()
        return "Booking added successfully!"

    # GET: show form
    customers = cursor.execute("SELECT * FROM Customers")
    customers = cursor.fetchall()
    packages = cursor.execute("SELECT * FROM TravelPackages")
    packages = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("add_booking.html", customers=customers, packages=packages)

@app.route('/bookings')
def bookings():
    conn = get_db_connection()
    cursor = conn.cursor()

    filters = {
        'city': request.args.get('city'),
        'month': request.args.get('month'),
        'search_name': request.args.get('search_name'),
        'email': request.args.get('email'),
        'phone': request.args.get('phone'),
        'from_date': request.args.get('from_date'),
        'to_date': request.args.get('to_date'),
        'group_size': request.args.get('group_size'),
        'sort_by': request.args.get('sort_by')
    }

    query = '''
        SELECT b.BookingID, c.Name, c.Email, c.Phone, d.City, d.Country, p.PackageName, 
               b.TravelDate, b.NumberOfPersons, py.Amount
        FROM Bookings b
        JOIN Customers c ON b.CustomerID = c.CustomerID
        JOIN TravelPackages p ON b.PackageID = p.PackageID
        JOIN Destinations d ON p.DestinationID = d.DestinationID
        JOIN Payments py ON b.BookingID = py.BookingID
        WHERE 1=1
    '''

    params = []

    if filters['city']:
        query += ' AND LOWER(d.City) = %s'
        params.append(filters['city'].lower())
    if filters['month']:
        query += ' AND MONTH(b.TravelDate) = %s'
        params.append(int(filters['month']))
    if filters['search_name']:
        query += ' AND LOWER(c.Name) LIKE %s'
        params.append(f"%{filters['search_name'].lower()}%")
    if filters['email']:
        query += ' AND LOWER(c.Email) LIKE %s'
        params.append(f"%{filters['email'].lower()}%")
    if filters['phone']:
        query += ' AND c.Phone LIKE %s'
        params.append(f"%{filters['phone']}%")
    if filters['from_date']:
        query += ' AND b.TravelDate >= %s'
        params.append(filters['from_date'])
    if filters['to_date']:
        query += ' AND b.TravelDate <= %s'
        params.append(filters['to_date'])
    if filters['group_size']:
        if filters['group_size'] == 'solo':
            query += ' AND b.NumberOfPersons = 1'
        elif filters['group_size'] == 'small':
            query += ' AND b.NumberOfPersons BETWEEN 2 AND 3'
        elif filters['group_size'] == 'large':
            query += ' AND b.NumberOfPersons >= 4'
    if filters['sort_by']:
        if filters['sort_by'] == 'amount':
            query += ' ORDER BY py.Amount DESC'
        elif filters['sort_by'] == 'date':
            query += ' ORDER BY b.TravelDate DESC'
        elif filters['sort_by'] == 'persons':
            query += ' ORDER BY b.NumberOfPersons DESC'

    cursor.execute(query, params)
    bookings = cursor.fetchall()

    cursor.execute('''
        SELECT b.BookingID, c.Name, d.City, p.PackageName, b.NumberOfPersons
        FROM Bookings b
        JOIN Customers c ON b.CustomerID = c.CustomerID
        JOIN TravelPackages p ON b.PackageID = p.PackageID
        JOIN Destinations d ON p.DestinationID = d.DestinationID
        WHERE b.NumberOfPersons > 2
    ''')
    group_bookings = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('bookings.html', bookings=bookings, group_bookings=group_bookings)

@app.route('/revenue')
def revenue():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(Amount) as total FROM Payments')
    result = cursor.fetchone()
    revenue = result['total'] if result['total'] is not None else 0
    cursor.close()
    conn.close()
    return render_template('revenue.html', revenue=revenue)

@app.route('/top-customers')
def top_customers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.Name, c.Email, SUM(p.Amount) as total_spent,
               RANK() OVER (ORDER BY SUM(p.Amount) DESC) as spending_rank
        FROM Customers c
        JOIN Bookings b ON c.CustomerID = b.CustomerID
        JOIN Payments p ON b.BookingID = p.BookingID
        GROUP BY c.CustomerID
        ORDER BY total_spent DESC
    ''')
    top_customers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('top_customers.html', top_customers=top_customers)

if __name__ == '__main__':
    app.run(debug=True)
