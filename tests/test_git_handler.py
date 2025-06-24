import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src to path to allow importing git_handler
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from dw6 import git_handler

class TestGitHandler(unittest.TestCase):

    @patch('os.getenv')
    def test_is_github_token_present_true(self, mock_getenv):
        """Test that token is found when present."""
        mock_getenv.return_value = 'ghp_fake_token'
        self.assertTrue(git_handler.is_github_token_present())

    @patch('os.getenv')
    def test_is_github_token_present_false(self, mock_getenv):
        """Test that token is not found when absent."""
        mock_getenv.return_value = None
        self.assertFalse(git_handler.is_github_token_present())

    @patch('dw6.git_handler.get_repo')
    @patch('dw6.git_handler.is_github_token_present')
    def test_push_to_remote(self, mock_is_token_present, mock_get_repo):
        """Test that push is called with the correct authenticated URL."""
        mock_is_token_present.return_value = True
        
        # Mock the repo and its remote URL
        mock_repo = MagicMock()
        mock_repo.remotes.origin.url = 'https://github.com/user/repo.git'
        mock_get_repo.return_value = mock_repo
        
        with patch('os.getenv', return_value='ghp_fake_token'):
            git_handler.push_to_remote()
        
        expected_url = 'https://ghp_fake_token@github.com/user/repo.git'
        mock_repo.git.push.assert_called_once_with(expected_url, 'main', '--tags', '--force')

if __name__ == '__main__':
    unittest.main()
