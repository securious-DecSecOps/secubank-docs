# 증적 재현 런북 — axios식 공급망 차단, 직접 확인하기

<div class="sb-lede" markdown>
"막을 수 있다"는 말은 누구나 합니다. 이 문서는 그 말을 **당신 손으로 확인하는 절차**입니다. 추가 VM 없이 이미 떠 있는 runtime k3s에서 그대로 돌리고, 모든 단계는 VulnBank 네임스페이스(`secure-path-dev`)에만 적용되고 되돌릴 수 있어 같은 클러스터를 쓰는 동료 작업을 건드리지 않습니다.
</div>

세 가지 실험으로 [공급망 방어](supply-chain-defense.md)의 핵심 주장 3개를 증적으로 바꾼다 — 런타임 egress 차단, 행위 탐지, 시간축 재평가.

## 사전 조건

```bash
# 1) runtime k3s 접근 (SSM 세션 또는 kubeconfig)
kubectl get nodes

# 2) VulnBank가 secure-path-dev에 떠 있는지 (6 서비스 + DB)
kubectl -n secure-path-dev get pods

# 3) 런타임 보안 플랫폼 동작 확인
kubectl -n falco get pods         # Falco
cilium status                     # Cilium / Hubble
```

> 추가 VM은 만들지 않는다. 기존 3대(CI · runtime · DefectDojo) 중 **runtime 한 대**에서만 진행한다.

---

## 실험 1 — 런타임 egress 차단 (RAT C2·exfil 무력화)

악성 의존성이 모든 빌드 검사를 통과해 배포돼도, **외부로 나가지 못하면 C2도 credential 탈취도 실패**한다. VulnBank 네임스페이스에만 egress를 잠그고, 외부 호출이 Hubble에 `DROPPED`로 찍히는지 본다.

```yaml
# vulnbank-egress-lockdown.yaml — secure-path-dev 에만 적용
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: vulnbank-egress-lockdown
  namespace: secure-path-dev
spec:
  endpointSelector: {}            # 네임스페이스 내 모든 파드
  egress:
    - toEndpoints:                # 같은 네임스페이스 내부 통신 허용
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: secure-path-dev
    - toEndpoints:                # DNS 허용
        - matchLabels:
            k8s:io.kubernetes.pod.namespace: kube-system
            k8s:k8s-app: kube-dns
      toPorts:
        - ports: [{ port: "53", protocol: UDP }]
  # 그 외 모든 egress는 default-deny
```

```bash
# 적용
kubectl apply -f vulnbank-egress-lockdown.yaml

# 트리거: 임의의 백엔드 파드에서 외부로 연결 시도 (차단되어야 정상)
POD=$(kubectl -n secure-path-dev get pod -l app.kubernetes.io/name=transaction-service -o name | head -1)
kubectl -n secure-path-dev exec "$POD" -- sh -c 'timeout 5 wget -qO- https://1.1.1.1 || echo BLOCKED'

# 증적 캡처: Hubble 에서 DROPPED flow 확인
hubble observe --namespace secure-path-dev --verdict DROPPED --last 20
#   또는 Hubble UI 에서 secure-path-dev → DROPPED 필터

# 롤백 (동료 작업 영향 0)
kubectl delete -f vulnbank-egress-lockdown.yaml
```

**기대 증적** — `hubble observe` 출력에 `secure-path-dev/... → 1.1.1.1 ... DROPPED (Policy denied)` 라인. 이 한 줄이 "런타임 egress 차단이 실제로 작동한다"의 증거다.

---

## 실험 2 — Falco 행위 탐지 (페이로드 실행 포착)

빌드를 통과한 페이로드라도 *실행 단계*에서 잡는다. 의도된 파일 업로드 RCE(VULN-4)를 트리거해 Falco 룰이 발화하는지 본다.

```bash
# 프론트엔드 게이트웨이로 포트포워드
kubectl -n secure-path-dev port-forward svc/vulnbank-msa-frontend 18080:8080 &

# (a) 웹쉘 업로드 — PHP 파일 쓰기 → Falco CRITICAL
printf "<?php echo 'VULNBANK_RCE_OK'; ?>\n" > /tmp/msa-webshell.php
curl -s -F "id=1" \
  -F "upload_avatar=@/tmp/msa-webshell.php;type=application/x-php" \
  http://localhost:18080/api/v1/files/upload

# (b) 컨테이너 내부 셸 실행 → Falco WARNING
POD=$(kubectl -n secure-path-dev get pod -l app.kubernetes.io/name=file-service -o name | head -1)
kubectl -n secure-path-dev exec "$POD" -- sh -c 'id'

# 증적 캡처
kubectl -n falco logs ds/falco | grep -E "VulnBank PHP file upload detected|Shell spawned in VulnBank"
```

**기대 증적** — Falco 로그에 두 룰의 발화:

- `CRITICAL VulnBank PHP file upload detected` (웹 디렉터리에 PHP 파일 생성)
- `WARNING Shell spawned in VulnBank container` (비인가 셸)

---

## 실험 3 — SBOM 재스캔 (시간축 재평가)

axios·node-ipc류는 침해 *직후*엔 advisory가 없어 빌드 시점 SCA가 못 잡는다. 핵심은 **재빌드 없이, 저장된 SBOM만으로** 며칠 뒤 공개된 CVE의 영향 여부를 답하는 것이다.

```bash
# 빌드 때 저장한 SBOM을 오늘 갱신된 취약점 DB로 재스캔
# (SBOM은 CI 아티팩트/Harbor에 보관. 없으면 이미지에서 즉석 생성)
syft <HARBOR>/secure-delivery/vulnbank-msa-user-service:<TAG> -o spdx-json > user-service.spdx.json

trivy sbom user-service.spdx.json --severity CRITICAL,HIGH
```

**기대 증적** — 원본 빌드 이후 NVD/GHSA에 새로 등재된 CVE가 SBOM의 패키지에 매칭되어 출력된다. 이미지를 다시 빌드하지 않고도 "우리 배포본이 그 악성/취약 버전을 쓰는가"를 즉시 답한 것 — 이게 시간축 방어다.

---

## 결과 기록

핵심 3종은 **AWS 라이브로 실증 완료**했다(증적 `reports/dev/aws-live/evidence-summary.md`). 아래 표가 그 결과이며, 다른 환경에서 재현하면 같은 절차로 동일 증적을 캡처할 수 있다.

| 실험 | 입증하는 주장 | 증적 | 상태 |
| --- | --- | --- | --- |
| 1 · egress 차단 | RAT C2·exfil 무력화 | Hubble `DROPPED`(SYN)·`http_code=000` (cmd `ba96945a`) | <span class="st st--done">실증완료</span> |
| 2 · Falco | 페이로드 실행 행위 탐지 | 웹쉘 `Critical`(18:31:55)·셸 spawn `Warning`(룰 수정 후 발화) | <span class="st st--done">실증완료</span> |
| 3 · SBOM 재스캔 | 시간축 재평가 | `trivy sbom` → 빌드 당시 없던 2026 CVE 3건 식별 | <span class="st st--done">실증완료</span> |

<div class="sb-key" markdown>
세 실험 모두 **VulnBank 네임스페이스에만** 작용하고 한 줄 명령으로 롤백된다. 같은 클러스터를 쓰는 다른 작업에는 영향이 없으며, **추가 VM도 만들지 않는다**. 누가 실행하든 같은 명령에서 같은 증적이 나오는 것 — 그것이 이 프로젝트가 "주장"과 다른 지점이다.
</div>
