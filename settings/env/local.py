from settings.base import *

DEBUG = True

ALLOWED_HOSTS = env_list("BLOG_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
