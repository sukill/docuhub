# [Master Plan] 분산 Git 기반 가이드라인 저장소 시스템

## 1. 아키텍처 개요

- **방식:** API 서버가 직접 파일에 접근하지 않고, 전용 **Storage Node**와 gRPC로 통신.
    
- **데이터 관리:** `user_id`를 기반으로 저장소 위치를 샤딩(Sharding)하여 특정 노드에 할당.
    
- **커밋 모델:** `git push` 대신 서버 내부에서 `git update-ref`를 사용하여 즉시 커밋 반영.
    

---

## 2. 주요 단계별 실행 계획

### **Phase 1: 인프라 및 라우팅 설계**

- **노드 샤딩:** 유저 ID를 해싱하거나 DB 매핑 테이블을 통해 어느 스토리지 노드에 저장할지 결정.
    
    - _Tool:_ Redis 또는 PostgreSQL (유저-노드 매핑용).
        
- **디렉토리 구조:** `/data/repo/{hash_prefix}/{username}/guideline.git` 형태로 OS 파일 시스템 부하 분산.
    

### **Phase 2: gRPC 인터페이스 정의 (.proto)**

커밋, 포크, 브랜치 관리 등 핵심 기능을 정의합니다.

- **핵심 RPC 목록:**
    
    - `InitRepo`: 유저 저장소 생성.
        
    - `ApplyCommit`: 푸시 과정 없이 파일 추가/수정/삭제를 하나의 커밋으로 즉시 반영.
        
    - `ForkRepo`: 기존 저장소를 새 경로로 하드링크/복제.
        
    - `GetRef`: 현재 브랜치/태그의 최신 커밋 해시 조회.
        
    - `CheckoutView`: 특정 해시/태그의 파일 내용 읽기.
        

### **Phase 3: Storage Node 에이전트 개발**

- **Git Plumbing 활용:** `git add/commit` 등 하이레벨 명령보다 `hash-object`, `update-ref` 등 로우레벨 명령을 사용하여 속도와 안정성 확보.
    
- **Concurrency Lock:** 동일 저장소에 대한 동시 쓰기 요청 시 gRPC 서버 수준에서 **Mutex** 또는 **File Lock** 처리.
    
- **Streaming:** 대용량 문서나 이미지 처리를 위해 `stream` 응답 구현.
    

### **Phase 4: API 서버 연동 및 기능 구현**

- **Atomic 작업:** 파일 여러 개를 수정할 때 API 서버가 하나의 gRPC 요청에 모든 변경사항을 담아 전송.
    
- **Branch/Tag 관리:** 가이드라인의 버전업(Tagging) 및 초안 작성(Branching) 로직 구현.
    

### **Phase 5: 확장성 및 안정성 강화**
    
- **Garbage Collection:** 스토리지 노드별로 유휴 시간에 `git gc` 자동 실행.
    

---

## 3. 핵심 인터페이스 상세 (예시)

|기능|RPC 메서드|설명|
|---|---|---|
|**저장소 생성**|`Create(repo_id)`|`git init --bare` 실행|
|**즉시 커밋**|`ApplyCommit(...)`|파일 변경분 수신 후 서버에서 즉시 커밋 및 Ref 업데이트|
|**해시 조회**|`GetHead(repo_id)`|특정 브랜치의 최신 커밋 SHA-1 반환|
|**복제**|`Fork(src, dest)`|특정 가이드라인을 다른 유저에게 복사|
|**태깅**|`CreateTag(name)`|특정 시점의 가이드라인을 고정 버전으로 저장|

Sheets로 내보내기

---

## 4. 기술 스택 추천

- **Language:** **Python** (빠른 프로토타이핑).
    
- **Communication:** **gRPC** (HTTP/2 기반 고성능 스트리밍).
    
- **Storage:** **NVMe SSD** 기반 로컬 디스크 (Git의 빈번한 I/O 대응).
    

---

이 플랜을 바탕으로 다음 단계를 진행할 준비가 되었습니다. **가장 먼저 어떤 부분을 구체화해 드릴까요?**

1. **Phase 2의 상세 `.proto` 코드 작성** (인터페이스 확정)
    
2. **Phase 3의 `ApplyCommit` 핵심 로직 샘플 구현** (푸시 없는 커밋 구현체)
    
3. **Phase 1의 유저-노드 매핑을 위한 데이터베이스 테이블 설계**