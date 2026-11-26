import sqlite3
from datetime import datetime
def get_connection():
    conn = sqlite3.connect("recycling.db", timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_database():
    """ Using Python + SQL to create a test database for the app """
    conn = get_connection()
    cursor = conn.cursor()
    #executescript is for multiple queries per a time
    #Declare other attributes before foreign key
    cursor.executescript(
        """ CREATE TABLE IF NOT EXISTS Person (
            person_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            total_point INTEGER
        );
        
            CREATE TABLE IF NOT EXISTS waste_type (
            waste_id INTEGER PRIMARY KEY AUTOINCREMENT,
            waste_name TEXT NOT NULL UNIQUE,
            waste_point INTEGER
        );
            CREATE TABLE IF NOT EXISTS sorting_event (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            time_start TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            time_end TEXT DEFAULT NULL,
            FOREIGN KEY (person_id) REFERENCES Person(person_id)
            );
            CREATE TABLE IF NOT EXISTS event_item (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            waste_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES sorting_event(event_id),
            FOREIGN KEY (waste_id) REFERENCES waste_type(waste_id)
            )
        """
    )
    conn.commit()
    conn.close()

def data_retrieval(name):
    """
    Check if an user's records existed beforehand, and if so, retrieve that
    data and add points to item
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Person")
    records = cursor.fetchall()
    name_record = []
    for record in records:
        actual_name = record[0]
        name_record.append(actual_name)
    if name not in name_record:
        cursor.execute("INSERT INTO Person (name, total_point) VALUES(?, ?)", (name, 0))
        conn.commit()
        cursor.execute("SELECT person_id, total_point FROM Person WHERE name = ?", (name,))
        person = cursor.fetchone()
        per_id, points = person
    else:
        cursor.execute("SELECT person_id, total_point FROM Person WHERE name = ?", (name,))
        person = cursor.fetchone()
        per_id, points = person
    conn.close()
    return {
        "person_id": per_id,
        "name": name,
        "total_point": points
    }

def update_database(person_id, point, trash_name):
    """
    Update person's points in the database based on their id and
    the input from he computer vision model
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT waste_point FROM waste_type WHERE waste_name = ?", (trash_name,))
    adding = (cursor.fetchone())[0]
    point += adding
    cursor.execute("UPDATE Person SET total_point = ? WHERE person_id = ?", (point, person_id))
    conn.commit()
    conn.close()
def ranking_database():
    """
    Ranking the participant based on descending points, return as a list
    for streamlit to draw
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT
        Person.name,
        COUNT(DISTINCT sorting_event.event_id) AS total_sessions,
        COALESCE(SUM(event_item.quantity), 0) AS total_items,
        Person.total_point
    FROM Person
    LEFT JOIN sorting_event
        ON Person.person_id = sorting_event.person_id
    LEFT JOIN event_item
        ON sorting_event.event_id = event_item.event_id
    GROUP BY
        Person.person_id,
        Person.name,
        Person.total_point
    ORDER BY Person.total_point DESC;""")
    ranking_list = cursor.fetchall()
    conn.close()
    return ranking_list

def init_waste_type():
    conn = get_connection()
    cursor = conn.cursor()
    default_waste = [
        ("plastic", 20), #0
        ("paper", 15),  #1
        ("metal", 10), #2
        ("other", 5) #3
    ]
    for item in default_waste:
        #Prevent duplicate between copies
        cursor.execute("INSERT OR IGNORE INTO waste_type (waste_name, waste_point) VALUES(?, ?)", item)
    conn.commit()
    conn.close()
def start_session(name):
    """
    The session will start when the user enter their name and press the
    button start on the dashboard
    """
    conn = get_connection()
    cursor = conn.cursor()
    user_record = data_retrieval(name)
    user_id = user_record["person_id"]
    time = datetime.now()
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO sorting_event (person_id, time_start) VALUES(?, ?)", (user_id, current_time))
    conn.commit()
    #Return the id of the latest event
    event_id = cursor.lastrowid
    conn.close()
    return event_id

def saving_recycling_logs(event_id, trash_name):
    """
    Saving a person recycling logs and used event_id to trace
    the person_id when they want to see their records.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT waste_id FROM waste_type WHERE waste_name = ?", (trash_name,))
    cocurrent = cursor.fetchone()
    if cocurrent is not None: 
        trash_id = cocurrent[0]
        now = datetime.now()
        current = now.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO event_item (event_id, waste_id, quantity, time) VALUES (?, ?, ?, ?)", (event_id, trash_id, 1, current))
        conn.commit()
    conn.close()

def take_session_statistics(event_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT waste_type.waste_name, SUM(event_item.quantity)
        FROM event_item
        JOIN waste_type
            ON event_item.waste_id = waste_type.waste_id
        WHERE event_item.event_id = ?
        GROUP BY waste_type.waste_name
    """, (event_id,))

    result = cursor.fetchall()
    conn.close()

    item_counter = {
        "plastic": 0,
        "paper": 0,
        "metal": 0,
        "other": 0
    }

    for name, quantity in result:
        item_counter[name] = quantity

    return item_counter
    
def end_session(person_id, event_id):
    """
    When a person pressed end their session, calculate their total points based
    on their history and return the number of things they sorted during that
    session.
    """
    conn = get_connection()
    cursor = conn.cursor()
    item_counter = {
        "plastic": 0,
        "paper": 0,
        "metal": 0,
        "other": 0
    }
    cursor.execute("""SELECT waste_type.waste_name, event_item.quantity
       FROM event_item
       JOIN waste_type
       ON event_item.waste_id = waste_type.waste_id
       WHERE event_item.event_id = ?""", (event_id,))
    item_sorted = cursor.fetchall()
    for item in item_sorted:
        name, quan = item
        if name == "plastic":
            item_counter["plastic"] += quan
        elif name == "paper":
            item_counter["paper"] += quan
        elif name == "metal":
            item_counter["metal"] += quan
        elif name == "other":
            item_counter["other"] += quan
        else:
            print("Invalid code")
    total_point = 0
    cursor.execute("SELECT waste_name, waste_point FROM waste_type")
    point_list = cursor.fetchall()
    for item in point_list:
        name, point = item
        if name == "plastic":
            total_point += item_counter["plastic"] * point
        elif name == "paper":
            total_point += item_counter["paper"] * point
        elif name == "metal":
            total_point += item_counter["metal"] * point
        elif name == "other":
            total_point += item_counter["other"] * point
    cursor.execute("SELECT time_end FROM sorting_event WHERE event_id = ?", (event_id,))
    ending = (cursor.fetchone())[0]
    #NULL SOL = None Python
    if ending is None:
        cursor.execute("SELECT total_point FROM Person WHERE person_id = ?", (person_id,))
        previous_point = (cursor.fetchone())[0]
        total_point += previous_point
        cursor.execute("UPDATE Person SET total_point = ? WHERE person_id = ?", (total_point, person_id))
        now = datetime.now()
        current = now.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE sorting_event SET time_end = ? WHERE event_id = ?", (current, event_id))
        conn.commit()
    else:
        print("Your points have been added before, please start a new session!")
    conn.close()
    return {
        "item_counter": item_counter,
        "points_earned": total_point - previous_point,
        "total_points": total_point
        }

def get_waste_decomposition():
    """ Return the total number of waste for each type """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT waste_type.waste_name, SUM(event_item.quantity)
    FROM waste_type
    JOIN event_item
    ON waste_type.waste_id = event_item.waste_id
    GROUP BY waste_type.waste_name
    """)
    summary = cursor.fetchall()
    conn.close()
    return summary

def get_activity_data():
    """ 
    Get daily sorting data for weekly, monthly, and yearly.
    Use SQL for data retrieval
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DATE(time), SUM(quantity)
    FROM event_item
    GROUP BY DATE(time)
    ORDER BY DATE(time)
    """)
    data_daily = cursor.fetchall()
    cursor.execute("""
    SELECT strftime('%Y-%W', time) AS period,
    SUM(quantity) AS total_quantity
    FROM event_item
    GROUP BY strftime('%Y-%W', time)
    ORDER BY period;
    """)
    data_weekly = cursor.fetchall()
    cursor.execute("""
    SELECT
    strftime('%Y-%m', time) AS period,
    SUM(quantity) AS total_quantity
    FROM event_item
    GROUP BY strftime('%Y-%m', time)
    ORDER BY period;
    """)
    data_monthly = cursor.fetchall()
    conn.close()
    return data_daily, data_weekly, data_monthly

def get_activity_per_material():
    """
    Get the trends of sorting per each material 
    from the database
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DATE(e.time), w.waste_name, SUM(e.quantity)
        FROM event_item e
        JOIN waste_type w ON e.waste_id = w.waste_id
        GROUP BY DATE(e.time), w.waste_name
        ORDER BY DATE(e.time);
    """)
    daily = cursor.fetchall()
    cursor.execute("""
        SELECT strftime('%Y-%W', e.time), w.waste_name, SUM(e.quantity)
        FROM event_item e
        JOIN waste_type w ON e.waste_id = w.waste_id
        GROUP BY strftime('%Y-%W', e.time), w.waste_name
        ORDER BY strftime('%Y-%W', e.time);
    """)
    weekly = cursor.fetchall()
    cursor.execute("""
        SELECT strftime('%Y-%m', e.time), w.waste_name, SUM(e.quantity)
        FROM event_item e
        JOIN waste_type w ON e.waste_id = w.waste_id
        GROUP BY strftime('%Y-%m', e.time), w.waste_name
        ORDER BY strftime('%Y-%m', e.time);
    """)
    monthly = cursor.fetchall()
    conn.close()
    return daily, weekly, monthly
    
    
def get_best_material():
    """
    Return the most sorted material
    """
    sorting_summary = get_waste_decomposition()
    best_material = None
    best_quantity = 0
    for item in sorting_summary:
        name = item[0]
        quantity = item[1]
        if quantity > best_quantity:
            best_quantity = quantity
            best_material = name
    return best_material

def get_recent_sorting():
    """
    Get the most recent sorting sessions based on SQL queries
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Person.name, sorting_event.time_start, sorting_event.time_end
        FROM Person
        JOIN sorting_event
            ON Person.person_id = sorting_event.person_id
        ORDER BY sorting_event.time_start DESC""")
    output = cursor.fetchall()
    conn.close()
    return output

def get_user_details():
    """
    Get personal details: name, id and use it for details retrieval
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT Person.person_id, Person.name, Person.total_point FROM Person;""")
    name_list = cursor.fetchall()
    cursor.execute("""
        SELECT Person.person_id, Person.name, COUNT(DISTINCT sorting_event.event_id), COALESCE(SUM(event_item.quantity), 0)
        FROM Person
        LEFT JOIN sorting_event
            ON Person.person_id = sorting_event.person_id
        LEFT JOIN event_item
            ON sorting_event.event_id = event_item.event_id
        GROUP BY Person.person_id
        ORDER BY Person.person_id ASC;
    """)
    data = cursor.fetchall()
    cursor.execute("""
    SELECT Person.name, waste_type.waste_name, COALESCE(SUM(event_item.quantity), 0)
    FROM Person 
    LEFT JOIN sorting_event
        ON Person.person_id = sorting_event.person_id
    LEFT JOIN event_item
        ON sorting_event.event_id = event_item.event_id
    LEFT JOIN waste_type
        ON event_item.waste_id = waste_type.waste_id
    WHERE waste_type.waste_name IS NOT NULL
    GROUP BY Person.name, waste_type.waste_name
    ORDER BY SUM(event_item.quantity);
    """)
    data_decomposition = cursor.fetchall()
    conn.close()
    return name_list, data, data_decomposition
    
def get_personal_details(person_id):
    """
    Get time data based on person_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DATE(time), SUM(quantity)
    FROM Person
    JOIN sorting_event
        ON Person.person_id = sorting_event.person_id
    JOIN event_item
        ON sorting_event.event_id = event_item.event_id
    WHERE Person.person_id = ?
    GROUP BY DATE(time)
    ORDER BY DATE(time)
    """, (person_id,))
    data_daily = cursor.fetchall()
    cursor.execute("""
    SELECT strftime('%Y-%W', time) AS period,
    SUM(quantity) AS total_quantity
    FROM Person
    JOIN sorting_event
        ON Person.person_id = sorting_event.person_id
    JOIN event_item
        ON sorting_event.event_id = event_item.event_id
    WHERE Person.person_id = ?
    GROUP BY strftime('%Y-%W', time)
    ORDER BY period;
    """, (person_id,))
    data_weekly = cursor.fetchall()
    cursor.execute("""
    SELECT
    strftime('%Y-%m', time) AS period,
    SUM(quantity) AS total_quantity
    FROM Person
    JOIN sorting_event
        ON Person.person_id = sorting_event.person_id
    JOIN event_item
        ON sorting_event.event_id = event_item.event_id
    WHERE Person.person_id = ?
    GROUP BY strftime('%Y-%m', time)
    ORDER BY period;
    """, (person_id,))
    data_monthly = cursor.fetchall()
    conn.close()
    return data_daily, data_weekly, data_monthly

def get_personal_histories(person_id):
    """
    Get personal sorting histories based on their user_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sorting_event.time_start, sorting_event.time_end, waste_type.waste_name, event_item.quantity
        FROM Person
        JOIN sorting_event
            ON Person.person_id = sorting_event.person_id
        JOIN event_item
            ON sorting_event.event_id = event_item.event_id
        JOIN waste_type
            ON event_item.waste_id = waste_type.waste_id
        WHERE Person.person_id = ?
        ORDER BY sorting_event.time_start DESC;
        """, (person_id,))
    data = cursor.fetchall()
    conn.close()
    return data

def reset_database():
    """
    Reset everything in the database
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM event_item")
    cursor.execute("DELETE FROM sorting_event")
    cursor.execute("DELETE FROM Person")
    conn.commit()
    conn.close()

def delete_participant(person_id):
    """
    Delete a specific participant from the 
    database based on their person_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""DELETE FROM event_item WHERE event_id IN (SELECT event_id FROM sorting_event WHERE person_id = ?)""", (person_id,))
    cursor.execute("DELETE FROM sorting_event WHERE person_id = ?", (person_id,))
    cursor.execute("DELETE FROM Person WHERE person_id = ?", (person_id,))
    conn.commit()
    conn.close()

def get_all_participants():
    """
    Get person_id, name, points
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT person_id, name, total_point FROM Person")
    data_list = cursor.fetchall()
    conn.close()
    return data_list
