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

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'chakri1234'
app.config['MYSQL_DB'] = 'emp'


mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('sign-up.html')

@app.route('/header')
def header():
    return render_template('header.html')

UPLOAD_FOLDER = 'uploads/'  # Modify this path based on your project structure
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}

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
        cursor.execute("SELECT * FROM profile WHERE username != %s", (username,))
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

        cur.execute(insert_query, (sitemap_id, project, module, module_list, page_name, page_url, page_description))
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
            cur.execute(
                'INSERT INTO notifications (username, notification) VALUES (%s, %s)',
                (ceo[0], notification_message)  # Fix: Access the username from ceo tuple
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

def post_redflags_for_missing_work_reports():
    # Push the application context to make sure the app is accessible in the background task
    with app.app_context():
        cursor = mysql.connection.cursor()

        # Define the available time slots
        time_slots = [
            "9am to 10am", "10am to 11am", "11am to 12pm",
            "12pm to 1pm", "1pm to 2pm",
            "2pm to 3pm", "3pm to 4pm", "4pm to 4:30pm",
            "4:30pm to 5pm", "5pm to 6pm"
        ]

        # Get the current date
        current_date = datetime.now().date()

        # Check if today is a holiday
        cursor.execute("""
            SELECT COUNT(*) FROM holidays WHERE holiday_date = %s
        """, (current_date,))
        is_holiday = cursor.fetchone()[0] > 0

        # If today is a holiday, skip the red flag process
        if is_holiday:
            cursor.close()
            return

        # Get all employees from the profile table
        cursor.execute("SELECT empid, username FROM profile")
        all_employees = cursor.fetchall()  # Returns a list of tuples (empid, username)

        # Get all work reports for today
        cursor.execute("""
            SELECT wr.empid, wr.time
            FROM workreport wr
            WHERE wr.date = %s
        """, (current_date,))
        work_reports = cursor.fetchall()

        # Organize work reports into a dictionary by empid
        work_reports_dict = {}
        for empid, time_slot in work_reports:
            if empid not in work_reports_dict:
                work_reports_dict[empid] = set()
            if time_slot:
                work_reports_dict[empid].add(time_slot)

        # Process each employee
        for empid, username in all_employees:
            reported_slots = work_reports_dict.get(empid, set())

            # Check if the employee is on approved leave
            cursor.execute("""
                SELECT COUNT(*) FROM empleave
                WHERE username = %s AND status = 'Approved'
                AND start_date <= %s AND end_date >= %s
            """, (username, current_date, current_date))
            is_on_leave = cursor.fetchone()[0] > 0

            if not is_on_leave:
                # Identify missing slots
                missing_slots = [slot for slot in time_slots if slot not in reported_slots]

                if missing_slots:
                    missing_slots_str = ", ".join(missing_slots)
                    cursor.execute("""
                        INSERT INTO redflags (username, redflag)
                        VALUES (%s, %s)
                    """, (username, f"You haven't reported for the following time slots today ({current_date}): ({missing_slots_str})"))

        # Commit the changes and close the cursor
        mysql.connection.commit()
        cursor.close()


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
        current_time = datetime.now()
        today_date = current_time.strftime('%Y-%m-%d')  # Format the current date as YYYY-MM-DD
        print(f"Running auto-reject task at {current_time}")
        
        cur.execute("""
            UPDATE empleave
            SET status = 'Rejected'
            WHERE leave_type = 'sick' 
              AND status = 'Pending'
              AND start_date = %s
        """, (today_date,))
        
        mysql.connection.commit()
        cur.close()
        print("Auto-reject task completed.")

def add_weekend_holidays():
    with app.app_context():  # Ensure the application context is active
        today = datetime.now(pytz.timezone('Asia/Kolkata'))
        # print(today) 
        # Current time in 'Asia/Kolkata' timezone
        day_of_week = today.weekday()  # Monday is 0, Sunday is 6

        if day_of_week in [5, 6]:  # 5 is Saturday, 6 is Sunday
            holiday_reason = "Weekend (Saturday)" if day_of_week == 5 else "Weekend (Sunday)"
            holiday_date = today.strftime('%Y-%m-%d')

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
    user_designation = session.get('designation')
    print(user_designation)
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
                cur.execute(
                    'INSERT INTO notifications (username, notification) VALUES (%s, %s)',
                    (leave_username, notification_message)
                )
            elif status == 'Approved':
                # Update leave status and send notification for approval
                cur.execute("""
                    UPDATE empleave
                    SET status = %s
                    WHERE start_date = %s AND leave_type = %s AND username = %s
                """, (status, start_date, leave_type, leave_username))

                notification_message = f"Your leave request starting {start_date} has been approved."
                cur.execute(
                    'INSERT INTO notifications (username, notification) VALUES (%s, %s)',
                    (leave_username, notification_message)
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
def generate_empid() -> str:
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT value FROM counters WHERE name = 'latest_empid'")
    result = cursor.fetchone()
    latest_empid = result[0] if result else 0
    new_empid = latest_empid + 1
    # Do not commit the change here; just return the new_empid for now
    return f"BA{new_empid:03d}", new_empid


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

        empid, new_empid_value = generate_empid()

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
            
            # Updating the counter value only if the above queries succeed
            cursor.execute("UPDATE counters SET value = %s WHERE name = 'latest_empid'", (new_empid_value,))
            
            mysql.connection.commit()
        except Exception as e:
            # Rollback the transaction in case of an error
            mysql.connection.rollback()
            print(f"Error occurred: {e}")
            return f"Error occurred: {e}"
        finally:
            # Close the cursor
            cursor.close()

        return redirect(url_for('adduser'))  # Redirect to the adduser page

    return render_template('adduser.html', user_role=user_role,user_designation = user_designation)


#leaverequest 
@app.route('/leaverequest', methods=['GET', 'POST'])
def leavemanagement():
    username = session.get('username')  # Get username from session

    user_designation = session.get('designation')
    cursor = mysql.connection.cursor()  # Open the cursor

    # Fetch leave requests for the logged-in user
    cursor.execute('SELECT * FROM empleave WHERE username = %s', (username,))
    data = cursor.fetchall()

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

                if leave_type == 'casual' and casual_leaves_taken >= 12:
                    return '''
                        <script type="text/javascript">
                            alert("You have already taken the maximum of 12 casual leaves for the selected year.");
                            window.location.href = "/dashboard";
                        </script>
                    '''
                elif leave_type == 'sick' and sick_leaves_taken >= 12:
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
                notification_message = f"{username} is requesting for a leave."
                cursor.execute("SELECT username FROM profile WHERE designation IN (%s, %s)", ('CEO', 'HR'))
                ceo_users = cursor.fetchall()

                for ceo in ceo_users:
                    ceo_username = ceo[0]
                    cursor.execute(
                        'INSERT INTO notifications (username, notification) VALUES (%s, %s)',
                        (ceo_username, notification_message)
                    )

                # Check for red flags (approved leaves only)
                cursor.execute("""
                    SELECT MAX(end_date) AS last_approved_date 
                    FROM empleave 
                    WHERE username = %s 
                    AND leave_type = %s
                    AND status = 'Approved'
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

                if last_approved_date:
                    last_approved_date_str = last_approved_date.strftime('%d/%m/%Y')
                    today_date_str = datetime.today().strftime('%d/%m/%Y')
                    cursor.execute("""
                        INSERT INTO redflags (username, redflag)
                        VALUES (%s, %s)
                    """, (username, f"You've already taken {approved_leave_count} {leave_type} leave(s).Last approved leave on {last_approved_date_str}.Requesting on {today_date_str}."))

                mysql.connection.commit()  # Commit all changes

                # Fetch updated leave requests
                cursor.execute('SELECT * FROM empleave WHERE username = %s', (username,))
                data = cursor.fetchall()

                return redirect(url_for('leavemanagement'))

            except ValueError:
                error_message = "There was an error processing the date. Please check your input."

        return render_template('leaverequest.html', leaves=data, error_message=error_message,user_designation=user_designation)

    cursor.close()  # Close the cursor
    return render_template('leaverequest.html', leaves=data, user_designation=user_designation)






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
        cur.execute("SELECT username FROM profile")
        usernames = [user[0] for user in cur.fetchall()]

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
            cur.execute("SELECT * FROM payslip WHERE username=%s AND pay_period=%s", (selected_username, pay_period_with_day))
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
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''

    cur = mysql.connection.cursor()
    cur.execute("SELECT empid, username, uan, pan, bname, branch, account_number FROM profile")
    data = cur.fetchall()  # Fetches all relevant fields
    cur.close()
    
    #empid = session.get('empid')

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
        payment_mode = request.form.get('payment_mode')  # Capture payment_mode
        working_days = request.form.get('working_days')
        non_working_days = request.form.get('non_working_days')
        unqID = request.form.get('unqID')
        

        pay_period = datetime.strptime(pay_period_input + '-01', '%Y-%m-%d').date()

        ge = float(bp) + float(hra) + float(ma) + float(ca) + float(oa)
        td = float(pt) + float(pf) + float(ld)
        net_payable = ge - td

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO payslip (employee_id, username, pay_period, pay_date, bp, hra, ma, ca, oa, ge, pt, pf,ld, td, net_payable, payment_mode, working_days, non_working_days,unqID) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s)",
            (employee_id, username, pay_period, pay_date, bp, hra, ma, ca, oa, ge, pt, pf,ld, td, net_payable, payment_mode, working_days, non_working_days, unqID)
        )
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('payrollallocation'))

    return render_template('payrollallocation.html', users=data, user=user, user_role=user_role,user_designation = user_designation)





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
    status = data.get('status')

    try:
        cur = mysql.connection.cursor()
        query = """
            UPDATE profile
            SET username=%s, email_address=%s, phone_number=%s, designation=%s, user_status=%s
            WHERE empid=%s
        """
        cur.execute(query, (username, email, phone, designation, status, empid))
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
scheduler.add_job(auto_reject_pending_leaves, 'cron', hour=10, minute=30)
scheduler.add_job(post_redflags_for_missing_work_reports, 'cron', hour=11, minute=18)
scheduler.add_job(add_weekend_holidays,'cron', hour=0, minute=0)
                  


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

@app.route('/workreportlist', methods=['GET', 'POST'])
def workreportlist():
    global allow_updates
    user_designation = session.get('designation')
    try:
        # Fetch the current toggle state from the database
        # cursor = mysql.connection.cursor()
        # cursor.execute("SELECT toogle FROM work LIMIT 1")
        # result = cursor.fetchone()
        # allow_updates = result[0] == "on" if result else False
        # cursor.close()

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
            if user_role == "CEO":
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





# if __name__ == '__main__':
#     app.run(debug=True)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)