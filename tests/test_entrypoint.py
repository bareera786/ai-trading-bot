import os
import subprocess
import tempfile


def test_entrypoint_creates_and_writes(tmp_path):
    # Use the repo's entrypoint script to run a simple touch command
    entrypoint = os.path.join(os.path.dirname(__file__), "..", "docker", "entrypoint.sh")
    entrypoint = os.path.abspath(entrypoint)

    data_dir = tmp_path / "bot_persistence"
    os.environ["BOT_PERSISTENCE_DIR"] = str(data_dir)

    cmd = [entrypoint, "sh", "-c", f"echo hello > {data_dir}/testfile && ls {data_dir}"]
    # Run and ensure it succeeds
    res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert "testfile" in res.stdout
