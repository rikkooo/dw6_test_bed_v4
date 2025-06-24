import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import os
from datetime import datetime
from dw6.state_manager import WorkflowManager
from dw6.templates import TECHNICAL_SPECIFICATION_TEMPLATE

def main():
    parser = argparse.ArgumentParser(
        description="DW5-Preview: A modern, robust development workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'approve' command
    approve_parser = subparsers.add_parser(
        "approve", help="Approve the current stage and advance to the next."
    )

    # 'status' command
    status_parser = subparsers.add_parser(
        "status", help="Display the current status of the workflow."
    )

    # 'engineer' command group
    engineer_parser = subparsers.add_parser(
        "engineer", help="Commands for the engineering stage."
    )
    engineer_subparsers = engineer_parser.add_subparsers(dest="engineer_command", required=True)

    # 'engineer start' command
    engineer_start_parser = engineer_subparsers.add_parser(
        "start", help="Start the engineering stage by creating the technical specification document."
    )

    args = parser.parse_args()
    manager = WorkflowManager()

    if args.command == "approve":
        manager.approve()
    elif args.command == "status":
        manager.get_status()
    elif args.command == "engineer":
        if args.engineer_command == "start":
            handle_engineer_start(manager)

def handle_engineer_start(manager):
    """
    Handles the logic for the 'engineer start' command.
    """
    state = manager.get_state()
    project_name = os.path.basename(os.getcwd())
    cycle_number = state['Cycle']
    
    spec_dir = "deliverables/engineering"
    spec_filename = f"cycle_{cycle_number}_technical_specification.md"
    spec_filepath = os.path.join(spec_dir, spec_filename)

    if os.path.exists(spec_filepath):
        print(f"Error: Technical specification file already exists at '{spec_filepath}'.")
        return

    os.makedirs(spec_dir, exist_ok=True)

    content = TECHNICAL_SPECIFICATION_TEMPLATE.format(
        project_name=project_name,
        cycle_number=cycle_number,
        date=datetime.now().strftime("%Y-%m-%d")
    )

    with open(spec_filepath, "w") as f:
        f.write(content)

    print(f"Successfully created technical specification at '{spec_filepath}'.")
    print("You can now begin detailing the project requirements in this file.")


if __name__ == "__main__":
    main()
