# ISMS-P 통제 매핑

!!! note "이 문서의 성격"
    이 페이지는 본 PoC의 기술 통제가 **ISMS-P(정보보호 및 개인정보보호 관리체계) 인증기준의 보호대책 요구사항(2.x)** 과 어떻게 정합되는지를 보여주는 **매핑 자료**다. 인증 취득을 주장하지 않으며, "DevSecOps 파이프라인의 각 통제가 어느 관리체계 항목을 뒷받침하는가"를 가시화해 **규제 관리 관점의 설명 가능성**을 제공하는 것이 목적이다. 구현(✅) / 계획(🟡)을 명시한다.

## 왜 ISMS-P 매핑인가

금융권 보안담당자는 도구의 탐지 결과를 **관리체계 인증 항목의 이행 증거**로 연결해야 한다. "Trivy를 돌렸다"가 아니라 "**2.10 보안관리의 취약점·패치 관리 요구사항을 자동화된 이미지 스캔으로 이행하고 그 증적을 보관한다**"가 감사에서 통하는 언어다. 이 매핑은 각 파이프라인 통제를 그 언어로 번역한다.

## 핵심 매핑 (보호대책 요구사항 2.x)

| ISMS-P 도메인 | 본 PoC 통제 | 구현 | 증적 |
| --- | --- | --- | --- |
| **2.6 접근통제** | Cilium 제로트러스트 `default-deny` + allow 화이트리스트(L3–L7), egress 통제 / DAST IDOR 탐지(응용 접근권한 결함) | ✅ / 🟡(default-deny 수동) | CiliumNetworkPolicy, Hubble flow, DAST 리포트 |
| **2.7 암호화 적용** | SAST가 TLS 인증서·호스트명 검증 비활성(CWE-295/297), 약한 해시·난수 탐지 | ✅ | SonarQube 리포트(Build #3 Vulnerability 2건) |
| **2.8 정보시스템 도입 및 개발 보안** | SAST(SonarQube)·SCA(Trivy)·시크릿 스캔(Gitleaks)·IaC 스캔(Checkov)·Security Gate·소스/운영 분리(3-repo)·GitOps 이관 | ✅ | 18-stage 파이프라인, gate summary, SBOM |
| **2.9 시스템 및 서비스 운영관리** | 변경관리=GitOps(ArgoCD, Git=단일 진실)·드리프트 selfHeal / 로그관리(Hubble·CloudWatch) | ✅(GitOps) / 🟡(중앙로그) | ArgoCD Application, sync 이력 |
| **2.10 시스템 및 서비스 보안관리** | 이미지 취약점·패치관리(Trivy CVE, SBOM 재평가)·K8s 보안설정(Kubescape NSA/CIS)·런타임 보안(Falco/Cilium)·DefectDojo 증적통합 | ✅ / 🟡(SBOM 재평가 자동화) | Trivy 29 CRIT/1319 HIGH, Kubescape CIS 26/33, DefectDojo |
| **2.11 사고 예방 및 대응** | 취약점 점검(전 계층 스캐닝)·이상행위 분석(Falco 런타임 탐지, Hubble DROPPED flow)·알림(SNS) | ✅(탐지) / 🟡(알림) | Falco 이벤트, Hubble 증적 |
| **2.12 재해복구 및 업무연속성** | (미구현) 백업·DR·RTO/RPO | 🟡 | — (한계로 명시) |

## 도메인별 상세

### 2.8 정보시스템 도입 및 개발 보안 — 가장 강한 매핑 ✅
- **2.8.1 보안 요구사항 정의 / 2.8.2 보안 설계·구현**: SAST(SonarQube)로 코드 레벨 취약 패턴(암호·인젝션) 점검, Quality Gate로 보안등급 기준 강제
- **2.8.5 소스 프로그램 관리 / 2.8.6 운영환경 이관**: app-source / gitops / CI 3-repo 분리, GitOps(ArgoCD)로 Git 승인 기반 이관 — 임의 배포 차단
- **공급망**: SCA(Trivy) + SBOM(Syft)으로 도입 컴포넌트의 취약점·구성 추적

### 2.6 접근통제 ✅/🟡
- **네트워크 접근통제**: Cilium `default-deny` CiliumNetworkPolicy로 허용되지 않은 트래픽 전면 차단(제로트러스트), 서비스 간 통신만 화이트리스트
- **인터넷 접속(egress) 통제**: 백엔드 파드의 외부 통신 차단 → 데이터 유출·C2 방지
- **응용프로그램 접근권한**: DAST가 IDOR(CWE-639) 같은 인가 결함을 실제 요청으로 검출 → SAST 사각을 보완

### 2.10 시스템 및 서비스 보안관리 ✅/🟡
- **취약점·패치 관리**: 이미지 CVE(Trivy) + SBOM 기반 신규 CVE 재평가로 "지속 점검" 이행
- **클라우드/K8s 보안설정**: Kubescape(NSA/MITRE/CIS), Checkov(IaC)로 설정 미준수 점검
- **악성행위 통제**: Falco 런타임 탐지

### 2.11 사고 예방 및 대응 ✅/🟡
- **취약점 점검**: SAST/SCA/IaC/DAST 전 계층 정기 스캔
- **이상행위 분석·모니터링**: Falco(프로세스 이상) + Hubble(네트워크 flow, DROPPED 증적) → 공격 행위 가시화
- **대응 자동화**: 게이트 BLOCK·알림(SNS, 계획) → 조치 트리거

## 한계 (정직한 갭)

| 영역 | 상태 | 보완 방향 |
| --- | --- | --- |
| 2.12 재해복구 | 미구현 | Harbor/gitops/DB 백업, RTO/RPO, 멀티 AZ |
| 2.9 중앙 로그관리 | 부분 | CloudWatch Logs / Loki 연동 |
| 2.5 인증·권한관리 | 부분 | 시크릿을 SSM Parameter Store로, 도구 SSO |
| 변경관리 승인·직무분리 | 부분 | PR 승인 워크플로우, 권한 분리 |

→ 이 갭들은 [기술 블로그의 "한계 및 향후"](overview.md#limitations)와 연결되며, 프로덕션화 로드맵의 일부다.

## 다음 단계: 실측 기반 컴플라이언스 스코어카드

이 매핑을 정적 표에서 **실시간 점수**로 끌어올리는 것이 다음 목표다 — Kubescape(CIS %)·Checkov·DefectDojo(미해결 finding·SLA) 수치를 ISMS-P 도메인별 가중 점수로 집계해 **경영진 보고용 증적**을 자동 생성한다. (선언적 체크리스트가 아니라 **파이프라인이 실제로 막은 증거 기반 점수**)
