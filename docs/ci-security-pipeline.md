# CI Security Pipeline

CI-only Jenkinsfile은 `devsecops-path/Jenkinsfile.aws-ci`이다. 목적은 AWS CI VM에서 배포 없이 build, scan, gate, Harbor push까지 검증하는 것이다.

## Pipeline stages

| 순서 | Stage | 목적 |
| --- | --- | --- |
| 1 | Checkout | CI repo checkout |
| 2 | Preflight Tools | Docker, Git, Trivy, Python, Gitleaks, Checkov, Kubescape 등 확인 |
| 3 | Checkout App Source | `app-source-repo` checkout |
| 4 | Checkout GitOps Repo | `gitops-manifest-repo` checkout |
| 5 | Prepare Metadata | build number, repo SHA, image tag, report path 기록 |
| 6 | Gitleaks Secret Scan | Git history와 working tree secret leak 탐지 |
| 7 | SonarQube SAST | PHP와 shell script 중심 SAST |
| 8 | Checkov IaC Scan | Dockerfile, Helm chart, K8s manifest misconfiguration 탐지 |
| 9 | Kubescape K8s Manifest Scan | NSA/MITRE/CIS framework 기준 K8s manifest 점검 |
| 10 | Docker Build Services | 6개 서비스 image build |
| 11 | Generate SBOM | 6개 서비스 SPDX/CycloneDX SBOM 생성 |
| 12 | Trivy Scan Services | 6개 image SCA/image vulnerability scan |
| 13 | Security Gate | Trivy, Checkov, Gitleaks 결과 기준 gate 판단 |
| 14 | Registry Login | Harbor login |
| 15 | Registry Push Services | 6개 image push |
| 16 | Collect CI Evidence | evidence summary와 파일 목록 생성 |
| 17 | Archive Evidence | Jenkins artifact archive |

문서 내 stage 수는 Jenkinsfile 기준으로 계산한다. 사용자가 발표 슬라이드에서 stage를 묶어서 설명할 경우, "보안 stage"와 "전체 stage"를 분리해 말하는 것이 안전하다.

## Shift-left control map

| 위치 | 도구 | 막으려는 문제 |
| --- | --- | --- |
| Build 전 | Gitleaks | source, history, config에 남은 secret |
| Build 전 | SonarQube | PHP 코드 버그, 취약한 코딩 패턴, hotspot |
| Build 전 | Checkov | Dockerfile/Helm/K8s 설정 오류 |
| Build 전 | Kubescape | K8s hardening 관점의 manifest 취약 설정 |
| Build 후 | SBOM | 이미지 구성요소 추적, 신규 CVE 재평가 기준 |
| Build 후 | Trivy | OS/package/image 취약점 |
| Push 전 | Security Gate | 취약점 기준에 따른 차단 또는 report-only |

## Evidence layout

AWS CI Build `#3` 기준 Jenkins artifact 경로는 다음 구조로 확인되었다.

```text
reports/dev/3/
├── checkov/
├── gate/
├── gitleaks/
├── kubescape/
├── registry/
├── sbom/
├── services/
├── sonarqube/
└── trivy/
```

## Confirmed build result

Build `#3`에서 확인된 사실은 다음과 같다.

| 항목 | 결과 |
| --- | --- |
| Jenkins result | SUCCESS |
| Docker build | 6개 서비스 성공 |
| SBOM | 6개 서비스 생성, 각 service SPDX package count 170 |
| Kubescape | NSA 14/20 pass, MITRE 16/17 pass, CIS 26/33 pass |
| Security Gate | BLOCK 판단 |
| ENFORCE_GATE | false, 따라서 warn 후 계속 진행 |
| Harbor push | 6개 repository push 완료 |

Security Gate가 BLOCK인데 build가 SUCCESS인 이유는 현재 PoC 기본값이 `ENFORCE_GATE=false`이기 때문이다. 이 모드는 취약 실습 워크로드를 배포 가능한 상태로 유지하면서도, 판단 근거를 evidence로 남기는 report-only 운영을 재현한다.

## Known CI gap

Build `#3` 당시 Checkov는 Helm chart directory scan을 수행했지만, CI VM의 Helm CLI 상태에 따라 rendered manifest scan이 skip될 수 있다. CI user-data에는 Helm CLI 설치가 추가되어 있으므로, 재생성된 CI VM에서는 rendered manifest scan까지 수행되는 것을 목표로 한다.
