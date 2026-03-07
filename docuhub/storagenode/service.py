import os
import grpc
import threading
from concurrent import futures

import redis
from docuhub.generated import repository_pb2
from docuhub.generated import repository_pb2_grpc
from .git_plumbing import GitPlumbing, RefNotFoundError, PathNotFoundError, RepoNotFoundError
from .auth import AuthHelper


class RepositoryService(repository_pb2_grpc.RepositoryServiceServicer):
    def __init__(self, base_dir=None):
        base = base_dir or os.getenv("STORAGE_BASE_DIR", "data/repo")
        self.git = GitPlumbing(base_dir=base)
        self.locks = {}  # Basic in-memory lock per repo
        self.lock_mutex = threading.Lock()

    def _get_lock(self, repo_key):
        with self.lock_mutex:
            if repo_key not in self.locks:
                self.locks[repo_key] = threading.Lock()
            return self.locks[repo_key]

    def InitRepo(self, request, context):
        try:
            rel_path = f"{request.namespace}/{request.repo_name}.git"
            full_path = self.git.init_bare_repo(rel_path)
            return repository_pb2.InitRepoResponse(
                success=True, message="Repository initialized", repo_path=full_path
            )
        except Exception as e:
            return repository_pb2.InitRepoResponse(success=False, message=str(e))

    def ApplyCommit(self, request, context):
        repo_key = f"{request.namespace}/{request.repo_name}"
        repo_path = os.path.join(self.git.base_dir, f"{repo_key}.git")

        lock = self._get_lock(repo_key)
        with lock:
            try:
                # 1. Get current tree
                parent_hash = self.git.get_ref(repo_path, request.target_ref)
                tree_entries = {}  # path -> (mode, type, hash)

                if parent_hash:
                    ls_tree = self.git.get_tree(repo_path, parent_hash)
                    for line in ls_tree:
                        if not line:
                            continue
                        # Format: <mode> <type> <hash>\t<path>
                        meta, path = line.split("\t")
                        mode, type_, hash_ = meta.split(" ")
                        tree_entries[path] = (mode, type_, hash_)

                # 2. Apply changes
                for change in request.changes:
                    if change.action == repository_pb2.FileChange.DELETE:
                        if change.path in tree_entries:
                            del tree_entries[change.path]
                    else:  # ADD or MODIFY
                        blob_hash = self.git.hash_object(repo_path, change.content)
                        tree_entries[change.path] = ("100644", "blob", blob_hash)

                # 3. Build tree info for mktree
                mktree_lines = []
                for path, (mode, type_, hash_) in sorted(tree_entries.items()):
                    mktree_lines.append(f"{mode} {type_} {hash_}\t{path}")

                new_tree_hash = self.git.write_tree(
                    repo_path, "\n".join(mktree_lines) + "\n"
                )

                # 4. Create commit
                new_commit_hash = self.git.commit_tree(
                    repo_path,
                    new_tree_hash,
                    parent_hash=parent_hash,
                    message=request.commit_message,
                    author_name=request.author_name,
                    author_email=request.author_email,
                )

                # 5. Update ref
                self.git.update_ref(
                    repo_path, request.target_ref, new_commit_hash, old_hash=parent_hash
                )

                return repository_pb2.ApplyCommitResponse(
                    success=True,
                    commit_hash=new_commit_hash,
                    message="Commit applied successfully via plumbing",
                )
            except Exception as e:
                return repository_pb2.ApplyCommitResponse(success=False, message=str(e))

    def MergeRepo(self, request, context):
        # Implementation of merging src into dest
        src_repo_path = os.path.join(
            self.git.base_dir, f"{request.src_namespace}/{request.src_repo_name}.git"
        )
        dest_repo_path = os.path.join(
            self.git.base_dir, f"{request.dest_namespace}/{request.dest_repo_name}.git"
        )

        # In a distributed system, we might need to fetch objects if nodes are different.
        # But for this Phase, assume they are on the same filesystem or node.
        try:
            # We treat dest as the target Upstream repo
            src_hash = self.git.get_ref(src_repo_path, request.src_ref)
            if not src_hash:
                raise Exception(f"Source ref {request.src_ref} not found")

            # For this simplified implementation, we'll fast-forward the dest ref
            # to the src_hash if it's the Upstream repo.
            # (In reality, you'd do a 'git fetch' from src to dest first)

            # Since objects are shared (hardlinks/same node), we can update ref directly.
            self.git.update_ref(dest_repo_path, request.dest_ref, src_hash)

            return repository_pb2.MergeRepoResponse(
                success=True,
                new_commit_hash=src_hash,
                message="Merged successfully (Fast-forwarded)",
            )
        except Exception as e:
            return repository_pb2.MergeRepoResponse(success=False, message=str(e))

    def ForkRepo(self, request, context):
        try:
            src_rel = f"{request.src_namespace}/{request.src_repo_name}.git"
            dest_rel = f"{request.dest_namespace}/{request.dest_repo_name}.git"
            self.git.fork_repo(src_rel, dest_rel)
            return repository_pb2.ForkRepoResponse(
                success=True, message="Forked successfully"
            )
        except Exception as e:
            return repository_pb2.ForkRepoResponse(success=False, message=str(e))

    def CloneRepo(self, request, context):
        try:
            rel_path = f"{request.namespace}/{request.repo_name}.git"
            auth_helper = None
            if request.HasField("auth"):
                auth_helper = AuthHelper(request.auth)
                
            full_path = self.git.clone_repo(request.remote_url, rel_path, auth_helper=auth_helper)
            return repository_pb2.CloneRepoResponse(
                success=True,
                message="Repository cloned from external source",
                repo_path=full_path,
            )
        except Exception as e:
            return repository_pb2.CloneRepoResponse(success=False, message=str(e))

    def ListFiles(self, request, context):
        try:
            repo_path = os.path.join(
                self.git.base_dir, f"{request.namespace}/{request.repo_name}.git"
            )
            entries = self.git.list_files(repo_path, request.ref, request.path)

            proto_entries = [
                repository_pb2.FileEntry(
                    name=e["name"],
                    is_dir=e["is_dir"],
                    size=e["size"],
                    commit_hash=e["hash"],
                )
                for e in entries
            ]
            return repository_pb2.ListFilesResponse(entries=proto_entries)
        except (RefNotFoundError, PathNotFoundError, RepoNotFoundError) as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return repository_pb2.ListFilesResponse()
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return repository_pb2.ListFilesResponse()

    def CheckoutView(self, request, context):
        try:
            repo_path = os.path.join(
                self.git.base_dir, f"{request.namespace}/{request.repo_name}.git"
            )
            content = self.git.cat_file(repo_path, request.ref, request.file_path)

            # Streaming back in 1MB chunks
            chunk_size = 1024 * 1024
            for i in range(0, len(content), chunk_size):
                yield repository_pb2.FileContent(chunk=content[i : i + chunk_size])
        except (RefNotFoundError, PathNotFoundError, RepoNotFoundError) as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))


def serve():
    port = os.getenv("STORAGE_PORT", "50051")
    node_id = os.getenv("NODE_ID", "node-1")
    # In a real distributed setup, this address would be the node's reachable IP/hostname
    node_address = os.getenv("NODE_ADDRESS", f"localhost:{port}")

    # Register with Redis
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    try:
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        r.hset("storage_nodes", node_id, node_address)
        print(f"Node {node_id} registered at {node_address}")
    except Exception as e:
        print(f"Warning: Failed to register node with Redis: {e}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    repository_pb2_grpc.add_RepositoryServiceServicer_to_server(
        RepositoryService(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    print(f"Storage Node starting on port {port}...")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
