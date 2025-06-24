# dw6/main.py
import argparse
import sys
from dw6.state_manager import StateManager

def main():
    """Main entry point for the DW6 CLI."""
    parser = argparse.ArgumentParser(description="DW6 Workflow Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Review command
    subparsers.add_parser("review", help="Review the changes for the current stage.")
    
    # Approve command
    subparsers.add_parser("approve", help="Approve the current stage and move to the next.")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    manager = StateManager()

    if args.command == "review":
        manager.review()
    elif args.command == "approve":
        manager.approve()

if __name__ == "__main__":
    main()
