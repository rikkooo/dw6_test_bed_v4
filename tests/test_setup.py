import os
import subprocess
import sys
import unittest
from unittest.mock import patch, call

# Add src to path to allow importing setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dw6 import setup

class TestSetup(unittest.TestCase):

    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_create_venv_does_not_exist(self, mock_run, mock_exists):
        """Test venv creation when it doesn't exist."""
        mock_exists.return_value = False
        project_dir = '/fake/project'
        
        setup.create_venv(project_dir)
        
        venv_path = os.path.join(project_dir, 'venv')
        expected_command = [sys.executable, '-m', 'venv', venv_path]
        mock_run.assert_called_once_with(expected_command, check=True, capture_output=True, text=True, cwd=None)

    @patch('os.path.exists')
    @patch('subprocess.run')
    def test_create_venv_exists(self, mock_run, mock_exists):
        """Test venv creation is skipped when it exists."""
        mock_exists.return_value = True
        project_dir = '/fake/project'
        
        setup.create_venv(project_dir)
        
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_install_dependencies(self, mock_run):
        """Test that pip install is called correctly."""
        project_dir = '/fake/project'
        venv_path = os.path.join(project_dir, 'venv')
        pip_executable = os.path.join(venv_path, 'bin', 'pip')
        
        setup.install_dependencies(project_dir)
        
        expected_command = [pip_executable, 'install', '-e', f'{project_dir}[test]']
        mock_run.assert_called_once_with(expected_command, check=True, capture_output=True, text=True, cwd=project_dir)

if __name__ == '__main__':
    unittest.main()
