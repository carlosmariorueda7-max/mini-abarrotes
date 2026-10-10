import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "mini_abarrotes"),
    "user": os.getenv("DB_USER", "mini_abarrotes_app"),
    "password": os.environ["DB_PASSWORD"],
}