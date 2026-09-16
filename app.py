import logging
import os
from datetime import datetime, timezone

import boto3
import pymysql
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log")),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------------------------------------------------
# Open-Meteo
# ---------------------------------------------------------

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

# ---------------------------------------------------------
# Environment variables
# ---------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "cloud_weather")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Hyderabad")

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
S3_REGION = os.getenv("S3_REGION", "ap-south-1")

# IAM role attached to EC2 supplies AWS credentials.
s3_client = boto3.client(
    "s3",
    region_name=S3_REGION
)

# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_db_connection():
    if not all([DB_HOST, DB_USER, DB_PASSWORD]):
        return None

    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        autocommit=True,
    )


def check_database():
    connection = get_db_connection()

    if not connection:
        return False

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return True

    except Exception as error:
        logger.error("Database check failed: %s", error)
        return False

    finally:
        connection.close()


def save_weather_search(city, location, weather):
    connection = get_db_connection()

    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO weather_searches
                (
                    city,
                    country,
                    latitude,
                    longitude,
                    temperature,
                    humidity,
                    weather_condition
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    city,
                    location.get("country"),
                    location.get("latitude"),
                    location.get("longitude"),
                    weather.get("temperature"),
                    weather.get("humidity"),
                    weather.get("condition"),
                ),
            )

    except Exception as error:
        logger.error(
            "Could not save weather search: %s",
            error
        )

    finally:
        connection.close()


def get_recent_searches(limit=10):
    connection = get_db_connection()

    if not connection:
        return []

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    city,
                    country,
                    temperature,
                    humidity,
                    weather_condition,
                    searched_at
                FROM weather_searches
                ORDER BY searched_at DESC
                LIMIT %s
                """,
                (limit,),
            )

            return cursor.fetchall()

    except Exception as error:
        logger.error(
            "Could not load recent searches: %s",
            error
        )

        return []

    finally:
        connection.close()


# ---------------------------------------------------------
# Open-Meteo API
# ---------------------------------------------------------

def get_location(city):

    response = requests.get(
        GEOCODING_URL,
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=10,
    )

    response.raise_for_status()

    results = response.json().get(
        "results",
        []
    )

    return results[0] if results else None


def get_weather(latitude, longitude):

    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "weather_code,"
                "wind_speed_10m"
            ),
            "daily": (
                "weather_code,"
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "forecast_days": 7,
            "timezone": "auto",
        },
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    current = data["current"]

    weather = {
        "temperature": current.get(
            "temperature_2m"
        ),

        "humidity": current.get(
            "relative_humidity_2m"
        ),

        "feels_like": current.get(
            "apparent_temperature"
        ),

        "wind_speed": current.get(
            "wind_speed_10m"
        ),

        "condition": WEATHER_CODES.get(
            current.get("weather_code"),
            "Unknown"
        ),

        "unit": data.get(
            "current_units",
            {}
        ).get(
            "temperature_2m",
            "°C"
        ),
    }

    daily = data.get(
        "daily",
        {}
    )

    forecast = []

    for i, day in enumerate(
        daily.get("time", [])
    ):

        forecast.append(
            {
                "date": day,

                "condition": WEATHER_CODES.get(
                    daily.get(
                        "weather_code",
                        []
                    )[i],
                    "Unknown",
                ),

                "max": daily.get(
                    "temperature_2m_max",
                    []
                )[i],

                "min": daily.get(
                    "temperature_2m_min",
                    []
                )[i],

                "rain": daily.get(
                    "precipitation_probability_max",
                    []
                )[i],
            }
        )

    return weather, forecast


# ---------------------------------------------------------
# Amazon S3
# ---------------------------------------------------------

def check_s3_connection():

    if not S3_BUCKET_NAME:
        return False

    try:

        s3_client.head_bucket(
            Bucket=S3_BUCKET_NAME
        )

        return True

    except Exception as error:

        logger.error(
            "S3 connection failed: %s",
            error
        )

        return False


def list_s3_assets():

    if not S3_BUCKET_NAME:
        return []

    try:

        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix="assets/"
        )

        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": (
                    obj["LastModified"]
                    .isoformat()
                ),
            }
            for obj in response.get(
                "Contents",
                []
            )
        ]

    except Exception as error:

        logger.error(
            "Could not list S3 assets: %s",
            error
        )

        return []


def upload_file_to_s3(
    local_file,
    s3_key
):

    if not S3_BUCKET_NAME:
        return False

    try:

        s3_client.upload_file(
            local_file,
            S3_BUCKET_NAME,
            s3_key
        )

        logger.info(
            "Uploaded %s to S3 as %s",
            local_file,
            s3_key
        )

        return True

    except Exception as error:

        logger.error(
            "S3 upload failed: %s",
            error
        )

        return False


# ---------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------

@app.route("/")
def home():

    city = (
        request.args.get(
            "city",
            DEFAULT_CITY
        ).strip()
        or DEFAULT_CITY
    )

    location = None
    weather = None
    forecast = []

    error = None

    try:

        location = get_location(city)

        if not location:

            error = (
                f"Could not find a location "
                f"for '{city}'."
            )

        else:

            weather, forecast = get_weather(
                location["latitude"],
                location["longitude"]
            )

            save_weather_search(
                city,
                location,
                weather
            )

            logger.info(
                "Weather search requested for city: %s",
                city
            )

    except requests.RequestException:

        logger.exception(
            "Weather API request failed"
        )

        error = (
            "Weather service is temporarily "
            "unavailable."
        )

    except Exception:

        logger.exception(
            "Unexpected application error"
        )

        error = (
            "An unexpected error occurred."
        )

    return render_template(
        "index.html",

        city=city,

        location=location,

        weather=weather,

        forecast=forecast,

        recent_searches=get_recent_searches(),

        database_status=check_database(),

        s3_status=check_s3_connection(),

        error=error,
    )


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.route("/health")
def health():

    database_status = check_database()

    s3_status = check_s3_connection()

    overall_status = (
        "healthy"
        if database_status and s3_status
        else "degraded"
    )

    return jsonify(
        {
            "status": overall_status,

            "application":
                "Cloud Weather Dashboard",

            "service":
                "Flask",

            "database":
                "connected"
                if database_status
                else "not connected",

            "s3":
                "connected"
                if s3_status
                else "not connected",

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }
    )


# ---------------------------------------------------------
# Database test
# ---------------------------------------------------------

@app.route("/db-test")
def db_test():

    if check_database():

        return jsonify(
            {
                "status":
                    "success",

                "message":
                    "Connected to Amazon RDS MySQL."
            }
        )

    return jsonify(
        {
            "status":
                "error",

            "message":
                "Could not connect to Amazon RDS MySQL."
        }
    ), 500


# ---------------------------------------------------------
# S3 test
# ---------------------------------------------------------

@app.route("/s3-test")
def s3_test():

    if check_s3_connection():

        return jsonify(
            {
                "status":
                    "success",

                "message":
                    "Connected to Amazon S3.",

                "bucket":
                    S3_BUCKET_NAME,

                "assets":
                    [
                        item["key"]
                        for item
                        in list_s3_assets()
                    ],
            }
        )

    return jsonify(
        {
            "status":
                "error",

            "message":
                "Could not connect to Amazon S3."
        }
    ), 500


# ---------------------------------------------------------
# S3 upload test
# ---------------------------------------------------------

@app.route("/s3-upload-test")
def s3_upload_test():

    local_file = os.path.join(
        BASE_DIR,
        "README.md"
    )

    if upload_file_to_s3(
        local_file,
        "assets/README.md"
    ):

        return jsonify(
            {
                "status":
                    "success",

                "message":
                    "File uploaded to S3.",

                "object":
                    "assets/README.md",
            }
        )

    return jsonify(
        {
            "status":
                "error",

            "message":
                "S3 upload failed."
        }
    ), 500


# ---------------------------------------------------------
# Application start
# ---------------------------------------------------------

if __name__ == "__main__":

    logger.info(
        "Cloud Weather Dashboard started"
    )

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        ),
        debug=False,
    )
