from settings.base import *

DEBUG = False

ALLOWED_HOSTS = env_list("BLOG_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("BLOG_DB_NAME", "blog_db"),
        "USER": env_str("BLOG_DB_USER", "blog_user"),
        "PASSWORD": env_str("BLOG_DB_PASSWORD", "blog_password"),
        "HOST": env_str("BLOG_DB_HOST", "localhost"),
        "PORT": env_int("BLOG_DB_PORT", 5432),
    }
}
