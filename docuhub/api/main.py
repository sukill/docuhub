from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from docuhub.generated import repository_pb2
from docuhub.api.router import RepositoryRouter

app = FastAPI(title="DocuHub API")
router = RepositoryRouter()


# Data models
class FileChange(BaseModel):
    path: str
    content: str
    action: str  # ADD, MODIFY, DELETE


class ApplyCommitRequest(BaseModel):
    user_id: str
    repo_name: str
    target_ref: str
    commit_message: str
    author_name: str
    author_email: str
    changes: List[FileChange]


class ForkRepoRequest(BaseModel):
    src_user_id: str
    src_repo_name: str
    dest_user_id: str
    dest_repo_name: str


class MergeRepoRequest(BaseModel):
    src_user_id: str
    src_repo_name: str
    src_ref: str
    dest_user_id: str
    dest_repo_name: str
    dest_ref: str


class CloneRepoRequest(BaseModel):
    remote_url: str
    user_id: str
    repo_name: str


@app.post("/repo/init")
async def init_repo(user_id: str, repo_name: str):
    """Initialize a new personal repository."""
    try:
        stub = router.get_client_stub(user_id)
        request = repository_pb2.InitRepoRequest(user_id=user_id, repo_name=repo_name)
        response = stub.InitRepo(request)
        if not response.success:
            raise HTTPException(status_code=500, detail=response.message)
        return {
            "success": True,
            "message": response.message,
            "repo_path": response.repo_path,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repo/clone")
async def clone_repo(request_data: CloneRepoRequest):
    """Initialize an Upstream repository by cloning from an external source."""
    try:
        stub = router.get_client_stub(request_data.user_id)
        request = repository_pb2.CloneRepoRequest(
            remote_url=request_data.remote_url,
            user_id=request_data.user_id,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repo/fork")
async def fork_repo(request_data: ForkRepoRequest):
    """Fork the Upstream repository into a personal user repository."""
    try:
        stub = router.get_client_stub(request_data.dest_user_id)
        request = repository_pb2.ForkRepoRequest(
            src_user_id=request_data.src_user_id,
            src_repo_name=request_data.src_repo_name,
            dest_user_id=request_data.dest_user_id,
            dest_repo_name=request_data.dest_repo_name,
        )
        response = stub.ForkRepo(request)
        if not response.success:
            raise HTTPException(status_code=500, detail=response.message)
        return {"success": True, "message": "Repository forked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repo/commit")
async def apply_commit(request_data: ApplyCommitRequest):
    """Perform atomic multi-file updates directly to the user's repository."""
    try:
        stub = router.get_client_stub(request_data.user_id)

        changes = [
            repository_pb2.FileChange(
                path=c.path,
                content=c.content.encode("utf-8"),
                action=repository_pb2.FileChange.Action.Value(c.action),
            )
            for c in request_data.changes
        ]

        request = repository_pb2.ApplyCommitRequest(
            user_id=request_data.user_id,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repo/merge")
async def merge_repo(request_data: MergeRepoRequest):
    """Merge personal changes back to Upstream."""
    try:
        # Repository routing logic
        stub = router.get_client_stub(request_data.dest_user_id)
        request = repository_pb2.MergeRepoRequest(
            src_user_id=request_data.src_user_id,
            src_repo_name=request_data.src_repo_name,
            src_ref=request_data.src_ref,
            dest_user_id=request_data.dest_user_id,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/repo/tag")
async def create_tag(
    user_id: str, repo_name: str, tag_name: str, target_ref: str = "main"
):
    """Create a version tag for a guideline."""
    try:
        stub = router.get_client_stub(user_id)
        request = repository_pb2.CreateTagRequest(
            user_id=user_id,
            repo_name=repo_name,
            tag_name=tag_name,
            target_ref=target_ref,
        )
        response = stub.CreateTag(request)
        if not response.success:
            raise HTTPException(status_code=500, detail=response.message)
        return {"success": True, "message": f"Tag {tag_name} created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repo/files")
async def list_files(user_id: str, repo_name: str, ref: str = "main", path: str = ""):
    """List files/directories at a specific revision and path."""
    try:
        stub = router.get_client_stub(user_id)
        request = repository_pb2.ListFilesRequest(
            user_id=user_id, repo_name=repo_name, ref=ref, path=path
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repo/file")
async def read_file(user_id: str, repo_name: str, ref: str = "main", path: str = ""):
    """Read the content of a specific file."""
    try:
        stub = router.get_client_stub(user_id)
        request = repository_pb2.CheckoutViewRequest(
            namespace=user_id, repo_name=repo_name, ref=ref, file_path=path
        )
        
        content = b""
        # CheckoutView returns a stream of FileContent
        for response in stub.CheckoutView(request):
            content += response.chunk
            
        return {
            "success": True,
            "content": content.decode("utf-8", errors="replace")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run():
    import uvicorn

    uvicorn.run("docuhub.api.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
