import os
import logging

from flask import Flask, render_template, request, redirect, url_for
import psycopg2
import boto3

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "cloudapp")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )


@app.route("/")
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, message, created_at "
            "FROM messages ORDER BY created_at DESC"
        )

        messages = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("index.html", messages=messages)

    except Exception as e:
        logging.exception("Database error")
        return render_template(
            "index.html",
            messages=[],
            error=str(e)
        )


@app.route("/add", methods=["POST"])
def add_message():

    name = request.form.get("name")
    message = request.form.get("message")

    if not name or not message:
        return redirect(url_for("index"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO messages (name, message) VALUES (%s, %s)",
            (name, message)
        )

        conn.commit()

        cursor.close()
        conn.close()

        logging.info("New message added by %s", name)

    except Exception:
        logging.exception("Failed to insert message")

    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {
        "status": "healthy",
        "application": "Cloud Services Web App"
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
