import logging
import grpc
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from docuhub.generated import repository_pb2
from docuhub.api.router import RepositoryRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="DocuHub API")
router = RepositoryRouter()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, grpc.RpcError):
        status_code = 500
        detail = str(exc)
        code = exc.code()
        
        if code == grpc.StatusCode.NOT_FOUND:
            status_code = 404
            detail = exc.details()
            logger.warning(f"Resource not found via gRPC: {detail}")
        elif code == grpc.StatusCode.UNAVAILABLE:
            status_code = 503
            detail = "Storage node unavailable"
            logger.error(f"gRPC service unavailable: {exc.details()}")
        else:
            logger.exception(f"gRPC error: {code} - {exc.details()}")
            detail = exc.details()

        return JSONResponse(
            status_code=status_code,
            content={"detail": detail},
        )

    logger.exception(f"Unhandled exception: {exc.detail if isinstance(exc, HTTPException) else str(exc)}")
    status_code = exc.status_code if isinstance(exc, HTTPException) else 500
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.detail if isinstance(exc, HTTPException) else str(exc)},
    )


# Data models
class FileChange(BaseModel):
    path: str
    content: str
    action: str  # ADD, MODIFY, DELETE


class ApplyCommitRequest(BaseModel):
    namespace: str
    repo_name: str
    target_ref: str
    commit_message: str
    author_name: str
    author_email: str
    changes: List[FileChange]


class ForkRepoRequest(BaseModel):
    src_namespace: str
    src_repo_name: str
    dest_namespace: str
    dest_repo_name: str


class MergeRepoRequest(BaseModel):
    src_namespace: str
    src_repo_name: str
    src_ref: str
    dest_namespace: str
    dest_repo_name: str
    dest_ref: str


class CloneRepoRequest(BaseModel):
    remote_url: str
    namespace: str
    repo_name: str


@app.post("/repo/init")
async def init_repo(namespace: str, repo_name: str):
    """Initialize a new personal repository."""
    stub = router.get_client_stub(namespace)
    request = repository_pb2.InitRepoRequest(namespace=namespace, repo_name=repo_name)
    response = stub.InitRepo(request)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.message)
    return {
        "success": True,
        "message": response.message,
        "repo_path": response.repo_path,
    }


@app.post("/repo/clone")
async def clone_repo(request_data: CloneRepoRequest):
    """Initialize an Upstream repository by cloning from an external source."""
    stub = router.get_client_stub(request_data.namespace)
    request = repository_pb2.CloneRepoRequest(
        remote_url=request_data.remote_url,
        namespace=request_data.namespace,
        repo_name=request_data.repo_name,
    )
    response = stub.CloneRepo(request)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.message)
    return {
        "success": True,
        "message": response.message,
        "repo_path": response.repo_path,
    }


@app.post("/repo/fork")
async def fork_repo(request_data: ForkRepoRequest):
    """Fork the Upstream repository into a personal user repository."""
    stub = router.get_client_stub(request_data.dest_namespace)
    request = repository_pb2.ForkRepoRequest(
        src_namespace=request_data.src_namespace,
        src_repo_name=request_data.src_repo_name,
        dest_namespace=request_data.dest_namespace,
        dest_repo_name=request_data.dest_repo_name,
    )
    response = stub.ForkRepo(request)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.message)
    return {"success": True, "message": "Repository forked"}


@app.post("/repo/commit")
async def apply_commit(request_data: ApplyCommitRequest):
    """Perform atomic multi-file updates directly to the user's repository."""
    stub = router.get_client_stub(request_data.namespace)

    changes = [
        repository_pb2.FileChange(
            path=c.path,
            content=c.content.encode("utf-8"),
            action=repository_pb2.FileChange.Action.Value(c.action),
        )
        for c in request_data.changes
    ]

    request = repository_pb2.ApplyCommitRequest(
        namespace=request_data.namespace,
        repo_name=request_data.repo_name,
        target_ref=request_data.target_ref,
        commit_message=request_data.commit_message,
        author_name=request_data.author_name,
        author_email=request_data.author_email,
        changes=changes,
    )

    response = stub.ApplyCommit(request)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.message)
    return {
        "success": True,
        "commit_hash": response.commit_hash,
        "message": response.message,
    }


@app.post("/repo/merge")
async def merge_repo(request_data: MergeRepoRequest):
    """Merge personal changes back to Upstream."""
    # Repository routing logic
    stub = router.get_client_stub(request_data.dest_namespace)
    request = repository_pb2.MergeRepoRequest(
        src_namespace=request_data.src_namespace,
        src_repo_name=request_data.src_repo_name,
        src_ref=request_data.src_ref,
        dest_namespace=request_data.dest_namespace,
        dest_repo_name=request_data.dest_repo_name,
        dest_ref=request_data.dest_ref,
    )
    response = stub.MergeRepo(request)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.message)
    return {
        "success": True,
        "new_commit_hash": response.new_commit_hash,
        "message": response.message,
    }


@app.post("/repo/tag")
async def create_tag(
    namespace: str, repo_name: str, tag_name: str, target_ref: str = "main"
):
    """Create a version tag for a guideline."""
    stub = router.get_client_stub(namespace)
    request = repository_pb2.CreateTagRequest(
        namespace=namespace,
        repo_name=repo_name,
        tag_name=tag_name,
        target_ref=target_ref,
    )
    response = stub.CreateTag(request)
    if not response.success:
        raise HTTPException(status_code=500, detail=response.message)
    return {"success": True, "message": f"Tag {tag_name} created"}


@app.get("/repo/files")
async def list_files(namespace: str, repo_name: str, ref: str = "main", path: str = ""):
    """List files/directories at a specific revision and path."""
    stub = router.get_client_stub(namespace)
    request = repository_pb2.ListFilesRequest(
        namespace=namespace, repo_name=repo_name, ref=ref, path=path
    )
    response = stub.ListFiles(request)
    entries = [
        {
            "name": e.name,
            "is_dir": e.is_dir,
            "size": e.size,
            "commit_hash": e.commit_hash,
        }
        for e in response.entries
    ]
    return {"entries": entries}


@app.get("/repo/file")
async def read_file(namespace: str, repo_name: str, ref: str = "main", path: str = ""):
    """Read the content of a specific file."""
    stub = router.get_client_stub(namespace)
    request = repository_pb2.CheckoutViewRequest(
        namespace=namespace, repo_name=repo_name, ref=ref, file_path=path
    )

    content = b""
    # CheckoutView returns a stream of FileContent
    for response in stub.CheckoutView(request):
        content += response.chunk

    return {
        "success": True,
        "content": content.decode("utf-8", errors="replace")
    }


@app.get("/repo/list")
async def list_repos(namespace: str):
    """List all repositories for a specific namespace."""
    stub = router.get_client_stub(namespace)
    request = repository_pb2.ListReposRequest(namespace=namespace)
    response = stub.ListRepos(request)
    return {"repo_names": list(response.repo_names)}


@app.get("/repo/refs")
async def list_refs(namespace: str, repo_name: str):
    """List all branches and tags for a repository."""
    from docuhub.storagenode.git_plumbing import GitPlumbing, RepoNotFoundError
    import os
    base_dir = os.getenv("STORAGE_BASE_DIR", "data/repo")
    git = GitPlumbing(base_dir=base_dir)
    repo_path = os.path.join(base_dir, f"{namespace}/{repo_name}.git")
    try:
        refs = git.list_refs(repo_path)
        return {"refs": refs}
    except RepoNotFoundError:
        raise HTTPException(status_code=404, detail="Repository not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run():
    import uvicorn

    uvicorn.run("docuhub.api.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
