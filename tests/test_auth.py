import unittest
from docuhub.storagenode.auth import AuthHelper

class MockAuth:
    def __init__(self, auth_type, token=None, ssh_key=None):
        self.auth_type = auth_type
        self.token = token
        self.ssh_key = ssh_key

class TestAuthHelper(unittest.TestCase):
    def test_token_auth(self):
        auth = MockAuth(auth_type=1, token="my-secret-token")
        helper = AuthHelper(auth)
        url = "https://github.com/user/repo.git"
        auth_url = helper.get_authenticated_url(url)
        self.assertEqual(auth_url, "https://my-secret-token@github.com/user/repo.git")

    def test_no_auth(self):
        auth = MockAuth(auth_type=0)
        helper = AuthHelper(auth)
        url = "https://github.com/user/repo.git"
        auth_url = helper.get_authenticated_url(url)
        self.assertEqual(auth_url, url)

    def test_ssh_env(self):
        ssh_key = "ssh-rsa AAAAB3Nza..."
        auth = MockAuth(auth_type=2, ssh_key=ssh_key)
        helper = AuthHelper(auth)
        env = helper.get_env()
        self.assertIn("GIT_SSH_COMMAND", env)
        self.assertIn("-i ", env["GIT_SSH_COMMAND"])
        
        # Check if file exists and content is correct
        key_file = env["GIT_SSH_COMMAND"].split("-i ")[1].split(" ")[0]
        with open(key_file, 'r') as f:
            content = f.read()
            self.assertEqual(content.strip(), ssh_key)
        
        helper.cleanup()
        import os
        self.assertFalse(os.path.exists(key_file))

if __name__ == "__main__":
    unittest.main()
