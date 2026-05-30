---
title: 실습 가이드 · CI 하나하나 보기
---

# 실습 가이드 · CI 파이프라인 하나하나 보기

<div class="sb-lede" markdown>
"설치했다"가 아니라 *직접 들어가서 까보며* 배우는 실습 런북이다. 명령을 한 줄씩 치고, 각 토막이 무슨 뜻인지, 출력에서 무엇을 볼지 확인한다. (참조용 접속/연동은 <a href="operator-runbook/">운영자 런북</a>, 이건 학습용.)
</div>

대상: CI 노드 `i-01011276c12b34d2c`(10.0.1.169). 전부 SSM으로 접속한다.

## 0. CI VM에 들어가기

```bash
aws ssm start-session --target i-01011276c12b34d2c --profile secubank --region ap-northeast-2
sudo -i      # root로 — Jenkins 파일·docker 소켓이 root 권한이라 필요
```

## 1. Jenkins — 어디 살고, 어떻게 도나

```bash
systemctl status jenkins --no-pager | head -5
```
- `systemctl` = systemd(리눅스 서비스 관리자)에게 묻는 명령. Jenkins가 *systemd 서비스*로 등록돼 돈다.
- **볼 것**: `active (running)`, 그리고 실행줄에 `java ... jenkins.war --httpPort=8083`, Java 21. (Java 17이면 안 떠 — 1화의 그 함정.)

```bash
ls /var/lib/jenkins/jobs/
```
- Jenkins의 *잡*은 디렉터리 하나씩이다.
- **볼 것**: `vulnbank-msa-ci`(메인 파이프라인) · `secubank-runtime-security` · `secubank-sast-defectdojo-test`(DefectDojo 연동 잡).

```bash
ls /var/lib/jenkins/jobs/vulnbank-msa-ci/builds/
cat /var/lib/jenkins/jobs/vulnbank-msa-ci/builds/3/log | tail -40
```
- 빌드는 번호별 디렉터리(`builds/3/`)로 남고, `log`가 그 빌드의 *콘솔 출력*이다.
- **볼 것**: 스테이지 진행(Checkout→Build→Trivy→Gate→Push→Deploy)과 마지막 결과.

## 2. 빌드 엔진 — Docker

```bash
docker version --format 'server {{.Server.Version}}'
docker images | grep secubank | head
```
- 이미지 빌드는 *호스트 Docker 데몬*이 한다(Jenkins가 docker 그룹).
- **볼 것**: `10.0.1.169:8082/secubank/vulnbank-msa-*` 태그가 붙은 *우리가 빌드한* 이미지들. 태그 `10.0.1.169:8082`가 곧 "Harbor로 보낼 주소"다.

## 3. Harbor — OCI 레지스트리

```bash
docker ps --format '{{.Names}}\t{{.Status}}' | grep -i harbor
curl -s -o /dev/null -w 'GET /v2/ -> %{http_code}\n' http://localhost:8082/v2/
```
- `curl` 토막: `-s` 조용히, `-o /dev/null` 본문 버림, `-w '%{http_code}'` HTTP 코드만 출력. `/v2/`는 OCI Distribution API 루트.
- **볼 것**: Harbor는 컨테이너 *8개 스택*(core·registry·db·nginx·portal·jobservice·registryctl·log). 그리고 `/v2/ -> 401` — **익명 거부(인증 필요)**. 레지스트리가 열려 있지 않다는 증거.

## 4. 스캐너 — 무엇으로 판단하나

```bash
trivy --version; gitleaks version; checkov --version; syft version
ls -lh /var/lib/jenkins/.cache/trivy/db/trivy.db
```
- **볼 것**: `trivy.db`가 **약 1.1GB** — 이게 *등재된 CVE 데이터베이스*다. Trivy는 이미지 패키지를 이 DB와 대조한다. 그래서 *DB에 없는 0-day는 못 잡는다*(구조적 한계).

직접 한 번 돌려보기(공개 이미지라 인증 불필요):
```bash
trivy image --severity CRITICAL,HIGH alpine:3.12 | head -25
```
- `trivy image <이미지>` = 그 이미지를 풀어 패키지 목록을 뽑고 DB와 대조. `--severity`로 등급 필터.
- **볼 것**: 오래된 alpine이라 CVE가 줄줄 뜬다. "패키지 → 설치버전 → 취약버전 → 수정버전" 형식 = Trivy가 *매칭*하는 방식.

## 5. SonarQube — 서버형 SAST

```bash
docker ps --format '{{.Names}} {{.Status}}' | grep -i sonar
curl -s http://localhost:9000/api/system/status
```
- **볼 것**: SonarQube는 CLI가 아니라 *컨테이너로 뜬 서버*(`{"status":"UP"}`). 스캐너가 결과를 *서버에 올리고* Quality Gate를 *되묻는다*. 그래서 SonarQube만 결과가 파일이 아니라 서버에 산다.

## 6. 증적 — 워크스페이스에서 archive로

```bash
ls /var/lib/jenkins/workspace/vulnbank-msa-ci/reports/dev/3/
ls /var/lib/jenkins/jobs/vulnbank-msa-ci/builds/3/archive/reports/dev/3/gate/
cat /var/lib/jenkins/jobs/vulnbank-msa-ci/builds/3/archive/reports/dev/3/gate/msa-gate-summary.txt
```
- **볼 것**: 같은 빌드 #3의 증적이 *워크스페이스*(휘발 — 다음 빌드에 덮어씀)와 *archive*(불변 — 빌드번호별 영구 보존) 두 군데에 있다. `msa-gate-summary.txt`엔 게이트 임계값·판정·사유가 박혀 있다 — "왜 통과/차단했나"의 증적.

---

## 한 장 흐름

```mermaid
flowchart LR
  G["git push"] --> J["Jenkins (8083)"]
  J --> D["Docker build → secubank/* 이미지"]
  J --> S["스캐너: trivy(1.1GB DB)·gitleaks·checkov·syft"]
  J --> SQ["SonarQube 서버(9000)"]
  S --> R["REPORT_DIR/&lt;도구&gt;/*.json"]
  R --> A["archive (builds/N, 불변)"]
  D -->|"PASS만"| H["Harbor(8082, /v2/ 401)"]
```

> 다음 실습: 런타임(k3s·Cilium·Falco)도 같은 방식으로 하나하나 — 별도 면으로 잇는다.
