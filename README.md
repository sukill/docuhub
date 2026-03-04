# DocuHub: Distributed Git-based Guideline Repository

이 프로젝트는 분산형 Git 시스템을 기반으로 가이드라인을 관리하는 저장소 시스템입니다.

## 아키텍처 개요 (Architecture Overview)

DocuHub는 서비스의 확장성과 안정성을 위해 **API 서버**와 **스토리지 노드**가 분리된 분산 구조를 채택하고 있습니다.

### 1. API 서버 (Entry Point & Router)
*   **역할:** 외부 사용자의 HTTP 요청을 수신하고 인증/인가 및 데이터 검증을 수행합니다.
*   **라우팅:** 요청한 사용자 ID에 기반하여 해당 데이터가 저장된 물리적 **스토리지 노드**로 요청을 전달(Routing)합니다.
*   **특징:** 상태를 가지지 않는(Stateless) 구조로, 사용자가 늘어나면 자유롭게 수평 확장(Scale-out)이 가능합니다.

### 2. 스토리지 노드 (Storage Node & Git Engine)
*   **역할:** 실제 파일 시스템에 접근하여 Git 리포지토리를 생성하고 관리합니다.
*   **고성능 처리:** gRPC를 통해 전달받은 파일 변경 사항을 Git의 로우레벨 명령어(Plumbing commands)를 사용하여 고속으로 커밋하고 리프레시합니다.
*   **데이터 격리:** 특정 유저 그룹의 데이터를 전담하여 처리하므로, 대량의 I/O 작업이 발생해도 시스템 전체의 응답성에 영향을 주지 않습니다.

---

## 시작하기

이 프로젝트는 라이브러리 및 가상환경 관리를 위해 [uv](https://github.com/astral-sh/uv)를 사용합니다.

### 1. 의존성 설치

```bash
uv sync
```

### 2. Protobuf 컴파일

```bash
make proto
```

### 3. 프로그램 실행

프로젝트의 진입점을 더 직관적으로 사용할 수 있도록 루트 디렉토리에 `main.py`를 제공합니다.

#### 통합 실행 (`main.py` 사용)
```bash
# API 서버 실행
python main.py api --reload

# 스토리지 노드 실행
python main.py storagenode
```

#### CLI 명령어로 실행 (패키지 설치 후)
```bash
docuhub-api
docuhub-storagenode
```

#### 기존 방식 (`uv run` 사용)
```bash
# 스토리지 노드
uv run python -m docuhub.storagenode.service

# API 서버
uv run uvicorn docuhub.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Docker Compose로 실행 (추천)

Docker가 설치되어 있다면 Redis와 모든 서버를 한 번에 실행할 수 있습니다.

```bash
docker-compose up --build
```

---
## 주요 기술 스택
- **Language:** Python 3.9+
- **Infrastructure:** uv (Dependency Management)
- **Communication:** gRPC
- **API Framework:** FastAPI
- **Storage:** Git (Plumbing commands)