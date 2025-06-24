import sys
import os
import unittest
from unittest.mock import patch, mock_open
from pathlib import Path

# Add src to path to allow importing state_manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dw6.state_manager import WorkflowManager

class TestStateManager(unittest.TestCase):

    @patch('dw6.state_manager.git_handler.get_changes_since_last_commit')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_generate_coder_deliverable(self, mock_mkdir, mock_file, mock_get_changes):
        """Test that the coder deliverable is generated correctly."""
        # Arrange: Set up mock return values
        mock_changed_files = ['src/dw6/state_manager.py', 'src/dw6/git_handler.py']
        mock_diff = '--- a/src/dw6/git_handler.py\n+++ b/src/dw6/git_handler.py\n@@ -1,1 +1,1 @@...'
        mock_get_changes.return_value = (mock_changed_files, mock_diff)
        
        # Instantiate the manager and set the stage
        with patch('dw6.state_manager.WorkflowState.save'): # Mock save to avoid file system interaction
            manager = WorkflowManager()
        manager.current_stage = 'Coder'

        # Reset the mock to ignore the call made during initialization
        mock_file.reset_mock()

        # Act: Call the private method to generate the deliverable
        manager._generate_coder_deliverable()

        # Assert: Check that the mocks were called as expected
        mock_get_changes.assert_called_once()
        mock_file.assert_called_once_with(Path('deliverables/coding/coder_deliverable.md'), 'w')
        
        handle = mock_file()
        handle.write.assert_any_call('# Coder Deliverable\n\n')
        handle.write.assert_any_call('## Changed Files\n\n')
        handle.write.assert_any_call('- `src/dw6/state_manager.py`\n')
        handle.write.assert_any_call('```diff\n')
        handle.write.assert_any_call(mock_diff)

if __name__ == '__main__':
    unittest.main()
