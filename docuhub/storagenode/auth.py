import os
import tempfile
from urllib.parse import urlparse, urlunparse

class AuthHelper:
    def __init__(self, auth_req):
        """
        auth_req is an instance of repository_pb2.AuthCredentials
        """
        self.auth = auth_req
        self._ssh_key_file = None

    def get_authenticated_url(self, remote_url):
        if not self.auth or self.auth.auth_type != 1:  # TOKEN
            return remote_url

        parsed = urlparse(remote_url)
        if not self.auth.token:
            return remote_url

        # For GitHub/GitLab, token can be used as 'https://<token>@github.com/reponame.git'
        # Or 'https://x-access-token:<token>@github.com/reponame.git'
        # We'll use the common '<token>@' format
        netloc = f"{self.auth.token}@{parsed.netloc}"
        
        return urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    def get_env(self):
        if not self.auth or self.auth.auth_type != 2:  # SSH
            return {}

        if not self.auth.ssh_key:
            return {}

        # Create a temporary file for the SSH key
        # Note: In a production environment, you'd want to handle this more securely
        # and ensure cleanup.
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(self.auth.ssh_key)
            if not self.auth.ssh_key.endswith('\n'):
                f.write('\n')
        
        os.chmod(path, 0o600)
        self._ssh_key_file = path

        # Set GIT_SSH_COMMAND to use this key and skip host key checking for convenience
        # (WARNING: Skipping host key checking might be a security risk)
        ssh_cmd = f"ssh -i {path} -o StrictHostKeyChecking=no"
        return {"GIT_SSH_COMMAND": ssh_cmd}

    def cleanup(self):
        if self._ssh_key_file and os.path.exists(self._ssh_key_file):
            try:
                os.remove(self._ssh_key_file)
            except OSError:
                pass
            self._ssh_key_file = None
