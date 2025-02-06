import MySQLdb
from flask import Flask, render_template, request, redirect, url_for, session, flash, json, jsonify, send_file
from flask_mysqldb import MySQL
from datetime import datetime,timedelta,time
from docx import Document
import io,pytz
import random
import os
from werkzeug.utils import secure_filename
from flask import Flask, send_from_directory, abort
from apscheduler.schedulers.background import BackgroundScheduler
import time # To simulate time
from functools import wraps
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'chakri1234'
app.config['MYSQL_DB'] = 'emp'

mysql = MySQL(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'disputes.batalks@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'lfak qpxp rahl puqp'  # Use an app password if using Gmail
app.config['MAIL_DEFAULT_SENDER'] = 'disputes.batalks@gmail.com'
mail = Mail(app)

@app.route('/')
def index():
    return render_template('sign-up.html')

@app.route('/header')
def header():
    return render_template('header.html')

@app.route('/dispute')
def dispute():
    return render_template('dispute.html')


@app.route('/submit_dispute', methods=['POST'])
def submit_dispute():
    try:
        username = session.get('username')
        data = request.json
        ticket_id = data.get('id')
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        data_dis = data.get('data_dis')
        status = "pending"
        created_at = datetime.now()  # Get the current timestamp

        if not all([ticket_id, name, email, phone, data_dis, username, status]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # Insert into the database
        cur = mysql.connection.cursor()
        cur.execute('''
            INSERT INTO disputes (ticket_id, full_name, email, phone, dispute_details, username, status, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (ticket_id, name, email, phone, data_dis, username, status, created_at))
        
        mysql.connection.commit()
        cur.close()

        # Send confirmation email
        send_dispute_email(email, name, ticket_id)

        return jsonify({"success": True, "message": "Dispute submitted successfully, and email sent"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def send_dispute_email(email, name, ticket_id):
    
    try:
        subject = "Dispute Ticket Submitted Successfully"
        body = f"""
        Hello {name},

        Your dispute (Ticket ID: {ticket_id}) has been submitted successfully.
        Our team will review it and respond within 14 days.

        Thank you for your patience.

        Best regards,
        Support Team
        """

        msg = Message(subject, recipients=[email])
        msg.body = body
        mail.send(msg)
        print("ok")

    except Exception as e:
        print(f"Error sending email: {e}")

def send_dispute_review_email(email, name, ticket_id, status, message):
    try:
        subject = f"Dispute Ticket ID {ticket_id} - {status}"
        body = f"""
        Hello {name},

        Your dispute (Ticket ID: {ticket_id}) has been reviewed.

        Reviewer’s Message:{message}

        Thank you for reaching out to us.

        Best regards,
        Support Team
        """

        msg = Message(subject, recipients=[email])
        msg.body = body
        mail.send(msg)
        print("Email sent successfully.")

    except Exception as e:
        print(f"Error sending email: {e}")

    

# API Endpoint to Handle Dispute Updates
@app.route('/update_dispute_status', methods=['POST'])
def update_dispute_status():
    data = request.form
    dispute_id = data.get('id')
    status = data.get('status')
    message = data.get('message', 'No additional comments.')
    email = data.get('email')
    name = data.get('name')

    # Send email notification
    send_dispute_review_email(email, name, dispute_id, status, message)

    return jsonify({"success": True, "message": "Dispute status updated and email sent."})

@app.route('/attendence', methods=['GET', 'POST'])
def attendence():
    user_role = session.get('user_role')
    username = session.get('username')
    current_time2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not username:
        # return jsonify({'message': "", 'redirect': '/login'}), 401
        return '''
            <script type="text/javascript">
                alert("Access denied. Please log in.");
                window.location.href = "/";  // Redirect to the desired page after alert
            </script>
        '''

    # Restrict attendance update/insert before 9:00 AM
    current_time = datetime.now().time()
    earliest_allowed_time = time(12, 15, 0)  # 9:00 AM
    if current_time < earliest_allowed_time:
        return '''
            <script type="text/javascript">
                alert("Attendance cannot be updated or inserted before 9:00 AM.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''

    if request.method == 'POST':
        date = request.form['date']
        option = request.form['option']

        cur = mysql.connection.cursor()

        # Check if attendance exists for the date
        cur.execute("SELECT * FROM attendence WHERE date = %s AND username = %s", (date, username))
        existing_entry = cur.fetchone()

        if existing_entry:
            updated_index = 5
            if existing_entry[updated_index]:
                cur.close()
                return jsonify({'message': "You can only update your attendance once for the same date."}), 400
            else:
                cur.execute("UPDATE attendence SET type = %s, updated = TRUE, created_at = %s WHERE date = %s AND username = %s", 
                            (option, current_time2, date, username))
                mysql.connection.commit()
        else:
            cur.execute("INSERT INTO attendence (username, date, type, created_at, updated) VALUES (%s, %s, %s, %s, %s)", 
                        (username, date, option, current_time2, True))
            mysql.connection.commit()

        today_date = datetime.now().date()
        cur.execute("SELECT checkin, checkout FROM worklog WHERE username = %s AND date = %s", 
                    (username, today_date))
        record = cur.fetchone()

        if record:
            checkin_time, checkout_time = record
            if checkin_time and checkout_time is None:
                cur.close()
                return jsonify({'message': "Please check out before checking in again."}), 400
        else:
            cur.execute("INSERT INTO worklog (username, date, checkin, status) VALUES (%s, %s, %s, %s)", 
                        (username, today_date, current_time, "pending"))
            mysql.connection.commit()

        cur.close()
        return jsonify({'message': "Attendance submitted successfully!"}), 200

    return render_template('attendence.html', user_role=user_role)


@app.route('/insert_attendance', methods=['POST'])
def insert_attendance_records():
    """Function to insert attendance records for all active users."""
    with app.app_context():  # Push the application context manually
        active_users = get_active_users()
        cursor = mysql.connection.cursor()

        # Get tomorrow's date dynamically
        current_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')  
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Current timestamp
        
        try:
            # Check if tomorrow is a holiday
            cursor.execute("SELECT COUNT(*) FROM holidays WHERE holiday_date = %s", (current_date,))
            is_holiday = cursor.fetchone()[0] > 0

            if is_holiday:
                cursor.close()
                return jsonify({"message": "Tomorrow is a holiday. Attendance not recorded."}), 200
            
            # Check if attendance for tomorrow is already recorded
            cursor.execute("SELECT COUNT(*) FROM attendence WHERE date = %s", (current_date,))
            already_exists = cursor.fetchone()[0] > 0

            if already_exists:
                cursor.close()
                return jsonify({"message": "Attendance for tomorrow has already been recorded."}), 200

            # Insert attendance record for each active user
            for user in active_users:
                username = user[0]  # Assuming `username` is the first field in the tuple
                cursor.execute(
                    "INSERT INTO attendence (username, date, type, created_at, updated) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (username, current_date, 'leave', current_time, False)
                )

            mysql.connection.commit()  # Commit changes after all inserts
            return jsonify({"message": "Attendance records inserted successfully for tomorrow."}), 200

        except Exception as e:
            mysql.connection.rollback()  # Roll back changes in case of an error
            return jsonify({"error": str(e)}), 500
        finally:
            cursor.close()


@app.route('/disputeslist')
def disputeslist():
    username = session.get('username')
    user_role=session.get('user_role')
    user_designation = session.get('designation')
    if not username or user_designation not in ['CEO', 'HR']:
            return '''
                <script type="text/javascript">
                    alert("Access denied. You do not have permission to view this page.");
                    window.location.href = "/dashboard";
                </script>
            '''
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT ticket_id, full_name, email, phone, dispute_details, username, status, created_at FROM disputes where status='pending'")
        disputes_data = cur.fetchall()
        cur.close()

        # Check if data exists
        no_data = len(disputes_data) == 0

        return render_template('disputeslist.html', disputes_data=disputes_data, no_data=no_data, user_designation=user_designation,user_role=user_role)

    except Exception as e:
        return render_template('disputeslist.html', disputes_data=[], no_data=True, error=str(e), user_designation=user_designation,user_role=user_role)

@app.route('/update_dispute_status_resolved', methods=['POST'])
def update_dispute_status_resolved():
    """Update dispute status and send email notification."""
    try:
        data = request.form
        dispute_id = data.get('id')
        status = data.get('status')
        message = data.get('message', 'No additional comments.')
        email = data.get('email')
        name = data.get('name')

        cur = mysql.connection.cursor()
        cur.execute("UPDATE disputes SET status = %s WHERE ticket_id = %s", (status, dispute_id))
        mysql.connection.commit()
        cur.close()

        # Send email notification
        send_dispute_review_email(email, name, dispute_id, status, message)

        return jsonify({"success": True, "message": f"Dispute status updated to {status} and email sent."})

    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating dispute status: {e}"})

@app.route('/attendencelist', methods=['GET', 'POST'])
def attendencelist():
    user_role = session.get('user_role')
    username = session.get('username')
    user_designation = session.get('designation')
    if not username or user_designation not in ['CEO' , 'HR']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";
            </script>
        '''

    # Get today's date in the required format (YYYY-MM-DD)
    today_date = datetime.today().strftime('%Y-%m-%d')

    # Create a cursor object to interact with the database
    cur = mysql.connection.cursor()

    # Fetch distinct usernames for filter options
    cur.execute("SELECT DISTINCT username FROM profile")
    usernames = [row[0] for row in cur.fetchall()]
    cur.close()

    # Attendance types
    types = ['work from home', 'work from office', 'leave']

    if request.method == 'POST':
        # Fetch form inputs
        selected_username = request.form.get('usernameFilter', '')
        from_date_filter = request.form.get('fromDateFilter', today_date)
        to_date_filter = request.form.get('toDateFilter', today_date)

        cur = mysql.connection.cursor()
        
        # Modify query to show all users if no specific user is selected
        query = """
            SELECT a.id, a.username, a.type, a.date, a.created_at, 
                   COALESCE(SUM(w.work_time), 0) AS total_work_time
            FROM attendence a
            LEFT JOIN worklog w ON a.date = w.date AND a.username = w.username
            WHERE (%s = '' OR a.username = %s) 
              AND a.date BETWEEN %s AND %s
            GROUP BY a.id, a.username, a.type, a.date
        """
        cur.execute(query, (selected_username, selected_username, from_date_filter, to_date_filter))

        # Fetch all matching records with work time included
        attendence_data = cur.fetchall()
        cur.close()

        # Check if no data is found
        no_data = not attendence_data

        return render_template('attendencelist.html', 
                               attendence_data=attendence_data, 
                               no_data=no_data,
                               usernames=usernames,
                               user_role=user_role,
                               selected_username=selected_username,
                               selected_from_date=from_date_filter,
                               selected_to_date=to_date_filter,
                               types=types)

    # Default case for GET request
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.id, a.username, a.type, a.date, a.created_at, 
               COALESCE(SUM(w.work_time), 0) AS total_work_time
        FROM attendence a
        LEFT JOIN worklog w ON a.date = w.date AND a.username = w.username
        WHERE a.date BETWEEN %s AND %s
        GROUP BY a.id, a.username, a.type, a.date
    """, (today_date, today_date))
    attendence_data = cur.fetchall()
    cur.close()

    return render_template('attendencelist.html', 
                           attendence_data=attendence_data, 
                           no_data=not attendence_data,
                           usernames=usernames,
                           user_role=user_role,
                           selected_username='',
                           selected_from_date=today_date,
                           selected_to_date=today_date,
                           types=types)

@app.route('/rejectlist', methods=['GET', 'POST'])
def rejectlist():
    user_role = session.get('user_role')
    username = session.get('username')
    user_designation = session.get('designation')
    if not username or user_designation not in ['CEO', 'HR']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";
            </script>
        '''

    # Get today's date in the required format (YYYY-MM-DD)
    today_date = datetime.today().strftime('%Y-%m-%d')

    # Create a cursor object to interact with the database
    cur = mysql.connection.cursor()

    # Fetch distinct usernames for filter options
    cur.execute("SELECT DISTINCT username FROM profile")
    usernames = [row[0] for row in cur.fetchall()]
    cur.close()

    # Attendance types
    types = ['work from home', 'work from office', 'leave']

    if request.method == 'POST':
        # Fetch form inputs
        selected_username = request.form.get('usernameFilter', '')
        from_date_filter = request.form.get('fromDateFilter', today_date)
        to_date_filter = request.form.get('toDateFilter', today_date)

        cur = mysql.connection.cursor()
        
        # Modify query to show all users if no specific user is selected
        query = """
            SELECT a.id, a.username, a.type, a.date, a.created_at
            FROM attendence a
            LEFT JOIN worklog w ON a.date = w.date AND a.username = w.username
            WHERE (%s = '' OR a.username = %s)
              AND a.date BETWEEN %s AND %s
              AND w.status = 'Rejected'
        """
        cur.execute(query, (selected_username, selected_username, from_date_filter, to_date_filter))

        # Fetch all matching records with 'Rejected' status
        attendence_data = cur.fetchall()
        cur.close()

        # Check if no data is found
        no_data = not attendence_data

        return render_template('rejectlist.html', 
                               attendence_data=attendence_data, 
                               no_data=no_data,
                               usernames=usernames,
                               user_role=user_role,
                               selected_username=selected_username,
                               selected_from_date=from_date_filter,
                               selected_to_date=to_date_filter,
                               types=types)

    # Default case for GET request
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.id, a.username, a.type, a.date, a.created_at
        FROM attendence a
        LEFT JOIN worklog w ON a.date = w.date AND a.username = w.username
        WHERE a.date BETWEEN %s AND %s
          AND w.status = 'Rejected'
    """, (today_date, today_date))
    attendence_data = cur.fetchall()
    cur.close()

    return render_template('rejectlist.html', 
                           attendence_data=attendence_data, 
                           no_data=not attendence_data,
                           usernames=usernames,
                           user_role=user_role,
                           selected_username='',
                           selected_from_date=today_date,
                           selected_to_date=today_date,
                           types=types)



import os
from werkzeug.utils import secure_filename
from flask import Flask, send_from_directory, abort
UPLOAD_FOLDER = 'uploads/'  # Modify this path based on your project structure
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip', 'xls', 'xlsx', 'csv', 'ppt', 'pptx',  
    'py', 'java', 'cpp', 'c', 'cs', 'rb', 'php', 'html', 'css', 'js', 'ts', 'json', 'xml', 'yaml', 'yml',  
    'sql', 'sh', 'bat', 'cmd', 'swift', 'kt', 'kts', 'dart', 'go', 'r', 'pl', 'lua', 'scala', 'rs', 'm', 'h',  
    'vue', 'jsx', 'tsx', 'md', 'ini', 'cfg', 'toml', 'lock', 'env', 'ipynb'
}


# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to save file
def save_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)  # Secure the filename to prevent directory traversal
        file_path = os.path.join(UPLOAD_FOLDER, filename)  # Save the file to the 'uploads' folder
        file.save(file_path)
        
        # You can return the file path or URL to access the file
        file_url =request.host_url + 'uploads/' + filename  # This should be accessible via your static folder
        return file_url
    else:
        raise ValueError("Invalid file type")
@app.route('/chatbox')
def chat():
    if 'username' in session:
        username = session['username']
        user_role = session['user_role']
        empid = session['empid']
        
        cursor = mysql.connection.cursor()
        
        # Query to get all usernames from profile where status = '1' and prioritize those with the latest messages
        cursor.execute("""
            SELECT p.*, COALESCE(m.latest_message_time, '1970-01-01 00:00:00') AS message_time
            FROM profile p
            LEFT JOIN (
                SELECT 
                    CASE
                        WHEN sender = %s THEN receiver
                        ELSE sender
                    END AS username, 
                    MAX(created_at) AS latest_message_time
                FROM messages
                WHERE sender = %s OR receiver = %s
                GROUP BY 
                    CASE
                        WHEN sender = %s THEN receiver
                        ELSE sender
                    END
            ) m ON p.username = m.username
            WHERE p.user_status = '1'
            ORDER BY m.latest_message_time DESC, p.username ASC
        """, (username, username, username, username))
        
        profile = cursor.fetchall()
        cursor.close()
        
        return render_template('chatbox.html', profile=profile, user_role=user_role)
    else:
        return redirect(url_for('login'))


@app.route('/send_message', methods=['POST'])
def send_message():
    sender = request.form.get('sender')
    receiver = request.form.get('receiver')
    message = request.form.get('message')

    print(f"Sender: {sender}, Receiver: {receiver}, Message: {message}")  # Debugging line

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO messages (sender, receiver, message,is_read) VALUES (%s, %s, %s,%s)",
            (sender, receiver, message,False)
        )
        mysql.connection.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Error: {str(e)}")  # Log any database-related errors
        return jsonify({'status': 'error', 'message': str(e)}), 500
@app.route('/get_messages', methods=['POST'])
def get_messages():
    sender = request.form.get('sender')
    receiver = request.form.get('receiver')

    # Fetch messages from the database between sender and receiver
    messages = get_messages_from_db(sender, receiver)

    return jsonify({'messages': messages})

# Function to get messages from the database
def get_messages_from_db(sender, receiver):
    # Create a cursor object using the MySQL connection
    cursor = mysql.connection.cursor()

    # Execute the query to fetch messages
    cursor.execute("""
    SELECT sender, message, is_read, created_at 
    FROM messages 
    WHERE (sender = %s AND receiver = %s) OR (sender = %s AND receiver = %s)
    ORDER BY created_at ASC
""", (sender, receiver, receiver, sender))

    rows = cursor.fetchall()
    messages = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    # Mark messages as read
    cursor.execute("""
        UPDATE messages 
        SET is_read = TRUE 
        WHERE receiver = %s AND sender = %s AND is_read = FALSE
    """, (sender, receiver))
    mysql.connection.commit()

    return messages
@app.route('/send_attachment', methods=['POST'])
def send_attachment():
    file = request.files['file']
    sender = request.form['sender']
    receiver = request.form['receiver']
    try:
        filename = save_file(file)  # Save the file and get the filename
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO messages (sender, receiver, message) VALUES (%s, %s, %s)",
            (sender, receiver, filename)  # Save only the file name in the message
        )
        mysql.connection.commit()
        return jsonify({'status': 'success', 'filename': filename}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')  # Get the file from the request

    if not file:
        return "No file part", 400

    try:
        file_url = save_file(file)
        return f"File uploaded successfully! Access it <a href='{file_url}'>here</a>.", 200
    except ValueError as e:
        return str(e), 400


# Route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(
            UPLOAD_FOLDER, 
            filename,
            as_attachment=True,  # This will force the file to be downloaded
            download_name=filename  # This will specify the file name in the download prompt
        )
    except FileNotFoundError:
        return "File not found", 404
@app.route('/get_unread_counts', methods=['POST'])
def get_unread_counts():
    current_user = session.get('username')  # Get the current logged-in user

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT sender, COUNT(*) AS unread_count
        FROM messages
        WHERE receiver = %s AND is_read = FALSE
        GROUP BY sender
    """, (current_user,))
    counts = cursor.fetchall()
   
    # Return the counts as a JSON response
    return jsonify({'counts': counts})


@app.after_request
def apply_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# @app.context_processor
# def inject_notification_count():
#     notification_count = 0  # Default value

#     username = session.get('username')
#     if username:
#         cur = mysql.connection.cursor()
#         cur.execute("SELECT COUNT(*) FROM notifications WHERE username = %s", (username,))
#         notification_count = cur.fetchone()[0]
        
#         cur.close()

#     return {'notificationCount': notification_count}


@app.route('/issues', methods=['GET', 'POST'])
def sitemap():
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    sitemap_id = f"SM-{random.randint(1, 1000)}"
    
    if request.method == 'POST':
        # Extract form data
        sitemap=request.form.get('sitemap-id')
        project = request.form.get('project')
        module = request.form.get('module')
        module_list = request.form.get('module-list')  # Convert list to a string
        page_name = request.form.get('page-name')
        page_url = request.form.get('page-url')
        page_description = request.form.get('page-description')

        # Ensure sitemap_id is not None
        if not sitemap_id:
            return "Error: sitemap_id is missing or invalid."

        # Insert data into the MySQL database
        cur = mysql.connection.cursor()

        # Insert query to add data to the 'sitemap' table with default status
        insert_query = """
        INSERT INTO sitemap (sitemap_id, project, module, module_list, page_name, page_url, page_description, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'incomplete')
        """

        cur.execute(insert_query, (sitemap, project, module, module_list, page_name, page_url, page_description))
        mysql.connection.commit()  # Commit the transaction

        notification_message = f"New Ticket is raised with Sitemap_Id: {sitemap_id}"
        cur.execute("SELECT username FROM profile WHERE designation = %s", ('Jr Tester',))  # Fix: Ensure single-element tuple
        ceo_users = cur.fetchall()

        for ceo in ceo_users:
            cur.execute(
                'INSERT INTO notifications (username, notification) VALUES (%s, %s)',
                (ceo[0], notification_message)  # Fix: Access the username from ceo tuple
            )
        mysql.connection.commit()

        # Redirect to the same page or a success page after insertion
        return redirect(url_for('sitemap'))

    # Generate a random sitemap ID on GET request
    return render_template('sitemap.html', sitemap_id=sitemap_id, user_role=user_role, user_designation=user_designation)

@app.route('/requestform', methods=['GET', 'POST'])
def requestform():
    today_date = datetime.today().strftime('%Y-%m-%d')  # Get today's date
    user_role = session.get('user_role')  # Get user role from session
    user_designation = session.get('user_designation')  # Get designation from session

    if request.method == 'POST':
        project_name = request.form.get('project-name')
        request_date = today_date  # Set request_date to today's date
        change_description = request.form.get('change-description')
        requested_changes = request.form.get('requested-changes')
        reason_for_change = request.form.get('reason-for-change')
        impact_of_change = request.form.get('impact-of-change')
        priority = request.form.get('priority')
        username = session.get('username')
        approved = 'No one approved'
        status = 'Pending'

        if not all([project_name, change_description, requested_changes, reason_for_change, impact_of_change, priority]):
            return "Error: Missing required fields."

        cur = mysql.connection.cursor()
        insert_query = """
        INSERT INTO requests (project_name, request_date, change_description, requested_changes, reason_for_change, impact_of_change, priority, username, approved, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (project_name, request_date, change_description, requested_changes, reason_for_change, impact_of_change, priority, username, approved, status))
        mysql.connection.commit()

        notification_message = f"New Change Request submitted for {project_name}."
        cur.execute("SELECT username FROM profile WHERE designation = %s", ('CEO',))
        managers = cur.fetchall()

        for manager in managers:
            cur.execute('INSERT INTO notifications (username, notification) VALUES (%s, %s)', (manager[0], notification_message))
        mysql.connection.commit()
        
        return redirect(url_for('requestform'))

    return render_template('requestform.html', today_date=today_date, user_role=user_role, user_designation=user_designation)

@app.route('/update_request_status', methods=['POST'])
def update_request_status():
    request_id = request.form.get('request_id')  # Get the request ID
    action = request.form.get('action')  # Get the action (approve/reject)
    user_role = session.get('user_role')  # Get the current user role
    username = session.get('username')  # Get the current user's username

    if action not in ['approve', 'reject']:
        return "Invalid action", 400

    # Set status and approved fields based on the action
    if action == 'approve':
        status = 'Approved'
        approved_by = username
    elif action == 'reject':
        status = 'Rejected'
        approved_by = username  # No one approved if rejected

    # Update the request status in the database
    cur = mysql.connection.cursor()
    update_query = """
    UPDATE requests 
    SET status = %s, approved = %s 
    WHERE id = %s
    """
    cur.execute(update_query, (status, approved_by, request_id))
    mysql.connection.commit()

    # Redirect back to the request form page
    return redirect(url_for('requestedlist'))



@app.route('/update_status', methods=['POST'])
def update_status():
    try:
        # Parse the JSON request
        data = request.get_json()
        sitemap_id = data.get('sitemapId')
        new_status = data.get('status')

        if not sitemap_id or not new_status:
            return jsonify({"error": "Invalid data"}), 400

        # Update the status in the database
        cur = mysql.connection.cursor()
        update_query = "UPDATE sitemap SET status = %s WHERE sitemap_id = %s"
        cur.execute(update_query, (new_status, sitemap_id))
        cur.execute("SELECT * FROM sitemap WHERE sitemap_id = %s", (sitemap_id,))
        sitemap = cur.fetchone()

        if not sitemap:
            return jsonify({"error": "Sitemap not found"}), 404

        if new_status.lower() == "complete":
            notification_message = f"{sitemap[1]} is Resolved."
        else:
            notification_message = f"{sitemap[1]} is Not Resolved, please assign another."

        # Notify CEO and HR
        cur.execute("SELECT username FROM profile WHERE designation IN (%s, %s)", ('CEO', 'HR'))
        ceo_users = cur.fetchall()
        for ceo in ceo_users:
            ceo_username = ceo[0]
            cur.execute(
                'INSERT INTO notifications (username, notification) VALUES (%s, %s)',
                (ceo_username, notification_message)
            )

        cur.close()
        mysql.connection.commit()

        return jsonify({"message": "Status updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/raiseticket', methods=['GET'])
def raiseticket():
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if 'username' in session:
        username = session['username']
        cur = mysql.connection.cursor()
        # user_designation = session.get('designation')
        # print(user_designation)
        cur.execute("SELECT * FROM sitemap")
        sitemap = cur.fetchall()
        cur.close()
        
        return render_template('raiseticket.html', sitemap=sitemap, user_designation=user_designation,user_role=user_role)
    else:
        return redirect(url_for('login'))

@app.route('/ticket', methods=['GET'])
def ticket():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    return render_template('ticket.html',user_role=user_role,user_designation=user_designation)

@app.route('/empreview', methods=['GET', 'POST'])
def empreview():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')

    if request.method == 'POST':
        # Get data from the form
        submitted_username = request.form.get('username')
        month = request.form.get('month')
        review_number = request.form.get('review_number')
        work = request.form.get('work')
        work_reason = request.form.get('work_reason')
        code_of_conduct_value = request.form.get('code_of_conduct_value')
        code_of_conduct_reason = request.form.get('code_of_conduct_reason')
        time_management_value = request.form.get('time_management_value')
        time_management_reason = request.form.get('time_management_reason')
        ethical_behaviour_value = request.form.get('ethical_behaviour_value')
        ethical_behaviour_reason = request.form.get('ethical_behaviour_reason')
        summary = request.form.get('summary')

        # Check if the entry already exists
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM empreview
            WHERE username = %s AND month = %s AND review_number = %s
        """, (submitted_username, month, review_number))
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            return '''
                        <script type="text/javascript">
                            alert("You have already reviewed that user");
                            window.location.href = "/empreview";
                        </script>
                    '''

        # Insert the data into the empreview table
        cursor.execute(""" 
            INSERT INTO empreview (username, month, review_number, work, cywork, code_of_conduct, 
                                   cycode_of_conduct, time_management, cytime_management, 
                                   ethical_behaviour, cyethical_behaviour, summary) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            submitted_username, 
            month, 
            review_number, 
            work, 
            work_reason, 
            code_of_conduct_value, 
            code_of_conduct_reason, 
            time_management_value, 
            time_management_reason, 
            ethical_behaviour_value, 
            ethical_behaviour_reason, 
            summary
        ))
        mysql.connection.commit()
        cursor.close()

        # Redirect to the empreview page
        return redirect('/empreview')

    # Fetch the active users from the database
    return render_template(
        'empreview.html', 
        user_role=user_role, 
        user_designation=user_designation, 
        users=get_active_users()
    )

def get_active_users():
    """Helper function to fetch active users."""
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT username FROM profile WHERE user_status = '1'")
    users = cursor.fetchall()
    cursor.close()
    return users



@app.route('/empreview/edit', methods=['POST'])
def edit_review():
    if session.get('user_role') != 'CEO':
        abort(403)  # Forbidden for non-CEOs

    review_id = request.form.get('review_id')
    work = request.form.get('work1')
    work_reason = request.form.get('work_reason')
    code_of_conduct_value = request.form.get('code_of_conduct1')
    code_of_conduct_reason = request.form.get('code_of_conduct_reason')
    time_management_value = request.form.get('time_management1')
    time_management_reason = request.form.get('time_management_reason')
    ethical_behaviour_value = request.form.get('ethical_behaviour1')
    ethical_behaviour_reason = request.form.get('ethical_behaviour_reason')
    summary = request.form.get('summary')
    print(work)

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE empreview 
        SET work=%s, cywork=%s, code_of_conduct=%s, cycode_of_conduct=%s,
            time_management=%s, cytime_management=%s, ethical_behaviour=%s,
            cyethical_behaviour=%s, summary=%s 
        WHERE id=%s
    """, (
        work, work_reason, code_of_conduct_value, code_of_conduct_reason,
        time_management_value, time_management_reason, ethical_behaviour_value,
        ethical_behaviour_reason, summary, review_id
    ))
    mysql.connection.commit()
    cursor.close()
    return redirect('/empreviewlist')

@app.route('/empreview/validate', methods=['POST'])
def validate_review():
    if session.get('user_role') != 'CEO':
        abort(403)  # Forbidden for non-CEOs

    review_id = request.form.get('review_id')
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE empreview SET status='validated' WHERE id=%s", (review_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/empreviewlist')

@app.route('/empreview/details/<int:review_id>', methods=['GET'])
def get_review_details(review_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM empreview WHERE id=%s", (review_id,))
    review = cursor.fetchone()
    cursor.close()
    print(review)
    
    # Ensure the review exists
    if not review:
        return jsonify({"error": "Review not found"}), 404

    # Map the review fields to meaningful keys
    review_data = {
        "id": review[0],
        "work": review[4],
        "work_reason": review[5],
        "code_of_conduct": review[6],
        "code_of_conduct_reason": review[7],
        "time_management": review[8],
        "time_management_reason": review[9],
        "ethical_behaviour": review[10],
        "ethical_behaviour_reason": review[11],
        "summary": review[12],
    }

    return jsonify(review_data)



@app.route('/empreviewlist', methods=['GET', 'POST'])
def empreviewlist():
    
    username = session.get('username')
    # Get the form data if it's a POST request
    selected_username = request.form.get('usernameFilter', username)
    selected_month = request.form.get('month')
    selected_review_number = request.form.get('review_number')

    # You can also use session data (for user role, etc.) if needed
    user_role = session.get('user_role')
    user_designation = session.get('designation')

    # Fetch active users from the database (if needed)
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT username FROM profile WHERE user_status = '1'")
    users = cursor.fetchall()

    # Fetch review data based on the form data (selected username, month, and review number)
    cursor.execute("""
        SELECT * FROM empreview
        WHERE username = %s
        AND month = %s
        AND review_number = %s
    """, (selected_username, selected_month, selected_review_number))

    review_data = cursor.fetchall()
    # cursor.close()
    # print(review_data)
    cursor.execute("""
        SELECT work, code_of_conduct, time_management, ethical_behaviour
        FROM empreview
        WHERE username = %s AND month = %s AND review_number = %s
    """, (selected_username, selected_month, selected_review_number))

    review = cursor.fetchone()  # Assuming one row is returned
    cursor.close()

    # Prepare the 'row' for the frontend
    if review_data:
        row = [0, 0, 0, 0, review[0], 0, review[1], 0, review[2], 0, review[3]]
    else:
        row = [0] * 11  # Default if no data is found


    # Return the template with the fetched data
    return render_template('empreviewlist.html', 
                           user_role=user_role, 
                           user_designation=user_designation, 
                           users=users, 
                           row=row,
                           review_data=review_data,
                           selected_username=selected_username,
                           selected_month=selected_month,
                           selected_review_number=selected_review_number)



    
@app.route('/ticketlist', methods=['GET'])
def ticketlist():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM tickets")
        tickets = cur.fetchall()
        cur.execute("SELECT * FROM profile")
        users=cur.fetchall()
        cur.close()
        # print(data)
        
        return render_template('ticketslist.html', tickets=tickets, users=users,user_role=user_role,user_designation=user_designation)
    
@app.route('/requestedlist', methods=['GET'])
def requestedlist():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    
    if 'username' in session:
        cur = mysql.connection.cursor()
        
        # Check if the user is CEO or HR
        if user_designation in ['CEO', 'HR']:
            cur.execute("SELECT * FROM requests")  # Fetch all requests if CEO or HR
            requests = cur.fetchall()
            cur.execute("SELECT * FROM profile")  # Fetch all users
            users = cur.fetchall()
        else:
            cur.execute("SELECT * FROM requests WHERE username = %s", (username,))  # Fetch only user-specific requests
            requests = cur.fetchall()
            cur.execute("SELECT * FROM profile WHERE username = %s", (username,))  # Fetch user-specific profile
            users = cur.fetchall()
        
        cur.close()
        
        # Render the template with the appropriate data
        return render_template('requestedlist.html', requests=requests, users=users, user_role=user_role, user_designation=user_designation)


@app.route('/resolvedticket', methods=['GET'])
def resolvedticket():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if 'username' in session:
        cur = mysql.connection.cursor()
        
        # Correct the placeholder usage by ensuring `username` is passed as a tuple
        cur.execute("SELECT * FROM tickets WHERE allocated_to = %s", (username,))
        tickets = cur.fetchall()
        
        cur.execute("SELECT * FROM profile")
        users = cur.fetchall()
        
        cur.close()
        
        return render_template('resolveticket.html', tickets=tickets, users=users, user_role=user_role, user_designation=user_designation)
    else:
        # Handle the case where the user is not logged in
        return redirect(url_for('login'))

@app.route('/updateTicketDescription', methods=['POST'])
def update_ticket_description():
    if 'username' in session:
        data = request.json
        ticket_id = data.get('ticketId')
        description = data.get('description')

        if not ticket_id or not description:
            return jsonify({"error": "Invalid data"}), 400

        cur = mysql.connection.cursor()

        # Update the solution column in the tickets table
        query = "UPDATE tickets SET solution = %s WHERE ticket_id = %s"
        cur.execute(query, (description, ticket_id))

        notification_message = f"{ticket_id} has updated the status."
        cur.execute("SELECT username FROM profile WHERE designation = %s", ('Jr Tester',))  # Fix: Ensure single-element tuple
        ceo_users = cur.fetchall()

        for ceo in ceo_users:
            type="raise ticket"
            cur.execute(
                'INSERT INTO notifications (username, notification, type) VALUES (%s, %s, %s)',
                (ceo[0], notification_message, type)
            )
        mysql.connection.commit()

        cur.close()
        return jsonify({"message": "Description updated successfully!"}), 200
    else:
        return jsonify({"error": "Unauthorized"}), 401





@app.route('/ticketuser', methods=['POST'])
def ticketuser():
    try:
        # Retrieve ticketId and username from the JSON request
        data = request.get_json()
        ticket_id = data.get('ticketId')
        username = data.get('username')
        user_desgination = session.get('desgination')
        cur = mysql.connection.cursor()

        # Validate input data
        if not ticket_id or not username or username == "select Employee":
            return jsonify({'error': 'Invalid data, missing or incorrect values.'}), 400

        # Database connection and query execution
        cur.execute("UPDATE tickets SET allocated_to=%s WHERE ticket_id=%s", 
                    (username, ticket_id))
        cur.execute("SELECT ticket_description FROM tickets WHERE ticket_id = %s", (ticket_id,))
        descr = cur.fetchall()
        
        message=f"You have allocated to {ticket_id}. Ticket Description:{descr[0][0]} "
        cur.execute("""
                INSERT INTO notifications (username, notification, timestamp) 
                VALUES (%s, %s, NOW())
            """, (username, message))
        mysql.connection.commit()
        cur.close()
        mysql.connection.commit()


        # Check if any rows were updated
        if cur.rowcount == 0:
            return jsonify({'error': 'Ticket not found or already allocated.'}), 404

        # Return success response
        return jsonify({'message': 'User allocated successfully'}), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

    finally:
        # Ensure the cursor is always closed
        cur.close()


@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    if request.method == 'POST':
        sitemap_id = request.form['sitemapId']
        ticket_id = request.form['ticketId']
        ticket_description = request.form['ticketDescription']
        severity = request.form['severity']
        ticket_type = request.form['ticketType']

        # Insert the ticket data into the database
        cur = mysql.connection.cursor()
        insert_query = """
        INSERT INTO tickets (sitemap_id, ticket_id, ticket_description, severity, ticket_type)
        VALUES (%s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (sitemap_id, ticket_id, ticket_description, severity, ticket_type))
        mysql.connection.commit()

        return redirect('/raiseticket')


# Route to get notification count (AJAX)
allow_updates = False  # Initially set to True
@app.route('/report')
def report():
    global allow_updates
    user_designation = session.get('designation')
    if 'username' in session:
        username = session.get('username')
        user_role = session.get('user_role')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT toogle FROM work LIMIT 1")
        result = cursor.fetchone()
        allow_updates = result[0] == "on" if result else False
        cursor.close()
        
        return render_template(
            'report.html',
            user_role=user_role,
            allow_updates=allow_updates,
            user_designation=user_designation
        )
    else:
        return redirect(url_for('index'))
    
@app.route('/projectmenu')
def projectmenu():
    if 'username' in session:
        username = session.get('username')
        user_role = session.get('user_role')
        user_designation = session.get('designation')
        return render_template(
            'project.html',
            user_role=user_role,user_designation=user_designation
        )
    else:
        return redirect(url_for('index'))

@app.route('/redflag', methods=['GET', 'POST'])
def redflag():
    if 'username' in session:
        username = session.get('username')
        user_role = session.get('user_role')
        user_designation = session.get('designation')
        cursor = mysql.connection.cursor()

        # Fetch distinct usernames for filter options
        cursor.execute("SELECT DISTINCT username FROM profile")
        usernames = [row[0] for row in cursor.fetchall()]

        # Get filter parameters from the form
        selected_username = request.form.get('usernameFilter', username)

        selected_user_details = None
        red_flags = []
        if selected_username:
            # Fetch user details
            cursor.execute("SELECT empid, username FROM profile WHERE username = %s", (selected_username,))
            selected_user_details = cursor.fetchone()

            # Fetch red flag data
            cursor.execute("SELECT id, redflag FROM redflags WHERE username = %s", (selected_username,))
            red_flags = cursor.fetchall()

        mysql.connection.commit()
        cursor.close()

        # Render the template
        return render_template(
            'redflag.html',
            usernames=usernames,
            selected_username=selected_username,
            selected_user_details=selected_user_details,
            red_flags=red_flags,
            user_role=user_role,user_designation=user_designation
        )
    else:
        return redirect(url_for('index'))
    

@app.route('/redlist', methods=['GET', 'POST'])
def redlist():
    
    if 'username' in session:
        username = session.get('username')
        user_role = session.get('user_role')
        user_designation = session.get('designation')
        cursor = mysql.connection.cursor()
        if not username or user_designation not in ['CEO', 'HR']:
            return '''
                <script type="text/javascript">
                    alert("Access denied. You do not have permission to view this page.");
                    window.location.href = "/dashboard";
                </script>
            '''


        # Fetch distinct usernames for filter options
        cursor.execute("SELECT DISTINCT username FROM profile")
        usernames = [row[0] for row in cursor.fetchall()]

        # Get the selected month from the form
        selected_month = request.form.get('month')  # Format: 'yyyy-mm'

        selected_user_details = None
        red_flags = []
        selected_month = request.form.get('month')
        if not selected_month:
            selected_month = datetime.now().strftime("%Y-%m")
        formatted_month = datetime.strptime(selected_month, "%Y-%m").strftime("%B %Y")
        if selected_month:
            # Fetch users with more than 1 red flag in the selected month
            cursor.execute("""
                SELECT r.username, COUNT(r.id) as flag_count
                FROM redflags r
                WHERE r.created_at = %s
                GROUP BY r.username
                HAVING flag_count > 1
            """, (formatted_month,))

            users_with_red_flags = cursor.fetchall()
            

            # Fetch the red flags for each selected user with more than 1 red flag
            for user in users_with_red_flags:
                cursor.execute("SELECT id, redflag,username FROM redflags WHERE username = %s AND created_at = %s", (user[0], formatted_month))
                red_flags.extend(cursor.fetchall())
            

        mysql.connection.commit()
        cursor.close()

        # Render the template
        return render_template(
            'redlist.html',
            usernames=usernames,
            selected_username=username,
            red_flags=red_flags,
            user_role=user_role,
            users_with_red_flags=users_with_red_flags,
            user_designation=user_designation,
            selected_month=selected_month,
            formatted_month = formatted_month
        )
    else:
        return redirect(url_for('index'))



@app.route("/post_redflags", methods=["POST"])
def post_redflags():
    try:
        with app.app_context():
            cursor = mysql.connection.cursor()

            # Define the available time slots
            time_slots = [
                "9am to 10am", "10am to 11am", "11am to 12pm",
                "12pm to 1pm", "1pm to 2pm", "2pm to 3pm", "3pm to 4pm",
                "4pm to 4:30pm", "4:30pm to 5pm", "5pm to 6pm"
            ]

            current_time = datetime.now().time()
            current_date = datetime.now().date()

            # Restrict execution before 6:15 PM
            cutoff_time = datetime.strptime("10:15", "%H:%M").time()
            if current_time < cutoff_time:
                return jsonify({"message": "Red flags can only be posted after 6:15 PM."}), 200

            # Ensure data is entered only once per day
            cursor.execute("""
                SELECT COUNT(*) FROM redflags WHERE date = %s
            """, (current_date,))
            if cursor.fetchone()[0] > 0:
                cursor.close()
                return jsonify({"message": "Red flags have already been posted today."}), 200

            # Check if today is a holiday
            cursor.execute("SELECT COUNT(*) FROM holidays WHERE holiday_date = %s", (current_date,))
            if cursor.fetchone()[0] > 0:
                cursor.close()
                return jsonify({"message": "Today is a holiday. No red flags posted."}), 200

            # Get all active employees
            cursor.execute("SELECT empid, username FROM profile WHERE user_status = '1'")
            all_employees = cursor.fetchall()

            # Get all work reports for today
            cursor.execute("SELECT wr.empid, wr.time FROM workreport wr WHERE wr.date = %s", (current_date,))
            work_reports = cursor.fetchall()

            # Organize work reports into a dictionary by empid
            work_reports_dict = {}
            for empid, time_slot in work_reports:
                if empid not in work_reports_dict:
                    work_reports_dict[empid] = set()
                if time_slot:
                    work_reports_dict[empid].add(time_slot)

            for empid, username in all_employees:
                if username.lower() == "bharath@ceo":
                    continue

                reported_slots = work_reports_dict.get(empid, set())

                # Check if the employee is on approved leave
                cursor.execute("""
                    SELECT COUNT(*) FROM empleave
                    WHERE username = %s AND status = 'Approved'
                    AND start_date <= %s AND end_date >= %s
                """, (username, current_date, current_date))
                if cursor.fetchone()[0] > 0:
                    continue

                # Identify missing slots
                missing_slots = [slot for slot in time_slots if slot not in reported_slots]
                if missing_slots:
                    missing_slots_str = ", ".join(missing_slots)
                    current_month_year = datetime.now().strftime("%B %Y")
                    cursor.execute("""
                        INSERT INTO redflags (username, redflag, created_at, date)
                        VALUES (%s, %s, %s, %s)
                    """, (username, f"You haven't reported for the following time slots today '{current_date}': {missing_slots_str}", current_month_year, current_date))

            mysql.connection.commit()
            cursor.close()
            return jsonify({"message": "Red flags posted successfully!"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/complaint', methods=['GET', 'POST'])
def complaint():
    user_designation = session.get('designation')
    if request.method == 'POST':
        # Get the complaint text from the form
        complaint_text = request.form['complaint']
        notification_message = f"Someone has submitted a complaint: '{complaint_text}'"

        try:
            cur = mysql.connection.cursor()
            # Get usernames of users with the designation 'CEO' or 'HR'
            cur.execute("SELECT username FROM profile WHERE designation IN (%s, %s)", ('CEO', 'HR'))
            ceo_hr_users = cur.fetchall()

            # Insert notification for each user
            for user in ceo_hr_users:
                username = user[0]  # Extract the username from the query result
                cur.execute(
                    'INSERT INTO notifications (username, notification) VALUES (%s, %s)',
                    (username, notification_message)
                )
            
            mysql.connection.commit()
            flash('Complaint submitted successfully.', 'success')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        finally:
            cur.close()

        return redirect(url_for('complaint'))
    
    return render_template('complaint.html',user_designation=user_designation)

@app.route('/get-notification-count')
def get_notification_count():
    notification_count = 0  # Default value
    username = session.get('username')
    user_designation = session.get('designation')

    if username:
        cur = mysql.connection.cursor()
        
        # Fetch the notification count for the user
        cur.execute("SELECT COUNT(*) FROM notifications WHERE username = %s", (username,))
        notification_count = cur.fetchone()[0]
        mysql.connection.commit()
        
        cur.close()

    return jsonify({'notificationCount': notification_count})

@app.route('/meetings', methods=['GET'])
def meetings():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if 'username' in session:
        username = session['username']
        cur = mysql.connection.cursor()
        
        # If the user is a CEO, show all unique meetings
        if user_role == 'CEO' or user_role =='HR':
            cur.execute("SELECT DISTINCT meet_title, date, time_slots, meet_link,meet_description FROM scheduler")

        else:
            # If the user is not CEO, filter the meetings based on the username
            cur.execute("SELECT * FROM scheduler WHERE username = %s", (username,))
        
        meetings = cur.fetchall()
        cur.close()
        
        return render_template('meetings.html', meetings=meetings, username=username, user_designation=user_designation, user_role=user_role)
    else:
        return redirect(url_for('login'))

    
@app.route('/update_meeting', methods=['POST'])
def update_meeting():
    try:
        data = request.json
        meet_title = data.get('meet_title')
        meet_link = data.get('meet_link')

        if not meet_title or not meet_link:
            return jsonify({'success': False, 'error': 'Missing data.'}), 400

        cursor = mysql.connection.cursor()
        query = "UPDATE scheduler SET meet_link = %s WHERE meet_title = %s"
        cursor.execute(query, (meet_link, meet_title))
        mysql.connection.commit()  # commit should be mysql.connection.commit()
        cursor.close()

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating meeting: {e}")  # Print error for debugging
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/scheduler', methods=['GET', 'POST'])
def scheduler():
    if 'username' in session:
        username = session.get('username')
        user_role = session.get('user_role')
        user_designation = session.get('designation')
        print(user_designation)

        # Check user role for access control
        if not username or user_role in ['Employee', 'Trainee']:
            return '''
                <script type="text/javascript">
                    alert("Access denied. You do not have permission to view this page.");
                    window.location.href = "/dashboard";
                </script>
            '''

        # Fetch users from the profile table
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM profile")
        users = cur.fetchall()  # Fetch all rows

        # Fetch project titles from the project table
        cur.execute("SELECT project_title FROM project")
        projects = cur.fetchall()  # Fetch all rows

        cur.close()

        # Transform query results into lists for easier handling
        usernames = [user for user in users]
        project_titles = [project for project in projects]

        # Initialize selected_usernames2 as an empty list
        selected_usernames2 = []

        if request.method == 'POST':
            message = request.form.get('message')
            meet_title = request.form.get('meet_title')
            meet_time = request.form.get('time_slot')
            current_date = request.form.get('date')
            selected_usernames_json = request.form.get('selectedUsernames', '[]')
            selected_projects_json = request.form.get('selectedProjects', '[]')

            # Parse the selected usernames and projects
            try:
                selected_usernames = json.loads(selected_usernames_json) if selected_usernames_json else []
                selected_projects = json.loads(selected_projects_json) if selected_projects_json else []
            except json.JSONDecodeError as e:
                selected_usernames = []
                selected_projects = []
                print(f"JSON decode error: {e}")

            # Fetch email addresses for selected usernames
            if selected_usernames_json:
                selected_usernames = json.loads(selected_usernames_json)
                
                # Ensure selected_usernames is not empty before querying
                if selected_usernames:
                    cur = mysql.connection.cursor()
                    cur.execute(""" 
                        SELECT username 
                        FROM profile 
                        WHERE email_address IN %s
                    """, (tuple(selected_usernames),))
                    emails = cur.fetchall()
                    selected_usernames2 = [email[0] for email in emails]  # usernames matched with emails

            # Fetch usernames based on selected projects
            if selected_projects:
                cur = mysql.connection.cursor()
                cur.execute("""
                    SELECT username 
                    FROM workallocation 
                    WHERE project_title IN %s
                """, (tuple(selected_projects),))
                filtered_users = cur.fetchall()
                selected_usernames2.extend([user[0] for user in filtered_users])  # Append to the list

                # Fetch email addresses from the profile table based on the selected usernames
                cur.execute("""
                    SELECT email_address 
                    FROM profile 
                    WHERE username IN %s
                """, (tuple(selected_usernames2),))
                emails = cur.fetchall()
                selected_usernames = [email[0] for email in emails]

            # Handle 'All' selection for users
            if "All" in selected_usernames:
                selected_usernames = json.loads(selected_usernames_json)
                cur = mysql.connection.cursor()
                cur.execute("SELECT username FROM profile")
                selected_usernames2 = [user[0] for user in cur.fetchall()]

            # Default to the current date if not provided
            email_ids = selected_usernames
            print(email_ids)
            default_link = 'https://mail.google.com/mail/u/0/?tab=rm&ogbl#inbox' 

            # Insert meeting data into scheduler table
            for user, email in zip(selected_usernames2, email_ids):
                cur = mysql.connection.cursor()
                cur.execute("""
                    INSERT INTO scheduler (meet_title, date, time_slots, meet_link, guests, meet_description, username) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (meet_title, current_date, meet_time, default_link, email, message, user))

            # Commit changes after all inserts are completed
            mysql.connection.commit()

            # Insert notifications for each user
            cur = mysql.connection.cursor()
            notify = f"They have raised a meeting on {current_date} at {meet_time}"
            for user in selected_usernames2:
                type="meetings"
                cur.execute(
                    'INSERT INTO notifications (username, notification, type) VALUES (%s, %s, %s)',
                    (user, notify, type)
                )

            mysql.connection.commit()
            cur.close()

            return redirect(url_for('scheduler'))
        cur = mysql.connection.cursor()
        cur.execute(""" 
            SELECT project_title, email_address 
            FROM workallocation 
            JOIN profile ON workallocation.username = profile.username
        """)
        project_user_emails = cur.fetchall()
        projects_employees = {}
        for project_title, email in project_user_emails:
            if project_title in projects_employees:
                projects_employees[project_title].append(email)
            else:
                projects_employees[project_title] = [email]

        cur.close()
        return render_template(
            'scheduler.html',
            user_role=user_role,
            usernames=usernames,
            projects=project_titles,
            selected_username=None,
            disable_filter=False, 
            user_designation=user_designation,
            projects_employees=projects_employees
        )
    else:
        return redirect(url_for('login'))
    

from datetime import datetime, timedelta

def send_reminder_notifications():
    with app.app_context():  # Ensure the app context is available
        cur = mysql.connection.cursor()
        print("jack")

        # Get the current time and the time 30 minutes from now
        current_time = datetime.now()
        reminder_time = current_time + timedelta(minutes=30)

        # Custom time formatting to remove leading zero in the hour
        current_date_str = current_time.strftime('%Y-%m-%d')
        current_time_str = current_time.strftime('%I:%M %p').lstrip('0')  # Remove leading zero
        reminder_time_str = reminder_time.strftime('%I:%M %p').lstrip('0')  # Remove leading zero

        print(current_time_str)
        print(reminder_time_str)

        # Query for meetings happening in the next 30 minutes
        cur.execute("""
            SELECT username, meet_title, date, time_slots 
            FROM scheduler 
            WHERE date = %s AND time_slots BETWEEN %s AND %s
        """, (current_date_str, current_time_str, reminder_time_str))
        
        meetings = cur.fetchall()
        print(meetings)
        for meeting in meetings:
            username, meet_title, date, time_slots = meeting
            # Send notification
            notify = f"Reminder: You have a meeting '{meet_title}' on {date} at {time_slots}."
            print(notify)  # Replace with actual notification logic (e.g., email or SMS API)

            type="meetings"
            cur.execute(
                'INSERT INTO notifications (username, notification, type) VALUES (%s, %s, %s)',
                (username, notify, type)
            )
        
        mysql.connection.commit()
        cur.close()


@app.route('/communication', methods=['GET', 'POST'])
def communication():
    if 'username' in session:
        username = session.get('username')
        user_role = session.get('user_role')
        user_designation = session.get('designation')
        print(user_designation)
        if not username or user_role in ['Employee', 'Trainee']:
            return '''
                <script type="text/javascript">
                    alert("Access denied. You do not have permission to view this page.");
                    window.location.href = "/dashboard";
                </script>
            '''

        # Fetch usernames from the profile table
        cur = mysql.connection.cursor()
        cur.execute("SELECT username FROM profile")
        users = cur.fetchall()  # Fetch all rows

        # Fetch project titles from the project table
        cur.execute("SELECT project_title FROM project")
        projects = cur.fetchall()  # Fetch all rows

        cur.close()

        # Transform query results into lists for easier handling
        usernames = [user[0] for user in users]
        project_titles = [project[0] for project in projects]

        if request.method == 'POST':
            message = request.form.get('message')
            selected_usernames_json = request.form.get('selectedUsernames', '[]')
            selected_projects_json = request.form.get('selectedProjects', '[]')

            # Parse the selected usernames and projects
            try:
                selected_usernames = json.loads(selected_usernames_json) if selected_usernames_json else []
                selected_projects = json.loads(selected_projects_json) if selected_projects_json else []
            except json.JSONDecodeError as e:
                selected_usernames = []
                selected_projects = []
                print(f"JSON decode error: {e}")

            # Fetch usernames based on selected projects
            if selected_projects:
                cur = mysql.connection.cursor()
                cur.execute("""
                    SELECT username 
                    FROM workallocation 
                    WHERE project_title IN %s
                """, (tuple(selected_projects),))
                filtered_users = cur.fetchall()
                selected_usernames = [user[0] for user in filtered_users]
                cur.close()

            # Handle 'All' selection for users
            if "All" in selected_usernames:
                cur = mysql.connection.cursor()
                cur.execute("SELECT username FROM profile")
                selected_usernames = [user[0] for user in cur.fetchall()]
                cur.close()

            # Save notifications for selected users
            cur = mysql.connection.cursor()
            for user in selected_usernames:
                cur.execute("""
                    INSERT INTO notifications (username, notification, timestamp) 
                    VALUES (%s, %s, NOW())
                """, (user, message))
            mysql.connection.commit()
            cur.close()

            return redirect(url_for('communication'))

        return render_template(
            'communication.html',
            user_role=user_role,
            usernames=usernames,
            projects=project_titles,
            selected_username=None,
            disable_filter=False,user_designation=user_designation
        )
    else:
        return redirect(url_for('index'))



@app.route('/notification')
def notification():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if 'username' in session:
        # Fetch notifications for the logged-in user
        cur = mysql.connection.cursor()
        cur.execute("SELECT id,notification, timestamp FROM notifications WHERE username = %s", (username,))
        notifications = cur.fetchall()
        cur.close()

        # Pass notifications data to the template
        return render_template('notification.html', notifications=notifications, user_role=user_role,user_designation = user_designation)
    else:
        return redirect(url_for('index'))
    
@app.route('/get_holidays', methods=['GET'])
def get_holidays():
    try:
        cur = mysql.connection.cursor()
        # Change the ORDER BY clause to DESC to get holidays from the most recent to the oldest
        cur.execute("SELECT holiday_date, reason FROM holidays ORDER BY holiday_date DESC")
        holidays = cur.fetchall()
        cur.close()

        # Convert fetched data into a list of dictionaries
        holiday_list = [{"holiday_date": holiday_date.strftime("%Y-%m-%d"), "reason": reason} for holiday_date, reason in holidays]

        return jsonify({"success": True, "holidays": holiday_list}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/remove_holiday', methods=['POST'])
def remove_holiday():
    try:
        data = request.get_json()
        holiday_date = data.get('holiday_date')

        if not holiday_date:
            return jsonify({"success": False, "message": "Invalid holiday date."}), 400

        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM holidays WHERE holiday_date = %s", (holiday_date,))
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "Holiday removed successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/fetch_notifications')
def fetch_notifications():
    username = session.get('username')
    if username:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, notification, timestamp FROM notifications WHERE username = %s", (username,))
        notifications = cur.fetchall()
        cur.close()

        # Convert notifications to a list of dictionaries
        notifications_list = [{"id": n[0], "notification": n[1], "timestamp": n[2]} for n in notifications]

        return jsonify(notifications=notifications_list)
    else:
        return jsonify(notifications=[])


@app.route('/clear_notifications', methods=['POST'])
def clear_notifications():
    username = session.get('username')

    if 'username' in session:
        # Clear notifications for the logged-in user
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM notifications WHERE username = %s", (username,))
        mysql.connection.commit()
        cur.close()
        return {'success': True}
    else:
        return {'success': False, 'error': 'User not logged in'}, 401

@app.route('/delete_notification', methods=['POST'])
def delete_notification():
    notification_id = request.json.get('notification_id')
    username = session.get('username')

    if 'username' in session and notification_id:
        # Delete the specific notification
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM notifications WHERE id = %s AND username = %s", (notification_id, username))
        mysql.connection.commit()
        cur.close()
        return {'success': True}
    else:
        return {'success': False, 'error': 'Invalid request'}, 400



# # newdashboard
# @app.route('/newdashboard')
# def newdashboard():
#     if 'username' in session:
#         cur = mysql.connection.cursor()
#         cur.execute("SELECT * FROM profile")
#         data = cur.fetchall()
#         cur.close()
#         return render_template('dashboard.html', users=data)
#     else:
#         return redirect(url_for('index'))
# dashboard
@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    print(user_designation)
    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM profile")
        data = cur.fetchall()
        cur.close()
        return render_template('dashboard.html', users=data, user_role=user_role, user_designation=user_designation)
    else:
        return redirect(url_for('index'))


# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'username' not in session:
#             # Redirect to the login page if no session exists
#             return redirect(url_for('index'))
#         return f(*args, **kwargs)
#     return decorated_function
# login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM profile WHERE username = %s AND password = %s", (username, password))
    user = cur.fetchone()
    
    if user:
        session['username'] = username
        session['empid'] = user[1]  # Set empid in session
        session['user_role'] = user[20] 
        session['designation'] = user[9]       
        return redirect(url_for('dashboard'))
    else:
        cur.close()
        flash('Incorrect username or password', 'error')
        return redirect(url_for('index'))



@app.route('/logout')
def logout():
    # Clear the user session
    session.clear()
    return redirect(url_for('index')) # Redirect to login page after logout


#todo
@app.route('/todo', methods=['GET', 'POST'])
def manage_todo():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    cur = mysql.connection.cursor()
    
    if request.method == 'GET':
        # Fetch todos for the logged-in user
        if username:
            cur.execute("SELECT * FROM todo WHERE username = %s", (username,))
            todos = cur.fetchall()
            return render_template('To-do.html', todos=todos, user_role=user_role,user_designation = user_designation)

    elif request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            # Add a new todo item
            content = request.form['content']
            category = request.form['category']
            cur.execute("INSERT INTO todo (content, category, completed, username) VALUES (%s, %s, %s, %s)", 
                       (content, category, False, username))
            mysql.connection.commit()
            return redirect(url_for('manage_todo'))

        elif action == 'edit':
            # Edit an existing todo item
            todo_id = request.form['todo_id']
            content = request.form['content']
            category = request.form['category']
            completed = 'completed' in request.form
            cur.execute("UPDATE todo SET content=%s, category=%s, completed=%s WHERE id=%s", 
                       (content, category, completed, todo_id))
            mysql.connection.commit()
            return jsonify({'success': True, 'message': 'Todo item updated successfully'})

        elif action == 'delete':
            # Delete a todo item
            todo_id = request.form['todo_id']
            try:
                cur.execute("DELETE FROM todo WHERE id = %s", (todo_id,))
                mysql.connection.commit()
                return jsonify({'success': True, 'message': 'Todo item deleted successfully'})
            except Exception as e:
                print(e)
                return jsonify({'success': False, 'message': 'Failed to delete todo item'}), 500

        elif action == 'toggle_complete':
            # Toggle completion status of a todo item
            todo_id = request.form['todo_id']
            cur.execute("SELECT completed FROM todo WHERE id = %s", (todo_id,))
            completed = cur.fetchone()[0]
            completed = not completed
            cur.execute("UPDATE todo SET completed = %s WHERE id = %s", (completed, todo_id))
            mysql.connection.commit()
            return jsonify({'success': True, 'message': 'Todo item marked as complete'})

    cur.close()
#auto rejecting sick leaves
def auto_reject_pending_leaves():
    with app.app_context():  # Explicitly push the Flask app context
        cur = mysql.connection.cursor()
        
        # Retrieve all holiday dates
        cur.execute("SELECT holiday_date FROM holidays")
        holiday_dates = [row[0] for row in cur.fetchall()]
        
        if holiday_dates:
            # Reject 'Pending' or 'Approved' leaves where start_date equals end_date and matches a holiday
            cur.execute("""
                UPDATE empleave
                SET status = 'Rejected'
                WHERE (status = 'Pending' OR status = 'Approved')
                AND start_date = end_date
                AND start_date IN %s
            """, (tuple(holiday_dates),))
            
            # Adjust start_date for leave requests where start_date != end_date and start_date falls on a holiday
            cur.execute("""
                UPDATE empleave
                SET start_date = DATE_ADD(start_date, INTERVAL 1 DAY)
                WHERE start_date != end_date
                AND start_date IN %s
            """, (tuple(holiday_dates),))
            
            # Commit changes to the database
            mysql.connection.commit()
            cur.close()
            
            print("Auto-reject and adjustment task completed.")

def add_weekend_holidays():
    with app.app_context():  # Ensure the application context is active
        today = datetime.now(pytz.timezone('Asia/Kolkata'))
        # print(today) 
        # Current time in 'Asia/Kolkata' timezone
        day_of_week = today.weekday()  # Monday is 0, Sunday is 6
        if day_of_week in [5, 6]:  # 5 is Saturday, 6 is Sunday
            holiday_reason = "Weekend (Saturday)" if day_of_week == 5 else "Weekend (Sunday)"
            holiday_date = today.strftime('%Y-%m-%d')
            print(holiday_reason)
            cur = None
            try:
                # Save the holiday details to the database
                cur = mysql.connection.cursor()
                cur.execute(
                    "INSERT INTO holidays (holiday_date, reason) VALUES (%s, %s)",
                    (holiday_date, holiday_reason)
                )
                mysql.connection.commit()
                # print(f"Holiday added: {holiday_date} - {holiday_reason}")
            except Exception as e:
                print(f"Failed to add holiday: {e}")
            finally:
                if cur:
                    cur.close()

@app.route('/add_holiday', methods=['POST'])
def add_holiday():
    if not session.get("username"):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        # Parse JSON data from the request
        data = request.get_json()
        holiday_date = data.get("holiday_date")
        reason = data.get("reason")

        # Validate the input
        if not holiday_date or not reason:
            return jsonify({"success": False, "message": "Holiday date and reason are required."}), 400

        # Convert holiday_date to datetime object and format it as day-month-year
        try:
            holiday_date_obj = datetime.strptime(holiday_date, '%Y-%m-%d')
            formatted_holiday_date = holiday_date_obj.strftime('%d-%m-%Y')
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."}), 400

        # Save the holiday details to the database
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO holidays (holiday_date, reason) VALUES (%s, %s)",
            (holiday_date, reason)
        )
        mysql.connection.commit()
        
        # Send notifications to all users
        message = f"On {formatted_holiday_date} is a Holiday on account of {reason}"

        # Retrieve all usernames from the profile table
        cur.execute("SELECT username FROM profile")
        selected_usernames = [user[0] for user in cur.fetchall()]
        cur.close()

        # Insert notifications for each user
        cur = mysql.connection.cursor()
        for user in selected_usernames:
            cur.execute("""
                INSERT INTO notifications (username, notification, timestamp) 
                VALUES (%s, %s, NOW())
            """, (user, message))
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": True, "message": "Holiday added and notifications sent successfully!"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



#leavemanager
@app.route('/leavemanager', methods=['GET', 'POST'])
def leavemanager():
    username = session.get('username')
    user_role = session.get('user_role')
    # print(user_role)
    user_designation = session.get('designation')
    # print(user_designation)
    # Check permissions
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";
            </script>
        '''

    cur = mysql.connection.cursor()

    # Fetch usernames from the profile table
    cur.execute("SELECT username FROM profile")
    usernames = [row[0] for row in cur.fetchall()]  # Extract usernames into a list

    # Initialize filters
    selected_username = request.form.get('usernameFilter', '')
    selected_from_date = request.form.get('fromDateFilter', datetime.today().strftime('%Y-%m-%d'))
    selected_to_date = request.form.get('toDateFilter', (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d'))

    filtered_data = []

    if request.method == 'POST':
        # Check if the request is for leave status update or filtering
        if request.is_json:
            
            # Handle leave status update (approval/rejection)
            data = request.get_json()
            leave_username = data['username']
            leave_type = data['leave_type']
            start_date = data['start_date']
            status = data['status']
            reject_reason = data.get('rejectReason')  # Use get() to avoid KeyError in case of approval

            if status == 'Rejected' and reject_reason:
                # Update leave status and send notification for rejection
                cur.execute("""
                    UPDATE empleave
                    SET status = %s, rejectReason = %s
                    WHERE start_date = %s AND leave_type = %s AND username = %s
                """, (status, reject_reason, start_date, leave_type, leave_username))

                notification_message = f"Your leave request starting {start_date} has been rejected. Reason: {reject_reason}"
                type="leave request"
                cur.execute(
                    'INSERT INTO notifications (username, notification, type) VALUES (%s, %s, %s)',
                    (leave_username, notification_message, type)
                )
            elif status == 'Approved':
                # Update leave status and send notification for approval
                cur.execute("""
                    UPDATE empleave
                    SET status = %s
                    WHERE start_date = %s AND leave_type = %s AND username = %s
                """, (status, start_date, leave_type, leave_username))

                notification_message = f"Your leave request starting {start_date} has been approved by {username}."
                type="leave request"
                cur.execute(
                    'INSERT INTO notifications (username, notification, type) VALUES (%s, %s, %s)',
                    (leave_username, notification_message, type)
                )

            mysql.connection.commit()
            cur.close()

            return jsonify({'message': f'Status updated to {status} successfully'}), 200

        else:
            # Handle filters
            username_filter = request.form.get('usernameFilter')
            from_date_filter = request.form.get('fromDateFilter')
            to_date_filter = request.form.get('toDateFilter')

            query = "SELECT * FROM empleave WHERE 1=1"
            params = []

            if username_filter:
                query += " AND username = %s"
                params.append(username_filter)
            if from_date_filter:
                query += " AND start_date >= %s"
                params.append(from_date_filter)
            if to_date_filter:
                query += " AND start_date <= %s"
                params.append(to_date_filter)

            cur.execute(query, params)
            filtered_data = cur.fetchall()

    elif request.method == 'GET':
        # On initial load, set the filter to today's date
        query = "SELECT * FROM empleave WHERE start_date BETWEEN %s AND %s"
        params = [selected_from_date, selected_to_date]

        cur.execute(query, params)
        filtered_data = cur.fetchall()

    cur.close()

    # Sort the data with "Pending" on top, then "Rejected", then "Approved"
    sorted_data = sorted(filtered_data, key=lambda x: ("Pending", "Rejected", "Approved").index(x[6]))

    return render_template(
        'leavemanager.html',
        employees=filtered_data,
        user_role=user_role,
        leaves=sorted_data,
        usernames=usernames,
        selected_username=selected_username,
        selected_from_date=selected_from_date,
        selected_to_date=selected_to_date,
        disable_filter=False,user_designation = user_designation
    )

@app.route('/update-leave-status', methods=['POST'])
def update_leave_status():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            leave_id = data.get('id')
            leave_type = data.get('leaveType')
            status = data.get('status')

            try:
                # Create a cursor to interact with the database
                cur = mysql.connection.cursor()

                # Execute the update query
                cur.execute("""
                    UPDATE empleave
                    SET leave_type = %s, status = %s
                    WHERE id = %s
                """, (leave_type, status, leave_id))

                # Commit the transaction to save changes
                mysql.connection.commit()

                # Close the cursor
                cur.close()

                # Return a success response
                return jsonify({'message': 'Leave status updated successfully'}), 200
            except Exception as e:
                # Handle any errors that occur during the query
                print(f"Error: {e}")
                return jsonify({'error': 'An error occurred while updating the leave status'}), 500
        else:
            return jsonify({'error': 'Request must be in JSON format'}), 400


# profile update
def generate_empid(designation: str) -> str:
    cursor = mysql.connection.cursor()
    if designation.lower() == 'trainee':
        empid_prefix = 'BATRD'
    else:
        empid_prefix = 'BA'
    
    cursor.execute("SELECT value FROM counters WHERE name = %s", (f'latest_empid_{empid_prefix}',))
    result = cursor.fetchone()
    latest_empid = result[0] if result else 0
    new_empid = latest_empid + 1

    # Return formatted empid and new value
    formatted_empid = f"{empid_prefix}{new_empid:02d}" if designation.lower() == 'trainee' else f"{empid_prefix}{new_empid:03d}"
    return formatted_empid, new_empid

#adduser
@app.route('/adduser', methods=['GET', 'POST'])
def adduser():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";
            </script>
        '''

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email_address = request.form['email_address']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone_number = request.form['phone_number']
        date_of_birth = request.form['date_of_birth']
        designation = request.form['designation']
        joining_date = request.form['joining_date']
        address = request.form['address']
        city = request.form['city']
        country = request.form['country']
        postal_code = request.form['postal_code']
        uan = request.form['uan']
        pf_num = request.form['pf_num']
        pan = request.form['pan']
        bname = request.form['bname']
        branch = request.form['branch']
        account_number = request.form['account_number']
        user_role = request.form['user_role']

        empid, new_empid_value = generate_empid(designation)

        cursor = mysql.connection.cursor()
        try:
            # Inserting data into Profile table
            cursor.execute('''
                INSERT INTO profile (empid, username, password, email_address, first_name, last_name, phone_number, date_of_birth, designation, joining_date, address, city, country, postal_code, uan, pan, bname, branch, account_number, user_role, pf_num) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', 
            (empid, username, password, email_address, first_name, last_name, phone_number, date_of_birth, designation, joining_date, address, city, country, postal_code, uan, pan, bname, branch, account_number, user_role, pf_num))
            
            # Inserting data into Users table
            cursor.execute('''
                INSERT INTO users (id, username, password, designation, employed_on) 
                VALUES (%s, %s, %s, %s, %s)
            ''', 
            (empid, username, password, designation, joining_date))
            
            # Determine the correct prefix for counter updates
            counter_name = 'latest_empid_BATR' if designation.lower() == 'trainee' else 'latest_empid_BA'

            # Updating the counter based on the designation
            cursor.execute("UPDATE counters SET value = %s WHERE name = %s", (new_empid_value, counter_name))

            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            print(f"Error occurred: {e}")
            return f"Error occurred: {e}"
        finally:
            cursor.close()

        return redirect(url_for('adduser'))  # Redirect to the adduser page

    return render_template('adduser.html', user_role=user_role,user_designation = user_designation)


#leaverequest 
# leave request changing code start


@app.route('/calculate_end_date', methods=['POST'])
def calculate_end_date():
    """Calculate 5 working days from the given start date."""
    data = request.get_json()
    start_date_str = data.get('start_date')

    if not start_date_str:
        return jsonify({'error': 'Start date is required'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        days_added = 0
        current_date = start_date

        # Calculate 5 working days excluding weekends
        while days_added < 5:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # Monday to Friday
                days_added += 1

        end_date = current_date.strftime('%Y-%m-%d')
        return jsonify({'end_date': end_date})
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400


@app.route('/leaverequest', methods=['GET', 'POST'])
def leavemanagement():
    username = session.get('username')  # Get username from session

    user_designation = session.get('designation')
    cursor = mysql.connection.cursor()  # Open the cursor

    # Fetch leave requests for the logged-in user
    cursor.execute('SELECT * FROM empleave WHERE username = %s', (username,))
    data = cursor.fetchall()

    cursor.execute("""
        SELECT leave_type, SUM(DATEDIFF(end_date, start_date) + 1) AS total_days
        FROM empleave
        WHERE username = %s AND status = 'Approved' AND leave_type IN ('sick', 'casual')
        GROUP BY leave_type
    """, (username,))
    leave_days = cursor.fetchall()
    leave_days_dict = {row[0].lower(): row[1] for row in leave_days}
    total_casual_days = leave_days_dict.get('casual', 0)
    total_sick_days = leave_days_dict.get('sick', 0)
    print(total_casual_days)
    print(total_sick_days)

    if request.method == 'POST':
        leave_type = request.form['leave_type'].lower()
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        reason = request.form['reason']

        error_message = None

        # Validation
        if not leave_type or not start_date or not end_date or not reason:
            error_message = "All fields are required. Please fill in all the details."
        elif start_date > end_date:
            error_message = "Start date must be before end date."

        if error_message is None:
            try:
                start_date_obj = datetime.strptime(start_date, '%d/%m/%Y')
                end_date_obj = datetime.strptime(end_date, '%d/%m/%Y')
                year_from_start_date = start_date_obj.year

                # Count leaves by type and status (Approved)
                cursor.execute(
                    """
                    SELECT leave_type, COUNT(*) AS leave_count 
                    FROM empleave 
                    WHERE username = %s AND YEAR(start_date) = %s AND status = %s
                    GROUP BY leave_type
                    """,
                    (username, year_from_start_date, 'Approved')
                )
                leave_counts = cursor.fetchall()
                leave_counts_dict = {row[0].lower(): row[1] for row in leave_counts}

                casual_leaves_taken = leave_counts_dict.get('casual', 0)
                sick_leaves_taken = leave_counts_dict.get('sick', 0)

                if leave_type == 'casual' and total_casual_days >= 12:
                    return '''
                        <script type="text/javascript">
                            alert("You have already taken the maximum of 12 casual leaves for the selected year.");
                            window.location.href = "/dashboard";
                        </script>
                    '''
                elif leave_type == 'sick' and total_sick_days >= 12:
                    return '''
                        <script type="text/javascript">
                            alert("You have already taken the maximum of 12 sick leaves for the selected year.");
                            window.location.href = "/leaverequest";
                        </script>
                    '''

                # Insert leave request
                cursor.execute(
                    'INSERT INTO empleave (username, leave_type, start_date, end_date, reason, status) VALUES (%s, %s, %s, %s, %s, %s)',
                    (username, leave_type, start_date_obj.strftime('%Y-%m-%d'),
                     end_date_obj.strftime('%Y-%m-%d'), reason, 'Pending')
                )

                # Add notification
                notification_message = f"{username} is requesting for a leave.From {start_date} to {end_date}"
                cursor.execute("SELECT username FROM profile WHERE designation IN (%s, %s)", ('CEO', 'HR'))
                ceo_users = cursor.fetchall()

                for ceo in ceo_users:
                    ceo_username = ceo[0]
                    type="leave dispotion"
                    cursor.execute(
                        'INSERT INTO notifications (username, notification, type) VALUES (%s, %s,%s)',
                        (ceo_username, notification_message, type)
                    )

                # Check for red flags (approved leaves only)
                cursor.execute("""
                    SELECT MAX(end_date) AS last_approved_date 
                    FROM empleave 
                    WHERE username = %s 
                    AND leave_type = %s
                    AND status = 'Approved'
                    AND MONTH(end_date) = MONTH(CURRENT_DATE)  # Filter for current month
                    AND YEAR(end_date) = YEAR(CURRENT_DATE)  # Filter for current year
                """, (username, leave_type))

                last_approved_date = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM empleave 
                    WHERE username = %s 
                    AND leave_type = %s 
                    AND status = 'Approved'
                """, (username, leave_type))
                approved_leave_count = cursor.fetchone()[0]

                current_month_year = datetime.now().strftime("%B %Y")

                if last_approved_date:
                    last_approved_date_str = last_approved_date.strftime('%d/%m/%Y')
                    today_date_str = datetime.today().strftime('%d/%m/%Y')
                    cursor.execute("""
                        INSERT INTO redflags (username, redflag, created_at,date)
                        VALUES (%s, %s, %s)
                    """, (username, f"You've already taken {approved_leave_count} {leave_type} leave(s). Last approved leave on {last_approved_date_str}. Requesting on {today_date_str}.", current_month_year,today_date_str))

                mysql.connection.commit()  # Commit all changes

                # Fetch updated leave requests
                cursor.execute('SELECT * FROM empleave WHERE username = %s', (username,))
                data = cursor.fetchall()

                return redirect(url_for('leavemanagement'))

            except ValueError:
                error_message = "There was an error processing the date. Please check your input."

        return render_template('leaverequest.html', leaves=data, error_message=error_message,user_designation=user_designation)

    cursor.close()  # Close the cursor
    return render_template('leaverequest.html', leaves=data, user_designation=user_designation,total_sick_days=total_sick_days,total_casual_days=total_casual_days)


# profile display
@app.route('/profile')
def profile():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    # Ensure username is a string
    if 'username':
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM profile WHERE username=%s"  # Use prepared statement
        cur.execute(sql, (session['username'],))
        profile = cur.fetchone()
        cur.close()
        # print(profile)
    return render_template('profile.html', profile=profile, user_role=user_role,user_designation = user_designation)


#work
@app.route('/work', methods=['GET', 'POST'])
def work():
    empid = session.get('empid')  # Get empid from session
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation=session.get('user_designation')
    
    
    if 'username' in session:  # Check if user is logged in
        empid = session['empid']  # Get empid from session
        username = session.get('username') #get username from session
        
        cursor = mysql.connection.cursor()
        
        # Fetch distinct usernames for the filter
        cursor.execute("SELECT DISTINCT username FROM profile")  # Adjust the query as needed
        usernames = [row[0] for row in cursor.fetchall()]  # Extract usernames into a list
        
        # Fetch user role based on the logged-in empid
        cursor.execute("SELECT user_role FROM profile WHERE empid = %s", (empid,))
        user_role = cursor.fetchone()[0]  # Assuming 'user_role' is the first column in the fetched result
        
        # Fetch the logged-in user's time data from the workreport
        cursor.execute("SELECT time FROM workreport WHERE empid = %s", (empid,))
        time_result = cursor.fetchone()  # Fetch one result

        # Handle case where no time data is found
        if time_result is None:
            
            time = None  # Handle as needed (set time to None or use a default value)
        else:
            time = time_result[0]  # Access the first column if the result is not None

        # Fetch filter parameters from the request (POST or GET)
        selected_username = request.form.get('usernameFilter')  # From filter dropdown
        selected_date = request.form.get('dateFilter')  # From date input
        
        # If no date is selected, default to today's date
        if not selected_date:
            selected_date = datetime.today().strftime('%Y-%m-%d')  # Default to today's date
        
        # If no username is selected, treat it as None for filtering
        if not selected_username:
            selected_username = None

        # If the user is the CEO, allow filtering by username and date
        if user_role == "CEO":
            # Prepare query with filters
            query = """
                SELECT wr.*, p.username 
                FROM workreport wr 
                JOIN profile p ON wr.empid = p.empid
                WHERE (%s IS NULL OR p.username = %s)  -- If no username selected, get all
                AND wr.date = %s
            """
            cursor.execute(query, (selected_username, selected_username, selected_date))
            disable_filter = False  # CEO can use the filter
        else:
            # If not the CEO, only retrieve the work reports for the logged-in empid
            query = """
                SELECT wr.*, p.username 
                FROM workreport wr 
                JOIN profile p ON wr.empid = p.empid 
                WHERE wr.empid = %s 
                AND wr.date = %s
            """
            cursor.execute(query, (empid, selected_date))
            disable_filter = True  # Non-CEO cannot use the filter
        
        # Fetch the result
        data = cursor.fetchall()
        cursor.close()
        
        # Check if there's no data found
        no_data = not data  # True if no data, False otherwise
        
        # Initialize timer_status, pause_reason, and check_reason
        timer_status, pause_reason, check_reason = None, None, None
        
        # Handle timer updates (assuming the data comes in as JSON)
        if request.method == 'POST' and request.is_json:
            data = request.get_json()
            action = data.get('action')
            work_done = data.get('work_done')
            pause_reason = data.get('pause_reason')
            check_reason = data.get('check_reason')

            cursor = mysql.connection.cursor()

            # Check if a work report for the empid, date, and work_done already exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM workreport 
                WHERE empid = %s AND date = %s AND work_done = %s
            """, (empid, selected_date, work_done))
            report_exists = cursor.fetchone()[0]  # Gets the count

            if report_exists == 0:
                # Insert the default "yet to start" status if this is a new work report
                cursor.execute("""
                    INSERT INTO workreport (empid, time, date, work_done, timer_status) 
                    VALUES (%s, %s, %s, %s, 'yet to start')
                """, (empid, time, selected_date, work_done,work_done))
                mysql.connection.commit()

            # Update the timer_status based on the action
            if action == 'play':
                # Update the work report's timer status to "running"
                cursor.execute("""
                    UPDATE workreport 
                    SET timer_status = 'running'
                    WHERE empid = %s AND work_done = %s AND date = %s
                """, (empid, work_done, selected_date))
                timer_status= 'running'
            elif action == 'pause':
            # Update the work report's timer status to 'paused' and record the pause reason
                cursor.execute("""
                    UPDATE workreport 
                    SET timer_status = 'paused', pause_reason = %s
                    WHERE empid = %s AND work_done = %s AND date = %s
                """, (pause_reason, empid, work_done, selected_date))
                timer_status = 'paused'
            elif action == 'check':
            # Update the work report's timer status to 'done' and record the check reason
                cursor.execute("""
                    UPDATE workreport 
                    SET timer_status = 'done', check_reason = %s
                    WHERE empid = %s AND work_done = %s AND date = %s
                """, (check_reason, empid, work_done, selected_date))
                timer_status = 'done'

            mysql.connection.commit()
            cursor.close()
        
            cursor = mysql.connection.cursor()
            # Fetch the timer_status data from the workreport
            cursor.execute("SELECT timer_status, pause_reason, check_reason FROM workreport WHERE empid = %s AND date = %s AND work_done = %s", (empid,selected_date,work_done))
            work_report_data = cursor.fetchone()
            cursor.close()
        
            if work_report_data:
                timer_status, pause_reason, check_reason = work_report_data
            else:
                timer_status, pause_reason, check_reason = None, None, None
        
            # Render the workreportlist template with the filtered data
        return render_template('work.html', project=data, usernames=usernames, 
                               disable_filter=disable_filter, selected_username=selected_username,
                               selected_date=selected_date, no_data=no_data, timer_status=timer_status,
                               pause_reason=pause_reason,check_reason=check_reason, username=username, user_role=user_role, user_designation=user_designation)
    else:
        return redirect(url_for('index'))

#allocate-work
@app.route('/allocatework', methods=['GET', 'POST'])
def allocatework():
    empid = session.get('empid')  # Get empid from session
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    
    
    # Fetch profile data based on empid
    profile = None
    if empid:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM profile WHERE empid = %s", (empid,))
        profile = cursor.fetchone()  # Fetch the first row
        cursor.close()

    # Fetch all usernames to populate the dropdown
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT username FROM profile")  # Fetch all usernames
    usernames = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        date = request.form['date']
        time = request.form['Timings']
        work_done = request.form['workdone']
        selected_username = request.form.get('usernameFilter')  # Get selected username from form

        # Fetch empid of the selected user
        if selected_username:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT empid FROM profile WHERE username = %s", (selected_username,))
            selected_profile = cursor.fetchone()
            cursor.close()

            if selected_profile:
                selected_empid = selected_profile[0]  # Get empid of the selected user

                cursor = mysql.connection.cursor()
                cursor.execute(
                    'INSERT INTO workreport (empid, date, time, work_done) VALUES (%s, %s, %s, %s)', 
                    (selected_empid, date, time, work_done)
                )
                mysql.connection.commit()
                cursor.close()

                return redirect(url_for('work'))  # Redirect to work report list after saving

    return render_template('allocatework.html', profile=profile, usernames=[u[0] for u in usernames], user_role=user_role,user_designation = user_designation)  # Pass profile and usernames to the template


#createproject
@app.route('/createproject', methods=['GET', 'POST']) 
def createproject():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    print(user_designation)
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    if request.method == 'POST':
        project_title = request.form['project_title']
        description= request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        meet = request.form['meet_link']
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO project VALUES (NULL, %s, %s, %s, %s, %s)', (project_title, description, start_date, end_date, meet))
        mysql.connection.commit()
        return render_template('create-project.html',user_role=user_role,user_designation = user_designation)
    return render_template('create-project.html',user_role=user_role,user_designation = user_designation)

# project-list
@app.route('/projectlist')
def projectlist():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    # print(user_role)
    if not username:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    if 'username':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM project")
        data = cur.fetchall()
        cur.close()
        # print(data)
        return render_template('projectlist.html', project=data, user_role=user_role, user_designation=user_designation)
    else:
        return redirect(url_for('index'))
#Get Employee
@app.route('/get_users', methods=['GET'])
def get_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users")  # Assuming the users table has 'id' and 'name' columns
    users = cur.fetchall()
    cur.close()
    return jsonify({'users': users})

#update project
@app.route('/update_project/<int:project_id>', methods=['POST'])
def update_project(project_id):
    updated_data = request.json
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE project
            SET project_title = %s, description = %s, start_date = %s, end_date = %s , meet = %s
            WHERE id = %s
        """, (updated_data['project_title'], updated_data['description'], updated_data['start_date'], updated_data['end_date'],updated_data['meet'], project_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


#delete project
@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM project WHERE id = %s", (project_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

    
#projectallocation
@app.route('/projectallocation', methods=['GET', 'POST'])
def projectallocation():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')

    # Restrict access to only users with appropriate roles
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    
    # Fetch project and user data for dropdown options
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM project")
    project_title1 = cursor.fetchall()  # List of projects to display on webpage
    cursor.execute("SELECT * FROM profile")
    username1 = cursor.fetchall()  # List of users to display on webpage

    # Handle POST request when form is submitted
    if request.method == 'POST':
        project_title = request.form['project_title']
        username = request.form['username']
        work_date = request.form['start_date']
        work_end = "yet to be decide"
        work_description = request.form['work_description']

        # Ensure all fields are filled before inserting into the database
        if project_title and username and work_date and work_description:
            # Check if the username is already allocated to the same project
            cursor.execute('''
                SELECT * FROM workallocation 
                WHERE project_title = %s AND username = %s
            ''', (project_title, username))
            existing_allocation = cursor.fetchone()

            if existing_allocation:
                # Show a popup message if already allocated
                return '''
                    <script type="text/javascript">
                        alert("This user is already allocated to the selected project.");
                        window.history.back();  // Redirect back to the form
                    </script>
                '''

            # Insert the data into the workallocation table
            cursor.execute('''
                INSERT INTO workallocation (project_title, username, work_date, work_description, work_end)
                VALUES (%s, %s, %s, %s, %s)
            ''', (project_title, username, work_date, work_description, work_end))
            
            # Commit the transaction
            mysql.connection.commit()
            
            # Redirect back to the same page after successful submission
            return redirect(url_for('projectallocation'))
        else:
            # Optional: Show an error message if any field is missing
            return '''
                <script type="text/javascript">
                    alert("Please fill in all fields.");
                </script>
            '''

    # Render the template with project and user data
    return render_template('projectallocation.html', project=project_title1, users=username1, user_role=user_role,user_designation = user_designation)


#allocatedlist
@app.route('/allocationlist', methods=['POST', 'GET'])
def allocationlist():
    # Fetch session data
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')

    # Check if user has the right role
    if not user_role in ['CEO']:
        return '''
        <script type="text/javascript">
            alert("Access denied. You do not have permission to view this page.");
            window.location.href = "/dashboard";
        </script>
        '''

    # Handle POST actions
    if request.method == 'POST':
        action = request.form.get('action')
        project_title = request.form.get('project_title')
        username = request.form.get('username')

        cur = mysql.connection.cursor()
        try:
            if action == 'remove':
                # Update work_end to today's date
                today_date = datetime.now().strftime('%Y-%m-%d')
                cur.execute("""
                    UPDATE workallocation 
                    SET work_end = %s 
                    WHERE project_title = %s AND username = %s
                """, (today_date, project_title, username))
            elif action == 'add':
                # Update work_end to "yet to be decide"
                cur.execute("""
                    UPDATE workallocation 
                    SET work_end = 'yet to be decide' 
                    WHERE project_title = %s AND username = %s
                """, (project_title, username))
            mysql.connection.commit()
        except MySQLdb.ProgrammingError as e:
            print("MySQL error:", e)
        finally:
            cur.close()

    # Fetch the list of projects
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM project")
    project = cur.fetchall()
    cur.close()

    # Apply filters from form submission
    selected_project_title = request.form.get('projectTitleFilter')
    selected_status = request.form.get('statusFilter')
    filters = []
    params = []

    if selected_project_title:
        filters.append("wr.project_title = %s")
        params.append(selected_project_title)

    if selected_status:
        if selected_status == 'removed':
            filters.append("wr.work_end != %s")
            params.append("yet to be decide")
        elif selected_status == 'yet to be decide':
            filters.append("wr.work_end = %s")
            params.append("yet to be decide")
        else:
            filters.append("wr.work_end = %s")
            params.append(selected_status)

    query = """
    SELECT 
        wr.project_title, 
        wr.username, 
        pr.empid,  
        wr.work_date,
        wr.work_end
    FROM 
        workallocation wr
    INNER JOIN 
        profile pr ON wr.username = pr.username
    """

    if filters:
        query += " WHERE " + " AND ".join(filters)

        # Fetch workallocations data only when filters are applied
        cur = mysql.connection.cursor()
        cur.execute(query, tuple(params))
        workallocations = cur.fetchall()
        cur.close()
    else:
        # If no filters, set workallocations to an empty list
        workallocations = []

    return render_template(
        'allocationlist.html',
        user_role=user_role,
        project=project,
        selected_project_title=selected_project_title,
        selected_status=selected_status,
        workallocations=workallocations,
        user_designation = user_designation
    )




#projectallocated
@app.route('/projectallocated')
def projectallocated():
    username = session.get('username') 
    user_designation = session.get('designation')       
    if not username:
        return redirect(url_for('index'))

    # Establishing the database connection
    cursor = mysql.connection.cursor()
    
    # Query to join workallocation and project tables based on project title
    query = """
        SELECT 
            wa.id, 
            wa.project_title, 
            wa.work_date, 
            wa.work_end, 
            wa.work_description, 
            p.meet
        FROM workallocation wa
        JOIN project p ON wa.project_title = p.project_title
        WHERE wa.username = %s
    """
    
    # Execute the query
    cursor.execute(query, (username,))
    data = cursor.fetchall()
    cursor.close()

    # Render the template with the retrieved data
    return render_template('projectallocated.html', work=data, user_designation=user_designation)




#payroll
@app.route('/payroll', methods=['GET'])
def payroll():
    username = session.get('username')
    empid = session.get('empid')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''

    if not username:
        return redirect(url_for('login'))  # Redirect if not logged in

    cur = mysql.connection.cursor()
    
    try:
        # Fetch all usernames for display
        cur.execute("SELECT username,CONCAT(first_name, ' ', last_name) FROM profile")
        usernames = cur.fetchall()

        selected_username = request.args.get('selected_username')
        pay_period = request.args.get('pay_period')

        payslip = None
        user = None
        
        if selected_username and pay_period:
            pay_period_with_day = f"{pay_period}-01"

            # Fetch the user's profile
            cur.execute("SELECT * FROM profile WHERE username=%s", (selected_username,))
            user = cur.fetchone()

            # Fetch the payslip for the selected pay period
            cur.execute("SELECT * FROM payslip WHERE employee_id=%s AND pay_period=%s", (user[1], pay_period_with_day))
            payslip = cur.fetchone()

            # Convert pay_period (e.g., "2024-07") to "MONTH YYYY" format
            if payslip:
                pay_period_date = datetime.strptime(payslip[15], "%Y-%m-%d")  # Assuming payslip[15] contains pay_period in "YYYY-MM-DD"
                formatted_pay_period = pay_period_date.strftime("%B %Y")  # E.g., "July 2024"
                payslip = list(payslip)  # Convert tuple to list to modify
                payslip[15] = formatted_pay_period  # Update pay_period format in payslip
        print(payslip[16])

    except Exception as e:
        print(f"Error occurred: {e}")  # Replace with proper logging
    finally:
        cur.close()

    return render_template('payroll.html', user=user, payslip=payslip, usernames=usernames, user_role=user_role,user_designation=user_designation )


# payrollmanager
@app.route('/payrollallocation', methods=['GET', 'POST'])
def payrollallocation():
    username = session.get('username')
    empid = session.get('empid')
    user_role = session.get('user_role')
    user_designation = session.get('designation')

    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";
            </script>
        '''

    cur = mysql.connection.cursor()
    cur.execute("SELECT empid, username, uan, pan, bname, branch, account_number, CONCAT(first_name, ' ', last_name) FROM profile")
    data = cur.fetchall()
    cur.close()

    cur = mysql.connection.cursor()
    cur.execute("SELECT empid, username FROM profile WHERE empid = %s", (empid,))
    user = cur.fetchone()
    cur.close()

    if request.method == 'POST':
        employee_id = request.form.get('emp_id')
        username = request.form.get('emp_name')
        pay_period_input = request.form.get('pay_period')
        pay_date = request.form.get('pay_date')
        bp = request.form.get('bp')
        hra = request.form.get('hra')
        ma = request.form.get('ma')
        ca = request.form.get('ca')
        oa = request.form.get('oa')
        pt = request.form.get('pt')
        pf = request.form.get('pf')
        ld = request.form.get('ld')
        payment_mode = request.form.get('payment_mode')
        working_days = request.form.get('working_days')
        non_working_days = request.form.get('non_working_days')
        unqID = request.form.get('unqID', 'DEFAULT_UNQID')  # Provide a default if empty

        # Ensure correct pay period format
        pay_period = str(datetime.strptime(pay_period_input + '-01', '%Y-%m-%d').date())

        # Get username from profile
        cur = mysql.connection.cursor()
        cur.execute("SELECT username FROM profile WHERE CONCAT(first_name, ' ', last_name) = %s", (username,))
        user_data = cur.fetchone()
        cur.close()

        if not user_data:
            return '''
                <script type="text/javascript">
                    alert("Invalid Employee Name. Please check again.");
                    window.location.href = "/payrollallocation";
                </script>
            '''

        employee_username = user_data[0]

        # Check if payroll already exists for the same period
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM payslip WHERE employee_id = %s AND pay_period = %s", (employee_id, pay_period))
        existing_allocation = cur.fetchone()
        cur.close()

        if existing_allocation:
            return '''
                <script type="text/javascript">
                    alert("Payroll for this employee has already been allocated for the selected period.");
                    window.location.href = "/payrollallocation";
                </script>
            '''

        # Calculate Gross Earnings, Total Deductions, and Net Pay
        ge = float(bp) + float(hra) + float(ma) + float(ca) + float(oa)
        td = float(pt) + float(pf) + float(ld)
        net_payable = ge - td

        # Insert into database
        cur = mysql.connection.cursor()
        cur.execute(
            """INSERT INTO payslip 
               (employee_id, username, pay_period, pay_date, bp, hra, ma, ca, oa, ge, pt, pf, ld, td, net_payable, 
               payment_mode, working_days, non_working_days, unqID) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (employee_id, employee_username, pay_period, pay_date, str(bp), str(hra), str(ma), str(ca), str(oa),
             str(ge), str(pt), str(pf), str(ld), str(td), str(net_payable), payment_mode, working_days,
             non_working_days, unqID)
        )
        mysql.connection.commit()
        cur.close()

        flash("Payroll successfully allocated!", "success")
        return redirect(url_for('payrollallocation'))

    return render_template('payrollallocation.html', users=data, user=user, user_role=user_role, user_designation=user_designation)




# emplist
@app.route('/emplist')
def emplist():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
   
    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM profile")
        data = cur.fetchall()
        cur.close()

        # print(data)
        return render_template('emplist.html', user_role=user_role, users=data,user_designation =user_designation)
    else:
        return redirect(url_for('index'))

@app.route('/update_user', methods=['POST'])
def update_user():
    if 'username' not in session or session['user_role'] in ['Employee', 'Trainee']:
        return jsonify(success=False, message="Access denied")

    data = request.json
    empid = data.get('empid')
    username = data.get('username')
    email = data.get('email')
    phone = data.get('phone')
    designation = data.get('designation')
    account_number = data.get('account_number')
    status = data.get('status')

    tables = [
        "attendence", "disputes", "empleave", "empreview", "notifications", 
        "payslip", "profile", "redflags", "requests", "scheduler", "users", 
        "workallocation", "worklog"
    ]

    try:
        cur = mysql.connection.cursor()

        # Fetch the old username
        cur.execute("SELECT username FROM profile WHERE empid = %s", (empid,))
        old_username = cur.fetchone()
        
        if not old_username:
            return jsonify(success=False, message="User not found")

        old_username = old_username[0]  # Extract actual value from tuple

        # Update profile table (main update query)
        query = """
            UPDATE profile
            SET username=%s, email_address=%s, phone_number=%s, designation=%s, user_status=%s, account_number=%s
            WHERE empid=%s
        """
        cur.execute(query, (username, email, phone, designation, status, account_number, empid))

        # Update username in all related tables using old username
        for table in tables:
            query = f"UPDATE {table} SET username = %s WHERE username = %s"
            cur.execute(query, (username, old_username))

        mysql.connection.commit()
        cur.close()
        return jsonify(success=True)

    except Exception as e:
        return jsonify(success=False, message=str(e))


@app.route('/update-user', methods=['POST'])
def update_users():
    if 'username' not in session or session['user_role'] in ['Employee', 'Trainee']:
        return jsonify(success=False, message="Access denied")

    data = request.json
    username = data.get('username')  # Get username instead of empid
    status = str(data.get('status'))  # Ensure status is a string ('0' or '1')

    try:
        cur = mysql.connection.cursor()
        query = """
            UPDATE profile
            SET user_status=%s
            WHERE username=%s
        """
        cur.execute(query, (status, username))  # Use username instead of empid
        mysql.connection.commit()
        cur.close()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))




    

###############################
#change-password
@app.route('/change-password', methods=['POST'])
def change_password():
    empid = session.get('empid')
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if new_password != confirm_password:
        flash('New password and confirm password do not match', 'new_password_error')
        return redirect('/userprofile')

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT password FROM profile WHERE empid = %s", (empid,))
        result = cursor.fetchone()
        
        if result and result[0] == old_password:
            cursor.execute("UPDATE profile SET password = %s WHERE empid = %s", (new_password, empid))
            mysql.connection.commit()
            flash('Password changed successfully', 'success')
        else:
            flash('Current password is incorrect', 'old_password_error')  # Use flash for incorrect password

    except mysql.connector.Error as err:
        flash(f"Error: {err}", 'danger')

    return redirect('/userprofile')


@app.route('/validate-password', methods=['POST'])
def validate_password():
    empid = session.get('empid')
    old_password = request.json.get('old_password')  # Get the old password from the request

    # Connect to the database and check the password
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT password FROM profile WHERE empid = %s", (empid,))
    result = cursor.fetchone()

    # Check if the password matches
    if result and result[0] == old_password:
        return jsonify({'is_valid': True})  # Password is correct
    else:
        return jsonify({'is_valid': False})  # Password is incorrect
    
############################################################
#project report
@app.route('/projectreport', methods=['GET', 'POST'])
def projectreport():
    empid = session.get('empid')  # Get empid from session
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')

    if not username:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    
    cursor = mysql.connection.cursor()
    
    # Fetch all projects allocated to the user
    if user_role == 'CEO' or user_role == 'HR':
        cursor.execute("SELECT project_title FROM project")
        projects = cursor.fetchall()
    else:
        cursor.execute("SELECT project_title FROM workallocation WHERE username = %s", (username,))
        projects = cursor.fetchall()
      # Fetch all project titles as a list of tuples
    # print(projects)
    # Handle case if no projects are found
    if not projects:
        cursor.close()
        return '''
            <script type="text/javascript">
                alert("No projects available.");
                window.location.href = "/dashboard";
            </script>
        '''

    # Fetch user profile data
    cursor.execute("SELECT * FROM profile WHERE empid = %s", (empid,))
    profile = cursor.fetchone()

    if request.method == 'POST':
        project_title = request.form['project_title']  # Correctly named input field
        date = request.form['date']
        time = request.form['Timings']
        work_done = request.form['workdone']

        # Check if the global toggle is ON in the 'work' table
        cursor.execute('SELECT toogle FROM work LIMIT 1')  # Assuming there's only one row for toggle
        toggle_status = cursor.fetchone()

        if toggle_status and toggle_status[0] == 'on':  # Assuming 'ON' is stored as a string
            # Check for duplicate entry in the same time slot and project
            cursor.execute(
                'SELECT COUNT(*) FROM projectreport WHERE empid = %s AND project_title = %s AND date = %s AND time = %s',
                (empid, project_title, date, time)
            )
            duplicate_count = cursor.fetchone()[0]

            if duplicate_count > 0:
                cursor.close()
                return '''
                    <script type="text/javascript">
                        alert("You have already entered a report for this project, date, and time slot.");
                        window.history.back();
                    </script>
                '''

            # Insert the project work report into the table
            cursor.execute(
                'INSERT INTO projectreport (empid, project_title, date, time, work_done) VALUES (%s, %s, %s, %s, %s)', 
                (empid, project_title, date, time, work_done)
            )
            mysql.connection.commit()
        else:
            cursor.close()
            return '''
                <script type="text/javascript">
                    alert("Access denied to store the data.");
                    window.history.back();
                </script>
            '''

    cursor.close()
    return render_template('projectreport.html', projects=projects, profile=profile, user_role=user_role,user_designation = user_designation)



#workreport     
@app.route('/workreport', methods=['GET', 'POST'])
def workreport():
    empid = session.get('empid')  # Get empid from session
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    if not username:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    profile = None
    booked_slots = []
    if empid:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM profile WHERE empid = %s", (empid,))
        profile = cursor.fetchone()

        # Fetch booked slots for the user
        if request.method == 'POST' and 'date' in request.form:
            date = request.form['date']
            cursor.execute(
                'SELECT time FROM workreport WHERE empid = %s AND date = %s',
                (empid, date)
            )
            booked_slots = [row[0] for row in cursor.fetchall()]

        cursor.close()

    if request.method == 'POST' and 'workdone' in request.form:
        date = request.form['date']
        time = request.form['Timings']
        work_done = request.form['workdone']

        # Check if the toggle is ON in the 'work' table (global toggle, no empid/date reference)
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT toogle FROM work LIMIT 1')  # Assuming there's only one row for toggle
        toggle_status = cursor.fetchone()

        if toggle_status and toggle_status[0] == 'on':  # Assuming 'ON' is stored as a string
            # Check for duplicate entry in the same time slot
            cursor.execute(
                'SELECT COUNT(*) FROM workreport WHERE empid = %s AND date = %s AND time = %s',
                (empid, date, time)
            )
            duplicate_count = cursor.fetchone()[0]

            if duplicate_count > 0:
                cursor.close()
                return '''
                    <script type="text/javascript">
                        alert("You have selected already entered time slot");
                        window.history.back();
                    </script>
                '''

            # Insert the work done data into the table
            cursor.execute(
                'INSERT INTO workreport (empid, date, time, work_done) VALUES (%s, %s, %s, %s)',
                (empid, date, time, work_done)
            )
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('workreport'))
        else:
            cursor.close()
            return '''
                <script type="text/javascript">
                    alert("Access denied to store the data.");
                    window.history.back();
                </script>
            '''

    return render_template('workreport.html', profile=profile, user_role=user_role, booked_slots=booked_slots,user_designation = user_designation)

@app.route('/checklist')
def checklist():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')
    # print(user_designation)
    cursor = mysql.connection.cursor()
    if not username or user_designation not in ['CEO' , 'HR']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''


    today_date = datetime.today().date()

    # Modified query to join worklog and attendance based on today's date and username
    query = '''
        SELECT w.*, a.type 
        FROM worklog w
        LEFT JOIN attendence a ON a.username = w.username AND a.date = %s
        WHERE w.status = "pending" AND w.date = %s
    '''
    
    cursor.execute(query, (today_date,today_date,))
    worklog_data = cursor.fetchall()
    print(worklog_data)

    no_data = not worklog_data

    return render_template('checkinaccept.html', 
                           username=username, 
                           user_role=user_role, 
                           user_designation=user_designation, 
                           no_data=no_data, 
                           worklog_data=worklog_data)


@app.route('/update_checkin_status', methods=['POST'])
def update_checkin_status():
    worklog_id = request.form.get('id')
    status = request.form.get('status')

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE worklog SET status = %s WHERE id = %s", (status, worklog_id))
    mysql.connection.commit()
    cursor.close()

    return jsonify({"message": "Status updated successfully"})


@app.route('/checkin', methods=['POST'])
def checkin():
    # Get the username from the session
    username = session.get('username')
    if not username:
        return jsonify({'message': 'Access denied. Please log in.', 'redirect': '/login'}), 401

    # Get today's date and current time
    today_date = datetime.now().date()
    current_time = datetime.now().time()

    # Restrict check-in before 9:00 AM
    earliest_checkin_time = time(9, 0, 0)  # 9:00 AM
    if current_time < earliest_checkin_time:
        return jsonify({'message': 'You cannot check in before 9:00 AM.'}), 403

    try:
        cursor = mysql.connection.cursor()

        # Check if the user has already checked in today
        cursor.execute(
            'SELECT checkin, checkout FROM worklog WHERE username = %s AND date = %s',
            (username, today_date)
        )
        record = cursor.fetchone()

        if record:
            checkin_time, checkout_time = record

            # If check-in exists but checkout is NULL, user must check out first
            if checkin_time and checkout_time is None:
                cursor.close()
                return jsonify({'message': 'Please check out before checking in again.'}), 400

        # Insert check-in record
        cursor.execute(
            'INSERT INTO worklog (username, date, checkin, status) VALUES (%s, %s, %s, %s)',
            (username, today_date, current_time, "pending")
        )
        mysql.connection.commit()
        cursor.close()

        return jsonify({'message': 'Check-in successful!', 'redirect': '/dashboard'}), 200

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500
    


from flask import Flask, jsonify, session
from datetime import datetime, time

@app.route('/checkout', methods=['POST'])
def checkout():
    # Get the username from the session
    username = session.get('username')
    if not username:
        return jsonify({'message': 'Access denied. Please log in.', 'redirect': '/login'}), 401

    try:
        cursor = mysql.connection.cursor()
        # Get today's date and current time
        today_date = datetime.now().date()
        current_time = datetime.now().time()

        # Restrict checkout after 7:00 PM
        cutoff_time = time(11, 41, 0)  # 7:00 PM
        if current_time > cutoff_time:
            return jsonify({'message': 'You cannot checkout after 7:00 PM.'}), 403

        # Check if the user has already checked in today
        cursor.execute(
            'SELECT checkin, work_time, checkout, status FROM worklog WHERE username = %s AND date = %s AND checkout IS NULL',
            (username, today_date)
        )
        record = cursor.fetchone()

        if not record:
            cursor.close()
            return jsonify({'message': 'No check-in record found for today or already checked out. Please check in first.'}), 400

        checkin_time = record[0]
        checkout_time = record[2]  # Will be None
        previous_work_time = record[1] or 0  # Handle NULL values by defaulting to 0

        # Ensure checkout time is None
        if checkout_time is not None:
            cursor.close()
            return jsonify({'message': 'Already checked out. Cannot check out again.'}), 400
        
        # Restrict users with pending or rejected status
        if record[3] in ['pending', 'rejected']:
            cursor.close()
            return jsonify({'message': 'Your account status is pending or rejected. You cannot checkout.'}), 403

        # Calculate work time
        checkin_time_obj = datetime.strptime(str(checkin_time), "%H:%M:%S").time()
        time_difference = datetime.combine(today_date, current_time) - datetime.combine(today_date, checkin_time_obj)
        time_difference_minutes = time_difference.total_seconds() // 60

        total_work_time = previous_work_time + time_difference_minutes

        # Update the worklog and set checkout time
        cursor.execute(
            'UPDATE worklog SET checkout = %s, work_time = %s WHERE username = %s AND date = %s AND checkout IS NULL',
            (current_time, total_work_time, username, today_date)
        )
        mysql.connection.commit()
        cursor.close()

        return jsonify({'message': 'Checkout successful!', 'redirect': '/dashboard'}), 200

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500




# Track toggle state
@app.route('/toggle_updates', methods=['POST'])
def toggle_updates():
    global allow_updates
    allow_updates = not allow_updates  # Toggle the state
    # Determine the new toggle state as "on" or "off"
    new_toggle_state = "on" if allow_updates else "off"
    # Update the toggle state in the database
    cursor = mysql.connection.cursor()
    try:
        # Assuming there is only one row for the toggle setting
        cursor.execute("UPDATE work SET toogle = %s", (new_toggle_state,))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

    # Respond with the updated state
    return jsonify({"allow_updates": allow_updates})


def manual_toggle_updates():
    with app.app_context():  # Explicitly push the Flask app context
        current_time = datetime.now().time().replace(microsecond=0)  # Remove microseconds
        allow_updates = False
        
        # Check if the current time matches 12:40 or 12:39
        if current_time == datetime.strptime("09:00", "%H:%M").time():
            allow_updates = True
        elif current_time == datetime.strptime("18:15", "%H:%M").time():
            allow_updates = False # Turn off

        # Determine the new toggle state as "on" or "off"
        new_toggle_state = "on" if allow_updates else "off"
        
        # Update the toggle state in the database
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("UPDATE work SET toogle = %s", (new_toggle_state,))
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            print(f"Error updating toggle state: {e}")
        finally:
            cursor.close()

# Scheduler setup
scheduler = BackgroundScheduler()

# Add jobs to toggle at specific times
scheduler.add_job(manual_toggle_updates, 'cron', hour=9, minute=0)  # 9:00 AM
scheduler.add_job(manual_toggle_updates, 'cron', hour=18, minute=15)  # 6:15 PM
scheduler.add_job(auto_reject_pending_leaves, 'cron', hour=12, minute=37)
scheduler.add_job(add_weekend_holidays,'cron', hour=0, minute=0)
scheduler.add_job(insert_attendance_records, 'cron', hour=10, minute=5)
scheduler.add_job(func=send_reminder_notifications, trigger="interval", minutes=30)
                  


# Start the scheduler
scheduler.start()

@app.route('/toggle_updates', methods=['POST'])
def manual_toggle_endpoint():
    """Manually toggle updates if needed."""
    response = manual_toggle_updates()
    return response

#workreportlist
# # Logging
# logging.basicConfig(level=logging.ERROR)

def get_missing_time_slots_data(start_date, end_date, selected_username=None):
    with app.app_context():
        cursor = mysql.connection.cursor()

        # Define the available time slots
        time_slots = [
            "9am to 10am", "10am to 11am", "11am to 12pm",
            "12pm to 1pm", "1pm to 2pm",
            "2pm to 3pm", "3pm to 4pm", "4pm to 4:30pm",
            "4:30pm to 5pm", "5pm to 6pm"
        ]

        # Fetch all employees
        if selected_username:
            cursor.execute("SELECT empid, username, user_status FROM profile WHERE username = %s", (selected_username,))
        else:
            cursor.execute("SELECT empid, username, user_status FROM profile")
        all_employees = cursor.fetchall()

        # Fetch work reports for the given date range
        cursor.execute(""" 
            SELECT empid, date, time FROM workreport 
            WHERE date BETWEEN %s AND %s
        """, (start_date, end_date))
        work_reports = cursor.fetchall()

        # Organize work reports into a dictionary by empid and date
        work_reports_dict = {}
        for empid, date, time_slot in work_reports:
            key = (empid, date)
            if key not in work_reports_dict:
                work_reports_dict[key] = set()
            if time_slot:
                work_reports_dict[key].add(time_slot)

        # Prepare the result data
        missing_slots_data = []
        for empid, username, user_status in all_employees:
            if user_status == "0":
                continue  # Skip inactive employees

            for date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)):
                # Check if the current date is a holiday
                cursor.execute("""
                    SELECT COUNT(*) FROM holidays WHERE holiday_date = %s
                """, (date,))
                is_holiday = cursor.fetchone()[0] > 0

                if is_holiday:
                    continue  # Skip the current date if it's a holiday

                key = (empid, date)
                reported_slots = work_reports_dict.get(key, set())

                # Check if the employee is on approved leave
                cursor.execute("""
                    SELECT COUNT(*) FROM empleave
                    WHERE username = %s AND status = 'Approved'
                    AND start_date <= %s AND end_date >= %s
                """, (username, date, date))
                is_on_leave = cursor.fetchone()[0] > 0

                if not is_on_leave:
                    # Identify missing slots
                    missing_slots = [slot for slot in time_slots if slot not in reported_slots]

                    if missing_slots:
                        missing_slots_data.append({
                            "username": username,
                            "date": str(date),
                            "missed_slots_count": len(missing_slots),
                            "missed_slots": ", ".join(missing_slots)
                        })

        cursor.close()
        return missing_slots_data

def get_non_holiday_non_leave_dates_count(start_date, end_date, selected_username=None):
    with app.app_context():
        cursor = mysql.connection.cursor()

        # Fetch all employees
        if selected_username:
            cursor.execute("SELECT empid, username, user_status FROM profile WHERE username = %s", (selected_username,))
        else:
            cursor.execute("SELECT empid, username, user_status FROM profile")
        all_employees = cursor.fetchall()

        # Prepare the result data for counting non-holiday and non-leave dates
        non_holiday_non_leave_counts = {}

        for empid, username, user_status in all_employees:
            if user_status == "0":
                continue  # Skip inactive employees

            non_holiday_non_leave_count = 0
            for date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)):
                # Check if the current date is a holiday
                cursor.execute("""
                    SELECT COUNT(*) FROM holidays WHERE holiday_date = %s
                """, (date,))
                is_holiday = cursor.fetchone()[0] > 0

                if is_holiday:
                    continue  # Skip the current date if it's a holiday

                # Check if the employee is on approved leave
                cursor.execute("""
                    SELECT COUNT(*) FROM empleave
                    WHERE username = %s AND status = 'Approved'
                    AND start_date <= %s AND end_date >= %s
                """, (username, date, date))
                is_on_leave = cursor.fetchone()[0] > 0

                if not is_on_leave:
                    non_holiday_non_leave_count += 1  # Count the date if it's not a holiday and not a leave day

            # Store the count for each employee
            non_holiday_non_leave_counts[username] = non_holiday_non_leave_count

        cursor.close()
        return non_holiday_non_leave_counts


@app.route('/missing', methods=['GET', 'POST'])
def missing():
    try:
        # Check if the user is logged in
        if 'username' in session:
            empid = session.get('empid')
            username = session.get('username')
            user_role = session.get('user_role')

            cursor = mysql.connection.cursor()

            # Fetch distinct usernames for filter options
            cursor.execute("SELECT DISTINCT username FROM profile")
            usernames = [row[0] for row in cursor.fetchall()]

            # Get filter parameters from the form
            selected_username = request.form.get('usernameFilter')
            selected_from_date = request.form.get('fromDateFilter')
            selected_to_date = request.form.get('toDateFilter')

            # Default to today's date if no filter dates provided
            today_date = datetime.today().strftime('%Y-%m-%d')
            if not selected_from_date:
                selected_from_date = today_date
            if not selected_to_date:
                selected_to_date = today_date

            # Convert string to date object
            try:
                start_date = datetime.strptime(selected_from_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(selected_to_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

            # Fetch the missing slots data
            missing_slots_data = get_missing_time_slots_data(start_date, end_date, selected_username)
            actual=get_non_holiday_non_leave_dates_count(start_date, end_date, selected_username)
            actual_count = actual.get(selected_username, 0) * 10
            print(actual_count)

            # Render the template
            return render_template(
                'missing.html',
                usernames=usernames,
                selected_username=selected_username,
                selected_from_date=selected_from_date,
                selected_to_date=selected_to_date,
                missing_slots_data=missing_slots_data,
                user_role=user_role,
                actual_count=actual_count
            )
        else:
            return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error in missing: {str(e)}")
        return render_template('error.html', message="An error occurred while processing your request.")


@app.route('/workreportlist', methods=['GET', 'POST'])
def workreportlist():
    global allow_updates
    user_designation = session.get('designation')
    print(user_designation)
    try:
        # Fetch the current toggle state from the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT toogle FROM work LIMIT 1")
        result = cursor.fetchone()
        allow_updates = result[0] == "on" if result else False
        cursor.close()

        # Check if the user is logged in
        if 'username' in session:
            empid = session['empid']
            username = session.get('username')
            user_role = session.get('user_role')

            cursor = mysql.connection.cursor()

            # Fetch distinct usernames for filter options
            cursor.execute("SELECT DISTINCT username FROM profile")
            usernames = [row[0] for row in cursor.fetchall()]

            # Get filter parameters from the form
            selected_username = request.form.get('usernameFilter', username)
            selected_from_date = request.form.get('fromDateFilter')
            selected_to_date = request.form.get('toDateFilter')

            # Default to today's date if no filter dates provided
            today_date = datetime.today().strftime('%Y-%m-%d')
            if not selected_from_date:
                selected_from_date = today_date
            if not selected_to_date:
                selected_to_date = today_date

            # Fetch user details for CEO-selected user
            selected_user_details = None
            if selected_username:
                cursor.execute("SELECT empid, username FROM profile WHERE username = %s", (selected_username,))
                selected_user_details = cursor.fetchone()

            # Build filters and query parameters
            filters = []
            params = []
            if user_role == "CEO" or user_designation == "HR":
                if selected_username:
                    filters.append("p.username = %s")
                    params.append(selected_username)
                if selected_from_date and selected_to_date:
                    filters.append("wr.date BETWEEN %s AND %s")
                    params.extend([selected_from_date, selected_to_date])
                disable_filter = False
            else:
                filters.append("wr.empid = %s")
                params.append(empid)
                if selected_from_date and selected_to_date:
                    filters.append("wr.date BETWEEN %s AND %s")
                    params.extend([selected_from_date, selected_to_date])
                disable_filter = True

            # Final query
            query = f"""
                SELECT wr.*, p.username 
                FROM workreport wr 
                JOIN profile p ON wr.empid = p.empid 
                WHERE {' AND '.join(filters)}
            """
            cursor.execute(query, params)
            data = cursor.fetchall()
            cursor.close()

            no_data = not data

            # Render the template
            return render_template(
                'workreportlist.html',
                project=data,
                usernames=usernames,
                disable_filter=disable_filter,
                selected_username=selected_username,
                selected_user_details=selected_user_details,
                selected_from_date=selected_from_date,
                selected_to_date=selected_to_date,
                today_date=today_date,
                no_data=no_data,
                user_role=user_role,
                allow_updates=allow_updates,
                user_designation=user_designation
            )
        else:
            return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error in workreportlist: {str(e)}")
        return render_template('error.html', message="An error occurred while processing your request.")

#projectreportlist
@app.route('/projectreportlist', methods=['GET', 'POST'])
def projectreportlist():
    global allow_updates

    user_designation = session.get('designation')
    try:
        # Fetch the current toggle state from the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT toogle FROM work LIMIT 1")
        result = cursor.fetchone()
        allow_updates = result[0] == "on" if result else False
        cursor.close()

        # Check if the user is logged in
        if 'username' in session:
            empid = session['empid']
            username = session.get('username')
            user_role = session.get('user_role')

            cursor = mysql.connection.cursor()

            # Fetch distinct project titles
            if user_role in ['CEO', 'HR']:
                cursor.execute("SELECT DISTINCT project_title FROM workallocation")
            else:
                cursor.execute("SELECT DISTINCT project_title FROM workallocation WHERE username = %s", (username,))
            project_titles = [row[0] for row in cursor.fetchall()]

            # Get filter parameters from the form
            selected_project_title = request.form.get('projectTitleFilter')
            selected_from_date = request.form.get('fromDateFilter')
            selected_to_date = request.form.get('toDateFilter')

            # Default to today's date if no filter dates provided
            today_date = datetime.today().strftime('%Y-%m-%d')
            if not selected_from_date:
                selected_from_date = today_date
            if not selected_to_date:
                selected_to_date = today_date

            # Build filters and query parameters
            filters = []
            params = []

            if user_role in ['CEO', 'HR']:
                # CEO/HR: Filter by selected project title and date range
                if selected_project_title:
                    filters.append("wr.project_title = %s")
                    params.append(selected_project_title)
                if selected_from_date and selected_to_date:
                    filters.append("wr.date BETWEEN %s AND %s")
                    params.extend([selected_from_date, selected_to_date])
            else:
                # Other roles: Filter by username, project title, and date range
                filters.append("p.username = %s")
                params.append(username)
                if selected_project_title:
                    filters.append("wr.project_title = %s")
                    params.append(selected_project_title)
                if selected_from_date and selected_to_date:
                    filters.append("wr.date BETWEEN %s AND %s")
                    params.extend([selected_from_date, selected_to_date])

            # Final query with dynamic filter conditions
            query = f"""
                SELECT wr.*, p.username 
                FROM projectreport wr 
                JOIN profile p ON wr.empid = p.empid 
                {f"WHERE {' AND '.join(filters)}" if filters else ""}
            """
            cursor.execute(query, params)
            data = cursor.fetchall()
            cursor.close()

            no_data = not data
            # print(len(project_titles))
            # print(project_titles)
            # Render the template
            return render_template(
                'projectreportlist.html',
                project=data,
                project_titles=project_titles if len(project_titles) > 1 else None,
                disable_filter=user_role not in ['CEO', 'HR'],
                selected_project_title=selected_project_title,
                selected_from_date=selected_from_date,
                selected_to_date=selected_to_date,
                today_date=today_date,
                no_data=no_data,
                user_role=user_role,
                allow_updates=allow_updates,
                user_designation=user_designation
            )
        else:
            return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Error in projectreportlist: {str(e)}")
        return render_template('error.html', message="An error occurred while processing your request.")


    
# employe agreement code
# Route to display the form
# Define the templates for each role
TEMPLATES = {
    "developer": "developer_template.docx",
    "designer": "designer_template.docx",
    "tester": "tester_template.docx"
}

# Function to update document with the provided details
def update_document(role, name, parent_name, address, age, email):
    try:
        # Select the correct template based on the role
        template_file = TEMPLATES.get(role)
        if not template_file:
            return "Invalid role selected."

        # Load the selected Word document template
        doc = Document(template_file)

        # Loop through all paragraphs in the document and update placeholders
        for para in doc.paragraphs:
            if 'Pedasingu Abhi Priya' in para.text:
                para.text = para.text.replace('Pedasingu Abhi Priya', name)
                for run in para.runs:
                    if name in run.text:
                        run.bold = True

            if 'son/daughter/wife of Venkata Rama Raju' in para.text:
                para.text = para.text.replace('son/daughter/wife of Venkata Rama Raju', f'son/daughter/wife of {parent_name}')
                for run in para.runs:
                    if f'son/daughter/wife of {parent_name}' in run.text:
                        run.bold = True

            if '4-307, Vuyyari vari Meraka, Pragathi Nagar, Sakhinetipalli , East Godavari, Andhra Pradesh – 533251' in para.text:
                para.text = para.text.replace('4-307, Vuyyari vari Meraka, Pragathi Nagar, Sakhinetipalli , East Godavari, Andhra Pradesh – 533251', address)
                for run in para.runs:
                    if address in run.text:
                        run.bold = True

            if '21 years' in para.text:
                para.text = para.text.replace('21 years', f'{age} years')
                for run in para.runs:
                    if f'{age} years' in run.text:
                        run.bold = True

            if 'abhipriya0432@gmail.com' in para.text:
                para.text = para.text.replace('abhipriya0432@gmail.com', email)
                for run in para.runs:
                    if email in run.text:
                        run.bold = True

        # Save the updated document into a BytesIO object to send as a download
        byte_io = io.BytesIO()
        doc.save(byte_io)
        byte_io.seek(0)

        return byte_io
    except Exception as e:
        return str(e)


@app.route("/emp_agreement", methods=["GET", "POST"])
def emp_agreement():
    username = session.get('username')
    user_role = session.get('user_role')
    user_designation = session.get('designation')

    if not username or user_role in ['Employee', 'Trainee','HR']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    if request.method == "POST":
        # Get the form data
        role = request.form["role"]
        name = request.form["name"]
        parent_name = request.form["parent_name"]
        address = request.form["address"]
        age = request.form["age"]
        email = request.form["email"]

        # Generate the updated document based on the selected role
        updated_doc = update_document(role, name, parent_name, address, age, email)

        if isinstance(updated_doc, str):
            # If there's an error, display it
            return render_template("index.html", error=updated_doc)

        # Send the document as a downloadable file
        return send_file(updated_doc, as_attachment=True, download_name=f"Employee_Agreement_{name}.docx")

    return render_template("emp_agreement.html", user_role=user_role,user_designation =user_designation)

@app.route('/worktype')
def home():
    # Example data for rendering
    user_role = 'CEO'  # This could be dynamic based on the logged-in user
    disable_filter = False  # Set to True to disable the filters
    selected_work_type = ''  # Default selection for work type filter
    selected_work_from_date = ''  # Default selection for from date filter
    selected_work_to_date = ''  # Default selection for to date filter

    # Render the HTML with these variables
    return render_template('worktype.html', 
                           session={'user_role': user_role},
                           disable_filter=disable_filter,
                           selected_work_type=selected_work_type,
                           selected_work_from_date=selected_work_from_date,
                           selected_work_to_date=selected_work_to_date)

@app.route('/filter', methods=['POST'])
def filter_data():
    # Extract filter parameters from the request
    work_type = request.form.get('workTypeFilter', '')
    from_date = request.form.get('workFromDateFilter', '')
    to_date = request.form.get('workToDateFilter', '')

    # Debugging logs
    print("Work Type:", work_type)
    print("From Date:", from_date)
    print("To Date:", to_date)

    # Here, you can add logic to query the database or process the filters
    filtered_data = {
        "work_type": work_type,
        "from_date": from_date,
        "to_date": to_date,
    }

    # Return a JSON response for demonstration purposes
    return jsonify(filtered_data)

# if __name__ == '__main__':
#     app.run(debug=True)



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)