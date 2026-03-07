# DocuHub REST API Specification

DocuHub은 분산 Git 기반의 가이드라인 저장소 시스템입니다. 본 문서는 DocuHub API 서버에서 제공하는 주요 REST 엔드포인트를 설명합니다.

## 기본 정보
- **Base URL**: `http://localhost:8000` (기본 설정 기준)
- **Content-Type**: `application/json`

---

## 1. 저장소 관리 (Repository Management)

### 1-1. 저장소 초기화 (Init Repo)
사용자의 새로운 개인 저장소를 초기화합니다.

- **URL**: `/repo/init`
- **Method**: `POST`
- **Query Parameters**:
  - `user_id` (string, required): 사용자 식별자
  - `repo_name` (string, required): 저장소 이름
- **Response**:
  ```json
  {
    "success": true,
    "message": "Repository initialized",
    "repo_path": "/path/to/repo"
  }
  ```

### 1-2. 외부 저장소 클론 (Clone Repo)
외부 원격 소스(Upstream)로부터 저장소를 동기화하여 초기화합니다.

- **URL**: `/repo/clone`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "remote_url": "https://github.com/user/repo.git",
    "user_id": "target_user",
    "repo_name": "target_repo"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Repository cloned",
    "repo_path": "/path/to/repo"
  }
  ```

### 1-3. 저장소 포크 (Fork Repo)
기존 Upstream 저장소를 사용자의 개인 저장소로 포크합니다.

- **URL**: `/repo/fork`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "src_user_id": "upstream_user",
    "src_repo_name": "guideline_repo",
    "dest_user_id": "personal_user",
    "dest_repo_name": "my_guideline"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Repository forked"
  }
  ```

---

## 2. 변경 사항 관리 (Commit & Merge)

### 2-1. 커밋 적용 (Apply Commit)
여러 파일의 변경 사항(추가, 수정, 삭제)을 하나의 원자적(Atomic) 커밋으로 적용합니다.

- **URL**: `/repo/commit`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "user_id": "user123",
    "repo_name": "guideline",
    "target_ref": "main",
    "commit_message": "Update docs",
    "author_name": "Author Name",
    "author_email": "author@example.com",
    "changes": [
      {
        "path": "README.md",
        "content": "# New Content",
        "action": "MODIFY"
      }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "commit_hash": "a1b2c3d4...",
    "message": "Commit applied successfully"
  }
  ```

### 2-2. 저장소 병합 (Merge Repo)
사용자의 개인 변경 사항을 Upstream 저장소로 병합합니다.

- **URL**: `/repo/merge`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "src_user_id": "personal_user",
    "src_repo_name": "my_guideline",
    "src_ref": "main",
    "dest_user_id": "upstream_user",
    "dest_repo_name": "guideline_repo",
    "dest_ref": "main"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "new_commit_hash": "e5f6g7h8...",
    "message": "Merge successful"
  }
  ```

---

## 3. 버전 및 탐색 (Tagging & Browsing)

### 3-1. 태그 생성 (Create Tag)
특정 시점의 가이드라인을 고정 버전으로 태깅합니다.

- **URL**: `/repo/tag`
- **Method**: `POST`
- **Query Parameters**:
  - `user_id` (string, required): 사용자 식별자
  - `repo_name` (string, required): 저장소 이름
  - `tag_name` (string, required): 태그 이름 (예: v1.0.0)
  - `target_ref` (string, optional): 대상 Ref (기본값: main)
- **Response**:
  ```json
  {
    "success": true,
    "message": "Tag v1.0.0 created"
  }
  ```

### 3-2. 파일 목록 조회 (List Files)
특정 리비전 및 경로의 파일/디렉토리 목록을 조회합니다.

- **URL**: `/repo/files`
- **Method**: `GET`
- **Query Parameters**:
  - `user_id` (string, required)
  - `repo_name` (string, required)
  - `ref` (string, optional): 브랜치나 태그 (기본값: main)
  - `path` (string, optional): 조회 경로 (기본값: "")
- **Response**:
  ```json
  {
    "entries": [
      {
        "name": "README.md",
        "is_dir": false,
        "size": 1024,
        "commit_hash": "a1b2c3d4..."
      }
    ]
  }
  ```

### 3-3. 파일 내용 조회 (Read File)
특정 파일의 전체 텍스트 내용을 조회합니다.

- **URL**: `/repo/file`
- **Method**: `GET`
- **Query Parameters**:
  - `user_id` (string, required)
  - `repo_name` (string, required)
  - `ref` (string, optional): 브랜치나 태그 (기본값: main)
  - `path` (string, optional): 파일 경로 (기본값: "")
- **Response**:
  ```json
  {
    "success": true,
    "content": "File content string..."
  }
  ```
