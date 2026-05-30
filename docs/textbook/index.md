---
title: 실전 교본 — 골든패스 도입기
---

# 실전 교본 · 골든패스 도입기

<div class="sb-lede" markdown>
주니어 엔지니어 **A**가 빈 AWS 계정에서 시작해, 보안 도구를 하나씩 붙여가며 마침내 최근 공급망 공격까지 다루는 골든패스를 완성하는 기록이다. 모든 장은 ① A의 스토리 ② **실제 레포 코드**(파일·줄 인용) ③ 메커니즘 ④ **한계와 면접 포인트**로 구성된다. 미화하지 않는다 — 못 잡는 것은 *못 잡는다*고 쓴다.
</div>

## 이 교본을 읽는 법

<ul class="sb-points">
<li><span class="sb-points__k">실제 코드</span><span>모든 코드 블록은 이 프로젝트의 *실제 파일*에서 가져온다(경로 표기). 지어낸 설정은 없다.</span></li>
<li><span class="sb-points__k">성장하는 아키텍처</span><span>장이 진행될수록 같은 다이어그램에 컴포넌트가 쌓인다(STAGE 1→6, AWS 공식 아이콘).</span></li>
<li><span class="sb-points__k">정직</span><span>"막는다"가 과장이면 "탐지·완화"라고 쓴다. 한계는 면접 예상 질문으로 따로 박는다.</span></li>
</ul>

## 목차

| 장 | 무엇을 세우나 | 핵심 질문 | STAGE |
| --- | --- | --- | :---: |
| [1 · 인프라](01-infra.md) | terraform 3-VM · SSM | 왜 SSH가 없죠? | 1 |
| 2 · 첫 관문 Gitleaks | 시크릿 스캔 | 비번이 코드에 있네? | 2 |
| 3 · SAST SonarQube | 코드 정적분석 | 왜 IDOR를 못 잡나 (0/4의 진실) | 2 |
| 4 · IaC/K8s | Checkov · Kubescape | 매니페스트가 위험한가 | 2 |
| 5 · 빌드 & SBOM | Docker build · Syft | 공급망은 여기서 시작된다 | 3 |
| 6 · 이미지 스캔 Trivy | 이미지 CVE | known-bad만 잡는다는 뜻 | 3 |
| 7 · Security Gate | 판단의 코드화 | 등급 D인데 왜 PASS? | 3 |
| 8 · 레지스트리 & GitOps | Harbor · ArgoCD | CI는 어디서 CD가 되나 | 4 |
| 9 · 런타임 제로트러스트 | Cilium egress | "막는다"는 왜 조건부인가 | 5 |
| 10 · 런타임 탐지 | Falco | 탐지와 차단은 다르다 | 5 |
| 11 · DAST & 벤치마크 | OWASP ZAP · kube-bench | 0/4를 3/4로 메운다 | 5 |
| 12 · 증적 & 공급망의 진짜 결말 | DefectDojo | 결국 axios를 막느냐? | 6 |

> 1장이 먼저 공개되었고, 나머지 장은 같은 형식(실제 코드 + 다이어그램 + 한계)으로 이어진다.

## 완성될 모습 (STAGE 6)

![최종 아키텍처](../assets/img/textbook/textbook-stage6.png){ loading=lazy }

> 처음엔 빈 VM 세 대뿐이다. 12장을 지나면 이 그림이 된다 — 그리고 마지막 장에서, 이 그림이 *실제로 무엇을 막고 무엇을 못 막는지*를 정직하게 따진다.
