from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
from datetime import datetime

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///data.db")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # recover info for current user
    get_info = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
    # if no username for current session id, redirect to register
    if len(get_info) == 0:
        return redirect(url_for("register"))
    else:
        # save all their credentials to display on profile
        credentials = []
        credentials.append(get_info[0]["email"])
        credentials.append(get_info[0]["pref_name"])
        for i in range(0,5):
            key = "dept_" + str(i)
            if get_info[0][key] != None and get_info[0][key] != "":
                credentials.append(get_info[0][key])
        
        #record if a student or faculty member is logged in
        is_student = get_info[0]["is_student"]
    
        if request.method=="GET":
            
            # if student is logged in
            if is_student:
                
                # retrieve events with which student is involved
                requests = db.execute("SELECT * FROM requests WHERE  confirmed = :confirmed AND (primary_contact_email = :primary_contact_email OR person_1 = :primary_contact_email OR person_2 = :primary_contact_email OR person_3 = :primary_contact_email)",
                            primary_contact_email = get_info[0]["email"], confirmed = 1)
                            
                # get preferred name of faculty member for use in message
                for row in requests:
                    pref_name = db.execute("SELECT pref_name FROM users WHERE email = :faculty_email",
                    faculty_email=row["faculty_email"])
                    
                    # add name to each dict in list as a key-value pair
                    row['pref_name'] = pref_name[0]["pref_name"]
                
                # find faculty whose department matches my interests
                # conditional upon the number of departments I have input
                if len(credentials) - 2 == 5:
                    primary_matches = db.execute("SELECT id FROM users WHERE is_student = :is_student AND dept_0 = :dept_0 OR dept_0 = :dept_1 OR dept_0 = :dept_2 OR dept_0 = :dept_3 OR dept_0 = :dept_4",
                        is_student = 0, dept_0 = credentials[2], dept_1 = credentials[3], dept_2 = credentials[4],
                        dept_3 = credentials[5], dept_4 = credentials[6])
                elif len(credentials) - 2 == 4:
                    primary_matches = db.execute("SELECT id FROM users WHERE is_student = :is_student AND dept_0 = :dept_0 OR dept_0 = :dept_1 OR dept_0 = :dept_2 OR dept_0 = :dept_3",
                        is_student = 0, dept_0 = credentials[2], dept_1 = credentials[3], dept_2 = credentials[4],
                        dept_3 = credentials[5])
                elif len(credentials) - 2 == 3:
                    primary_matches = db.execute("SELECT id FROM users WHERE is_student = :is_student AND dept_0 = :dept_0 OR dept_0 = :dept_1 OR dept_0 = :dept_2",
                        is_student = 0, dept_0 = credentials[2], dept_1 = credentials[3], dept_2 = credentials[4])
                elif len(credentials) - 2 == 2:
                    primary_matches = db.execute("SELECT id FROM users WHERE is_student = :is_student AND dept_0 = :dept_0 OR dept_0 = :dept_1",
                        is_student = 0, dept_0 = credentials[2], dept_1 = credentials[3])
                elif len(credentials) - 2 == 1:
                    primary_matches = db.execute("SELECT id FROM users WHERE is_student = :is_student AND dept_0 = :dept_0",
                        is_student = 0, dept_0 = credentials[2])
                
                # generate a list of ids of professors who match my interests AND have times posted 
                id_list = []
                for match in primary_matches:
                    check_times = db.execute("SELECT * FROM times WHERE faculty_id = :match", match = match["id"])
                    if len(check_times) != 0:
                        id_list.append(match["id"])
                
                # retrieve data for professors who match my interests AND have times posted 
                recommendations = []
                for id in id_list:
                    recommendations.append(db.execute("SELECT * FROM users WHERE id = :my_id", my_id = id))
                
                return render_template("student_home.html", credentials=credentials, is_student = is_student, requests = requests, recommendations = recommendations)
    
            else:
                # get confirmed requests for upcoming events
                requests = db.execute("SELECT * FROM requests WHERE faculty_email = :faculty_email AND confirmed = :confirmed",
                            faculty_email = get_info[0]["email"], confirmed = 1)
                # get preferred name of primary contact for use in message
                for row in requests:
                    pref_name = db.execute("SELECT pref_name FROM users WHERE email = :primary_contact_email",
                        primary_contact_email=row["primary_contact_email"])
                    # add key-value pair to each dict
                    row['pref_name'] = pref_name[0]["pref_name"]
                
                return render_template("faculty_home.html", credentials=credentials, is_student = is_student, requests = requests)
        
        # if method is POST
        else:
            # if current user is a student
            if get_info[0]["is_student"]:
                # get faculty id associated with the button user clicked
                faculty = request.form.get("click")
                
                # retrieve faculty information, format for display
                prof_info = db.execute("SELECT * FROM users WHERE id = :id", id = faculty)
                credentials1 = []
                credentials1.append(prof_info[0]["email"])
                credentials1.append(prof_info[0]["pref_name"])
                for i in range(0,5):
                    key = "dept_" + str(i)
                    if prof_info[0][key] != None and prof_info[0][key] != "":
                        credentials1.append(prof_info[0][key])
                
                # get times corresponding to this faculty member
                times = db.execute("SELECT * FROM times WHERE faculty_id = :faculty_id", faculty_id = faculty)
                length = len(times)
                faculty_info = db.execute("SELECT * FROM users WHERE id = :faculty", faculty = faculty)
                if len(faculty_info) == 0:
                    error = "No faculty with that name."
                    return render_template("search.html", error = error, is_student = is_student)
                return render_template("profprofile.html", credentials1 = credentials1, times = times, length=length, is_student = is_student)

            # if current user is faculty
            else:
                # faculty has pressed undo button
                undo_this = request.form.get("undo")
                # unconfirm the selected request
                db.execute("UPDATE requests SET confirmed = :confirmed WHERE id = :id", confirmed = 0, id = undo_this)
                return redirect(url_for("index"))
                    

@app.route("/MyRequests", methods=["GET","POST"])
@login_required
def MyRequests():
    
    # recover info for current user
    get_info = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
    
    if request.method == "GET":
        # ensure user exists in database
        if len(get_info) == 0:
            return redirect(url_for("register"))
            
        # ensure that user is faculty
        if get_info[0]["is_student"] == 1:
            return redirect(url_for("index"))
        
        #Get all of user's unconfirmed requests
        requests = db.execute("SELECT * FROM requests WHERE faculty_email = :faculty_email AND confirmed = :confirmed",
                    faculty_email = get_info[0]["email"], confirmed = 0)
        for row in requests:
            pref_name = db.execute("SELECT pref_name FROM users WHERE email = :primary_contact_email",
                        primary_contact_email=row["primary_contact_email"])
            row['pref_name'] = pref_name[0]["pref_name"]
        
        #pass request info to myrequests html 
        return render_template("myrequests.html", requests=requests)
        
    else:
        #if user is undoing a confirmation then update requests accordingly
        accept_this = request.form.get("accept")
        db.execute("UPDATE requests SET confirmed = :confirmed WHERE id = :id", confirmed = 1, id = accept_this)
        return redirect(url_for("MyRequests"))
    
        

@app.route("/info", methods=["GET"])
@login_required
def info():
    """Program information."""
    # recover info for current user
    get_info = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
    is_student = get_info[0]["is_student"]
    
    return render_template("info.html", is_student = is_student)
    
@app.route("/restaurants", methods=["GET"])
@login_required
def restaurants():
    """Program information."""
    # recover info for current user
    get_info = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
    
    #keep track of whether student or faculty is logged in
    is_student = get_info[0]["is_student"]
    
    return render_template("restaurants.html", is_student = is_student)

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    
    #get info from users table
    get_info = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
    is_student = get_info[0]["is_student"]
    
    #if route was reached via GET return html template
    if request.method == "GET":
        return render_template("search.html", is_student = is_student)
    
    else:
        #record input value of search and retrieve faculty info
        faculty = request.form.get("search")
        
        faculty_id = db.execute("SELECT id FROM users WHERE email = :email OR pref_name = :email AND is_student = :is_student",
        email = faculty, is_student = 0)
        
        #check to make sure search input is legitimate
        if len(faculty_id) == 0:
            error = "No faculty with this name or email address."
            return render_template("search.html", is_student = is_student, error = error)
        else:
            use_id = faculty_id[0]['id']
            
            #get all info for given professor
            prof_info = db.execute("SELECT * FROM users WHERE id = :id", id = use_id)
            credentials1 = []
            credentials1.append(prof_info[0]["email"])
            credentials1.append(prof_info[0]["pref_name"])
            for i in range(0,5):
                key = "dept_" + str(i)
                if prof_info[0][key] != None and prof_info[0][key] != "":
                    credentials1.append(prof_info[0][key])
            
            is_student = get_info[0]["is_student"]
            
            #get faculty's available times 
            times = db.execute("SELECT * FROM times WHERE faculty_id = :faculty_id", faculty_id = use_id)
            length = len(times)
            
            return render_template("profprofile.html", credentials1 = credentials1, times = times, length=length, is_student = is_student)


@app.route("/request1", methods=["GET", "POST"])
@login_required
def request1():
    # retrieve user info
    get_info = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
    # used in template to check if user is student
    is_student = get_info[0]["is_student"]
    
    if request.method == "GET":
        return render_template("request1.html", is_student = is_student)
    
    # if method is POST    
    else:
        #retrieve all information from request form
        primary_contact_email = get_info[0]["email"]
        faculty_email = request.form.get("inputFac")
        date = request.form.get("inputDate")
        time = request.form.get("inputTime")
        people = request.form.getlist("other_students")
        length = len(people)
        for i in range(0,4-length):
            people.append("")
        restaurant = request.form.get("restaurant")
        
        #insert info from request form to the requests table, with request yet unconfirmed
        db.execute("INSERT INTO requests (primary_contact_email, faculty_email, date, time, person_1, person_2, person_3, person_4, restaurant, confirmed) VALUES(:primary_contact_email, :faculty_email, :date, :time, :person_1, :person_2, :person_3, :person_4, :restaurant, :confirmed)",
                primary_contact_email = primary_contact_email, faculty_email = faculty_email, date = date, time = time, person_1 = people[0], person_2 = people[1], person_3 = people[2], person_4 = people[3], restaurant = restaurant, confirmed = 0)
        return redirect(url_for("request1"))
    
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("email"):
            error = "You must provide an email address."
            return render_template("login.html", error=error)

        # ensure password was submitted
        elif not request.form.get("password"):
            error = "You must provide a password."
            return render_template("login.html", error=error)

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE email = :email", email=request.form.get("email"))

        # ensure username exists and password is correct
        if len(rows) != 1:
            error = "Invalid email address."
            return render_template("login.html", error=error)
        if not pwd_context.verify(request.form.get("password"), rows[0]["password"]):
            error = "Incorrect password."
            return render_template("login.html", error=error)

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))
    
@app.route("/addtime", methods=["GET", "POST"])
def addtime():
    if request.method == "GET":
        times = db.execute("SELECT * FROM times WHERE faculty_id = :faculty_id", faculty_id = session["user_id"])
        return render_template("addtime.html", times = times)
        
    else:
        # get list of selected times to delete
        delete_this = request.form.getlist("delete_this")
        
        # add available time to times table
        day = request.form.get("inputDate")
        time = request.form.get("inputTime")
        button_pressed = request.form.get("button_pressed")
        
        times = db.execute("SELECT * FROM times WHERE faculty_id = :faculty_id", faculty_id = session["user_id"])
        # make sure date/time entered
        if (day == "" or time == "") and button_pressed == "add":
            error = "Please enter date and time."
            return render_template("addtime.html", times=times, error = error)
        
        # if deleting times, make sure a time was selected
        if len(delete_this) == 0 and button_pressed=="delete":
            error = "Please select times to delete."
            return render_template("addtime.html", times=times, error = error)
        
        else:
            # if intention is to add times, add to table
            if button_pressed == "add":
                db.execute("INSERT INTO times (faculty_id, day, time) VALUES (:faculty_id, :day, :time)",
                            faculty_id = session["user_id"], day = day, time = time)
                            
            # if intention is to delete selected times, delete according to unique id
            if button_pressed == "delete":
                for delete in delete_this:
                    db.execute("DELETE FROM times WHERE time_id = :time_id", time_id = delete)
        
            return redirect(url_for("addtime"))

@app.route("/update", methods=["GET", "POST"])
def update():
    
    if request.method == "GET":
        return render_template("update.html")
    
    else:
        # recover current information for current user
        get_info = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
        
        # if no info for current session id, redirect to register
        if len(get_info) == 0:
            return redirect(url_for("register"))
        else:
            # save current information as variables
            email = get_info[0]["email"]
            pref_name = get_info[0]["pref_name"]
            departments = []
            for i in range(0,5):
                key = "dept_" + str(i)
                if key in get_info[0]:
                    departments.append(get_info[0][key])
            
            # if departments were updated
            if request.form.get("update_depts")=="update":
                # get new list of selected departments
                new_departments = request.form.getlist("departments")
            else:
                new_departments = None
        
            # ensure that email was entered
            if (request.form.get("email") == ""):
                error = "You must include an email address."
                return render_template("update.html",error=error)
            
            # ensure email has standard @ ending
            at_check = 0
            for character in request.form.get("email"):
                if character == '@':
                    at_check += 1
            if at_check != 1:
                error = "Please provide a valid email address."
                return render_template("update.html",error=error)
            
            # ensure preferred name entered
            elif request.form.get("first_name") == None or request.form.get("last_name") == None:
                error = "Please enter your first and last name."
                return render_template("update.html",error=error)
            
            # if radio selected but no departments, give error
            elif request.form.get("update_depts")=="update" and new_departments == None:
                error = "You must select at least one department."
                return render_template("update.html",error=error)
            
            # if all entered correctly, check whether email taken by someone else
            else:
                get_users = db.execute("SELECT * FROM users WHERE email = :email AND id <> :id", email = request.form.get("email"),
                id = session["user_id"])
                if len(get_users) != 0:
                    error = "Email address already taken."
                    return render_template("update.html", error=error)
                
                else:
                    # get new information from HTML
                    new_email = request.form.get("email")
                    new_pref_name = request.form.get("first_name") + " " + request.form.get("last_name")

                    
                    # save any new information to users database
                    if new_email != email:
                        db.execute("UPDATE users SET email = :new WHERE id = :id", new = new_email, id=session["user_id"])
                    # save new name
                    if new_pref_name != pref_name:
                        db.execute("UPDATE users SET pref_name = :new WHERE id = :id", new = new_pref_name, id=session["user_id"])
                    # if new departments selected
                    if new_departments != None:
                        # record number of new departments selected
                        num_depts = len(new_departments)
                        
                        # store new primary department (required)
                        if new_departments[0] != departments[0]:
                            db.execute("UPDATE users SET dept_0 = :new WHERE id = :id", new = new_departments[0], id=session["user_id"])
                        
                        # if additional departments were entered, update those and clear the rest
                        if num_depts==2:
                            db.execute("UPDATE users SET dept_1 = :dept_1, dept_2 = :dept_2, dept_3 = :dept_3, dept_4 = :dept_4 WHERE id = :id", 
                            dept_1 = new_departments[1], dept_2 = "", dept_3 = "", dept_4 = "", id = session["user_id"])
                        elif num_depts==3:
                            db.execute("UPDATE users SET dept_1 = :dept_1, dept_2 = :dept_2, dept_3 = :dept_3, dept_4 = :dept_4 WHERE id = :id", 
                            dept_1 = new_departments[1], dept_2 = new_departments[2], dept_3 = "", dept_4 = "", id = session["user_id"])
                        elif num_depts==4:
                            db.execute("UPDATE users SET dept_1 = :dept_1, dept_2 = :dept_2, dept_3 = :dept_3, dept_4 = :dept_4 WHERE id = :id", 
                            dept_1 = new_departments[1], dept_2 = new_departments[2], dept_3 = new_departments[3], dept_4 = "", id = session["user_id"])
                        elif num_depts==5:
                            db.execute("UPDATE users SET dept_1 = :dept_1, dept_2 = :dept_2, dept_3 = :dept_3, dept_4 = :dept_4 WHERE id = :id", 
                            dept_1 = new_departments[1], dept_2 = new_departments[2], dept_3 = new_departments[3], dept_4 = new_departments[4],
                            id = session["user_id"])
                    
                    return redirect(url_for("index"))

@app.route("/register", methods=["GET", "POST"])
def register():
    
    # upon GET, render the registration page
    if request.method == "GET":
        
        # end any ongoing session
        session.clear()
        
        return render_template("register.html")
        
    else:
        # get list of departments selected
        departments = request.form.getlist('departments')
        
        # ensure that username entered
        if request.form.get("email") == "":
            error = "You must include an email address."
            return render_template("register.html",error=error)
        
        # ensure email has standard @ ending
        at_check = 0
        for i in request.form.get("email"):
            if i == '@':
                at_check += 1
        if at_check == 0:
            error = "Please provide a valid email address."
            return render_template("register.html",error=error)
        
        # ensure password entered and confirmed
        elif (request.form.get("password") == ""):
            error = "You must include a password."
            return render_template("register.html",error=error)
        
        elif (request.form.get("re_password") == ""):
            error = "You must confirm your chosen password."
            return render_template("register.html",error=error)
     
        # ensure password matches re-entered password
        elif request.form.get("password") != request.form.get("re_password"):
            error = "Passwords did not match"
            return render_template("register.html",error=error)
        
        # ensure first and last name entered
        elif request.form.get("first_name") == "" or request.form.get("last_name") == "":
            error = "Please enter your first and last name."
            return render_template("register.html",error=error)
        
        # ensure user selects either student or faculty
        elif request.form.get("type_user")==None:
            error = "Let us know what type of user you are!"
            return render_template("register.html",error=error)
        
        # ensure departments are selected
        elif len(departments)==0:
            error = "You must select at least one department."
            return render_template("register.html",error=error)
        
        # if all entered correctly, check whether username taken
        else:
            get_users = db.execute("SELECT * FROM users WHERE email = :email", email = request.form.get("email"))
            if len(get_users) != 0:
                error = "Email address already taken."
                return render_template("register.html", error=error)
            
            else:
                #store new information
                email = request.form.get("email")
                hash = pwd_context.encrypt(request.form.get("password"))
                pref_name = request.form.get("first_name") + " " + request.form.get("last_name")
                type_user = request.form.get("type_user")
                pwd_context.encrypt(request.form.get("password"))
                num_depts = len(departments)
                
                # check whether student or faculty
                if request.form.get("type_user") == "Student":
                    is_student = 1
                elif request.form.get("type_user") == "Faculty":
                    is_student = 0
                
                # save information to users database
                db.execute("INSERT INTO users (email, password, pref_name, is_student, dept_0) VALUES(:email, :hash, :pref_name, :is_student, :dept_0)",
                email = email, hash = hash, pref_name = pref_name, is_student = is_student, dept_0 = departments[0])
                
                # if additional departments were entered, include those
                if num_depts==2:
                        db.execute("UPDATE users SET dept_1 = :dept_1 WHERE email = :email", dept_1 = departments[1], email = email)
                elif num_depts==3:
                    db.execute("UPDATE users SET dept_1 = :dept_1, dept_2 = :dept_2 WHERE email = :email", 
                    dept_1 = departments[1], dept_2 = departments[2], email = email)
                elif num_depts==4:
                    db.execute("UPDATE users SET dept_1 = :dept_1, dept_2 = :dept_2, dept_3 = :dept_3 WHERE email = :email", 
                    dept_1 = departments[1], dept_2 = departments[2], dept_3 = departments[3], email = email)
                elif num_depts==5:
                    db.execute("UPDATE users SET dept_1 = :dept_1, dept_2 = :dept_2, dept_3 = :dept_3, dept_4 = :dept_4 WHERE email = :email", 
                    dept_1 = departments[1], dept_2 = departments[2], dept_3 = departments[3], dept_4 = departments[4], email = email)
                
                # remember who registered
                get_id = db.execute("SELECT id FROM users WHERE email = :email", email = email)
                session["user_id"] = get_id[0]["id"]
            
                # redirect user to home page
                return redirect(url_for("index"))