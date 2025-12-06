

import mysql.connector
from mysql.connector import Error
import getpass
import bcrypt
import datetime

# ---------- CONFIG ----------
DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "HotelManagementSystem"
# Don't hardcode the password in production. For local testing we prompt the user.
# When running, you'll be asked to enter the MySQL root password.
# ----------------------------

def connect(db=DB_NAME):
    pwd = getpass.getpass("Enter MySQL password for user '{}': ".format(DB_USER))
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=pwd, database=db
        )
        return conn
    except Error as e:
        print("Connection error:", e)
        return None

def create_admin(conn):
    cur = conn.cursor()
    username = input("Choose admin username: ").strip()
    full_name = input("Full name: ").strip()
    raw_pw = getpass.getpass("Choose admin password (will be hashed): ")
    hashed = bcrypt.hashpw(raw_pw.encode(), bcrypt.gensalt())
    try:
        cur.execute("INSERT INTO admins (username, password_hash, full_name) VALUES (%s,%s,%s);",
                    (username, hashed.decode(), full_name))
        conn.commit()
        print("Admin user created.")
    except Error as e:
        print("Error creating admin:", e)
    finally:
        cur.close()

def add_hotel(conn):
    cur = conn.cursor()
    name = input("Hotel name: ").strip()
    address = input("Address: ").strip()
    city = input("City: ").strip()
    phone = input("Phone: ").strip()
    try:
        cur.execute("INSERT INTO hotels (name,address,city,phone) VALUES (%s,%s,%s,%s);",
                    (name, address, city, phone))
        conn.commit()
        print("Hotel added with id", cur.lastrowid)
    except Error as e:
        print("Error adding hotel:", e)
    finally:
        cur.close()

def add_room(conn):
    cur = conn.cursor()
    hotel_id = input("Hotel ID (number): ").strip()
    room_number = input("Room number: ").strip()
    room_type = input("Room type: ").strip()
    price = input("Price (e.g. 3500): ").strip()
    try:
        cur.execute("INSERT INTO rooms (hotel_id, room_number, room_type, price) VALUES (%s,%s,%s,%s);",
                    (hotel_id, room_number, room_type, price))
        conn.commit()
        print("Room added with id", cur.lastrowid)
    except Error as e:
        print("Error adding room:", e)
    finally:
        cur.close()

def add_guest(conn):
    cur = conn.cursor()
    name = input("Guest full name: ").strip()
    phone = input("Phone: ").strip()
    email = input("Email: ").strip()
    try:
        cur.execute("INSERT INTO guests (full_name, phone, email) VALUES (%s,%s,%s);",
                    (name, phone, email))
        conn.commit()
        print("Guest added with id", cur.lastrowid)
    except Error as e:
        print("Error adding guest:", e)
    finally:
        cur.close()

def check_available_rooms(conn, hotel_id, check_in, check_out):
    cur = conn.cursor()
    # Simple availability: room.status = 'available' and not reserved overlapping
    query = """
    SELECT r.room_id, r.room_number, r.room_type, r.price
    FROM rooms r
    WHERE r.hotel_id=%s AND r.room_id NOT IN (
        SELECT room_id FROM reservations
        WHERE hotel_id=%s
          AND NOT (check_out <= %s OR check_in >= %s)
          AND status IN ('booked','checked_in')
    ) AND r.status='available';
    """
    cur.execute(query, (hotel_id, hotel_id, check_in, check_out))
    rows = cur.fetchall()
    cur.close()
    return rows

def make_reservation(conn):
    cur = conn.cursor()
    guest_id = input("Guest ID (or leave blank to create a new guest): ").strip()
    if not guest_id:
        add_guest(conn)
        # retrieve last guest id
        cur_inner = conn.cursor()
        cur_inner.execute("SELECT LAST_INSERT_ID();")
        guest_id = cur_inner.fetchone()[0]
        cur_inner.close()
    hotel_id = input("Hotel ID: ").strip()
    check_in = input("Check-in date (YYYY-MM-DD): ").strip()
    check_out = input("Check-out date (YYYY-MM-DD): ").strip()
    # Show available rooms
    available = check_available_rooms(conn, hotel_id, check_in, check_out)
    if not available:
        print("No available rooms for those dates.")
        return
    print("Available rooms:")
    for r in available:
        print(f" - room_id={r[0]}, number={r[1]}, type={r[2]}, price={r[3]}")
    chosen = input("Choose room_id from above: ").strip()
    total = input("Total amount (or leave blank to use room price): ").strip()
    if not total:
        # find price
        price = next((r[3] for r in available if str(r[0])==chosen), 0)
        total = price
    try:
        cur.execute("""INSERT INTO reservations
            (guest_id, hotel_id, room_id, check_in, check_out, status, total_amount)
            VALUES (%s,%s,%s,%s,%s,'booked',%s);""",
            (guest_id, hotel_id, chosen, check_in, check_out, total))
        conn.commit()
        res_id = cur.lastrowid
        print("Reservation created id:", res_id)
    except Error as e:
        print("Error creating reservation:", e)
    finally:
        cur.close()

def make_payment(conn):
    cur = conn.cursor()
    res_id = input("Reservation ID: ").strip()
    amount = input("Amount: ").strip()
    method = input("Method (card/cash/etc): ").strip()
    try:
        cur.execute("INSERT INTO payments (reservation_id, amount, method) VALUES (%s,%s,%s);",
                    (res_id, amount, method))
        # Optionally mark reservation as paid or change status — decision left to user
        conn.commit()
        print("Payment recorded, id:", cur.lastrowid)
    except Error as e:
        print("Error recording payment:", e)
    finally:
        cur.close()

def list_tables(conn):
    cur = conn.cursor()
    cur.execute("SHOW TABLES;")
    print("Tables:", [r[0] for r in cur.fetchall()])
    cur.close()

def list_table_data(conn, table):
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM `{table}` LIMIT 50;")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        print("Columns:", cols)
        for r in rows:
            print(r)
    except Error as e:
        print("Error reading table:", e)
    finally:
        cur.close()

def main_menu():
    conn = connect()
    if not conn:
        return
    try:
        while True:
            print("\n--- Hotel Management CLI ---")
            print("1) Create admin user")
            print("2) Add hotel")
            print("3) Add room")
            print("4) Add guest")
            print("5) Make reservation")
            print("6) Make payment")
            print("7) List tables")
            print("8) Show table data")
            print("9) Exit")
            choice = input("Choose: ").strip()
            if choice == '1':
                create_admin(conn)
            elif choice == '2':
                add_hotel(conn)
            elif choice == '3':
                add_room(conn)
            elif choice == '4':
                add_guest(conn)
            elif choice == '5':
                make_reservation(conn)
            elif choice == '6':
                make_payment(conn)
            elif choice == '7':
                list_tables(conn)
            elif choice == '8':
                tab = input("Table name: ").strip()
                list_table_data(conn, tab)
            elif choice == '9':
                print("Goodbye.")
                break
            else:
                print("Invalid choice.")
    finally:
        conn.close()

if __name__ == "__main__":
    main_menu()
