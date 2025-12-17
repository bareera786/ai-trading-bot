from types import SimpleNamespace
import importlib.util
import sys


def load_migrations_with_fake_db(monkeypatch, executed):
    # Create fake 'app.extensions' module with db
    class FakeInspector:
        def get_columns(self, table_name):
            if table_name == "user":
                return [{"name": "id"}, {"name": "username"}]
            return []

    class FakeConn:
        def execute(self, text):
            executed.append(str(text))

    class FakeEngine:
        def connect(self):
            class Ctx:
                def __enter__(self_non):
                    return FakeConn()

                def __exit__(self_non, exc_type, exc, tb):
                    return False

            return Ctx()

    fake_db = SimpleNamespace(
        inspect=lambda e: FakeInspector(), engine=FakeEngine(), text=lambda s: s
    )

    # inject fake 'app.extensions' into sys.modules so migrations can import it
    # Use monkeypatch so the original module is restored after the test.
    fake_extensions = SimpleNamespace(db=fake_db)
    monkeypatch.setitem(sys.modules, "app.extensions", fake_extensions)

    # load the migrations module directly from file
    spec = importlib.util.spec_from_file_location("migrations", "./app/migrations.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migrate_adds_email_verified(monkeypatch):
    executed = []
    migrations = load_migrations_with_fake_db(monkeypatch, executed)

    # Should not raise
    migrations.migrate_database()

    # Ensure ALTER TABLE for email_verified was executed
    assert any("ALTER TABLE user ADD COLUMN email_verified" in e for e in executed)
