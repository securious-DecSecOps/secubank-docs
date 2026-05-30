# 공급망 공격 방어 분석 — 우리 파이프라인은 막을 수 있는가

> 질문: "최근 뉴스에 나오는 공급망 공격을 이 Golden Path가 막을 수 있는가?"
> 답은 단순한 yes/no가 아니라 **계층별로 '어디서 잡고, 어디서 못 잡고, 무엇이 보완하는가'** 다.
> 정직 원칙: 현재 **구현된 통제**와 **계획된 통제(Cosign/Kyverno 등)**를 명확히 구분한다. VulnBank는 PHP라 npm 패키지를 직접 쓰지 않으므로, 아래는 **메커니즘 방어**(Node 워크로드를 이 파이프라인에 태웠을 때 일반화되는 방어)로 논한다.

## 1. 2026년 공급망 공격 지형 (실제 사건)

| 사건 | 시기 | 메커니즘 | 영향 |
| --- | --- | --- | --- |
| **axios npm 침해** | 2026-03 | 메인테이너 계정 탈취 → `axios@1.14.1/0.30.4`에 악성 의존성 `plain-crypto-js` 주입 → 다단계 페이로드(RAT) 다운로드 | 주간 1억 다운로드 패키지 |
| **Shai-Hulud 웜** | 2026-04~05 | 자가전파 웜이 npm 패키지·CI 토큰·시크릿 탈취 후 추가 패키지 감염 | 수백 패키지 연쇄 |
| **TanStack CI 침해** | 2026-05-11 | **GitHub Actions CI 파이프라인**을 초기 벡터로 6분 내 42개 `@tanstack/*`에 84개 악성 아티팩트 publish | npm 170+ / PyPI 404 버전 |
| **node-ipc 자격증명 탈취** | 2026-05-14 | 주간 1천만 다운로드 라이브러리 3개 버전에 동일 80KB 난독화 credential-stealer | 광범위 |
| **SAP npm (Mini Shai-Hulud)** | 2026-04-29 | 4개 패키지 감염, 합산 57만 주간 다운로드 | SAP 개발 생태계 |

**공통 패턴 3가지** → 방어 설계의 기준:
1. **신뢰된 의존성의 무기화** (axios/node-ipc): 정상 패키지의 새 버전이 악성. → 빌드 시점 SCA의 한계.
2. **CI 파이프라인 자체 침해** (TanStack): 빌드 인프라가 벡터. → CI 하드닝·서명·최소권한.
3. **페이로드 행위** (RAT C2, credential 탈취/exfil): 설치 후 외부 통신·시크릿 접근. → 런타임 egress 차단·행위 탐지.

## 2. 계층별 방어 매핑 — 막는 곳 / 못 막는 곳

범례: ✅ 구현·동작 · 🟡 구현됐으나 한계 · ▢ 계획(planned)

| 공격 단계 | 우리 통제 | 효과 | 상태 |
| --- | --- | --- | --- |
| **악성 버전이 의존성에 들어옴** | SCA(Trivy) + SBOM(Syft) | 🟡 **이미 알려진(advisory/CVE 등재) 악성 버전**은 차단. 단 **공개 직후 0-day 악성 패키지는 DB에 없어 미탐** | ✅(known) / 🟡(novel) |
| 〃 (시간이 지나 advisory 등재) | **SBOM 지속 재평가** (`cve-rescan-pipeline`) | ✅ 저장된 SBOM을 갱신된 feed로 재스캔 → "우리가 그 버전 썼나?" 즉시 식별. **axios류는 며칠 내 GHSA 등재 → 재평가로 포착** | ✅(설계)/🟡(자동화 진행) |
| **하드코딩/유출 시크릿** | Gitleaks | ✅ 소스 커밋 단계 시크릿 차단(공격자의 탈취 대상 축소) | ✅ |
| **CI 파이프라인 침해** (TanStack형) | Jenkins 격리 + PAT 최소권한 + GitOps(Git=단일 진실) + 빌드 증적 | 🟡 빌드 변조 탐지·추적엔 유리하나, **CI 자체 침해 방지엔 추가 하드닝 필요**(서명된 커밋, OIDC, 빌드 출처) | 🟡 |
| **미신뢰 이미지가 배포됨** | **Cosign 서명 + Kyverno verifyImages** | ▢ 서명된 신뢰 아티팩트만 배포 허용 → 변조/미서명 이미지 차단 (**공급망 무결성의 핵심 통제**) | ▢ **planned** |
| **페이로드 실행 → 외부 C2/exfil** | **Cilium egress 차단(default-deny)** | ✅ **가장 강력한 보완통제**: 악성 코드가 빌드를 통과해도 **외부 통신을 막아 RAT C2·credential exfil 무력화**. axios RAT·node-ipc 탈취의 *효과*를 런타임에서 차단 | ✅(구현)/🟡(default-deny 수동적용) |
| **페이로드의 비정상 프로세스** | Falco | ✅ node/php에서 셸 spawn·의심 syscall 탐지 → 행위 기반 경보 | ✅ |
| **증적·triage** | DefectDojo | ✅ finding 통합·SLA·VEX | 🟡(import 동작) |

## 3. 핵심 결론 — "막을 수 있는가"의 정직한 답

**단일 통제로는 못 막는다. 계층으로 막는다 (defense-in-depth):**

1. **빌드 시점(SCA)은 known-bad만.** axios가 침해된 그 순간엔 advisory가 없어 Trivy가 못 잡는다. → SCA를 "공급망 1차 방어"로 과신하면 안 된다.
2. **시간축 방어(SBOM 재평가)가 진짜 무기.** advisory가 며칠 내 등재되면, **저장된 SBOM을 재스캔**해 "우리 배포본이 axios@1.14.1을 쓰는가"를 즉시 답한다. = "배포 시점 1회 검사"가 아니라 **지속 재평가**. (이게 이 프로젝트의 #2 시나리오)
3. **런타임 egress 차단(Cilium)이 최후·최강 보완.** 악성 의존성이 모든 빌드 검사를 통과해 배포돼도, **외부로 못 나가면 RAT C2도 credential exfil도 실패**한다. 이건 *지금 구현돼 있고* 실증 가능 — VulnBank에 default-deny + allow 화이트리스트를 적용하면 "백엔드 파드의 외부 통신 차단"을 Hubble DROPPED로 보일 수 있다.
4. **이미지 서명(Cosign/Kyverno)은 무결성의 정공법** — 단 현재 planned. TanStack형 CI 침해·이미지 변조를 정면 차단하려면 이게 필요. **로드맵 최우선 보강 후보.**

→ **요약**: "axios/Shai-Hulud를 막느냐?" → 침해의 *순간*은 못 막는다(예방 실패). 대신 **빌드(SCA known) + 시간(SBOM 재평가) + 런타임(Cilium egress·Falco) 3겹으로 *탐지하고 피해를 봉쇄*하며, 무결성 정면 차단(Cosign/Kyverno)은 다음 보강이다.** 단일 도구가 아니라 계층이 답이라는 것 자체가 evidence-driven 메시지.

## 4. 실증 가능성 (이론 아님)

<div class="sb-key" markdown>
아래 주장들은 **[증적 재현 런북](reproduce.md)** 으로 누구나 직접 확인할 수 있다 — 추가 VM 없이 기존 클러스터에서, VulnBank 네임스페이스에만 적용·롤백되는 비파괴 절차다. 핵심 3종(egress 차단·Falco 탐지·SBOM 재평가)은 **AWS 라이브로 실증 완료**(증적 `reports/dev/aws-live/evidence-summary.md`)했고, 남은 ▢는 워크로드 추가 시의 다음 단계다.
</div>

| 주장 | 실증 방법 | 현재 |
| --- | --- | --- |
| "런타임 egress로 C2를 막는다" | VulnBank 파드에 default-deny CiliumNetworkPolicy 적용 → 외부 IP 호출이 Hubble에 DROPPED로 기록 | ✅ 실증완료 — AWS 라이브 Hubble `DROPPED`(SYN), `http_code=000` (cmd `ba96945a`) |
| "Falco가 악성 행위를 잡는다" | 업로드된 웹쉘이 셸 spawn/네트워크 시도 → Falco 이벤트 | ✅ 실증완료 — 룰 수정(rename syscall) 후 웹쉘 `Critical`(18:31:55)·셸 spawn 발화 |
| "SBOM 재평가로 영향 버전을 찾는다" | 신규 CVE 가정 → 저장 SBOM을 `trivy sbom` 재스캔 → 영향 이미지 식별 | ✅ 실증완료 — `trivy sbom` 재스캔, 빌드 당시 없던 2026 CVE 3건 식별 |
| "Node 워크로드면 axios류가 SBOM에 잡힌다" | Juice Shop(취약 npm) 워크로드를 파이프라인에 태움 → Syft SBOM에 axios 버전·Trivy advisory | ▢ 워크로드 추가 시(=다음) |

## 5. 연결

- 탐지 효능 수치: [정탐/오탐 메트릭](detection-efficacy.md)
- 다양한 워크로드(Node 포함)로 일반화: [워크로드 벤치마크 계획](code-map.md)
- 계획 통제(Cosign/Kyverno·SBOM 재평가 자동화)는 [한계 및 향후](overview.md#limitations)
