import os
from pathlib import Path


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_persistence_dirs_and_status_are_profile_scoped(tmp_path, monkeypatch):
    # Force all persistence writes into the tmp sandbox.
    base = tmp_path / "bot_persistence"
    monkeypatch.setenv("BOT_PERSISTENCE_DIR", str(base))

    from app.services.persistence import ProfessionalPersistence, ensure_persistence_dirs

    # Create two independent profiles.
    user1_dir = ensure_persistence_dirs("user_1")
    user2_dir = ensure_persistence_dirs("user_2")

    assert user1_dir != user2_dir
    assert user1_dir == base / "user_1"
    assert user2_dir == base / "user_2"

    # Seed per-profile save counts and backups.
    _write_text(user1_dir / "save_count.txt", "3")
    _write_text(user2_dir / "save_count.txt", "7")

    _write_text(user1_dir / "backups" / "state_backup_20260103_000001.json", "{}")
    _write_text(user1_dir / "backups" / "state_backup_20260103_000002.json", "{}")
    _write_text(user2_dir / "backups" / "state_backup_20260103_000003.json", "{}")

    # Manager instance should read profile-scoped status when profile is provided.
    manager = ProfessionalPersistence(persistence_dir=str(base))

    status1 = manager.get_persistence_status(profile="user_1")
    status2 = manager.get_persistence_status(profile="user_2")

    assert status1["total_saves"] == 3
    assert status2["total_saves"] == 7

    assert status1["backup_count"] == 2
    assert status2["backup_count"] == 1

    # Ensure no cross-profile file leakage.
    assert not (user1_dir / "backups" / "state_backup_20260103_000003.json").exists()
    assert not (user2_dir / "backups" / "state_backup_20260103_000001.json").exists()
