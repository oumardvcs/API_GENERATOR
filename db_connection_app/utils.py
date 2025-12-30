from django.conf import settings

ENGINE_MAP = {
    "postgresql": "django.db.backends.postgresql",
    "mysql": "django.db.backends.mysql",
    "sqlite": "django.db.backends.sqlite3",
}

def register_dynamic_db(
    alias,
    db_type,
    name,
    user="",
    password="",
    host="",
    port="",
):
    settings.DATABASES[alias] = {
        "ENGINE": ENGINE_MAP[db_type],
        "NAME": name,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": port,
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 0,
        "AUTOCOMMIT": True,
    }
