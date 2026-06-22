# 보안 강화 조치 — 워크로드 하드닝 (어떻게 조치했나)

<div class="sb-lede" markdown>
이 페이지는 "어떻게 보안 조치를 했는가"의 **구체적 기록(How)**이다. 사이트의 다른 장이 *발견*(컨테이너 root 실행, 게이트 관측 모드, 이미지 서명 미적용 등)을 다룬다면, 이 장은 그 발견에 대한 **실제 조치**를 무엇을·어떻게·증거·한계로 정리한다. 각 통제의 동작 원리는 [보안 도구 원리](security-tools.md)·[CI 보안 파이프라인](ci-security-pipeline.md)·[런타임 보안](runtime-security.md)에서 다루고, 여기서는 *우리가 실제로 바꾼 것*에 집중한다.
</div>

<div class="sb-key" markdown>
**조치 범위와 검증 수준(정직 표기)** — 이 라운드는 AWS Build #3 *이후*, 비용 없이 골든패스 차트·게이트·매니페스트에 적용한 in-repo 하드닝이다. 검증은 `helm template`(차트 기본값 + GitOps values 양 경로)·`kustomize build`·게이트 시나리오 실행·`mkdocs build --strict`로 했다. **"라이브 클러스터에서 돌렸다"는 의미가 아니며**, 라이브 재검증은 대부분 후속 과제다. 강제(Enforce)와 리포트(Audit), 코드 정의와 라이브 검증을 행마다 구분한다.
</div>

## 한눈에 — 조치 요약

| 영역 | 조치 | 상태 | 증거 |
| --- | --- | --- | --- |
| 워크로드 런타임 하드닝 | 앱 6종 restricted securityContext + Dockerfile `USER`, DB/Job 안전 부분집합, simple-web non-root 이미지 전환 | <span class="st st--done">렌더 검증</span> | helm template·kustomize build·helm lint |
| 게이트 fail-closed | `ENFORCE_GATE` 존중·report-only 정합, 예외 검증 실패 시 진단·종료코드 보존 | <span class="st st--done">시나리오 실증</span> | BLOCK 시나리오 3종 실행(아래) |
| Admission 거버넌스 | PSA(baseline/restricted) + ResourceQuota·LimitRange + Kyverno 2종 | <span class="st st--partial">Audit·코드</span> | YAML + kustomize/helm 렌더 |
| 네트워크 ingress | CiliumNetworkPolicy 3종(서비스 간 least-privilege) | <span class="st st--partial">코드만</span> | YAML 렌더 (라이브 미검증) |
| 공급망 서명·CI 무결성 | Cosign 서명·SLSA·CI 격리 | <span class="st st--planned">로드맵</span> | — |

## 1. 워크로드 런타임 하드닝

발견: 워크로드가 `securityContext` 없이 root로 실행됐다(컨테이너 root 실행). 조치는 워크로드를 위험 특성에 따라 **세 클래스로 나눠 차등 적용**했다 — 획일적 적용은 공식 이미지의 엔트리포인트를 깨뜨리기 때문이다.

| 클래스 | 대상 | 적용 수준 |
| --- | --- | --- |
| 앱 서비스 (6) | user / transaction / status / settings / file / frontend | full restricted |
| 인프라(root 필요) | MariaDB, db-init Job | 안전 부분집합 |
| 정석 예제 | simple-web | non-root 이미지 전환 후 full restricted |

- **앱 서비스 6종 — full restricted.** PHP 빌트인 서버가 `:8080`(&gt;1024)을 listen하므로 non-root로 충분하다. pod `runAsNonRoot`·`runAsUser/fsGroup 10001`·`seccompProfile: RuntimeDefault`, container `allowPrivilegeEscalation: false`·`readOnlyRootFilesystem: true`·`capabilities.drop: [ALL]`. 읽기전용 루트에서 쓰기 경로는 `emptyDir`로 명시(`/tmp`, file-service는 업로드 디렉터리 추가). Dockerfile에 `USER 10001`을 더해 이미지 자체도 non-root로 고정했다.
- **DB / Job — 안전 부분집합.** MariaDB 공식 이미지 엔트리포인트는 datadir를 root로 chown한 뒤 step-down하므로 `runAsNonRoot`를 강제하면 기동이 깨진다. 깨지지 않는 `allowPrivilegeEscalation: false` + `seccompProfile: RuntimeDefault`(Job은 `drop: [ALL]` 추가)만 적용했다. 완전 하드닝은 PVC+StatefulSet로 권한을 분리한 뒤(로드맵).
- **simple-web — 베이스 전환.** testbed가 아닌 정석 예제라 `nginx-unprivileged`(uid 101, `:8080`)로 바꿔 full restricted를 적용했다.

!!! note "베이스 이미지를 일부러 유지한 이유"
    앱 서비스 베이스 `php:7.4`(EOL)는 **의도적으로 유지**했다. 이 워크로드는 [탐지 효능](detection-efficacy.md)에서 다루는 수천 건 CVE(전부 베이스 OS 패키지)의 시연 testbed이므로, 베이스를 보존해야 그 측정이 유지된다. 즉 이번 하드닝은 "이미지를 깨끗하게"가 아니라 **"더러운 이미지라도 런타임 권한을 좁히는"** 방향이다 — 앱 취약점(트랙①)은 보존하고 권한·공급망(트랙②)만 강화한다.

## 2. 게이트 fail-closed

발견: Security Gate가 BLOCK을 산출해도 빌드가 통과하거나, 예외 레지스터가 깨졌을 때 조용히 죽는 결함이 있었다. 두 가지를 고쳤다.

- **`ENFORCE_GATE` 무시 버그** — MSA 게이트가 플래그를 보지 않고 BLOCK 시 항상 종료했다. 단일 의미로 통일: `false`(관측)면 경고 후 통과, `true`면 차단.
- **fail-closed 조기종료 버그** — `set -euo pipefail` 하에서 `var="$(cmd)"` 대입이 실패하면 진단·종료코드가 유실됐다. `if cmd; then … else exit 1`로 바꿔 보존.

**시나리오 3종 실행으로 실증**(합성 CRITICAL로 BLOCK 유도):

| 조건 | 결과 |
| --- | --- |
| BLOCK + `ENFORCE_GATE=false` | exit 0 (report-only, 경고 후 계속) |
| BLOCK + `ENFORCE_GATE=true` | exit 1 (차단) |
| 손상된 예외 레지스터 | report-only여도 **fail-closed 우선** exit 1 + 진단 보존 |

!!! warning "게이트는 현재 관측 모드"
    기본값은 report-only(`ENFORCE_GATE=false`)다. BLOCK 판정을 증적으로 남기고 배포는 진행한다 — "차단한다"가 아니라 "차단 판정을 기록한다". 강제 전환은 오탐을 예외 레지스터로 길들인 뒤의 단계적 결정이다([한계 및 향후 과제](limitations.md)).

## 3. Admission 거버넌스

"탐지에 머물지 말고 admission에서 강제로" — 그 *행동 계층*의 첫 코드를 깔았다. 단, 아직 **리포트(Audit)이지 강제(Enforce)가 아니다.**

- **Pod Security Admission** — 네임스페이스에 `enforce=baseline`(root DB 수용) + `warn/audit=restricted`(앱 서비스 컴플라이언스 노출).
- **ResourceQuota · LimitRange** — 네임스페이스 자원 상한 + 미지정 컨테이너 기본값 주입.
- **Kyverno ClusterPolicy 2종** — `require-non-root`(DB 예외), `verify-image-signatures`(Cosign, 공개키 placeholder=scaffold). 둘 다 `validationFailureAction: Audit`.

!!! warning "Audit ≠ Enforce"
    PSA `baseline`과 Kyverno `Audit`은 위반을 *기록*할 뿐 admission에서 *거부*하지 않는다. root Pod·미서명 이미지의 실제 거부(Enforce 승급)는 DB를 hardened StatefulSet로 옮기고 라이브 Kyverno 컨트롤러로 검증한 뒤다. 컨트롤러 없이 코드만으론 강제되지 않는다.

## 4. 네트워크 ingress 마이크로세그멘테이션

발견: CiliumNetworkPolicy가 egress baseline 하나뿐이라 서비스 간 통신이 사실상 무제한(측면 이동 무통제)이었다. ingress CNP 3종을 추가했다 — `db ← 앱서비스 :3306`, `백엔드 ← frontend+내부호출 :8080`, `frontend ← cluster :8080`.

!!! warning "egress(검증됨) vs ingress(코드만)"
    기존 **egress baseline**은 런타임 노드에서 Hubble로 world DROP을 **라이브 검증**했다([런타임 보안](runtime-security.md)). 이번 **ingress 세트는 코드 정의 단계이며 라이브 클러스터 검증 전**이다 — "정의했다"이지 "실증했다"가 아니다. L7 정책·네임스페이스 전체 default-deny는 로드맵.

## 5. 아직 열린 것 / 다음

<ul class="sb-points">
<li><span class="sb-points__k">이미지 서명 <span class="st st--planned">로드맵</span></span><span markdown>Cosign 서명 자체(`cosign sign`)와 admission Enforce 검증은 미구현. 현재는 검증 정책 scaffold만.</span></li>
<li><span class="sb-points__k">공급망 출처 <span class="st st--planned">로드맵</span></span><span markdown>SLSA provenance(attest)·앱 의존성 lockfile SCA 미구현. 공급망은 prevent가 아니라 reduce + detect.</span></li>
<li><span class="sb-points__k">CI 무결성 <span class="st st--planned">로드맵</span></span><span markdown>체크아웃 스크립트를 그대로 실행(poisoned pipeline 위험). 신뢰 브랜치·격리 실행·체크섬은 미착수.</span></li>
<li><span class="sb-points__k">Enforce 승급 <span class="st st--planned">P0</span></span><span markdown>PSA·Kyverno·게이트를 Audit/report-only → Enforce로. DB StatefulSet 하드닝 + 라이브 검증이 선결.</span></li>
</ul>

## 더 읽기

- [왜 DevSecOps인가](why-devsecops.md) — 이 조치들이 어떤 도입 동인에 답하는가.
- [보안 도구 원리](security-tools.md) · [CI 보안 파이프라인](ci-security-pipeline.md) — 각 통제의 동작 원리(how).
- [런타임 보안](runtime-security.md) — Cilium egress·Falco(egress는 라이브 검증).
- [한계 및 향후 과제](limitations.md) — 이 조치 이후 남은 한계와 로드맵.
