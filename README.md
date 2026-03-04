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
uv run python -m grpc_tools.protoc -I./proto --python_out=./generated --grpc_python_out=./generated ./proto/repository.proto
```

### 3. 프로그램 실행

`uv run`을 사용하면 별도의 가상환경 활성화 없이 즉시 실행이 가능합니다.

#### 가이드라인 스토리지 노드 실행 (gRPC)
```bash
uv run python storage/agent.py
```

#### API 서버 실행 (FastAPI)
```bash
# 새로운 터미널 세션 권장
uv run uvicorn api.main:app --reload
```

## 주요 기술 스택
- **Language:** Python 3.9+
- **Infrastructure:** uv (Dependency Management)
- **Communication:** gRPC
- **API Framework:** FastAPI
- **Storage:** Git (Plumbing commands)