<section class="hero" markdown>
<div class="eyebrow">DevSecOps Golden Path PoC</div>

# VulnBank MSA 보안 파이프라인

보안 도구를 **많이 붙였다**가 아니라, 금융권 보안담당자가 실제로 겪는 **판단·차단·추적·재평가·증적** 업무를 Kubernetes 파이프라인으로 재현한 기술문서다. VulnBank MSA를 기준으로 CI, GitOps, 런타임 보안, 증적 관리가 어디서 어떤 판단을 만드는지 연결한다.
</section>

<div class="metric-strip" markdown>

<div class="metric" markdown>
<strong>3 repos</strong>
<span>CI / GitOps / App source 분리</span>
</div>

<div class="metric" markdown>
<strong>6 services</strong>
<span>VulnBank MSA workload</span>
</div>

<div class="metric" markdown>
<strong>5 scan layers</strong>
<span>SAST, secret, IaC, SBOM, image CVE</span>
</div>

<div class="metric" markdown>
<strong>4 vulns</strong>
<span>DAST ground truth 보존</span>
</div>

</div>

<div class="grid cards" markdown>

-   <div class="card-title">:material-hubspot: 아키텍처</div>

    ---

    AWS 3-VM 토폴로지(CI · runtime k3s · DefectDojo) + `개발자 → CI → Harbor → GitOps → 런타임 보안 → 증적` 골든패스. VulnBank는 k3s 위에서 동작.

    [아키텍처 보기 →](architecture.md)

-   <div class="card-title">:material-shield-search: CI 보안 파이프라인</div>

    ---

    Jenkins 18-stage. shift-left(빌드 전 SAST·secret·IaC, 빌드 후 SBOM·image CVE) → Security Gate → Harbor push.

    [파이프라인 보기 →](ci-security-pipeline.md)

-   <div class="card-title">:material-clipboard-text-search: 보안 시나리오</div>

    ---

    상황 → 보안담당자 질문 → 통제 → 증적. 취약 이미지 차단, 신규 CVE 재평가, DAST 비즈로직, 런타임 차단.

    [시나리오 보기 →](security-scenarios.md)

-   <div class="card-title">:material-chart-box: 탐지 효능 (정탐/오탐)</div>

    ---

    도구별 OWASP/CWE/CVE 매핑, 정탐/오탐 지표, 예외처리(FP/Risk Accepted/VEX). SAST 0/4 → 계층방어 근거.

    [지표 보기 →](detection-efficacy.md)

-   <div class="card-title">:material-radar: 런타임 보안</div>

    ---

    Cilium/Hubble eBPF, Falco, kube-bench. 제로트러스트(default-deny) + 런타임 RCE 탐지·egress 차단.

    [런타임 보기 →](runtime-security.md)

-   <div class="card-title">:material-file-document-check: 증적 & Triage</div>

    ---

    DefectDojo(ASOC 통합), SBOM(CycloneDX/SPDX), 도구 결과 dedup·SLA·triage 흐름.

    [증적 보기 →](evidence-triage.md)

</div>

## 핵심 질문 4가지

| 질문 | 파이프라인에서의 대응 |
| --- | --- |
| 이 코드를 배포해도 되는가? | Jenkins CI에서 SAST, secret scan, IaC scan, image scan, SBOM 생성, Security Gate 수행 |
| 무엇 때문에 막거나 허용했는가? | 도구별 JSON/TXT 리포트와 gate summary를 evidence로 보관 + DefectDojo triage |
| 새 CVE가 공개되면 과거 이미지가 영향받는가? | 저장된 SBOM을 기준으로 이미지 구성요소를 재추적·재스캔 |
| 배포 후 실제 공격 행위는 보이는가? | 런타임 계층에서 Cilium/Hubble, Falco가 탐지·차단하고 증적화 |

## 프로젝트 3축

1. **Application** — 기존 VulnBank를 6개 서비스 MSA로 분해한 실습 워크로드
2. **CI / Supply Chain** — Jenkins, Harbor, SonarQube, Gitleaks, Checkov, Kubescape, SBOM(Syft), Trivy, Security Gate
3. **Runtime / GitOps** — k3s, ArgoCD, Helm, Cilium/Hubble, Falco, kube-bench, OWASP ZAP, DefectDojo

## What this is not

운영 환경 보안 기준서가 아니다. PoC 문서이며 일부 비밀번호·토큰 방식은 의도적으로 단순화돼 있다. 실제 운영 전에는 Secret 관리, TLS, 접근제어, 키 회전, 이미지 서명 정책, 네트워크 정책의 단계적 강제 적용이 필요하다.

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

민감한 registry host·credential은 문서에서 `<HARBOR_REGISTRY>`, `<HARBOR_PASSWORD>` 같은 placeholder로 표기한다.
