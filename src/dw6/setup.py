import os
import subprocess
import sys

def run_command(command, cwd=None):
    """Runs a command and exits if it fails."""
    print(f"Executing: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=cwd)
        print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed: {' '.join(command)}", file=sys.stderr)
        print(f"STDOUT: {e.stdout}", file=sys.stderr)
        print(f"STDERR: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def create_venv(project_dir):
    """Creates a Python virtual environment."""
    print("\n--- Creating Virtual Environment ---")
    venv_path = os.path.join(project_dir, "venv")
    if os.path.exists(venv_path):
        print(f"Virtual environment already exists at {venv_path}. Skipping creation.")
        return
    
    run_command([sys.executable, "-m", "venv", venv_path])
    print(f"Successfully created virtual environment at {venv_path}")

def install_dependencies(project_dir):
    """Installs project dependencies from pyproject.toml."""
    print("\n--- Installing Dependencies ---")
    venv_path = os.path.join(project_dir, "venv")
    pip_executable = os.path.join(venv_path, "bin", "pip")
    
    # With a src layout and pyproject.toml, 'pip install -e .[test]' from the root is the standard.
    run_command([pip_executable, "install", "-e", f"{project_dir}[test]"], cwd=project_dir)
    print("Successfully installed project dependencies.")

def main():
    """Main function to set up the project environment."""
    project_dir = os.getcwd()
    print(f"--- Starting Environment Setup for {os.path.basename(project_dir)} ---")
    
    create_venv(project_dir)
    install_dependencies(project_dir)
    
    print("\n--- Environment Setup Complete ---")
    print("Virtual environment is ready and dependencies are installed.")

if __name__ == "__main__":
    main()
