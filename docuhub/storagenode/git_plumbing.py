import subprocess
import os


class GitPlumbing:
    def __init__(self, base_dir="/data/repo"):
        self.base_dir = base_dir

    def _run_git(self, repo_path, args, input=None):
        cmd = ["git", "-C", repo_path] + args
        result = subprocess.run(
            cmd,
            input=input,
            capture_output=True,
            text=False,  # Keep bytes for content handling
        )
        if result.returncode != 0:
            error_msg = result.stderr.decode("utf-8", errors="replace")
            raise Exception(f"Git command failed: {' '.join(cmd)}\nError: {error_msg}")
        return result.stdout

    def init_bare_repo(self, rel_path):
        full_path = os.path.join(self.base_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if not os.path.exists(full_path):
            subprocess.run(["git", "init", "--bare", full_path], check=True)
        return full_path

    def clone_repo(self, remote_url, rel_path):
        full_path = os.path.join(self.base_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if os.path.exists(full_path):
            # Already exists, we might want to fetch instead, but for initialization:
            return full_path

        subprocess.run(["git", "clone", "--bare", remote_url, full_path], check=True)
        return full_path

    def fork_repo(self, src_rel_path, dest_rel_path):
        src_path = os.path.join(self.base_dir, src_rel_path)
        dest_path = os.path.join(self.base_dir, dest_rel_path)

        if os.path.exists(dest_path):
            raise Exception(f"Destination path already exists: {dest_path}")

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        # Use cp -al for hardlink-based cloning (efficient)
        # On Mac, 'cp -l' might not be available or behaves differently.
        # For cross-platform/stable git-specific approach: git clone --shared or manual hardlinking of objects
        try:
            # We want to hardlink the objects directory specifically for performance
            # and copy the rest.
            subprocess.run(["cp", "-R", src_path, dest_path], check=True)
            # Alternatively, we could do a 'git clone --bare --shared' then 'git repack -a -d' or similar
            # But let's start with a simple copy and optimize if needed.
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to copy repository: {e}")

        return dest_path

    def hash_object(self, repo_path, content):
        output = self._run_git(
            repo_path, ["hash-object", "-w", "--stdin"], input=content
        )
        return output.decode("utf-8").strip()

    def update_ref(self, repo_path, ref, new_hash, old_hash=None):
        args = ["update-ref", ref, new_hash]
        if old_hash:
            args.append(old_hash)
        self._run_git(repo_path, args)

    def write_tree(self, repo_path, index_info):
        # index_info format: "100644 blob <hash>\t<path>"
        output = self._run_git(repo_path, ["mktree"], input=index_info.encode("utf-8"))
        return output.decode("utf-8").strip()

    def commit_tree(
        self,
        repo_path,
        tree_hash,
        parent_hash=None,
        message="Commit",
        author_name="Admin",
        author_email="admin@example.com",
    ):
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = author_name
        env["GIT_AUTHOR_EMAIL"] = author_email
        env["GIT_COMMITTER_NAME"] = author_name
        env["GIT_COMMITTER_EMAIL"] = author_email

        args = ["commit-tree", tree_hash, "-m", message]
        if parent_hash:
            args.extend(["-p", parent_hash])

        cmd = ["git", "-C", repo_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise Exception(f"commit-tree failed: {result.stderr}")
        return result.stdout.strip()

    def get_ref(self, repo_path, ref):
        try:
            output = self._run_git(repo_path, ["rev-parse", ref])
            return output.decode("utf-8").strip()
        except Exception:
            print("rev-parse failed")
            return None

    def get_tree(self, repo_path, ref):
        # git ls-tree -r <ref>
        try:
            output = self._run_git(repo_path, ["ls-tree", "-r", ref])
            return output.decode("utf-8").strip().split("\n")
        except Exception:
            print("ls-tree failed")
            return []

    def merge_ref(self, repo_path, src_ref, dest_ref, message="Merge"):
        # This is a simplified merge: try to fast-forward or create a merge commit
        # For our plumbing model, we can use 'git merge-tree' or just 'git update-ref' if FF
        # Here we'll do a simple fast-forward check
        src_hash = self.get_ref(repo_path, src_ref)
        # dest_hash = self.get_ref(repo_path, dest_ref)

        if not src_hash:
            raise Exception(f"Source ref {src_ref} not found")

        # For simplicity, we'll force update-ref or use git merge-base
        # In a real system, you'd handle conflicts.
        self.update_ref(repo_path, dest_ref, src_hash)
        return src_hash

    def list_files(self, repo_path, ref, path):
        # git ls-tree -l <ref>:<path>
        args = ["ls-tree", "-l", f"{ref}:{path}" if path else ref]
        output = self._run_git(repo_path, args)
        lines = output.decode("utf-8").strip().split("\n")

        entries = []
        for line in lines:
            if not line:
                continue
            # Format: <mode> <type> <hash> <size>\t<name>
            if "\t" not in line:
                continue
            meta, name = line.split("\t", 1)
            parts = meta.split()
            if len(parts) < 4:
                continue

            type_, hash_, size_str = parts[1], parts[2], parts[3]

            entries.append(
                {
                    "name": name,
                    "is_dir": type_ == "tree",
                    "size": 0 if size_str == "-" else int(size_str),
                    "hash": hash_,
                }
            )
        return entries

    def cat_file(self, repo_path, ref, path):
        # git cat-file -p <ref>:<path>
        args = ["cat-file", "-p", f"{ref}:{path}"]
        return self._run_git(repo_path, args)
