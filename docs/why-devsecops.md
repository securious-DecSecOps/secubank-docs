# 왜 DevSecOps인가 — 도입 동인과 정량 효과

<div class="sb-lede" markdown>
보안 도구를 많이 붙이는 것이 목적이 아니다. 이 페이지는 **기업이 왜 DevSecOps로 옮기는가**(도입 동인)와, 이 PoC에서 **무엇이 실제로 측정됐는가**(정량 효과)를 비즈니스 관점으로 정리한다. 도구의 원리와 CI 파이프라인 상세, 탐지 수치의 근거는 중복하지 않고 기존 페이지로 연결한다.
</div>

<div class="sb-key" markdown>
한 줄 요약 — 릴리스 끝물의 **즉흥적·수작업 보안 검토**를 매 빌드 자동 검사로 좌측 이동(shift-left)시키고, 빌드 → SBOM → 게이트 → 배포 → 런타임으로 이어지는 **증적 체인**을 남긴다. 그 결과 "이 코드를 배포해도 되는가"와 "무엇 때문에 막거나 허용했는가"에 즉답할 수 있게 된다.
</div>

## 왜 도입하는가 — 5가지 Before pain

도입 동인은 추상적 구호가 아니라, 보안담당자가 실제로 겪는 다섯 가지 통증에서 출발한다. 각 통증(**Before pain**)은 곧 특정 **규제 노출**로 이어지고, 파이프라인의 특정 **통제**가 그 공백을 메운다. 아래 카드는 그 `pain → 규제 노출 → 우리 통제`의 방향을 한 행으로 읽도록 구성했다. 규제 통제 매핑은 [ISMS-P 매핑](isms-p-mapping.md)에서 다룬다.

<ul class="sb-driver">
<li>
<div class="sb-driver__pain"><span class="sb-driver__k">Before pain</span><span><strong>수작업 병목</strong> — 릴리스 끝물에 1~2명이 손으로 보안 검토. 사람과 피로도에 따라 깊이가 들쭉날쭉하다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__reg"><span class="sb-driver__k">규제 노출</span><span markdown>ISMS-P 2.8의 '반복가능 통제'가 즉흥 판단으로 충족된다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__ctl"><span class="sb-driver__k">우리 통제</span><span markdown>shift-left CI에서 6종 스캐너가 매 빌드 자동 검사.</span></div>
</li>
<li>
<div class="sb-driver__pain"><span class="sb-driver__k">Before pain</span><span><strong>배포 후 재평가 부재</strong> — 빌드 시점 1회 스캔 뒤 방치. "방금 공개된 라이브러리를 쓰는 배포본이 무엇이냐"에 즉답하지 못한다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__reg"><span class="sb-driver__k">규제 노출</span><span markdown>주기 점검(연/반기) 사이 구간의 노출이 미상으로 남는다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__ctl"><span class="sb-driver__k">우리 통제</span><span markdown>SBOM 보관 + 신규 CVE feed 재스캔으로 시간축 재평가.</span></div>
</li>
<li>
<div class="sb-driver__pain"><span class="sb-driver__k">Before pain</span><span><strong>감사 증적 산재</strong> — finding이 스프레드시트·스캐너 UI·이메일·누군가의 노트북에 흩어져 있다. 감사 때 며칠을 재구성에 쓴다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__reg"><span class="sb-driver__k">규제 노출</span><span markdown>증적의 출처·완전성을 입증하기 어렵다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__ctl"><span class="sb-driver__k">우리 통제</span><span markdown>DefectDojo 단일 집계 + evidence-map 자동 아카이브.</span></div>
</li>
<li>
<div class="sb-driver__pain"><span class="sb-driver__k">Before pain</span><span><strong>느리고 공포에 찬 배포</strong> — 수작업·늦은 검토 탓에 크고 드문 배포. 큰 diff = 고위험 = 검토가 더 느려지는 악순환.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__reg"><span class="sb-driver__k">규제 노출</span><span markdown>전자금융 변경관리에서 변경 단위·승인 추적이 흐려진다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__ctl"><span class="sb-driver__k">우리 통제</span><span markdown>GitOps 작은 배포 + 게이트가 변경 전 자동 검사.</span></div>
</li>
<li>
<div class="sb-driver__pain"><span class="sb-driver__k">Before pain</span><span><strong>런타임·제로트러스트 부재</strong> — 배포 후 행위 탐지·egress 통제가 없다. 침해된 파드가 C2를 호출하거나 측면 이동해도 보이지 않는다.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__reg"><span class="sb-driver__k">규제 노출</span><span markdown>배포 이후 행위 증적의 공백.</span></div>
<div class="sb-driver__arrow"></div>
<div class="sb-driver__ctl"><span class="sb-driver__k">우리 통제</span><span markdown>Cilium egress 통제 + Falco 행위 탐지로 런타임 증적.</span></div>
</li>
</ul>

!!! note "통증 → 규제 → 통제"
    다섯 통증은 모두 같은 구조를 가진다. **수작업·일회성·산재**라는 운영 약점이 규제 노출을 만들고, 파이프라인은 그것을 **자동·반복가능·집계된** 통제로 치환한다. 규제 통제 매핑은 [ISMS-P 매핑](isms-p-mapping.md)에서 다룬다.

## 측정된 정량 효과

아래는 AWS 라이브 **Build #3** 스냅샷에서 **실제로 측정된 값**이다. 모두 동일 워크로드·동일 인프라 기준이다.

<ul class="sb-kpis">
<li class="is-accent"><b>0 → 3/4</b><span>SAST → DAST recall (의도 취약점)</span></li>
<li><b>29 CRITICAL</b><span>Trivy / user-service 이미지</span></li>
<li><b>5,776</b><span>Trivy C+H+M 합계 (+931 LOW)</span></li>
<li><b>6 × 170</b><span>SBOM: 서비스 × SPDX 패키지</span></li>
</ul>

<span class="st st--done">측정값</span> 아래 표의 값은 전부 측정된 결과이며, 목표가 아니다.

| 항목 | 측정값 | 의미 |
| --- | --- | --- |
| 계층 방어 recall | SAST **0/4** → DAST **3/4** | SAST가 놓친 비즈니스 로직 취약점(음수 송금, user-update IDOR, 웹쉘 RCE)을 DAST가 실제 실행으로 재현. 나머지 1개(history IDOR)는 스크립트 미포함 → **4/4 목표**. (AWS 라이브 DAST, Build #3) |
| Trivy (user-service) | 29 CRITICAL / 1,319 HIGH / 4,428 MEDIUM (= 5,776) + 931 LOW | 거의 전부 `php:7.4`(EOL) debian 베이스 OS 패키지 CVE → **단일 근본원인**. Security Gate = BLOCK 산출. |
| Kubescape | NSA 14/20 · MITRE 16/17 · CIS 26/33 | 프레임워크별 passed/total 컨트롤. |
| SBOM / 보조 스캐너 | 6개 서비스 × 170 SPDX 패키지 · Gitleaks 2건 · Checkov 30건 | 공급망 인벤토리 + secret/IaC finding. |

!!! warning "게이트는 현재 관측 모드"
    Security Gate는 BLOCK을 **산출**하지만, 현재 기본값은 report-only(`ENFORCE_GATE=false`)다. 즉 BLOCK 판정을 증적으로 남기고 배포는 계속 진행한다. "차단한다"가 아니라 "차단 판정을 기록한다"가 현재 상태다. 게이트 강제(enforce) 전환은 운영 목표다.

탐지 수치의 정탐/오탐 프레임과 ground truth 정의는 [Detection Efficacy](detection-efficacy.md)에서 다룬다.

## 리더십 KPI (운영 목표)

아래 네 가지는 **'운영 시 이렇게 측정·추적한다'는 정의와 목표 궤적**이다. 측정된 달성치가 아니다. 이 PoC는 단발 빌드(#3) 스냅샷이므로 MTTR·%builds gated의 시계열 실측은 아직 없다.

<ul class="sb-points">
<li>
<span class="sb-points__k">MTTR <span class="st st--planned">목표</span></span>
<span markdown>finding 해결까지의 중앙값. 목표: CRITICAL ≤ 7일, HIGH ≤ 30일. 매핑: ISMS-P 2.11 / 취약점 조치 SLA.</span>
</li>
<li>
<span class="sb-points__k">% builds gated <span class="st st--planned">목표</span></span>
<span markdown>enforce 게이트 통과 비율. 궤적: P1 0%(report-only) → P2 ≥ 90% → 정상 ~100%. 매핑: 전자금융 변경관리.</span>
</li>
<li>
<span class="sb-points__k">컴플라이언스 커버리지 <span class="st st--planned">목표</span></span>
<span markdown>OWASP Top 10 중 탐지 계층 ≥ 1로 입증된 클래스 비율 + Kubescape 프레임워크 통과율의 상승 추세.</span>
</li>
<li>
<span class="sb-points__k">증적 완전성 <span class="st st--planned">목표</span></span>
<span markdown>build → SBOM → gate → deploy → runtime 체인이 완비된 릴리스 비율 → 100% 목표.</span>
</li>
</ul>

!!! warning "측정값과 목표를 분리한다"
    위 KPI는 <span class="st st--planned">목표·로드맵</span>이며, 앞 절의 <span class="st st--done">측정값</span>과 반드시 구분한다. 목표 수치를 달성치로 표기하지 않는다. 또한 이미지 서명(Cosign/Kyverno)·admission Enforce·Prometheus 대시보드 등은 planned 항목이며, 공급망 통제는 침해를 **예방(prevent)**한다기보다 **blast radius를 줄이고(reduce) 탐지(detect)**하는 통제로 표기한다.

## 더 읽기

- [보안 강화 조치](security-hardening.md) — 위 통제들을 실제로 *어떻게* 적용했는지(무엇을·어떻게·증거).
- [도입 가이드](adoption.md) — 배포 모델(AWS·온프레·하이브리드)과 단계별 도입 로드맵.
- [Detection Efficacy](detection-efficacy.md) — SAST→DAST recall, 도구 커버리지 매트릭스, 정탐/오탐 프레임.
- [CI Security Pipeline](ci-security-pipeline.md) — 6종 스캐너·SBOM·Security Gate의 동작과 'how'.
- [Runtime Security](runtime-security.md) — Cilium egress 통제와 Falco 행위 탐지(런타임 증적).
- [공급망 방어](supply-chain-defense.md) — axios·TanStack류 공급망 공격을 어디서 줄이고 탐지하는가.
- [Evidence & Triage](evidence-triage.md) — DefectDojo 단일 집계와 예외·VEX 처리 흐름.
- [ISMS-P 매핑](isms-p-mapping.md) — 규제 통제 매핑.
- [한계 및 향후 과제](limitations.md) — 게이트 강제력·공급망 무결성·admission 등 한계와 로드맵.
