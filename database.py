import os
import sqlite3
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():

    if DATABASE_URL:

        import psycopg

        return psycopg.connect(DATABASE_URL)

    else:

        connection = sqlite3.connect(
            "school_supplies.db"
        )

        connection.row_factory = sqlite3.Row

        return connection


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

            print("Product insert skipped:", error)


    connection.commit()
    connection.close()


if __name__ == "__main__":

    create_tables()

    add_sample_products()

    print(
        "Database and products created successfully."
    )
