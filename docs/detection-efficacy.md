# Detection Efficacy

이 장은 정탐/오탐 분석을 위한 틀이다. 수치를 지어내지 않기 위해, 현재 증적으로 확인된 값과 TODO를 분리한다.

## Tool coverage matrix

| 취약점/위험 클래스 | SonarQube | Gitleaks | Checkov | Kubescape | SBOM | Trivy | DAST | Falco/Cilium |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PHP 코드 취약 패턴 | Primary | - | - | - | - | - | Partial | - |
| Secret leak | - | Primary | - | - | - | - | - | - |
| Dockerfile misconfig | - | - | Primary | Partial | - | Partial | - | - |
| K8s manifest misconfig | - | - | Primary | Primary | - | - | - | - |
| OS/package CVE | - | - | - | - | Inventory | Primary | - | - |
| 신규 CVE 재평가 | - | - | - | - | Primary | Primary | - | - |
| IDOR | Weak | - | - | - | - | - | Primary | Runtime context only |
| Negative transfer | Weak | - | - | - | - | - | Primary | - |
| Webshell upload/RCE | Partial | - | - | - | - | - | Primary | Primary |
| Runtime shell execution | - | - | - | - | - | - | - | Falco |
| Runtime network egress | - | - | - | - | - | - | - | Cilium/Hubble |

## Ground truth

VulnBank MSA에서 명시적으로 재현 대상으로 잡은 ground truth는 4개다.

| ID | 취약점 | 검증 방식 | 현재 증적 |
| --- | --- | --- | --- |
| VULN-1 | 음수 송금 | Custom DAST script | `reports/dev/wsl-poc/evidence/02-negative-transfer.*` |
| VULN-2 | 거래내역 IDOR | Custom DAST script | `reports/dev/wsl-poc/evidence/03-idor-transaction-history.*` |
| VULN-3 | 사용자 정보 변경 IDOR | Custom DAST script | `reports/dev/wsl-poc/evidence/04-idor-user-update.*` |
| VULN-4 | PHP webshell upload/RCE | Custom DAST script | `reports/dev/wsl-poc/evidence/05-*`, `06-*` |

## Current measured CI evidence

AWS CI Build `#3`에서 확인된 정량 값이다.

| 항목 | 값 |
| --- | --- |
| SBOM service count | 6 |
| SPDX package count per service | 170 |
| Kubescape NSA | 14/20 controls passed, 6 failed |
| Kubescape MITRE | 16/17 controls passed, 1 failed |
| Kubescape CIS | 26/33 controls passed, 2 failed |
| Security Gate | BLOCK |
| Blocked service count | 6 |

## Metrics to complete

아래 값은 아직 evidence 기반 라벨링이 완료되지 않았으므로 TODO로 둔다.

| 지표 | 정의 | 현재 상태 |
| --- | --- | --- |
| Recall | ground truth 취약점 중 탐지된 비율 | TODO |
| Precision | 탐지 결과 중 실제 조치 대상 비율 | TODO |
| False positive rate | 오탐 비율 | TODO |
| False negative list | 놓친 취약점 목록 | TODO |
| Accepted risk count | 의도적으로 허용한 finding 수 | TODO |
| VEX status | not affected / affected / fixed 등 | TODO |

## Exception workflow

예외 처리는 "무시"가 아니라 근거 있는 상태 전환이어야 한다.

| 상태 | 의미 | 필요한 근거 |
| --- | --- | --- |
| False Positive | 도구가 잘못 탐지 | 재현 불가, 코드 경로 없음, scanner rule 근거 |
| Accepted Risk | 실제 위험이나 일정 기간 수용 | 영향도, 보완통제, 만료일 |
| VEX Not Affected | 구성요소는 있으나 취약 코드 경로가 아님 | SBOM component, call path 분석 |
| Fixed | 수정 완료 | 새 build tag, scan 재실행 결과 |

## Why multiple layers are needed

SAST는 비즈니스 로직 취약점에 약하고, DAST는 코드 경로와 원인을 설명하기 어렵다. SCA는 package CVE에 강하지만 IDOR 같은 권한 검증 결함을 직접 증명하지 못한다. Runtime detection은 공격 행위의 증거를 주지만 배포 전 차단에는 늦다.

따라서 이 PoC는 하나의 도구 점수가 아니라 `source → build → image → deploy → runtime → evidence` 전체 흐름의 판단 근거를 쌓는 구조다.
