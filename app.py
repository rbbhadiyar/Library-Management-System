from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace this with a strong random secret key

# Database connection
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Ram@0916',
        database='library_db'
    )
    return conn

# Landing page route
@app.route('/')
def landing():
    return render_template('landing.html')

# Signup page route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['fullname']
        email = request.form['email']
        phone_number = request.form['phone_number']
        address = request.form['address']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        if not re.match(r'^su-\d{5}@sitare\.org$', email):
            flash('Invalid email address. Please use an email of the format su-xxxxx@sitare.org', 'danger')
            return redirect(url_for('signup'))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users1 (username, password, role, name, email, phone_number, address) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (username, password, 'user', name, email, phone_number, address))
            conn.commit()
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash('Username already exists', 'danger')
            return redirect(url_for('signup'))
        finally:
            cur.close()
            conn.close()
        flash('Signup successful, please log in.', 'success')
        return redirect(url_for('userlogin'))
    return render_template('signup.html')

# Admin login route
@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    hashed_admin_password = generate_password_hash('admin123')  # Use hashed password

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and check_password_hash(hashed_admin_password, password):
            session['user_id'] = 'admin'
            session['role'] = 'admin'
            flash('Admin login successful', 'success')
            return redirect(url_for('index'))
        else:
            flash('Incorrect username or password', 'danger')
    return render_template('admin_login.html')

# User login route
@app.route('/userlogin', methods=['GET', 'POST'])
def userlogin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users1 WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['role'] = 'user'
            flash('User login successful', 'success')
            return redirect(url_for('user'))
        else:
            flash('User login failed. Please try again.', 'danger')
    return render_template('user_login.html')

# Main library route
@app.route('/index')
def index():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('adminlogin'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM books')
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', books=books)

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('adminlogin'))
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        publisher = request.form['publisher']
        copies = request.form['copies']

        try:
            copies = int(copies)
        except ValueError:
            flash('Invalid input for copies. Please enter a whole number.', 'error')
            return redirect(url_for('add_book'))
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM books WHERE isbn = %s', (isbn,))
        existing_count = cur.fetchone()[0]

        if existing_count > 0:
            flash('A book with this ISBN already exists. Please enter a different ISBN.', 'error')
            cur.close()
            conn.close()
            return redirect(url_for('add_book'))

        try:
            cur.execute('INSERT INTO books (title, author, isbn, publisher, copies) VALUES (%s, %s, %s, %s, %s)',
                        (title, author, isbn, publisher, copies))
            conn.commit()
            flash('Book added successfully', 'success')
        except Exception as e:
            flash(f'Error adding book: {str(e)}', 'error')
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/edit_book/<string:isbn>', methods=['GET', 'POST'])
def edit_book(isbn):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('adminlogin'))
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        publisher = request.form['publisher']
        copies = request.form['copies']

        cur.execute('UPDATE books SET title = %s, author = %s, publisher = %s, copies = %s WHERE isbn = %s',
                    (title, author, publisher, copies, isbn))
        conn.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('index'))

    cur.execute('SELECT * FROM books WHERE isbn = %s', (isbn,))
    book = cur.fetchone()
    cur.close()
    conn.close()

    return render_template('edit_book.html', book=book)


@app.route('/delete_book/<string:isbn>', methods=['POST'])
def delete_book(isbn):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM borrowed_books WHERE isbn = %s', (isbn,))
    cur.execute('DELETE FROM books WHERE isbn = %s', (isbn,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/adminsearch_books', methods=['GET'])
def adminsearch_books():
    query = request.args.get('query', '')
    if not query:
        flash('Please enter a search term.', 'warning')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(""" 
        SELECT * FROM books 
        WHERE title LIKE %s 
        OR author LIKE %s 
        OR isbn LIKE %s 
        OR publisher LIKE %s 
    """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('adminsearch_results.html', books=books, query=query)

@app.route('/user')
def user():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('userlogin'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM books')
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('user.html', books=books)

@app.route('/return_book', methods=['GET', 'POST'])
def return_book():
    if 'user_id' not in session:
        return redirect(url_for('userlogin'))
    
    if request.method == 'POST':
        print("try")
        isbn = request.form.get('isbn')
        user_id = session['user_id']

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            
            cur.execute('SELECT id FROM borrowed_books WHERE user_id = %s AND book_id = (SELECT id FROM books WHERE isbn = %s)', (user_id, isbn))
            borrowed_book = cur.fetchone()
            
            if borrowed_book:
                borrowed_book_id = borrowed_book[0]
                cur.execute('DELETE FROM borrowed_books WHERE id = %s', (borrowed_book_id,))
                cur.execute('UPDATE books SET copies = copies + 1 WHERE isbn = %s', (isbn,))
                conn.commit()
                flash('Book returned successfully', 'success')
            else:
                flash('You have not borrowed this book', 'danger')
                
        except Exception as e:
            flash(f'Error processing return: {str(e)}', 'danger')
            conn.rollback()
        
        finally:
            cur.close()
            conn.close()
            
        return redirect(url_for('user'))

    return render_template('return_book.html')

@app.route('/request_issue', methods=['POST'])
def request_issue():
    if 'user_id' not in session:
        return redirect(url_for('userlogin'))
    
    isbn = request.form['isbn']
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if the book exists and has available copies
    cur.execute('SELECT copies FROM books WHERE isbn = %s', (isbn,))
    book = cur.fetchone()

    if book and book[0] > 0:
        # Insert issue request into the database
        cur.execute('INSERT INTO issue_requests (user_id, isbn) VALUES (%s, %s)', (session['user_id'], isbn))
        conn.commit()
        flash('Issue request submitted successfully', 'success')
    else:
        flash('No copies of this book are available', 'danger')

    cur.close()
    conn.close()
    return redirect(url_for('user'))


@app.route('/issue_requests')
def issue_requests():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('adminlogin'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, u.username, b.title, b.author, r.isbn
        FROM issue_requests r
        JOIN users1 u ON r.user_id = u.id
        JOIN books b ON r.isbn = b.isbn
    """)
    requests = cur.fetchall()
    cur.close()
    conn.close()
    print(requests)

    return render_template('issue_requests.html', requests=requests)

@app.route('/issue_book/<int:request_id>', methods=['POST'])
def issue_book(request_id):

    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('adminlogin'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT user_id, isbn FROM issue_requests WHERE id = %s', (request_id,))
    request = cur.fetchone()
    
    if request:
        user_id, isbn = request
        try:
            cur.execute('INSERT INTO borrowed_books (user_id, isbn, issue_date) VALUES (%s, (SELECT id FROM books WHERE isbn = %s), NOW())', (user_id, isbn))
            cur.execute('UPDATE books SET copies = copies - 1 WHERE isbn = %s', (isbn,))
            cur.execute('DELETE FROM issue_requests WHERE id = %s', (request_id,))
            conn.commit()
            flash('Book issued successfully', 'success')
        except Exception as e:
            flash(f'Error issuing book: {str(e)}', 'danger')
            conn.rollback()
    if not request:
        flash('Issue request not found', 'danger')
        return redirect(url_for('issue_requests'))
    
    else:
        flash('Issue request not found', 'danger')

    cur.close()
    conn.close()
    return redirect(url_for('issue_requests'))

# @app.route('/issue_book/<int:request_id>', methods=['POST'])
# def issue_book(request_id):
#     print(f"Issue Book request for request ID: {request_id}")  # Debugging line

#     conn = get_db_connection()
#     cur = conn.cursor()
#     print("connection established")
#     # Fetch user_id and isbn from the request
#     cur.execute('SELECT user_id, isbn FROM issue_requests WHERE id = %s', (request_id,))
#     request = cur.fetchone()

#     print(f"Fetched request details: {request}")  # Debugging line

#     if request:
#         user_id, isbn = request
#         print("user_id",user_id)
#         print("isbn",isbn)
#         try:

#             if isbn:
                
#                 # Insert the record into borrowed_books
#                 insert_query = 'INSERT INTO borrowed_books (user_id, isbn, borrow_date) VALUES (%s, %s, NOW())'
#                 print(insert_query)
#                 cur.execute(insert_query, (user_id, isbn))
#                 conn.commit()  # Make sure to commit the transaction
#                 print("Record inserted successfully.")

#             # Update the number of copies available
#             cur.execute('UPDATE books SET copies = copies - 1 WHERE isbn = %s', (isbn,))

#             # Delete the request from issue_requests
#             cur.execute('DELETE FROM issue_requests WHERE id = %s', (request_id,))
#             print(f"Deleted issue request with id={request_id}")  # Debugging line

#             conn.commit()
#             flash('Book issued successfully', 'success')
#         except Exception as e:
#             print(str(e))
#             flash(f'Error issuing book: {str(e)}', 'danger')
#             conn.rollback()
#     else:
#         flash('Issue request not found', 'danger')
#         print("No matching request found in the database.")

#     cur.close()
#     conn.close()
#     return redirect(url_for('issue_requests'))


@app.route('/decline_request/<int:request_id>', methods=['POST'])
def decline_request(request_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('adminlogin'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM issue_requests WHERE id = %s', (request_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Issue request declined', 'success')
    return redirect(url_for('issue_requests'))

@app.route('/search_books', methods=['GET'])
def search_books():
    if 'user_id' not in session:
        return redirect(url_for('userlogin'))

    query = request.args.get('query', '')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM books 
        WHERE title LIKE %s 
        OR author LIKE %s 
        OR isbn LIKE %s 
        OR publisher LIKE %s
    """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('search_results.html', books=books, query=query)

@app.route('/adminlogout')
def adminlogout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('adminlogin'))

@app.route('/userlogout')
def userlogout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('User logged out successfully', 'success')
    return redirect(url_for('userlogin'))

if __name__ == '__main__':
    app.run(debug=True)
