from pathlib import Path

config = Path("/app/api/config.py")
source = config.read_text(encoding="utf-8")

old = '''        if not self.database_url.startswith(("postgresql://", "postgres://", "postgresql+")):
            raise RuntimeError("Production DATABASE_URL must point to Postgres")'''
new = '''        is_postgres = self.database_url.startswith(("postgresql://", "postgres://", "postgresql+"))
        allow_ephemeral_sqlite = os.environ.get("ALLOW_EPHEMERAL_SQLITE_PRODUCTION", "0").strip().lower() in {
            "1", "true", "yes", "on",
        }
        is_ephemeral_sqlite = allow_ephemeral_sqlite and self.database_url.startswith("sqlite:///")
        if not (is_postgres or is_ephemeral_sqlite):
            raise RuntimeError("Production DATABASE_URL must point to Postgres unless ephemeral SQLite is explicitly enabled")'''

count = source.count(old)
if count != 1:
    raise RuntimeError(f"Expected one production database validation block; found {count}")
config.write_text(source.replace(old, new, 1), encoding="utf-8")
print("Enabled explicitly opted-in ephemeral SQLite for the Render free-tier API.")
