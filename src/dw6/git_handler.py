import sys
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
import git
from dw6.config import LAST_COMMIT_FILE

# Load environment variables from .env file
load_dotenv()

# --- Helper Functions ---

def get_repo():
    """Initializes and returns a git.Repo object, handling errors gracefully."""
    try:
        return git.Repo(Path.cwd(), search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        print("ERROR: Not a Git repository. Please run 'git init' to start.", file=sys.stderr)
        sys.exit(1)
    except git.NoSuchPathError:
        print(f"ERROR: The path '{Path.cwd()}' does not exist.", file=sys.stderr)
        sys.exit(1)

def _get_authenticated_remote_url(repo):
    """Constructs a remote URL with the GITHUB_TOKEN for authentication."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not found in environment variables or .env file.", file=sys.stderr)
        print("Please create a .env file with your GITHUB_TOKEN to push changes.", file=sys.stderr)
        sys.exit(1)

    try:
        remote_url = repo.remotes.origin.url
        parsed_url = urlparse(remote_url)
        # The token is injected into the netloc for https authentication
        authenticated_url = parsed_url._replace(netloc=f"{token}@{parsed_url.netloc}").geturl()
        return authenticated_url
    except IndexError:
        print("ERROR: 'origin' remote not found. Please add a remote repository.", file=sys.stderr)
        sys.exit(1)

# --- Core Git Functions (using GitPython) ---

def is_github_token_present():
    """Checks for the GITHUB_TOKEN and returns True if present, False otherwise."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not found in environment variables or .env file.", file=sys.stderr)
        print("Please create a .env file in the project root with your GITHUB_TOKEN to proceed.", file=sys.stderr)
        print("Example: GITHUB_TOKEN=ghp_YourTokenHere", file=sys.stderr)
        return False
    return True

def is_working_directory_clean():
    """Checks if the Git working directory is clean (no uncommitted changes)."""
    repo = get_repo()
    return not repo.is_dirty(untracked_files=True)

def get_current_commit_sha():
    """Returns the SHA of the current HEAD commit."""
    repo = get_repo()
    return repo.head.commit.hexsha

def has_new_commits():
    """Checks if there are new commits since the last recorded SHA in the tracking file."""
    if not LAST_COMMIT_FILE.exists():
        print(f"ERROR: Tracking file not found at: {LAST_COMMIT_FILE}", file=sys.stderr)
        sys.exit(1)

    last_commit_sha = LAST_COMMIT_FILE.read_text().strip()
    return last_commit_sha != get_current_commit_sha()

def get_commit_stats():
    """Returns statistics about the changes (files, insertions, deletions) since the last approved commit."""
    repo = get_repo()
    if not LAST_COMMIT_FILE.exists():
        return None

    last_commit_sha = LAST_COMMIT_FILE.read_text().strip()
    current_commit_sha = repo.head.commit.hexsha

    if last_commit_sha == current_commit_sha:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}

    try:
        diff_summary = repo.git.diff('--shortstat', last_commit_sha, current_commit_sha)
        
        files_changed = 0
        insertions = 0
        deletions = 0

        parts = diff_summary.strip().split(', ')
        for part in parts:
            if 'file' in part:
                files_changed = int(part.split()[0])
            elif 'insertion' in part:
                insertions = int(part.split()[0])
            elif 'deletion' in part:
                deletions = int(part.split()[0])

        return {"files_changed": files_changed, "insertions": insertions, "deletions": deletions}
    except git.GitCommandError:
        return None

def get_remote_url():
    """Returns the URL of the 'origin' remote."""
    repo = get_repo()
    try:
        return repo.remotes.origin.url
    except IndexError:
        return None

def get_repo_info_from_remote_url(remote_url):
    """Extracts the owner and repo name from a GitHub remote URL."""
    if not remote_url:
        return None, None
    path = urlparse(remote_url).path
    if path.endswith('.git'):
        path = path[:-4]
    parts = path.strip('/').split('/')
    return (parts[-2], parts[-1]) if len(parts) >= 2 else (None, None)

def add_commit(message):
    """Adds all changes and creates a commit."""
    repo = get_repo()
    if not repo.is_dirty(untracked_files=True):
        print("[GIT] No changes to commit.")
        return
    try:
        repo.git.add(A=True)
        repo.index.commit(message)
        print(f"[GIT] Committed changes with message: '{message}'")
    except git.GitCommandError as e:
        print(f"ERROR: Failed to create commit.\n{e}", file=sys.stderr)

def push_to_remote():
    """Pushes the current branch to the remote 'origin' using token authentication."""
    repo = get_repo()
    authenticated_url = _get_authenticated_remote_url(repo)
    try:
        repo.remotes.origin.push(repo.head.ref.name, authenticated_url)
        print("[GIT] Successfully pushed changes to remote.")
    except git.GitCommandError as e:
        print(f"ERROR: Failed to push to remote.\n{e}", file=sys.stderr)
        sys.exit(1)

def create_and_push_tag(tag_name, message):
    """Creates a new tag and pushes it to the remote using token authentication."""
    repo = get_repo()
    authenticated_url = _get_authenticated_remote_url(repo)
    try:
        new_tag = repo.create_tag(tag_name, message=message)
        print(f"[GIT] Created tag '{tag_name}'.")
        repo.remotes.origin.push(new_tag, authenticated_url)
        print(f"[GIT] Pushed tag '{tag_name}' to remote.")
    except git.GitCommandError as e:
        print(f"ERROR: Failed to create or push tag '{tag_name}'.\n{e}", file=sys.stderr)
        sys.exit(1)

def get_all_tags_with_commits():
    """Returns a dictionary of all local tags and their associated commit SHAs."""
    repo = get_repo()
    return {tag.name: tag.commit.hexsha for tag in repo.tags}

def get_local_tags_for_commit(commit_sha):
    """Returns a list of local tags pointing to a specific commit."""
    repo = get_repo()
    return [tag.name for tag in repo.tags if tag.commit.hexsha == commit_sha]

def has_matching_tag(tag_name):
    """Checks if a local Git tag with the given name exists."""
    repo = get_repo()
    return any(tag.name == tag_name for tag in repo.tags)

def is_tag_pushed(tag_name):
    """Checks if a specific tag has been pushed to the remote."""
    repo = get_repo()
    try:
        # This is a simplification. A more robust check would involve fetching first.
        return any(tag_name in ref.name for ref in repo.remotes.origin.refs)
    except IndexError:
        return False  # No 'origin' remote

def initialize_git_repo():
    """Initializes a git repository if one doesn't exist."""
    if not (Path.cwd() / ".git").exists():
        print("[GIT] This is not a Git repository. Initializing...")
        repo = git.Repo.init(Path.cwd())
        # Create an initial commit because some operations require it
        repo.index.commit("Initial commit: Project setup")
        print("[GIT] Repository initialized and initial commit created.")

def get_latest_commit_hash(branch='main'):
    """Returns the hash of the latest commit on the specified local branch."""
    repo = get_repo()
    try:
        return repo.heads[branch].commit.hexsha
    except IndexError:
        print(f"ERROR: Branch '{branch}' not found.", file=sys.stderr)
        sys.exit(1)

def get_remote_tags_with_commits():
    """Returns a dictionary of remote tags and their corresponding commit SHAs after fetching."""
    repo = get_repo()
    if not is_github_token_present():
        sys.exit(1)
    authenticated_url = _get_authenticated_remote_url(repo)
    try:
        # Fetch tags from the authenticated remote. Use --prune to remove stale remote-tracking references
        repo.git.fetch(authenticated_url, tags=True, prune=True)
        # Now, local repo.tags should be updated with remote tags
        return {tag.name: tag.commit.hexsha for tag in repo.tags}
    except git.GitCommandError as e:
        print(f"ERROR: Could not fetch remote tags.\n{e}", file=sys.stderr)
        return {}

def get_last_commit_sha():
    """Reads the last recorded commit SHA from the tracking file."""
    if LAST_COMMIT_FILE.exists():
        return LAST_COMMIT_FILE.read_text().strip()
    return None

def save_current_commit_sha():
    """Saves the current commit SHA to the tracking file."""
    sha = get_current_commit_sha()
    LAST_COMMIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_COMMIT_FILE.write_text(sha)
    print(f"[GIT] Saved current commit SHA to tracking file: {sha[:7]}")

def commit_changes(requirement_id):
    """Adds and commits all changes with a standardized message."""
    print("[GIT] Committing approved code...")
    commit_message = f"feat(req-{requirement_id}): Coder stage submission for requirement {requirement_id}"
    add_commit(commit_message)

def add_commit_files(message, files):
    """Adds specific files and creates a commit."""
    repo = get_repo()
    try:
        repo.index.add(files)
        # Check if the index has changes compared to the last commit
        if repo.index.diff(repo.head.commit):
            repo.index.commit(message)
            print(f"[GIT] Committed changes for files {files} with message: '{message}'")
        else:
            print(f"[GIT] No changes to commit for files: {files}")
    except git.GitCommandError as e:
        print(f"ERROR: Failed to create commit for files {files}.\n{e}", file=sys.stderr)

def push_to_remote(branch='main'):
    """Pushes the specified branch and all tags to the 'origin' remote using token authentication."""
    repo = get_repo()
    if not is_github_token_present():
        sys.exit(1)
    authenticated_url = _get_authenticated_remote_url(repo)
    try:
        repo.git.push(authenticated_url, branch, '--tags', '--force')
        print(f"[GIT] Successfully pushed branch '{branch}' and all tags to remote.")
    except git.GitCommandError as e:
        print(f"ERROR: Failed to push to remote.\n{e}", file=sys.stderr)
        sys.exit(1)

def commit_and_push_deliverable(deliverable_path, stage_name, cycle):
    """Adds, commits, and pushes a single deliverable file."""
    commit_message = f"docs(cycle-{cycle}): Add {stage_name.lower()} deliverable for cycle {cycle}"
    
    print(f"[GIT] Committing deliverable: {deliverable_path}")
    add_commit_files(commit_message, [deliverable_path])
    
    # Push the changes
    print("[GIT] Pushing deliverable to remote...")
    push_to_remote()

def get_changes_since_last_commit():
    """Returns a list of changed files and the diff string since the last commit."""
    repo = get_repo()
    last_commit_sha = get_last_commit_sha()
    if not last_commit_sha:
        print("ERROR: Could not find the last commit SHA.", file=sys.stderr)
        return [], ""

    try:
        from_commit = repo.commit(last_commit_sha)
        diff_index = from_commit.diff(repo.head.commit)
        
        changed_files = [diff.b_path for diff in diff_index]
        diff_string = repo.git.diff(last_commit_sha, repo.head.commit)
        
        return changed_files, diff_string
    except git.GitCommandError as e:
        print(f"ERROR: Could not get changes since {last_commit_sha[:7]}.\n{e}", file=sys.stderr)
        return [], ""

def get_diff(from_commit, to_commit):
    """Returns the diff between two commits as a string."""
    repo = get_repo()
    try:
        return repo.git.diff(from_commit, to_commit)
    except git.GitCommandError as e:
        print(f"ERROR: Could not get diff between {from_commit} and {to_commit}.\n{e}", file=sys.stderr)
        return ""
