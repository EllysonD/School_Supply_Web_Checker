from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

import os
import sqlite3
from datetime import datetime, timedelta


app = Flask(__name__)


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key-change-online"
)


DATABASE_URL = os.environ.get("DATABASE_URL")


ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "admin"
)


ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_connection():

    if DATABASE_URL:

        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row
        )

        return connection


    connection = sqlite3.connect(
        "school_supplies.db"
    )

    connection.row_factory = sqlite3.Row

    return connection


# --------------------------------------------------
# CREATE TABLES
# --------------------------------------------------

def create_tables():

    connection = get_connection()

    cursor = connection.cursor()


    if DATABASE_URL:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS school_supplies (
                id SERIAL PRIMARY KEY,
                product_id VARCHAR(50) UNIQUE NOT NULL,
                product_name VARCHAR(100) NOT NULL,
                category VARCHAR(100) NOT NULL,
                quantity INTEGER NOT NULL,
                last_updated TIMESTAMP NOT NULL
            )
        """)


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS availability_history (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(100) NOT NULL,
                old_quantity INTEGER,
                new_quantity INTEGER NOT NULL,
                action VARCHAR(100) NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)

    else:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS school_supplies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE NOT NULL,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS availability_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                old_quantity INTEGER,
                new_quantity INTEGER NOT NULL,
                action TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


    connection.commit()

    connection.close()


# --------------------------------------------------
# ADD SAMPLE PRODUCTS
# --------------------------------------------------

def add_sample_products():

    connection = get_connection()

    cursor = connection.cursor()

    now = datetime.now()


    products = [
        ("P001", "Ballpen", "Writing Materials", 15),
        ("P002", "Pencil", "Writing Materials", 8),
        ("P003", "Eraser", "Writing Materials", 20),
        ("P004", "Notebook", "Paper Products", 0),
        ("P005", "Yellow Pad", "Paper Products", 10)
    ]


    for product in products:

        try:

            if DATABASE_URL:

                cursor.execute("""
                    INSERT INTO school_supplies
                    (
                        product_id,
                        product_name,
                        category,
                        quantity,
                        last_updated
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO NOTHING
                """, (
                    product[0],
                    product[1],
                    product[2],
                    product[3],
                    now
                ))

            else:

                cursor.execute("""
                    INSERT OR IGNORE INTO school_supplies
                    (
                        product_id,
                        product_name,
                        category,
                        quantity,
                        last_updated
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    product[0],
                    product[1],
                    product[2],
                    product[3],
                    now.strftime("%Y-%m-%d %H:%M:%S")
                ))

        except Exception as error:

            print(
                "Sample product already exists or was skipped:",
                error
            )


    connection.commit()

    connection.close()


# --------------------------------------------------
# GET PRODUCTS
# --------------------------------------------------

def get_products(search=""):

    connection = get_connection()

    cursor = connection.cursor()


    if DATABASE_URL:

        if search:

            cursor.execute("""
                SELECT *
                FROM school_supplies
                WHERE
                    product_name ILIKE %s
                    OR category ILIKE %s
                ORDER BY product_name
            """, (
                f"%{search}%",
                f"%{search}%"
            ))

        else:

            cursor.execute("""
                SELECT *
                FROM school_supplies
                ORDER BY product_name
            """)

    else:

        if search:

            cursor.execute("""
                SELECT *
                FROM school_supplies
                WHERE
                    product_name LIKE ?
                    OR category LIKE ?
                ORDER BY product_name
            """, (
                f"%{search}%",
                f"%{search}%"
            ))

        else:

            cursor.execute("""
                SELECT *
                FROM school_supplies
                ORDER BY product_name
            """)


    products = cursor.fetchall()

    connection.close()

    return products


# --------------------------------------------------
# GET HISTORY
# --------------------------------------------------

def get_history():

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT *
        FROM availability_history
        ORDER BY id DESC
    """)


    history = cursor.fetchall()

    connection.close()

    return history


# --------------------------------------------------
# GET LAST UPDATE
# --------------------------------------------------

def get_last_update():

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT MAX(updated_at) AS latest
        FROM availability_history
    """)


    result = cursor.fetchone()

    connection.close()


    if result:

        return result["latest"]


    return None


# --------------------------------------------------
# PUBLIC HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():

    search = request.args.get(
        "search",
        ""
    ).strip()


    products = get_products(
        search
    )


    last_update = get_last_update()


    show_notification = False


    if last_update:

        try:

            if isinstance(last_update, str):

                last_update_time = datetime.fromisoformat(
                    last_update
                )

            else:

                last_update_time = last_update


            if datetime.now() - last_update_time <= timedelta(
                hours=24
            ):

                show_notification = True

        except Exception:

            show_notification = True


    return render_template(
        "index.html",
        products=products,
        search=search,
        last_update=last_update,
        show_notification=show_notification
    )


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        )

        password = request.form.get(
            "password",
            ""
        )


        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin")
            )


        return render_template(
            "admin_login.html",
            error="Invalid username or password."
        )


    return render_template(
        "admin_login.html"
    )


# --------------------------------------------------
# ADMIN PANEL
# --------------------------------------------------

@app.route("/admin")
def admin():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("admin_login")
        )


    products = get_products()

    history = get_history()


    return render_template(
        "admin.html",
        products=products,
        history=history
    )


# --------------------------------------------------
# ADD PRODUCT
# --------------------------------------------------

@app.route(
    "/admin/add",
    methods=["POST"]
)
def add_product():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("admin_login")
        )


    product_id = request.form[
        "product_id"
    ].strip()


    product_name = request.form[
        "product_name"
    ].strip()


    category = request.form[
        "category"
    ].strip()


    quantity = int(
        request.form[
            "quantity"
        ]
    )


    connection = get_connection()

    cursor = connection.cursor()


    try:

        now = datetime.now()


        if DATABASE_URL:

            cursor.execute("""
                INSERT INTO school_supplies
                (
                    product_id,
                    product_name,
                    category,
                    quantity,
                    last_updated
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                product_id,
                product_name,
                category,
                quantity,
                now
            ))


            cursor.execute("""
                INSERT INTO availability_history
                (
                    product_name,
                    old_quantity,
                    new_quantity,
                    action,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                product_name,
                0,
                quantity,
                "Product Added",
                now
            ))


        else:

            cursor.execute("""
                INSERT INTO school_supplies
                (
                    product_id,
                    product_name,
                    category,
                    quantity,
                    last_updated
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                product_id,
                product_name,
                category,
                quantity,
                now.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))


            cursor.execute("""
                INSERT INTO availability_history
                (
                    product_name,
                    old_quantity,
                    new_quantity,
                    action,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                product_name,
                0,
                quantity,
                "Product Added",
                now.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))


        connection.commit()


    except Exception as error:

        connection.rollback()

        print(
            "Error adding product:",
            error
        )


    connection.close()


    return redirect(
        url_for("admin")
    )


# --------------------------------------------------
# UPDATE PRODUCT
# --------------------------------------------------

@app.route(
    "/admin/update/<int:product_id>",
    methods=["POST"]
)
def update_product(product_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("admin_login")
        )


    new_quantity = int(
        request.form[
            "quantity"
        ]
    )


    connection = get_connection()

    cursor = connection.cursor()


    if DATABASE_URL:

        cursor.execute("""
            SELECT product_name, quantity
            FROM school_supplies
            WHERE id = %s
        """, (
            product_id,
        ))

    else:

        cursor.execute("""
            SELECT product_name, quantity
            FROM school_supplies
            WHERE id = ?
        """, (
            product_id,
        ))


    product = cursor.fetchone()


    if product:

        old_quantity = product[
            "quantity"
        ]

        product_name = product[
            "product_name"
        ]


        now = datetime.now()


        if DATABASE_URL:

            cursor.execute("""
                UPDATE school_supplies
                SET
                    quantity = %s,
                    last_updated = %s
                WHERE id = %s
            """, (
                new_quantity,
                now,
                product_id
            ))


            cursor.execute("""
                INSERT INTO availability_history
                (
                    product_name,
                    old_quantity,
                    new_quantity,
                    action,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                product_name,
                old_quantity,
                new_quantity,
                "Quantity Updated",
                now
            ))


        else:

            cursor.execute("""
                UPDATE school_supplies
                SET
                    quantity = ?,
                    last_updated = ?
                WHERE id = ?
            """, (
                new_quantity,
                now.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                product_id
            ))


            cursor.execute("""
                INSERT INTO availability_history
                (
                    product_name,
                    old_quantity,
                    new_quantity,
                    action,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                product_name,
                old_quantity,
                new_quantity,
                "Quantity Updated",
                now.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))


    connection.commit()

    connection.close()


    return redirect(
        url_for("admin")
    )


# --------------------------------------------------
# DELETE PRODUCT
# --------------------------------------------------

@app.route(
    "/admin/delete/<int:product_id>",
    methods=["POST"]
)
def delete_product(product_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("admin_login")
        )


    connection = get_connection()

    cursor = connection.cursor()


    if DATABASE_URL:

        cursor.execute("""
            SELECT product_name, quantity
            FROM school_supplies
            WHERE id = %s
        """, (
            product_id,
        ))

    else:

        cursor.execute("""
            SELECT product_name, quantity
            FROM school_supplies
            WHERE id = ?
        """, (
            product_id,
        ))


    product = cursor.fetchone()


    if product:

        product_name = product[
            "product_name"
        ]

        old_quantity = product[
            "quantity"
        ]

        now = datetime.now()


        if DATABASE_URL:

            cursor.execute("""
                INSERT INTO availability_history
                (
                    product_name,
                    old_quantity,
                    new_quantity,
                    action,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                product_name,
                old_quantity,
                0,
                "Product Deleted",
                now
            ))


            cursor.execute("""
                DELETE FROM school_supplies
                WHERE id = %s
            """, (
                product_id,
            ))


        else:

            cursor.execute("""
                INSERT INTO availability_history
                (
                    product_name,
                    old_quantity,
                    new_quantity,
                    action,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                product_name,
                old_quantity,
                0,
                "Product Deleted",
                now.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))


            cursor.execute("""
                DELETE FROM school_supplies
                WHERE id = ?
            """, (
                product_id,
            ))


    connection.commit()

    connection.close()


    return redirect(
        url_for("admin")
    )


# --------------------------------------------------
# ADMIN LOGOUT
# --------------------------------------------------

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

create_tables()

add_sample_products()


if __name__ == "__main__":

    app.run(
        debug=True
    )
