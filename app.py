# from flask import Flask, request, jsonify
from flask import Flask, request, jsonify, render_template, session
from google.cloud import datastore # datastore mode
from google.appengine.api import wrap_wsgi_app
from google.appengine.api import memcache # memcache for efficiency
from datetime import datetime

import os
os.environ["GCLOUD_PROJECT"] = "datastore-tutorial-445100"

app = Flask(__name__)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)

# for session to record user_id
app.secret_key = os.urandom(24)

# Instantiates a client
datastore_client = datastore.Client()


@app.route("/")
def home():
    return render_template("home.html")

@app.route('/log_page')
def log_page():
    return render_template("log_page.html")

@app.route('/register')
def register():
    return render_template("register.html")

# log daily habit into the database
@app.route('/log_habit', methods=['POST'])
def log_habit():
    # with front end, comment out for now
    data = request.get_json()  # Parse JSON payload
    # user_id = data.get('user_id')

    # grab user id from the current session
    # since this page will be after log-in or register
    if 'user_id' in session:
        user_id = session['user_id']
    else:
        return jsonify({"success": False, "message": "User ID not properly recorded in session!"}), 404
    
    # get habit id from the request
    habit_id = data.get('habit_id')
    # get date info
    today = datetime.now()
    short_today = f"{today.year}_{today.month}_{today.day}"
    
    print(user_id, habit_id, short_today)
    
    habit_kind = "HabitLog"

    # keys for memcache: memcache currently commented out due to RPC call error
    streak_cache_key = f"streak_{user_id}_{habit_id}"
    month_cache_key = f"calendar_{user_id}_{habit_id}_{today.month}_{today.year}"
    print(streak_cache_key, month_cache_key)

    # update database
    # key = datastore_client.key(kind, name)
    log_key = datastore_client.key(habit_kind, f"{user_id}_{habit_id}_{short_today}")
    log = datastore.Entity(key=log_key)
    log.update({"user_id": user_id, "habit_id": habit_id, "last_log_date": short_today})
    # saves the entity
    datastore_client.put(log)

    # Update Streak in Memcache
    # streak = calculate_streak(user_id, habit_id)
    streak = 1
    memcache.set(key=streak_cache_key, value=streak, time=3600) # save for 1 hr # this is the first place where RPC Call error was raised

    # Update Logged Days in Memcache
    # logged_days = memcache.get(month_cache_key) or set()
    # logged_days.add(today.day)
    # memcache.set(month_cache_key, logged_days, time=3600)

    return jsonify({"message": "Habit logged successfully", "streak": streak})

# new user registration
@app.route('/user_register', methods=['POST'])
def user_register():
    data = request.get_json()  # Parse JSON payload
    user_id = data.get('user_id')
    user_pwd = data.get('user_pwd')
    
    print(user_id, user_pwd)
    
    user_kind = "User"
    
    # check if we have duplicated user_id
    query = datastore_client.query(kind=user_kind)
    query.add_filter(filter=datastore.query.PropertyFilter("user_id", "=", user_id))
    results = list(query.fetch())
    if len(results) > 0:
        return jsonify({"success": False, "message": "User ID not valid. Please pick another one."}), 404
    
    user_key = datastore_client.key(user_kind, user_id)
    user = datastore.Entity(key=user_key)
    user.update({"user_id": user_id, "user_pwd": user_pwd})
    
    # write user data into db
    datastore_client.put(user)

    session['user_id'] = user_id
    return jsonify({"success": True}), 200

# try user login
@app.route('/user_login', methods=['POST'])
def user_login():
    data = request.get_json()  # Parse JSON payload
    user_id = data.get('user_id')
    user_pwd = data.get('user_pwd')
    
    user_kind = "User"

    # check database
    query = datastore_client.query(kind=user_kind)
    query.add_filter(filter=datastore.query.PropertyFilter("user_id", "=", user_id))
    query.add_filter(filter=datastore.query.PropertyFilter("user_pwd", "=", user_pwd))

    # Execute the query
    results = list(query.fetch())

    # Return True if a match is found, otherwise False
    if len(results) > 0:
        session['user_id'] = user_id
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "message": "User ID or Password Incorrect!"}), 404

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8080)