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

class WorkflowManager:
    def __init__(self):
        self.state = WorkflowState()
        self.current_stage = self.state.get("CurrentStage")
        if self.current_stage not in STAGES:
            print(f"Error: Unknown stage '{self.current_stage}' in {MASTER_FILE}", file=sys.stderr)
            sys.exit(1)

    def get_status(self):
        print(f"Current Stage: {self.current_stage}")
        
        # Provide guidance on what to do next
        if self.current_stage == "Engineer":
            print("Next Step: Finalize the technical specification in 'deliverables/engineering/'.")
            print("Once complete, run 'dw6 approve' to move to the Researcher stage.")
        elif self.current_stage == "Researcher":
            print("Next Step: Complete your research and document it in 'deliverables/Researcher/'.")
            print("Once complete, run 'dw6 approve' to move to the Coder stage.")
        elif self.current_stage == "Coder":
            print("Next Step: Implement the required code changes.")
            print("Commit your changes and then run 'dw6 approve' to move to the Validator stage.")
        elif self.current_stage == "Validator":
            print("Next Step: Write and run tests to ensure code quality and coverage.")
            print("Once tests are passing, run 'dw6 approve' to move to the Deployer stage.")
        elif self.current_stage == "Deployer":
            print("Next Step: Tag the release and deploy the project.")
            print("Once deployed, run 'dw6 approve' to complete the cycle.")

        # Show git status
        print("\n--- Git Status ---")
        subprocess.run(["git", "status", "-s"])

    def get_current_stage_name(self):
        return self.current_stage

    def get_state(self):
        return self.state.data

    def approve(self):
        if not git_handler.is_working_directory_clean():
            print("ERROR: Uncommitted changes detected in the working directory.", file=sys.stderr)
            print("Please commit or stash your changes before approving the stage.", file=sys.stderr)
            sys.exit(1)

        print(f"--- Attempting to approve stage: {self.current_stage} ---")
        approved_stage = self.current_stage
        self._validate_stage_completion()
        self._run_pre_transition_actions()

        if self.current_stage == "Deployer":
            self._complete_requirement_cycle()
            next_stage_index = 0
        else:
            current_index = STAGES.index(self.current_stage)
            next_stage_index = current_index + 1
        
        self.current_stage = STAGES[next_stage_index]
        self.state.set("CurrentStage", self.current_stage)
        self.state.save()
        
        self._run_post_transition_actions()
        print(f"--- Stage '{approved_stage}' approved. New stage is '{self.current_stage}'. ---")

    def _validate_stage_completion(self):
        print("Validating current stage before approval...")
        
        deliverable_dir = DELIVERABLE_PATHS.get(self.current_stage)
        if deliverable_dir:
            if not os.path.exists(deliverable_dir) or not os.listdir(deliverable_dir):
                print(f"ERROR: No deliverable found for stage '{self.current_stage}'.", file=sys.stderr)
                print(f"Please create a deliverable file in the '{deliverable_dir}' directory.", file=sys.stderr)
                sys.exit(1)
            print(f"Deliverable for stage '{self.current_stage}' found.")

        if self.current_stage == "Coder":
            stats = git_handler.get_commit_stats()
            if not stats or (stats['insertions'] + stats['deletions']) < 10:
                print("ERROR: Not enough meaningful changes detected.", file=sys.stderr)
                if stats:
                    print(f"  - Files changed: {stats['files_changed']}", file=sys.stderr)
                    print(f"  - Lines added:   {stats['insertions']}", file=sys.stderr)
                    print(f"  - Lines removed: {stats['deletions']}", file=sys.stderr)
                print("Please commit at least 10 lines of code changes before requesting approval.", file=sys.stderr)
                sys.exit(1)
            print("Meaningful code changes detected.")

        elif self.current_stage == "Validator":
            print("Validating testing stage with coverage...")
            try:
                # Run pytest with coverage. Fail if coverage is below 1%.
                command = ["./venv/bin/pytest", "--cov-fail-under=1", "--cov-report=term-missing", "--cov=dw6", "tests"]
                print(f"Running command: {' '.join(command)}")
                result = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                print("Pytest execution and coverage check successful.")
            except subprocess.CalledProcessError as e:
                print("ERROR: Pytest execution or coverage check failed.", file=sys.stderr)
                print(e.stdout)
                print(e.stderr, file=sys.stderr)
                sys.exit(1)
        
        elif self.current_stage == "Deployer":
            # 1. Ensure a deliverable exists
            deliverable_dir = DELIVERABLE_PATHS.get(self.current_stage)
            if deliverable_dir:
                if not os.path.exists(deliverable_dir) or not os.listdir(deliverable_dir):
                    print(f"ERROR: No deliverable found for stage '{self.current_stage}'.", file=sys.stderr)
                    print(f"Please create a deliverable file in the '{deliverable_dir}' directory.", file=sys.stderr)
                    sys.exit(1)
                print(f"Deliverable for stage '{self.current_stage}' found.")

            # 2. Validate that the latest commit is tagged
            print("Validating deployment: Checking for a version tag...")
            latest_commit = git_handler.get_current_commit_sha()
            
            tag_found = False
            # First, try to check for a pushed remote tag
            remote_tags = git_handler.get_remote_tags_with_commits()
            if remote_tags:
                if latest_commit in remote_tags.values():
                    matching_tags = [tag for tag, commit in remote_tags.items() if commit == latest_commit]
                    print(f"Deployment validation successful: Latest commit is tagged on remote with: {', '.join(matching_tags)}")
                    tag_found = True
                else:
                    # Remote exists, but commit is not tagged. This is a failure.
                    print(f"ERROR: The latest commit ({latest_commit[:7]}) is not tagged on the remote.", file=sys.stderr)
                    print("Please create and push a new version tag for the latest commit.", file=sys.stderr)
                    sys.exit(1)
            
            # If no remote tag was found, check for a local tag
            if not tag_found:
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
