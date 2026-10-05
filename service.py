"""
BusGo service layer - MySQL version.

Stores:
- Users
- Login credentials
- User profiles
- Buses
- Routes
- Bookings
- Payments/status
"""

import mysql.connector
from mysql.connector import Error
import hashlib
import os
import json
import random
import uuid
from datetime import datetime, date
import pandas as pd


# ============================================================
# MYSQL CONFIGURATION
# ============================================================

DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"

# CHANGE THIS to your MySQL root password
DB_PASSWORD = "samarpit_45"

DB_NAME = "busgo"


TAX = 0.05
FEE = 20.0

PROMOS = {
    "BUSGO10": 0.10,
    "WELCOME50": 0.05
}


# ============================================================
# MYSQL CONNECTION
# ============================================================

def conn(database=DB_NAME):
    """
    Create a MySQL connection.
    """

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database
    )


def create_database():
    """
    Creates the BusGo database if it does not exist.
    """

    connection = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )

    cursor = connection.cursor()

    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`"
    )

    connection.commit()

    cursor.close()
    connection.close()


# ============================================================
# GENERIC QUERY FUNCTIONS
# ============================================================

def q(sql, args=(), one=False, commit=False):
    """
    Execute INSERT / UPDATE / DELETE / SELECT query.
    """

    connection = conn()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(sql, args)

        if commit:
            connection.commit()

            # INSERT query
            if cursor.lastrowid:
                return cursor.lastrowid

            return True

        rows = cursor.fetchall()

        if one:
            return rows[0] if rows else None

        return rows

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def df(sql, args=()):
    """
    Execute query and return pandas DataFrame.
    """

    connection = conn()

    try:
        return pd.read_sql_query(
            sql,
            connection,
            params=args
        )

    finally:
        connection.close()


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_pw(pw, salt=None):

    salt = salt or os.urandom(8).hex()

    h = hashlib.pbkdf2_hmac(
        "sha256",
        pw.encode(),
        salt.encode(),
        60000
    ).hex()

    return f"{salt}${h}"


def check_pw(pw, stored):

    if not stored:
        return False

    salt = stored.split("$")[0]

    return hash_pw(pw, salt) == stored


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init():

    # Make sure database exists
    create_database()

    connection = conn()
    cursor = connection.cursor()

    try:

        # ----------------------------------------------------
        # USERS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                phone VARCHAR(20),
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # ----------------------------------------------------
        # BUSES
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                operator VARCHAR(100),
                number VARCHAR(50),
                bus_type VARCHAR(100),
                ac TINYINT DEFAULT 0,
                seat_kind VARCHAR(50),
                src VARCHAR(100),
                dst VARCHAR(100),
                dep VARCHAR(10),
                arr VARCHAR(10),
                price DECIMAL(10,2),
                `rows` INT,
                rating DECIMAL(3,1)
            )
        """)


        # ----------------------------------------------------
        # ROUTES
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                src VARCHAR(100),
                dst VARCHAR(100),
                distance DECIMAL(10,2)
            )
        """)


        # ----------------------------------------------------
        # BOOKINGS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id VARCHAR(30) PRIMARY KEY,
                user_id INT NOT NULL,
                bus_id INT NOT NULL,
                journey_date DATE NOT NULL,
                passengers TEXT,
                seats TEXT,
                base DECIMAL(10,2),
                taxes DECIMAL(10,2),
                fee DECIMAL(10,2),
                discount DECIMAL(10,2),
                total DECIMAL(10,2),
                pay_method VARCHAR(50),
                pay_status VARCHAR(50),
                status VARCHAR(50),
                created DATETIME DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (bus_id)
                    REFERENCES buses(id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()

    finally:

        cursor.close()
        connection.close()


    # ========================================================
    # CREATE DEFAULT USERS
    # ========================================================

    if not q("SELECT 1 FROM users LIMIT 1"):

        q("""
            INSERT INTO users
            (name, email, phone, password, role)
            VALUES (?, ?, ?, ?, ?)
        """.replace("?", "%s"), (
            "Admin",
            "admin@busgo.com",
            "9999999999",
            hash_pw("admin123"),
            "admin"
        ), commit=True)

        q("""
            INSERT INTO users
            (name, email, phone, password, role)
            VALUES (?, ?, ?, ?, ?)
        """.replace("?", "%s"), (
            "Demo User",
            "user@busgo.com",
            "8888888888",
            hash_pw("user123"),
            "user"
        ), commit=True)


    # ========================================================
    # CREATE DEFAULT ROUTES AND BUSES
    # ========================================================

    if not q("SELECT 1 FROM routes LIMIT 1"):

        routes = [
            ("Mumbai", "Pune", 150),
            ("Pune", "Mumbai", 150),
            ("Mumbai", "Nashik", 167),
            ("Nashik", "Mumbai", 167),
            ("Pune", "Goa", 450),
            ("Goa", "Pune", 450)
        ]

        for r in routes:

            q("""
                INSERT INTO routes
                (src, dst, distance)
                VALUES (%s, %s, %s)
            """, r, commit=True)


        ops = [
            (
                "RedLine Travels",
                "Volvo Multi-Axle",
                1,
                "Seater",
                6.0,
                4.5,
                450
            ),

            (
                "Orange Tours",
                "Scania Sleeper",
                1,
                "Sleeper",
                6.5,
                4.3,
                700
            ),

            (
                "Shivneri Express",
                "Semi-Luxury",
                0,
                "Seater",
                7.0,
                4.0,
                300
            ),

            (
                "NightRider",
                "Mercedes Sleeper",
                1,
                "Sleeper",
                6.5,
                4.6,
                900
            ),

            (
                "CityLink",
                "Ordinary",
                0,
                "Seater",
                8.0,
                3.8,
                220
            )
        ]

        deps = [
            "06:00",
            "09:30",
            "14:00",
            "18:30",
            "22:30"
        ]


        for src, dst, dist in routes:

            hrs_scale = dist / 150

            for i, (
                op,
                bt,
                ac,
                kind,
                hrs,
                rat,
                pr
            ) in enumerate(ops):

                dh = int(hrs * hrs_scale)

                dm = int(
                    (hrs * hrs_scale - dh) * 60
                )

                h, m = map(
                    int,
                    deps[i].split(":")
                )

                tot = (
                    h * 60 +
                    m +
                    dh * 60 +
                    dm
                ) % 1440

                arrival = (
                    f"{tot // 60:02d}:"
                    f"{tot % 60:02d}"
                )

                price = round(
                    pr * hrs_scale,
                    -1
                )

                q("""
                    INSERT INTO buses
                    (
                        operator,
                        number,
                        bus_type,
                        ac,
                        seat_kind,
                        src,
                        dst,
                        dep,
                        arr,
                        price,
                        `rows`,
                        rating
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s
                    )
                """, (
                    op,
                    f"MH{12+i:02d}-{random.randint(1000,9999)}",
                    bt,
                    ac,
                    kind,
                    src,
                    dst,
                    deps[i],
                    arrival,
                    price,
                    10,
                    rat
                ), commit=True)


# ============================================================
# USERS
# ============================================================

def register(name, email, phone, pw):

    email = email.lower().strip()

    if q(
        "SELECT 1 FROM users WHERE email=%s",
        (email,)
    ):

        return False, "Email already registered."

    q("""
        INSERT INTO users
        (name, email, phone, password)
        VALUES (%s,%s,%s,%s)
    """, (
        name,
        email,
        phone,
        hash_pw(pw)
    ), commit=True)

    return True, "Account created. Please log in."


def login(email, pw):

    email = email.lower().strip()

    u = q(
        "SELECT * FROM users WHERE email=%s",
        (email,),
        one=True
    )

    if u and check_pw(pw, u["password"]):

        return dict(u)

    return None


def reset_password(email, phone, new_pw):

    email = email.lower().strip()

    u = q("""
        SELECT *
        FROM users
        WHERE email=%s AND phone=%s
    """, (
        email,
        phone
    ), one=True)

    if not u:
        return False

    q("""
        UPDATE users
        SET password=%s
        WHERE id=%s
    """, (
        hash_pw(new_pw),
        u["id"]
    ), commit=True)

    return True


def update_profile(uid, name, phone):

    q("""
        UPDATE users
        SET name=%s, phone=%s
        WHERE id=%s
    """, (
        name,
        phone,
        uid
    ), commit=True)


# ============================================================
# BUSES & SEATS
# ============================================================

def cities():

    d = df("""
        SELECT src
        FROM routes

        UNION

        SELECT dst
        FROM routes
    """)

    return sorted(
        d["src"].tolist()
    )


def duration_min(dep, arr):

    h1, m1 = map(
        int,
        dep.split(":")
    )

    h2, m2 = map(
        int,
        arr.split(":")
    )

    return (
        h2 * 60 +
        m2 -
        h1 * 60 -
        m1
    ) % 1440


def fmt_dur(mins):

    return f"{mins//60}h {mins%60:02d}m"


def seat_labels(rows):

    return [
        f"{r}{c}"
        for r in range(1, rows + 1)
        for c in "ABCD"
    ]


def reserved(rows):

    """
    Ladies reserved:
    1A, 1B

    Male reserved:
    2C, 2D
    """

    return {
        "1A": "F",
        "1B": "F",
        "2C": "M",
        "2D": "M"
    }


def taken_seats(bus_id, jdate):

    bus = q("""
        SELECT `rows`
        FROM buses
        WHERE id=%s
    """, (
        bus_id,
    ), one=True)

    if not bus:
        return set()

    rnd = random.Random(
        f"{bus_id}-{jdate}"
    )

    taken = {
        s
        for s in seat_labels(bus["rows"])
        if rnd.random() < 0.25
        and s not in reserved(0)
    }

    bookings = q("""
        SELECT seats
        FROM bookings
        WHERE bus_id=%s
        AND journey_date=%s
        AND status='Confirmed'
    """, (
        bus_id,
        str(jdate)
    ))

    for booking in bookings:

        if booking["seats"]:

            taken |= set(
                json.loads(
                    booking["seats"]
                )
            )

    return taken


def search_buses(src, dst, jdate):

    d = df("""
        SELECT *
        FROM buses
        WHERE src=%s AND dst=%s
    """, (
        src,
        dst
    ))

    if d.empty:
        return d

    d["duration"] = d.apply(
        lambda r:
        duration_min(
            r.dep,
            r.arr
        ),
        axis=1
    )

    d["available"] = d.apply(
        lambda r:
        r["rows"] * 4 -
        len(
            taken_seats(
                r["id"],
                jdate
            )
        ),
        axis=1
    )

    return d


# ============================================================
# FARE
# ============================================================

def fare(price, n, promo=""):

    base = price * n

    taxes = round(
        base * TAX,
        2
    )

    disc = round(
        base *
        PROMOS.get(
            promo.upper().strip(),
            0
        ),
        2
    )

    return {
        "base": base,
        "taxes": taxes,
        "fee": FEE,
        "discount": disc,
        "total": round(
            base +
            taxes +
            FEE -
            disc,
            2
        )
    }


# ============================================================
# BOOKINGS
# ============================================================

def create_booking(
    uid,
    bus_id,
    jdate,
    passengers,
    seats,
    f,
    method
):

    # Check seats before booking
    if set(seats) & taken_seats(
        bus_id,
        jdate
    ):
        return None


    bid = (
        "BG" +
        uuid.uuid4()
        .hex[:8]
        .upper()
    )


    q("""
        INSERT INTO bookings
        (
            id,
            user_id,
            bus_id,
            journey_date,
            passengers,
            seats,
            base,
            taxes,
            fee,
            discount,
            total,
            pay_method,
            pay_status,
            status,
            created
        )
        VALUES
        (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s
        )
    """, (
        bid,
        uid,
        bus_id,
        str(jdate),
        json.dumps(passengers),
        json.dumps(seats),
        f["base"],
        f["taxes"],
        f["fee"],
        f["discount"],
        f["total"],
        method,
        "Paid",
        "Confirmed",
        datetime.now()
    ), commit=True)

    return bid


def get_booking(bid):

    return q("""
        SELECT
            b.*,
            s.operator,
            s.bus_type,
            s.number,
            s.src,
            s.dst,
            s.dep,
            s.arr
        FROM bookings b

        JOIN buses s
        ON s.id = b.bus_id

        WHERE b.id=%s
    """, (
        bid,
    ), one=True)


def bookings_of(uid=None):

    sql = """
        SELECT
            b.*,
            s.operator,
            s.src,
            s.dst,
            s.dep,
            s.arr,
            u.name AS user_name

        FROM bookings b

        JOIN buses s
        ON s.id = b.bus_id

        JOIN users u
        ON u.id = b.user_id
    """

    if uid:

        sql += """
            WHERE b.user_id=%s
            ORDER BY b.created DESC
        """

        rows = q(
            sql,
            (uid,)
        )

    else:

        sql += """
            ORDER BY b.created DESC
        """

        rows = q(sql)

    return [
        dict(r)
        for r in rows
    ]


def cancel_booking(bid):

    q("""
        UPDATE bookings
        SET
            status='Cancelled',
            pay_status='Refunded'
        WHERE id=%s
    """, (
        bid,
    ), commit=True)


def group(b):

    if b["status"] == "Cancelled":
        return "Cancelled"

    journey_date = b["journey_date"]

    if isinstance(journey_date, str):
        journey_date = datetime.strptime(
            journey_date,
            "%Y-%m-%d"
        ).date()

    return (
        "Upcoming"
        if journey_date >= date.today()
        else "Completed"
    )

# ============================================================
# ADMIN
# ============================================================

def stats():

    t = str(date.today())

    buses = q("""
        SELECT COUNT(*) AS c
        FROM buses
    """, one=True)

    users = q("""
        SELECT COUNT(*) AS c
        FROM users
    """, one=True)

    today = q("""
        SELECT COUNT(*) AS c
        FROM bookings
        WHERE DATE(created)=%s
        AND status='Confirmed'
    """, (
        t,
    ), one=True)

    revenue = q("""
        SELECT COALESCE(SUM(total),0) AS c
        FROM bookings
        WHERE status='Confirmed'
    """, one=True)

    seat_rows = q("""
        SELECT `rows`
        FROM buses
    """)

    seats = sum(
        r["rows"] * 4
        for r in seat_rows
    )

    return {
        "buses": buses["c"],
        "users": users["c"],
        "today": today["c"],
        "revenue": revenue["c"],
        "seats": seats
    }


def save_bus(v, bid=None):

    cols = [
        "operator",
        "number",
        "bus_type",
        "ac",
        "seat_kind",
        "src",
        "dst",
        "dep",
        "arr",
        "price",
        "rows",
        "rating"
    ]

    vals = [
        v[c]
        for c in cols
    ]

    if bid:

        set_clause = ",".join(
            f"{c}=%s"
            for c in cols
        )

        q(
            f"""
            UPDATE buses
            SET {set_clause}
            WHERE id=%s
            """,
            (*vals, bid),
            commit=True
        )

    else:

        placeholders = ",".join(
            ["%s"] * len(cols)
        )

        q(
            f"""
            INSERT INTO buses
            ({",".join(cols)})
            VALUES
            ({placeholders})
            """,
            vals,
            commit=True
        )


def delete_bus(bid):

    q("""
        DELETE FROM buses
        WHERE id=%s
    """, (
        bid,
    ), commit=True)


def save_route(src, dst, dist):

    q("""
        INSERT INTO routes
        (src, dst, distance)
        VALUES (%s,%s,%s)
    """, (
        src,
        dst,
        dist
    ), commit=True)


def delete_route(rid):

    q("""
        DELETE FROM routes
        WHERE id=%s
    """, (
        rid,
    ), commit=True)


# ============================================================
# TEST CONNECTION
# ============================================================

def test_connection():

    try:

        connection = conn()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT DATABASE()"
        )

        database = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return True, database

    except Exception as e:

        return False, str(e)