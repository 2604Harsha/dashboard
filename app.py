from flask import Flask, render_template, request, redirect, url_for, session, flash, json, jsonify, send_file
from flask_mysqldb import MySQL
from datetime import datetime
from docx import Document
import io
import time # To simulate time

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Saty@136'
app.config['MYSQL_DB'] = 'emp'


mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('sign-up.html')

@app.route('/header')
def header():
    return render_template('header.html')

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
    
    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM profile")
        data = cur.fetchall()
        cur.close()
        return render_template('dashboard.html', users=data, user_role=user_role)
    else:
        return redirect(url_for('index'))



# login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM profile WHERE username = %s AND password = %s", (username, password))
    user = cur.fetchone()
    cur.close()

    if user:
        session['username'] = username
        session['empid'] = user[1]  # Set empid in session
        session['user_role'] = user[20]
        return redirect(url_for('dashboard'))
    else:
        flash('Incorrect username or password', 'error')
        return redirect(url_for('index'))


# logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

#todo
@app.route('/todo', methods=['GET', 'POST'])
def manage_todo():
    username = session.get('username')
    user_role = session.get('user_role')
    
    cur = mysql.connection.cursor()
    
    if request.method == 'GET':
        # Fetch todos for the logged-in user
        if username:
            cur.execute("SELECT * FROM todo WHERE username = %s", (username,))
            todos = cur.fetchall()
            return render_template('To-do.html', todos=todos, user_role=user_role)

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

#leavemanager
@app.route('/leavemanager', methods=['GET', 'POST'])
def leavemanager():
    username = session.get('username')
    user_role = session.get('user_role')

    # Check if the user is logged in and has proper permissions
    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        # Handle leave status update (approval/rejection)
        data = request.get_json()
        username = data['username']
        leave_type = data['leave_type']
        start_date = data['start_date']
        status = data['status']
        rejectReason = data.get('rejectReason')  # Use get() to avoid KeyError in case of approval

        # Check if the status is 'Rejected', and update the rejection reason if provided
        if status == 'Rejected' and rejectReason:
            cur.execute("""
                UPDATE empleave
                SET status = %s, rejectReason = %s
                WHERE start_date = %s AND leave_type = %s AND username = %s 
            """, (status, rejectReason, start_date, leave_type, username))
        else:
            cur.execute("""
                UPDATE empleave
                SET status = %s
                WHERE start_date = %s AND leave_type = %s AND username = %s
            """, (status, start_date, leave_type, username))

        mysql.connection.commit()
        cur.close()

        return jsonify({'message': f'Status updated to {status} successfully'}), 200

    # Fetch and display the leave requests (for GET method)
    cur.execute("SELECT * FROM empleave")
    data = cur.fetchall()
    cur.close()
    
    # Sort the data with "Pending" on top, then "Rejected", then "Approved"
    sorted_data = sorted(data, key=lambda x: ("Pending", "Rejected", "Approved").index(x[6]))

    return render_template('leavemanager.html', employees=data, user_role=user_role, leaves=sorted_data)


# profile update
def generate_empid() -> str:
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT value FROM counters WHERE name = 'latest_empid'")
    result = cursor.fetchone()
    latest_empid = result[0] if result else 0
    new_empid = latest_empid + 1
    cursor.execute("UPDATE counters SET value = %s WHERE name = 'latest_empid'", (new_empid,))
    mysql.connection.commit()
    return f"BA{new_empid:03d}"

#adduser
@app.route('/adduser', methods=['GET', 'POST'])
def adduser():
    username = session.get('username')
    user_role = session.get('user_role')

    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
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
        
        
       
        empid = generate_empid()
        
        cursor = mysql.connection.cursor()
        try:
            #Inseting data into Profile table
            cursor.execute('INSERT INTO profile (empid, username, password, email_address, first_name, last_name, phone_number, date_of_birth, designation, joining_date, address, city, country, postal_code,uan,pan,bname,branch,account_number, user_role, pf_num) VALUES (%s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                       (empid, username, password, email_address, first_name, last_name, phone_number, date_of_birth, designation, joining_date, address, city, country, postal_code,uan,pan,bname,branch,account_number, user_role, pf_num))
            
            #Inserting data into users table
            cursor.execute('''
                INSERT INTO users (id, username, password, designation, employed_on) 
                VALUES (%s, %s, %s, %s, %s)
            ''', 
            (empid, username, password, designation, joining_date))
        
            mysql.connection.commit()
        except Exception as e:
            # Rollback the transaction in case of an error
            mysql.connection.rollback()
            print(f"Error occurred: {e}")
            return f"Error occurred: {e}"
        finally:
            # Close the cursor
            cursor.close()
        return redirect(url_for('profile')) # change index to profile 
    
    return render_template('adduser.html', user_role=user_role)

#leaverequest 
#employeeleavemanaement--for emp
@app.route('/leaverequest', methods=['GET', 'POST'])
def leavemanagement():
    username = session.get('username')  # Get username from session
   

    # Open the cursor at the start of the function
    cursor = mysql.connection.cursor()

    # Fetch leave requests for the logged-in user based on username
    cursor.execute('SELECT * FROM empleave WHERE username = %s', (username,))
    data = cursor.fetchall()

    if request.method == 'POST':
        leave_type = request.form['leave_type']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        reason = request.form['reason']
        
        # Initialize an empty error message
        error_message = None

        # Server-side validation
        if not leave_type or not start_date or not end_date or not reason:
            error_message = "All fields are required. Please fill in all the details."
        elif start_date > end_date:  # Check if start date is before end date
            error_message = "Start date must be before end date."

        if error_message is None:
            try:
                # Convert date formats from DD/MM/YYYY to YYYY-MM-DD
                start_date = datetime.strptime(start_date, '%d/%m/%Y').strftime('%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%d/%m/%Y').strftime('%Y-%m-%d')
                
                # Insert into the database
                cursor.execute('INSERT INTO empleave (username, leave_type, start_date, end_date, reason, status) VALUES (%s, %s, %s, %s, %s, %s)', 
                               (username, leave_type, start_date, end_date, reason, 'Pending'))
                mysql.connection.commit()

                # After successful insertion, fetch the updated leave requests
                cursor.execute('SELECT * FROM empleave WHERE username = %s', (username,))
                data = cursor.fetchall()

                #return render_template('leaverequest.html', leaves=data)  # Redirect to updated data view
                return redirect(url_for('leavemanagement'))
            except ValueError:
                error_message = "There was an error processing the date. Please check your input."

        # If validation fails, return the error message to the template
        return render_template('leaverequest.html', leaves=data, error_message=error_message)

    # Close the cursor after all operations
    cursor.close()
    
    return render_template('leaverequest.html', leaves=data)

# profile display
@app.route('/profile')
def profile():
    username = session.get('username')
    user_role = session.get('user_role')
    
     # Ensure username is a string
    if 'username':
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM profile WHERE username=%s"  # Use prepared statement
        cur.execute(sql, (session['username'],))
        profile = cur.fetchone()
        cur.close()
        print(profile)
    return render_template('profile.html', profile=profile, user_role=user_role)


#work
@app.route('/work', methods=['GET', 'POST'])
def work():
    empid = session.get('empid')  # Get empid from session
    username = session.get('username')
    user_role = session.get('user_role')
    
    
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
                               pause_reason=pause_reason,check_reason=check_reason, username=username, user_role=user_role)
    else:
        return redirect(url_for('index'))

#allocate-work
@app.route('/allocatework', methods=['GET', 'POST'])
def allocatework():
    empid = session.get('empid')  # Get empid from session
    username = session.get('username')
    user_role = session.get('user_role')

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

    return render_template('allocatework.html', profile=profile, usernames=[u[0] for u in usernames], user_role=user_role)  # Pass profile and usernames to the template

#createproject
@app.route('/createproject', methods=['GET', 'POST']) 
def createproject():
    username = session.get('username')
    user_role = session.get('user_role')

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
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO project VALUES (NULL, %s, %s, %s, %s)', (project_title, description, start_date, end_date))
        mysql.connection.commit()
        return render_template('create-project.html',user_role=user_role)
    return render_template('create-project.html',user_role=user_role)

# project-list
@app.route('/projectlist')
def projectlist():
    username = session.get('username')
    user_role = session.get('user_role')

    # if not username or user_role in ['Employee', 'Trainee']:
    #     return '''
    #         <script type="text/javascript">
    #             alert("Access denied. You do not have permission to view this page.");
    #             window.location.href = "/dashboard";  // Redirect to the desired page after alert
    #         </script>
    #     '''    
    if 'username':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM project")
        data = cur.fetchall()
        cur.close()
        print(data)
        return render_template('projectlist.html', project=data,user_role=user_role)
    else:
        return redirect(url_for('index'))
    
#update project
@app.route('/update_project/<int:project_id>', methods=['POST'])
def update_project(project_id):
    updated_data = request.json
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE project
            SET project_title = %s, description = %s, start_date = %s, end_date = %s
            WHERE id = %s
        """, (updated_data['project_title'], updated_data['description'], updated_data['start_date'], updated_data['end_date'], project_id))
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

    if not username or user_role in ['Employee', 'Trainee']:
        return '''
            <script type="text/javascript">
                alert("Access denied. You do not have permission to view this page.");
                window.location.href = "/dashboard";  // Redirect to the desired page after alert
            </script>
        '''
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM project")
    project_title1 = cursor.fetchall()
    cursor.execute("SELECT * FROM users")
    username1 = cursor.fetchall()

    if request.method == 'POST':
       project_title = request.form['project_title']
       username = request.form['username']
       work_date = request.form['start_date']
       work_description = request.form['work_description']
       cursor.execute('INSERT INTO workallocation (project_title, username,work_date, work_description) VALUES (%s,%s %s, %s)', 
                      (project_title, username,work_date, work_description))
       mysql.connection.commit()
       return redirect(url_for('projectallocation'))

    return render_template('projectallocation.html', project=project_title1, users=username1, user_role=user_role)


#projectallocated
@app.route('/projectallocated')
def projectallocated():
    username = session.get('username')
    
    
    if not username:
        return redirect(url_for('index'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM workallocation WHERE username = %s", (username,))
    data = cursor.fetchall()
    cursor.close()

    return render_template('projectallocated.html', work=data)



#payroll
@app.route('/payroll', methods=['GET'])
def payroll():
    username = session.get('username')
    empid = session.get('empid')
    user_role = session.get('user_role')

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

    return render_template('payroll.html', user=user, payslip=payslip, usernames=usernames, user_role=user_role)


# payrollmanager
@app.route('/payrollallocation', methods=['GET', 'POST'])
def payrollallocation():
    username = session.get('username')
    empid = session.get('empid')
    user_role = session.get('user_role')

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
    
    empid = session.get('empid')

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

    return render_template('payrollallocation.html', users=data, user=user, user_role=user_role)





# emplist
@app.route('/emplist')
def emplist():
    username = session.get('username')
    user_role = session.get('user_role')

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
        print(data)
        return render_template('emplist.html', user_role=user_role, users=data)
    else:
        return redirect(url_for('index'))




    

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

#workreport     
@app.route('/workreport', methods=['GET', 'POST'])
def workreport():
    empid = session.get('empid')  # Get empid from session
    username = session.get('username')
    user_role = session.get('user_role')

    # if not username or user_role in ['Employee', 'Trainee']:
    #     return '''
    #         <script type="text/javascript">
    #             alert("Access denied. You do not have permission to view this page.");
    #             window.location.href = "/dashboard";  // Redirect to the desired page after alert
    #         </script>
    #     '''
   
    # Fetch profile data based on empid
    profile = None
    if empid:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM profile WHERE empid = %s", (empid,))
        profile = cursor.fetchone()  # Fetch the first row
        cursor.close()

    if request.method == 'POST':
        date = request.form['date']
        time = request.form['Timings']
        work_done = request.form['workdone']
        
        # Use empid fetched from profile
        if profile:
            empid = profile[1]  # Assuming empid is in the second column

            cursor = mysql.connection.cursor()
            cursor.execute(
                'INSERT INTO workreport (empid, date, time, work_done) VALUES (%s, %s, %s, %s)', (empid, date, time, work_done))
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('workreportlist'))  # Redirect to work report list

    return render_template('workreport.html', profile=profile, user_role=user_role)  # Pass profile to the template



#workreport list
@app.route('/workreportlist', methods=['GET', 'POST'])
def workreportlist():
    username = session.get('username')
    user_role = session.get('user_role')

    # if not username or user_role in ['Employee', 'Trainee']:
    #     return '''
    #         <script type="text/javascript">
    #             alert("Access denied. You do not have permission to view this page.");
    #             window.location.href = "/dashboard";  // Redirect to the desired page after alert
    #         </script>
    #     '''
    if 'username' in session:  # Check if user is logged in
        empid = session['empid']  # Get empid from session
        
        cursor = mysql.connection.cursor()
        
        # Fetch distinct usernames for the filter
        cursor.execute("SELECT DISTINCT username FROM profile")  # Adjust the query as needed
        usernames = [row[0] for row in cursor.fetchall()]  # Extract usernames into a list
        
        # Fetch user role based on the logged-in empid
        cursor.execute("SELECT user_role FROM profile WHERE empid = %s", (empid,))
        user_role = cursor.fetchone()[0]  # Assuming 'user_role' is the first column in the fetched result

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
        if not data:
            no_data = True  # Flag to indicate no data
        else:
            no_data = False

        # Render the workreportlist template with the filtered data
        return render_template('workreportlist.html', project=data, usernames=usernames, 
                               disable_filter=disable_filter, selected_username=selected_username,
                               selected_date=selected_date, no_data=no_data, user_role=user_role)
    else:
        return redirect(url_for('index'))
    
    
    
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

    return render_template("emp_agreement.html", user_role=user_role)





# if __name__ == '__main__':
#     app.run(debug=True)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)