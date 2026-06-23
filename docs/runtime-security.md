# Runtime Security

Runtime Security는 배포 후 실제 Pod, 네트워크, 커널 이벤트, 클러스터 설정을 관찰하는 계층이다. CI가 "배포 전 검사"라면 Runtime은 "배포 후 행위 관찰"이다.

## Components

| 컴포넌트 | 역할 | 현재 repo 상태 |
| --- | --- | --- |
| Cilium | CNI, eBPF 기반 네트워크 정책과 관측 | `platform/cilium-hubble` 존재 |
| Hubble | Cilium flow 시각화 | NodePort 보조 Service 존재 |
| Falco | syscall 기반 runtime detection | Helm Application, custom rules 존재 |
| kube-bench | K3s CIS benchmark audit | CronJob/RBAC/namespace 존재 |
| OWASP ZAP | DAST baseline CronJob | CronJob/ConfigMap/RBAC 존재 |

## Cilium and Hubble

Cilium은 k3s 설치 시 Flannel을 비활성화한 상태에서 CNI로 설치된다. Runtime user-data에는 다음 방향이 반영되어 있다.

```text
k3s install
  --flannel-backend=none
  --disable-network-policy
  --disable=traefik

Cilium install
  hubble.relay.enabled=true
  hubble.ui.enabled=true
```

Hubble은 네트워크 행위 증적에 유용하다.

| 질문 | Hubble에서 확인할 증거 |
| --- | --- |
| frontend가 어떤 backend를 호출했는가? | L7 HTTP flow |
| webshell 실행 후 외부 egress가 있었는가? | egress flow, verdict |
| default-deny 정책으로 차단되었는가? | DROPPED verdict |

## Falco

Falco custom rule은 VulnBank container에서 shell spawn과 PHP file write를 탐지하도록 정의되어 있다.

| Rule | 위험 |
| --- | --- |
| Shell spawned in VulnBank container | 컨테이너 내부 shell 획득 |
| VulnBank PHP file upload detected | 웹셸 업로드 또는 PHP 파일 쓰기 |

이 rule은 파일 업로드 RCE 시나리오와 연결된다. DAST가 "업로드와 실행이 가능했다"를 보여주면, Falco는 "컨테이너 내부에서 위험 행위가 발생했다"를 보여준다.

## kube-bench

kube-bench는 매주 월요일 새벽 3시에 K3s CIS benchmark를 점검하도록 CronJob으로 선언되어 있다.

운영 질문:

- control-plane 설정이 CIS 기준에서 얼마나 벗어났는가?
- hostPath, privileged, service account 권한이 필요한가?
- 실패 항목이 runtime hardening backlog로 관리되는가?

## OWASP ZAP

OWASP ZAP은 `secure-path-dev`의 VulnBank frontend를 대상으로 baseline scan을 수행하도록 CronJob 형태로 선언되어 있다.

ZAP은 자동 차단보다 post-deploy evidence와 수동 triage에 적합하다. 특히 VulnBank의 핵심 4개 취약점은 custom DAST가 더 정확한 ground truth를 제공한다.

## Zero-trust rollout caution

Default-deny 정책은 보안적으로 필요하지만, MSA 통신을 쉽게 깨뜨릴 수 있다. 따라서 다음 순서가 안전하다.

1. Hubble로 현재 정상 flow 관찰
2. allow-list 정책을 dry-run 성격으로 설계
3. staging에서 default-deny 적용
4. DAST와 verify script 재실행
5. production-like 환경에 단계적 적용

CNP의 완전 강제(전 네임스페이스 default-deny·L7)는 여전히 TODO지만, 핵심 통제들이 *실제로 작동하는지*는 아래처럼 로컬에서 반증 가능하게 실증했다.

## 라이브 실증 — 로컬 kind 클러스터 (2026-06)

AWS 환경이 내려가 있는 동안(비용 0 유지), 위 통제들이 작동하는지를 로컬 kind 클러스터(WSL2 · Cilium 1.16 · Kyverno · Falco modern_ebpf)에서 검증했다. **이건 메커니즘 실증이지 프로덕션 규모나 AWS 배포의 증명이 아니다.** CI 게이트는 여전히 관측 모드(report-only)이며, 여기서 닫은 것은 *클러스터 admission·런타임* 계층이다.

| 통제 | 라이브 증거 | 반증 (정책 OFF) |
| --- | --- | --- |
| **PSA restricted enforce** | root Pod → `violates PodSecurity "restricted"` 거부 / 하드닝 Pod는 admit·Running | 라벨 제거 시 root Pod 통과 |
| **Cosign verifyImages enforce** | 미서명 이미지 → `no matching signatures` 거부 / 서명 이미지 admit | 정책 미적용 ns에서 통과 |
| **Cilium egress DROP** | 웹쉘의 외부 콜아웃 → Hubble `… <> 1.1.1.1:80 (world) Policy denied DROPPED (SYN)` | 정책 ON↔OFF로 DROP↔통과 전환 |
| **Falco 탐지** | `cat /etc/shadow` → `Read sensitive file`(T1555) / 웹쉘 셸 spawn → 커스텀 룰(T1059) | — |

### 풀 체인 — V4 웹쉘에 대한 다층 응답

의도적으로 심은 취약 워크로드(file-service)를 하드닝 배포한 뒤 실제 침해를 재현했다.

1. 하드닝 file-service(non-root 10001 · ro-rootfs · drop ALL · seccomp)가 **restricted enforce 네임스페이스에서 정상 기동** — 하드닝이 앱을 깨지 않음을 확인.
2. 웹쉘 업로드 → HTTP 실행 → **RCE 확인**(`id` → `uid=10001`).
3. RCE가 **non-root**로 실행돼 `/etc/shadow` 읽기 차단 — 침해돼도 크리덴셜 접근 불가(blast radius 축소).
4. 웹쉘의 외부 콜아웃 → **Cilium이 DROP**(Hubble) — C2/exfil 불가.
5. 셸 spawn → **Falco 탐지**(T1059). *주: kind/WSL2 modern_ebpf는 BPF iterators가 비활성이라 부모-프로세스 계보가 불안정 → 부모명 대신 "앱 워크로드에서 셸 spawn = 이상"이라는 워크로드 정체성으로 룰을 설계했다.*

→ 단일 통제가 아니라 **하드닝 · 네트워크 봉쇄 · 런타임 탐지가 상호작용**해 침해를 봉쇄하고 가시화하는 것을 라이브로 보였다. CNP 완전 강제, 더 많은 시나리오, AWS 환경에서의 동일 재검증은 다음 과제다.
