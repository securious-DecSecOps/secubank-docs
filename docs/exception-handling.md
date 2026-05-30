---
title: 예외·오탐 처리 구조
---

# 예외·오탐 처리 구조

<div class="sb-lede" markdown>
스캐너는 매 빌드 수천 건을 쏟아낸다. 그중 상당수는 *지금 고칠 수 없거나, 고칠 필요가 없거나, 애초에 오탐*이다. 그래서 보안담당자의 진짜 질문은 "도구가 잡았나"가 아니라 — **그 판단이 어디에 쌓이고, 근거가 남고, 다음 빌드로 이어지는가**이다.
</div>

이 페이지는 그 질문에 대한 이 골든 패스의 *현재 답*과, 답을 만들며 메운 빈칸을 정직하게 기록한다.

## 오탐·예외는 "혹시"가 아니라 구조적으로 발생한다

| 도구 | 실측(Build #3 / 라이브) | 오탐·예외의 성격 |
| --- | --- | --- |
| SonarQube | security_hotspots **45**, vulnerabilities 2 | hotspot은 정의상 *"사람이 봐야 하는"* 검토 큐 = 오탐 트리아지 표면 |
| Trivy | 이미지 CVE **~6,000** (user-service) | 대부분 EOL 베이스 이미지 OS 패키지 → *도달 불가·수정 불가* = 실질적 오탐(VEX 대상) |
| Checkov / Kubescape | 30건 / NSA·CIS 일부 실패 | 일부는 *의도된 dev 설정*(acceptable-by-design) |
| Gitleaks | 2건 | TP/FP 확인 대상(테스트 더미 가능) |

매 빌드 hotspot 45건과 CVE 6천 건이 나온다. "무엇이 *진짜* 조치 대상인가"를 가리는 트리아지가 일상 업무라는 뜻이다. 그러니 *예외를 어떻게 다루는가*가 곧 이 시스템의 성숙도다.

## 세 층 — 쌓이고, 판정되고, 트리아지된다

**① 축적** — <span class="st st--done">구현됨</span> · 모든 raw finding이 빌드별로 쌓이고 불변 보관된다.

```text
reports/dev/<BUILD>/{trivy,gitleaks,sonarqube,checkov,kubescape,sbom}/*.json
Jenkinsfile: archiveArtifacts "${REPORT_DIR}/**", fingerprint: true   # 빌드 인덱싱·불변 증적
```

**② 판정(게이트)** — <span class="st st--done">임계값</span> + <span class="st st--done">예외 레지스터(신규)</span> · `security-gate-services.sh`가 Trivy 결과를 `GATE_MAX_CRITICAL=0`·`HIGH=3`과 비교해 BLOCK/PASS를 내고, 그 전제를 `msa-gate-summary.txt`에 남긴다. 여기에 아래의 **예외 레지스터**를 더했다.

**③ 트리아지(lifecycle)** — <span class="st st--partial">진행 중</span> · DefectDojo가 dedup·상태(Active→Verified/False Positive/Risk Accepted)·SLA를 맡는 단일 평면. 일부 도구 import는 동작하고, 메인 파이프라인 통합·상태 라벨링은 진행 중이다.

## 문제 — 코드화된 예외가 없었다

이 구조를 점검하다 빈칸을 발견했다. 게이트는 *카운트 임계값*만 봤고, **개별 finding을 예외 처리할 방법이 없었다.** `.gitleaksignore`·`.trivyignore`·VEX 같은 억제 파일도 하나도 없었다. SonarQube hotspot의 "acknowledged"는 *서버 안에만* 남아 git·증적 밖이었다. 결과적으로 — "이 CRITICAL은 도달 불가라 수용한다"는 결정을 *버전관리되고 감사 가능한 형태로 남길 곳이 없었다.*

<div class="sb-key" markdown>
보안담당자에게 예외는 *말*이 아니라 *코드*여야 한다. "왜 이 CRITICAL이 통과했죠?"라는 질문에 `git blame` 한 줄로 — 근거·승인자·만료일과 함께 — 답할 수 있어야 한다. 그게 없으면 게이트는 *통과시킨 이유*를 설명하지 못한다.
</div>

## 해결 — Exception-as-Code 레지스터

예외를 단일 레지스터(`security-exceptions.yaml`)로 코드화하고, 게이트가 이를 읽어 *활성(미만료)* 예외만 신뢰하도록 했다.

```yaml title="security-exceptions.yaml (발췌)"
exceptions:
  - id: CVE-2023-4911
    tool: trivy
    scope: user-service
    classification: not_reachable        # false_positive | not_reachable | risk_accepted
    reason: "glibc ld.so tunables. 코드경로 미사용으로 도달 불가. distroless 전환 시 해소."
    approver: security-lead
    created: 2026-05-30
    expires: 2026-08-30                   # 만료되면 자동으로 다시 차단된다
```

게이트가 빌드마다 도는 흐름은 이렇다.

<ul class="sb-points">
<li><span class="sb-points__k">검증 → fail-closed</span><span><code>security-exceptions.py</code>가 필수필드·분류·날짜를 검증한다. 레지스터가 깨졌으면 빌드를 <strong>멈춘다</strong>(통과가 아니라 정지).</span></li>
<li><span class="sb-points__k">활성만 신뢰</span><span>만료되지 않은 예외 id만 게이트에 넘긴다. 게이트는 해당 finding을 <strong>차단 카운트에서 제외하되 증적에 <code>SUPPRESSED</code>로 남긴다.</strong></span></li>
<li><span class="sb-points__k">만료 = 자동 재차단</span><span>만료된 예외는 무시되어 finding이 다시 게이트에 걸린다 — 수용은 영구가 아니라 <em>기한부</em>다.</span></li>
</ul>

실제 시나리오 테스트(활성 2 + 만료 1 + 미등록 1)를 돌린 게이트 증적이다.

```text title="msa-gate-summary.txt — 예외 적용 실측"
APPLIED_COUNT=2  EXPIRED_COUNT=1  INVALID_COUNT=0
APPLIED  CVE-2023-4911   scope=user-service  not_reachable  approver=security-lead  expires=2026-08-30
APPLIED  CVE-2023-38545  scope=user-service  risk_accepted  approver=security-lead  expires=2026-07-15
EXPIRED  CVE-2024-0001   scope=transaction-service  expired=2026-03-01  → 다시 게이트에 걸림(재검토 필요)

CRITICAL_COUNT=4   SUPPRESSED_CRITICAL=2   EFFECTIVE_CRITICAL=2   GATE_RESULT=BLOCK
SUPPRESSED_BEGIN
- CRITICAL CVE-2023-4911  package=glibc (security-exceptions.yaml 활성 예외)
- CRITICAL CVE-2023-38545 package=curl  (security-exceptions.yaml 활성 예외)
SUPPRESSED_END
VIOLATIONS_BEGIN
- CRITICAL CVE-2024-0001  package=openssl (만료 → 재차단)
- CRITICAL CVE-9999-0001  package=foo     (미등록 → 차단)
VIOLATIONS_END
```

읽는 법: 원래 CRITICAL 4건 중 *활성 예외 2건*은 `SUPPRESSED`로 통과하되 누가·왜 통과시켰는지 남았고, *만료 1건과 미등록 1건*은 `VIOLATIONS`로 차단됐다(effective 2 > 임계 0 → BLOCK). 이제 게이트 요약 한 장이 *무엇이 어떤 근거로 통과했는지*를 빌드 증적으로 답한다.

## 보안담당자가 분석 가능한가 — 현재 vs 목표

| 보안담당자가 하려는 것 | 상태 | 근거·비고 |
| --- | --- | --- |
| "무엇이 발견됐나" 추적·재현 | <span class="st st--done">가능</span> | REPORT_DIR + fingerprint archive(빌드별·불변) |
| "왜 막혔나/통과했나" 판정 근거 | <span class="st st--done">가능</span> | gate-summary(임계값·모드·서비스별 사유) |
| 오탐·수용을 *근거·승인자·만료*와 함께 코드화 | <span class="st st--done">신규 구현</span> | `security-exceptions.yaml` + 게이트 SUPPRESSED 증적 |
| 수용의 *자동 만료*로 재검토 강제 | <span class="st st--done">신규 구현</span> | expires 경과 시 자동 재차단 |
| 도구 간/빌드 간 *중복 제거* | <span class="st st--partial">진행 중</span> | DefectDojo 역할, 통합 진행 중 |
| 조치 *SLA·추세* 측정 | <span class="st st--partial">진행 중</span> | DefectDojo lifecycle + KPI |

## 남은 빈칸 (정직하게)

- **단일 평면 트리아지** — 예외 레지스터는 *게이트(Trivy)* 차단 결정을 코드화했다. 도구 간 dedup·상태 라벨·SLA·추세는 DefectDojo의 몫이고 <span class="st st--partial">통합 진행 중</span>이다.
- **다도구로 확장** — 이 레포의 enforce 게이트는 Trivy 중심이다. Gitleaks/SonarQube/Checkov는 자기 단계에서 차단하거나 보고하며, 레지스터를 *모든 도구의 finding*으로 넓히는 것이 다음 단계다.
- **SonarQube hotspot 흡수** — 현재 서버 내 "review" 상태로만 관리된다. 이를 레지스터/DefectDojo로 끌어와 증적화하는 것이 로드맵이다.

## 시니어의 네 렌즈로

기술적으로, 예외 레지스터는 게이트의 *카운트 임계값*에 *개별 finding 입도*를 더해, 차단 결정을 finding 단위로 설명 가능하게 만든다. 규제로 옮기면, 근거·승인자·만료가 남는 예외는 ISMS-P 2.11(취약점 관리)·2.9(변경·증적)가 요구하는 "위험 수용의 기록과 주기적 재검토"를 *코드로* 이행한다 — 감사에서 가장 약한 고리인 "예외의 정당성"을 git 한 줄로 답한다. 정책의 영역에서, 분류 체계(false_positive·not_reachable·risk_accepted)와 만료 정책이 곧 조직의 위험 수용 규칙이며, 만료를 강제함으로써 "한 번 수용하면 영원"이라는 부패를 막는다. 관리의 영역에서, 승인자 필드와 fail-closed가 통제의 소유권을 분명히 한다 — 엔지니어가 임의로 예외를 넣을 수 있으면 게이트는 장식이 되지만, 승인자가 남고 레지스터가 코드 리뷰를 거치면 예외조차 거버넌스 안에 들어온다.

<div class="sb-key" markdown>
도구는 finding을 *만들고*, 게이트는 *판정*하며, 예외 레지스터는 그 판정에 *설명과 기한*을 붙인다. 아직 비어 있는 칸(단일 평면 트리아지)은 DefectDojo가 채운다 — *지금 어디까지 왔고 어디가 비었는지*를 아는 것까지가 이 구조의 일부다.
</div>
