from pathlib import Path

# Define the root directory of the project
PROJECT_ROOT = Path.cwd()

# Path to the file that stores the SHA of the last approved commit
LAST_COMMIT_FILE = PROJECT_ROOT / "logs" / ".last_commit_sha"
