import re
import sys
import os
import subprocess

from datetime import datetime, timezone

# These would typically be in dw6/config.py
MASTER_FILE = "docs/WORKFLOW_MASTER.md"
REQUIREMENTS_FILE = "docs/PROJECT_REQUIREMENTS.md"
APPROVAL_FILE = "logs/approvals.log"
STAGES = ["Engineer", "Researcher", "Coder", "Validator", "Deployer"]
DELIVERABLE_PATHS = {
    "Engineer": "deliverables/engineering",
    "Coder": "deliverables/coding",
    "Researcher": "deliverables/Researcher", # Corrected path to match setup script
    "Validator": "deliverables/testing",
    "Deployer": "deliverables/deployment",
}

# Assuming git_handler provides these functions
from dw6 import git_handler

class WorkflowManager:
    def __init__(self):
        self.state = WorkflowState()
        self.current_stage = self.state.get("CurrentStage")

    def get_state(self):
        return self.state.data

    def approve(self):
        print(f"--- Approving Stage: {self.current_stage} ---")
        self._validate_stage()
        self._run_pre_transition_actions()
        self._transition_to_next_stage()
        self._run_post_transition_actions()
        self.state.save()
        print(f"--- Stage {self.current_stage} Approved. New Stage: {self.state.get('CurrentStage')} ---")

    def get_status(self):
        print("--- DW6 Workflow Status ---")
        for key, value in self.state.data.items():
            print(f"- {key}: {value}")
        print("---------------------------")

    def _transition_to_next_stage(self):
        current_index = STAGES.index(self.current_stage)
        if self.current_stage == "Deployer":
            self._complete_requirement_cycle()
            next_stage = "Engineer"
        else:
            next_stage = STAGES[current_index + 1]
        self.state.set("CurrentStage", next_stage)
        self.current_stage = next_stage

    def _validate_stage(self):
        print(f"Validating deliverables for stage: {self.current_stage}")
        if self.current_stage == "Validator":
            print("Running tests...")
            # The command needs to be adapted for the venv
            venv_python = os.path.join(os.getcwd(), "venv", "bin", "python")
            result = subprocess.run([venv_python, "-m", "pytest"], capture_output=True, text=True)
            if result.returncode != 0:
                print("ERROR: Pytest validation failed.", file=sys.stderr)
                print(result.stdout, file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                sys.exit(1)
            print("Pytest validation successful.")

        elif self.current_stage == "Deployer":
            print("Validating deployment...")
            latest_commit = git_handler.get_latest_commit_sha()
            remote_tags = git_handler.get_remote_tags_for_commit(latest_commit)
            if remote_tags:
                print(f"Deployment validation successful: Latest commit is tagged with: {', '.join(remote_tags)}.")
            else:
                print("Warning: Could not retrieve remote tags. Falling back to local tag check.")
                local_tags = git_handler.get_local_tags_for_commit(latest_commit)
                if not local_tags:
                    print(f"ERROR: The latest commit ({latest_commit[:7]}) has not been tagged.", file=sys.stderr)
                    print("No remote repository is configured or the tag has not been pushed.", file=sys.stderr)
                    print("Please tag the commit locally (e.g., 'git tag -a v1.0 -m \"Release 1.0\"').", file=sys.stderr)
                    sys.exit(1)
                print(f"Deployment validation successful: Latest commit is tagged locally with: {', '.join(local_tags)}.")

        print("Stage validation successful.")

    def _run_pre_transition_actions(self):
        pass

    def _run_post_transition_actions(self):
        if self.current_stage == "Coder":
            git_handler.save_current_commit_sha()

    def _complete_requirement_cycle(self):
        req_id = int(self.state.get("RequirementPointer"))
        
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(APPROVAL_FILE, "a") as f:
            f.write(f"Requirement {req_id} approved at {timestamp}\n")
        print(f"[INFO] Logged approval for Requirement ID {req_id}.")
        
        if os.path.exists(REQUIREMENTS_FILE):
            lines = open(REQUIREMENTS_FILE, "r").read().splitlines()
            for i, line in enumerate(lines):
                if f"ID {req_id}" in line and "[ ]" in line:
                    lines[i] = line.replace("[ ]", "[x]", 1)
                    with open(REQUIREMENTS_FILE, "w") as f:
                        f.write("\n".join(lines) + "\n")
                    print(f"Updated checkbox for Req ID {req_id} in {REQUIREMENTS_FILE}")
                    break

        next_req_id = req_id + 1
        self.state.set("RequirementPointer", next_req_id)
        print(f"[INFO] Advanced to next requirement: {next_req_id}.")

class WorkflowState:
    def __init__(self):
        if not os.path.exists(MASTER_FILE):
            print(f"Error: Master workflow file not found at {MASTER_FILE}", file=sys.stderr)
            sys.exit(1)
        self.lines = open(MASTER_FILE, "r").read().splitlines()
        self.data = {}
        self._parse()

    def _parse(self):
        for line in self.lines:
            cleaned_line = line.strip()
            if cleaned_line.startswith("-"):
                cleaned_line = cleaned_line[1:].lstrip()
            
            if ":" in cleaned_line:
                key, value_part = cleaned_line.split(":", 1)
                value = value_part.split("#", 1)[0].strip()
                self.data[key.strip()] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = str(value)
        key_found = False
        for i, line in enumerate(self.lines):
            if line.strip().startswith(key + ":"):
                comment = ""
                if "#" in line:
                    comment = " #" + line.split("#", 1)[1].strip()
                self.lines[i] = f"{key}: {value}{comment}"
                key_found = True
                return
        if not key_found:
            self.lines.append(f"{key}: {value}")

    def save(self):
        with open(MASTER_FILE, "w") as f:
            f.write("\n".join(self.lines) + "\n")

class StateManager:
    def __init__(self):
        self.state = WorkflowState()
        self.current_stage = self.state.get("CurrentStage")
        self.repo = git_handler.get_repo()

    def review(self):
        last_commit_sha = self.state.get("LastCommitSHA")
        current_commit_sha = git_handler.get_latest_commit_hash()
        
        if not last_commit_sha:
            print("No previous commit SHA found. Showing diff from initial commit.")
            last_commit_sha = git_handler.get_first_commit_hash()

        print(f"Comparing {self.current_stage} changes from {last_commit_sha[:7]} to {current_commit_sha[:7]}...")
        
        diff_output = git_handler.get_diff(last_commit_sha, current_commit_sha)
        print(diff_output)

    def approve(self):
        self._validate_stage()
        self._run_pre_transition_actions()
        
        current_stage_index = STAGES.index(self.current_stage)
        
        if current_stage_index == len(STAGES) - 1:
            self._complete_requirement_cycle()
            self.state.set("CurrentStage", STAGES[0])
        else:
            next_stage = STAGES[current_stage_index + 1]
            self.state.set("CurrentStage", next_stage)
        
        self.state.save()
        self._run_post_transition_actions()
        
        print(f"Approved. Moved to {self.state.get('CurrentStage')} stage.")

    def _validate_stage(self):
        print(f"Validating stage: {self.current_stage}")
        
        deliverable_path = DELIVERABLE_PATHS.get(self.current_stage)
        if not deliverable_path or not os.path.exists(deliverable_path) or not os.listdir(deliverable_path):
            print(f"ERROR: No deliverables found in {deliverable_path} for stage {self.current_stage}.", file=sys.stderr)
            sys.exit(1)
        
        print(f"Deliverables found in {deliverable_path}.")

        if self.current_stage == "Coder":
            last_commit_sha = self.state.get("LastCommitSHA")
            current_commit_sha = git_handler.get_latest_commit_hash()
            if last_commit_sha == current_commit_sha:
                print("ERROR: No new commits found for Coder stage.", file=sys.stderr)
                sys.exit(1)
            
            diff_output = git_handler.get_diff(last_commit_sha, current_commit_sha, "src/")
            if not diff_output.strip():
                print("ERROR: No meaningful code changes detected in 'src/' directory.", file=sys.stderr)
                sys.exit(1)
            
            print("Meaningful code changes detected.")

        elif self.current_stage == "Validator":
            print("Validating testing stage...")
            # This check requires a 'tests' directory and a virtual environment with pytest installed.
            if not os.path.exists("tests") or not os.listdir("tests"):
                print("ERROR: No tests found in the 'tests' directory. Stage validation failed.", file=sys.stderr)
                sys.exit(1)
            
            try:
                # Ensure the command is executable and the venv exists
                pytest_path = "./venv/bin/pytest"
                if not os.access(pytest_path, os.X_OK):
                    print(f"ERROR: '{pytest_path}' not found or not executable. Is the venv set up correctly?", file=sys.stderr)
                    sys.exit(1)

                command = [pytest_path, "tests"]
                print(f"Running command: {' '.join(command)}")
                result = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                print("Pytest execution successful.")
            except subprocess.CalledProcessError as e:
                print("ERROR: Pytest execution failed.", file=sys.stderr)
                print(e.stdout)
                print(e.stderr, file=sys.stderr)
                sys.exit(1)

        elif self.current_stage == "Deployer":
            print("Validating deployment stage...")
            latest_commit = git_handler.get_latest_commit_hash()
            
            remote_tags = git_handler.get_remote_tags_with_commits()
            if remote_tags:
                tagged_commits = [tag_commit for tag, tag_commit in remote_tags]
                if latest_commit not in tagged_commits:
                    print(f"ERROR: The latest commit ({latest_commit[:7]}) has not been tagged and pushed to the remote.", file=sys.stderr)
                    sys.exit(1)
                
                matching_tags = [tag for tag, tag_commit in remote_tags if tag_commit == latest_commit]
                print(f"Deployment validation successful: Latest commit is tagged on remote with: {', '.join(matching_tags)}.")
            else:
                print("WARNING: Could not retrieve remote tags. Falling back to local tag check.")
                local_tags = git_handler.get_local_tags_for_commit(latest_commit)
                if not local_tags:
                    print(f"ERROR: The latest commit ({latest_commit[:7]}) has not been tagged.", file=sys.stderr)
                    print("No remote repository is configured or the tag has not been pushed.", file=sys.stderr)
                    print("Please tag the commit locally (e.g., 'git tag -a v1.0 -m \"Release 1.0\"').", file=sys.stderr)
                    sys.exit(1)
                
                print(f"Deployment validation successful: Latest commit is tagged locally with: {', '.join(local_tags)}.")

        print("Stage validation successful.")

    def _run_pre_transition_actions(self):
        pass

    def _run_post_transition_actions(self):
        if self.current_stage == "Coder":
            git_handler.save_current_commit_sha()

    def _complete_requirement_cycle(self):
        req_id = int(self.state.get("RequirementPointer"))
        
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(APPROVAL_FILE, "a") as f:
            f.write(f"Requirement {req_id} approved at {timestamp}\n")
        print(f"[INFO] Logged approval for Requirement ID {req_id}.")
        
        if os.path.exists(REQUIREMENTS_FILE):
            lines = open(REQUIREMENTS_FILE, "r").read().splitlines()
            for i, line in enumerate(lines):
                if f"ID {req_id}" in line and "[ ]" in line:
                    lines[i] = line.replace("[ ]", "[x]", 1)
                    with open(REQUIREMENTS_FILE, "w") as f:
                        f.write("\n".join(lines) + "\n")
                    print(f"Updated checkbox for Req ID {req_id} in {REQUIREMENTS_FILE}")
                    break

        next_req_id = req_id + 1
        self.state.set("RequirementPointer", next_req_id)
        print(f"[INFO] Advanced to next requirement: {next_req_id}.")
