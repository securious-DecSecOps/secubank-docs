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

현재 문서 기준으로 CiliumNetworkPolicy의 완전 강제 적용과 evidence는 TODO다.
