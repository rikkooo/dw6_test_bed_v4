import subprocess
import sys
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from dw6.config import LAST_COMMIT_FILE

def is_working_directory_clean():
    """Checks if the git working directory is clean."""
    try:
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        return result.stdout.strip() == ""
    except subprocess.CalledProcessError as e:
        print("ERROR: Failed to execute 'git status' command.", file=sys.stderr)
        print(f"\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

def get_current_commit_sha():
    """Returns the SHA of the current HEAD commit."""
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()

def has_new_commits():
    """Checks if there are new commits since the last recorded SHA."""
    if not LAST_COMMIT_FILE.exists():
        print("ERROR: Cannot determine last approved commit. Tracking file not found.", file=sys.stderr)
        print(f"Expected file at: {LAST_COMMIT_FILE}", file=sys.stderr)
        sys.exit(1)

    last_commit_sha = LAST_COMMIT_FILE.read_text().strip()
    current_commit_sha = get_current_commit_sha()
    return last_commit_sha != current_commit_sha

def get_commit_stats():
    """Returns statistics about the changes since the last approved commit."""
    if not LAST_COMMIT_FILE.exists():
        return None

    last_commit_sha = LAST_COMMIT_FILE.read_text().strip()
    current_commit_sha = get_current_commit_sha()

    if last_commit_sha == current_commit_sha:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}

    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "--shortstat", last_commit_sha, current_commit_sha]
        ).decode()
        
        files_changed = 0
        insertions = 0
        deletions = 0

        parts = diff_output.strip().split(', ')
        for part in parts:
            if 'file changed' in part or 'files changed' in part:
                files_changed = int(part.split()[0])
            elif 'insertion' in part:
                insertions = int(part.split()[0])
            elif 'deletion' in part:
                deletions = int(part.split()[0])

        return {"files_changed": files_changed, "insertions": insertions, "deletions": deletions}
    except subprocess.CalledProcessError:
        return None

def save_current_commit_sha():
    """Saves the current commit SHA to the tracking file."""
    current_commit_sha = get_current_commit_sha()
    # Ensure the parent directory (logs) exists
    LAST_COMMIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_COMMIT_FILE.write_text(current_commit_sha)
    print(f"[GIT] Saved current commit SHA: {current_commit_sha}")

def commit_changes(requirement_id):
    """Adds and commits all changes with a standardized message."""
    print("[GIT] Committing approved code...")
    subprocess.run(["git", "add", "."], check=True)
    
    result = subprocess.run(["git", "diff", "--staged", "--quiet"])
    
    if result.returncode == 0:
        print("[GIT] Working directory is clean. No new commit will be created.")
    else:
        commit_message = f"feat(req-{requirement_id}): Coder stage submission for requirement {requirement_id}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print(f"[GIT] Code committed: {commit_message}")

def commit_and_push_deliverable(deliverable_path, stage_name):
    """Adds, commits, and pushes a single deliverable file."""
    from dw6.state_manager import WorkflowState # Local import to avoid circular dependency
    state = WorkflowState()
    cycle = state.get("Cycle")
    commit_message = f"docs(cycle-{cycle}): Add {stage_name.lower()} deliverable for cycle {cycle}"
    
    print(f"[GIT] Committing deliverable: {deliverable_path}")
    subprocess.run(["git", "add", deliverable_path], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    print(f"[GIT] Committed with message: {commit_message}")
    
    # Optional: Push to remote
    # push_to_remote() # This can be enabled if remote repo is configured

def get_remote_repo_url():
    """Retrieves the remote repository URL from the .env file."""
    load_dotenv()
    return os.getenv("GITHUB_REPO_URL")

def get_latest_commit_hash(branch='master'):
    """Returns the hash of the latest commit on the specified local branch."""
    result = subprocess.run(['git', 'rev-parse', branch], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()

def get_remote_tags_with_commits():
    """Returns a dictionary of remote tags and the commit hashes they point to."""
    result = subprocess.run(['git', 'ls-remote', '--tags', 'origin'], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {}
    
    tags = {}
    output = result.stdout.strip()
    if not output:
        return {}
        
    for line in output.split('\n'):
        if 'refs/tags/' in line:
            commit_hash, ref = line.split('\t')
            tag_name = ref.split('refs/tags/')[-1]
            if tag_name.endswith('^{}'):
                tag_name = tag_name[:-3]
                tags[tag_name] = commit_hash
            elif tag_name not in tags:
                tags[tag_name] = commit_hash
    return tags

def get_authenticated_url(repo_url):
    """Injects the GitHub token into the repository URL for authentication."""
    token = os.getenv("GITHUB_TOKEN")
    if not token or not repo_url:
        return None
    
    parts = urlparse(repo_url)
    if parts.hostname != 'github.com':
        return repo_url # Not a GitHub URL, return as is

    authed_parts = parts._replace(netloc=f"{token}@{parts.hostname}")
    return urlunparse(authed_parts)

def push_to_remote():
    """Pushes the current branch to the configured remote repository."""
    repo_url = get_remote_repo_url()
    if not repo_url:
        print("GITHUB_REPO_URL not set in .env file. Skipping push.", file=sys.stderr)
        return False

    auth_url = get_authenticated_url(repo_url)
    
    branch_result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    current_branch = branch_result.stdout.strip()

    if not current_branch:
        print("[ERROR] Could not determine the current git branch.", file=sys.stderr)
        return False

    push_url = auth_url if auth_url else repo_url

    try:
        command = ["git", "push", push_url, current_branch]
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("[GIT] Push successful.")
        return True
    except subprocess.CalledProcessError as e:
        print("Error: Command 'git push' failed.", file=sys.stderr)
        if "Authentication failed" in e.stderr:
            print("Git push failed due to an authentication error. Please check your GITHUB_TOKEN.", file=sys.stderr)
        else:
            print(e.stderr, file=sys.stderr)
        return False

def get_remote_tags_with_commits():
    """Returns a dictionary of remote tags and their corresponding commit SHAs."""
    try:
        result = subprocess.run(["git", "ls-remote", "--tags", "origin"], capture_output=True, text=True)
        if result.returncode != 0:
            return {}
        tags_with_commits = {}
        output = result.stdout.strip()
        if not output:
            return {}
        for line in output.split('\n'):
            parts = line.split('\t')
            if len(parts) == 2:
                commit_sha, tag_ref = parts
                tag_name = tag_ref.split('/')[-1]
                if not tag_name.endswith('^{}'):
                    tags_with_commits[tag_name] = commit_sha
        return tags_with_commits
    except Exception:
        return {}

def get_local_tags_for_commit(commit_sha):
    """Returns a list of local tags pointing to a specific commit."""
    try:
        result = subprocess.run(
            ["git", "tag", "--points-at", commit_sha],
            capture_output=True, text=True, check=True
        )
        tags = result.stdout.strip().split('\n')
        return [tag for tag in tags if tag]  # Filter out empty strings
    except subprocess.CalledProcessError:
        return []

def has_matching_tag(tag_name):
    """Checks if a local Git tag with the given name exists."""
    try:
        result = subprocess.run(["git", "tag", "--list", tag_name], capture_output=True, text=True)
        return tag_name in result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print("ERROR: Failed to execute 'git tag' command.", file=sys.stderr)
        print(f"\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

def is_tag_pushed(tag_name):
    """Checks if a specific tag has been pushed to the remote."""
    try:
        result = subprocess.run(["git", "ls-remote", "--tags", "origin", tag_name], capture_output=True, text=True, check=True)
        return tag_name in result.stdout
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to check remote for tag '{tag_name}'.", file=sys.stderr)
        print(f"\n{e.stderr}", file=sys.stderr)
        return False

def initialize_git_repo():
    """Initializes a git repository if one doesn't exist."""
    git_dir = Path.cwd() / ".git"
    if not git_dir.exists():
        print("[GIT] This is not a Git repository. Initializing...")
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit: Project setup"], check=True, capture_output=True)
        print("[GIT] Repository initialized and initial commit created.")
