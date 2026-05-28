# Introduction

이 문서는 VulnBank MSA DevSecOps Golden Path PoC를 설명한다. 목표는 보안 도구를 많이 붙였다는 사실을 보여주는 것이 아니라, 금융권 보안담당자가 실제로 겪는 판단 흐름을 Kubernetes 배포 파이프라인으로 재현하는 것이다.

핵심 질문은 다음 네 가지다.

| 질문 | 파이프라인에서의 대응 |
| --- | --- |
| 이 코드를 배포해도 되는가? | Jenkins CI에서 SAST, secret scan, IaC scan, image scan, SBOM 생성, Security Gate를 수행한다. |
| 무엇 때문에 막거나 허용했는가? | 도구별 JSON/TXT 리포트와 gate summary를 evidence로 보관한다. |
| 새 CVE가 공개되면 과거 이미지가 영향받는가? | SBOM을 기준으로 이미지 구성요소를 다시 추적한다. |
| 배포 후 실제 공격 행위는 보이는가? | Runtime 계층에서 Cilium/Hubble, Falco, kube-bench, DAST를 GitOps로 배치할 수 있게 한다. |

## Project framing

이 PoC는 세 가지 축으로 구성된다.

1. **Application**: 기존 VulnBank를 6개 서비스 기반 MSA 형태로 분해한 실습 워크로드
2. **CI/Supply Chain**: Jenkins, Harbor, SonarQube, Gitleaks, Checkov, Kubescape, SBOM, Trivy, Security Gate
3. **Runtime/GitOps**: k3s, ArgoCD, Helm, Cilium/Hubble, Falco, kube-bench, OWASP ZAP, DefectDojo 연계 자리

## What this is not

이 문서는 운영 환경 보안 기준서가 아니다. PoC 문서이며, 일부 비밀번호와 토큰 방식은 의도적으로 단순화되어 있다. 실제 운영 전에는 Secret 관리, TLS, 접근제어, 키 회전, 이미지 서명 정책, 네트워크 정책의 단계적 강제 적용이 필요하다.

## Evidence baseline

현재 확인된 AWS CI-only 기준 증적은 Jenkins `vulnbank-msa-ci` Build `#3`이다.

| 항목 | 확인 결과 |
| --- | --- |
| Jenkins result | SUCCESS |
| Docker build | 6개 서비스 build 완료 |
| SBOM | 6개 서비스 SPDX/CycloneDX 생성 |
| Kubescape | NSA/MITRE/CIS 3 framework scan 완료 |
| Trivy | 6개 서비스 image scan 완료 |
| Security Gate | BLOCK 판단, `ENFORCE_GATE=false`라 evidence 기록 후 계속 진행 |
| Harbor push | 6개 서비스 image push 완료 |

민감한 registry host와 credential은 문서에서 `<HARBOR_REGISTRY>`, `<HARBOR_PASSWORD>` 같은 placeholder로 표기한다.
