import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dw6.state_manager import WorkflowManager

class TestValidatorStage(unittest.TestCase):

    @patch('dw6.state_manager.subprocess.run')
    @patch('dw6.state_manager.Path.glob')
    @patch('dw6.state_manager.Path.is_dir')
    def test_validator_fails_with_no_test_files(self, mock_is_dir, mock_glob, mock_run):
        """Test that the Validator stage fails if no test files are found."""
        # Arrange
        mock_is_dir.return_value = True
        mock_glob.return_value = []
        manager = WorkflowManager()
        manager.current_stage = 'Validator'

        # Act & Assert
        with self.assertRaises(SystemExit) as cm:
            manager._validate_tests()
        self.assertEqual(cm.exception.code, 1)

    @patch('dw6.state_manager.subprocess.run')
    @patch('dw6.state_manager.Path.glob')
    @patch('dw6.state_manager.Path.is_dir')
    def test_validator_fails_with_no_tests_collected(self, mock_is_dir, mock_glob, mock_run):
        """Test that the Validator stage fails if pytest collects no tests."""
        # Arrange
        mock_is_dir.return_value = True
        mock_glob.return_value = ['test_placeholder.py']
        mock_run.return_value = MagicMock(stdout='collected 0 items', returncode=0)
        manager = WorkflowManager()
        manager.current_stage = 'Validator'

        # Act & Assert
        with self.assertRaises(SystemExit) as cm:
            manager._validate_tests()
        self.assertEqual(cm.exception.code, 1)

    @patch('dw6.state_manager.subprocess.run')
    @patch('dw6.state_manager.Path.glob')
    @patch('dw6.state_manager.Path.is_dir')
    def test_validator_succeeds_with_tests(self, mock_is_dir, mock_glob, mock_run):
        """Test that the Validator stage succeeds when tests are found and pass."""
        # Arrange
        mock_is_dir.return_value = True
        mock_glob.return_value = ['test_placeholder.py']
        # Mock the collect call and the run call separately
        mock_run.side_effect = [
            MagicMock(stdout='collected 1 items', returncode=0),
            MagicMock(stdout='== 1 passed in 0.01s ==', returncode=0)
        ]
        manager = WorkflowManager()
        manager.current_stage = 'Validator'

        # Act
        manager._validate_tests()

        # Assert
        self.assertEqual(mock_run.call_count, 2)

if __name__ == '__main__':
    unittest.main()
