import os

# Force tests to use a local SQLite DB unless explicitly overridden.
# This keeps the test suite runnable without a running Postgres instance.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///loopforge_test.db")