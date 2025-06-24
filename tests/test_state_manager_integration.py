import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dw6.state_manager import WorkflowManager

class TestWorkflowManagerIntegration(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory to simulate the project structure."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create dummy files and directories
        os.makedirs("docs", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("deliverables/coding", exist_ok=True)
        Path("docs/WORKFLOW_MASTER.md").touch()
        Path("docs/PROJECT_REQUIREMENTS.md").touch()

    def tearDown(self):
        """Clean up the temporary directory."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    @patch('dw6.state_manager.WorkflowState')
    @patch('dw6.git_handler.get_changes_since_last_commit')
    def test_approve_coder_stage_creates_deliverable(self, mock_get_changes, mock_WorkflowState):
        """Ensure approving Coder stage generates a deliverable without altering the real state."""
        # Arrange
        mock_state_instance = mock_WorkflowState.return_value
        mock_state_instance.get.return_value = 'Coder'
        mock_get_changes.return_value = (['src/main.py'], 'diff --git a/src/main.py b/src/main.py')
        
        manager = WorkflowManager()
        manager.current_stage = 'Coder'

        # Act
        manager.approve()

        # Assert
        deliverable_path = Path("deliverables/coding/coder_deliverable.md")
        self.assertTrue(deliverable_path.exists())
        mock_state_instance.save.assert_called_once()

if __name__ == '__main__':
    unittest.main()
