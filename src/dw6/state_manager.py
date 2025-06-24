import re
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from dw6 import git_handler

MASTER_FILE = "docs/WORKFLOW_MASTER.md"
REQUIREMENTS_FILE = "docs/PROJECT_REQUIREMENTS.md"
APPROVAL_FILE = "logs/approvals.log"
STAGES = ["Engineer", "Researcher", "Coder", "Validator", "Deployer"]
DELIVERABLE_PATHS = {
    "Engineer": "deliverables/engineering",
    "Coder": "deliverables/coding",
    "Researcher": "deliverables/Researcher",
    "Validator": "deliverables/testing",
    "Deployer": "deliverables/deployment",
}

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

    def _validate_stage(self):
        print(f"Validating deliverables for stage: {self.current_stage}")
        if self.current_stage == "Coder":
            self._generate_coder_deliverable()
        elif self.current_stage == "Validator":
            self._validate_tests()
        elif self.current_stage == "Deployer":
            self._validate_deployment()
        print("Stage validation successful.")

    def _generate_coder_deliverable(self):
        print("Generating Coder deliverable...")
        changed_files, diff_string = git_handler.get_changes_since_last_commit()
        if not changed_files:
            print("No changes detected since the start of the Coder stage.")
            return
        deliverable_path = Path("deliverables/coding/coder_deliverable.md")
        deliverable_path.parent.mkdir(parents=True, exist_ok=True)
        with open(deliverable_path, "w") as f:
            f.write("# Coder Deliverable\n\n")
            f.write("## Changed Files\n\n")
            for file_path in changed_files:
                f.write(f"- `{file_path}`\n")
            f.write("\n## Git Diff\n\n")
            f.write("```diff\n")
            f.write(diff_string)
            f.write("\n```")
        print(f"Coder deliverable created at: {deliverable_path}")

    def _validate_tests(self):
        print("Running test validation...")
        tests_dir = Path("tests")
        if not tests_dir.is_dir() or not any(tests_dir.glob("test_*.py")):
            print("ERROR: No test files found in the 'tests' directory.", file=sys.stderr)
            sys.exit(1)
        try:
            venv_python = os.path.join(os.getcwd(), "venv", "bin", "python")
            collect_result = subprocess.run([venv_python, "-m", "pytest", "--collect-only"], capture_output=True, text=True)
            if "no tests collected" in collect_result.stdout.lower():
                print("ERROR: Pytest collected no tests.", file=sys.stderr)
                print(collect_result.stdout, file=sys.stderr)
                sys.exit(1)
            match = re.search(r"collected (\d+) items", collect_result.stdout)
            if not match or int(match.group(1)) == 0:
                print("ERROR: Pytest collected no tests.", file=sys.stderr)
                print(collect_result.stdout, file=sys.stderr)
                sys.exit(1)
            print(f"Pytest collected {match.group(1)} tests. Running them now...")
            result = subprocess.run([venv_python, "-m", "pytest"], capture_output=True, text=True)
            if result.returncode != 0:
                print("Pytest validation failed:", file=sys.stderr)
                print(result.stdout, file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                sys.exit(1)
            print("Pytest validation successful.")
        except FileNotFoundError:
            print("ERROR: pytest command not found or venv is not set up correctly.", file=sys.stderr)
            sys.exit(1)

    def _validate_deployment(self):
        print("Validating deployment...")
        if not git_handler.is_github_token_present():
            sys.exit(1)
        latest_commit = git_handler.get_latest_commit_hash()
        all_remote_tags = git_handler.get_remote_tags_with_commits()
        if all_remote_tags is None:
            all_remote_tags = {}
        matching_tags = [tag for tag, commit in all_remote_tags.items() if commit == latest_commit]
        if not matching_tags:
            print("Warning: Could not retrieve remote tags. Falling back to local tag check.")
            local_tags = git_handler.get_local_tags_for_commit(latest_commit)
            if not local_tags:
                print(f"ERROR: The latest commit ({latest_commit[:7]}) has not been tagged.", file=sys.stderr)
                sys.exit(1)
            matching_tags = local_tags
        print(f"Deployment validation successful: Latest commit is tagged with: {', '.join(matching_tags)}.")
        print("Pushing changes to remote repository...")
        git_handler.push_to_remote()

    def _run_pre_transition_actions(self):
        pass

    def _run_post_transition_actions(self):
        if self.current_stage == "Coder":
            git_handler.save_current_commit_sha()

    def _transition_to_next_stage(self):
        current_index = STAGES.index(self.current_stage)
        if current_index == len(STAGES) - 1:
            self._complete_requirement_cycle()
            self.current_stage = STAGES[0]
        else:
            self.current_stage = STAGES[current_index + 1]
        self.state.set("CurrentStage", self.current_stage)

    def _complete_requirement_cycle(self):
        req_id = int(self.state.get("RequirementPointer"))
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(APPROVAL_FILE, "a") as f:
            f.write(f"Requirement {req_id} approved at {timestamp}\n")
        print(f"[INFO] Logged approval for Requirement ID {req_id}.")
        next_req_id = req_id + 1
        self.state.set("RequirementPointer", next_req_id)
        print(f"[INFO] Advanced to next requirement: {next_req_id}.")

class WorkflowState:
    def __init__(self):
        self.state_file = Path("logs/workflow_state.txt")
        self.data = {}
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                for line in f:
                    key, value = line.strip().split("=", 1)
                    self.data[key] = value
        else:
            self.initialize_state()

    def initialize_state(self):
        self.data = {
            "CurrentStage": "Engineer",
            "RequirementPointer": "1"
        }
        self.save()

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = str(value)

    def save(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            for key, value in self.data.items():
                f.write(f"{key}={value}\n")
