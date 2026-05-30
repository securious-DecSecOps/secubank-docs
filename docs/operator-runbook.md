---
title: 운영자 런북
---

# 운영자 런북

<div class="sb-lede" markdown>
"어디에 접속하고, 어디서 로그를 보고, 무엇이 어떻게 연결됐는가." 팀원이 인계받아 바로 움직일 수 있도록, 접속점·로그 위치·연동 메커니즘을 한 면에 모았다. 비밀번호는 적지 않는다 — 접속 *방법*만 적는다.
</div>

전제: SSH(22)는 닫혀 있고 **전부 SSM으로 접속**한다. AWS는 `--profile secubank --region ap-northeast-2`(계정 `428156589833`).

## 1. 무엇에 어떻게 접속하나

| 대상 | 노드 | 포트/엔드포인트 | 접속 | 인증 출처 |
| --- | --- | --- | --- | --- |
| VM 셸 | 전 노드 | — | `ssm start-session` | IAM |
| Jenkins | CI `i-01011276c12b34d2c` | `:8083` | SSM 포트포워딩 | admin 계정 |
| Harbor | CI | `:8082` (`/v2/`) | SSM 포트포워딩 | 토큰/계정(익명 401) |
| SonarQube | CI | `:9000` | SSM 포트포워딩 | admin/토큰 |
| DefectDojo | DD `i-04d99f7279f7144e7` | `:8080`·`:8443`, `/api/v2/` | SSM 포트포워딩 | 세션 / API 토큰 |
| ArgoCD | runtime `i-05d583e02dcb52aef` | `svc/argocd-server` | port-forward (2단) | `argocd-initial-admin-secret` |
| Hubble UI | runtime | `svc/hubble-ui` | `cilium hubble ui` / port-forward | — |
| 앱(VulnBank) | runtime | `svc/vulnbank-msa-frontend:8080` | port-forward | — |
| k3s API | runtime | `:6443` | SSM 셸 → `k3s kubectl` | k3s 인증서 |

```bash title="접속 두 패턴"
# (a) VM 셸
aws ssm start-session --target <id> --profile secubank --region ap-northeast-2

# (b) VM에 직접 뜬 웹 UI (Jenkins/Harbor/Sonar/DefectDojo) — 1단 포트포워딩
aws ssm start-session --target <id> --profile secubank --region ap-northeast-2 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["8083"],"localPortNumber":["8083"]}'
#  → 브라우저 localhost:8083

# (c) 클러스터 내부 서비스(ArgoCD/Hubble/앱): 런타임 셸에서 port-forward + (b) 2단
k3s kubectl -n argocd port-forward --address 0.0.0.0 svc/argocd-server 8443:443
```

!!! note "런타임 kubectl"
    `KUBECONFIG=/etc/rancher/k3s/k3s.yaml`, 명령은 `k3s kubectl`. 앱 네임스페이스는 `secure-path-dev`.

## 2. 로그는 어디서 보나 (트러블슈팅)

VulnBank 서비스는 전부 PHP 파드라 **stdout/stderr → `kubectl logs`** 로 나온다. 증상별로 보는 곳이 다르다.

| 증상 | 어디서 났나 | 명령 |
| --- | --- | --- |
| **Permission denied / 403** | 앱(PHP) 로직 | `k3s kubectl -n secure-path-dev logs -f <pod>` |
| **Access denied for user** | DB(MariaDB) 권한 | `… logs vulnbank-db-… \| grep -i denied` |
| **파일 EACCES / not writable** | 서비스 컨테이너 내부 | `… exec <pod> -- sh -c 'tail /var/log/apache2/error.log 2>/dev/null'` |
| **연결 안 됨 / timeout** | 네트워크 정책(egress) | `hubble observe --namespace secure-path-dev --type drop` |
| **셸/웹쉘 탐지 등 행위** | Falco (`falco` ns) | `k3s kubectl -n falco logs <falco-pod> \| grep -iE 'Warning\|Critical'` |
| **파드가 안 뜸 / CrashLoop** | kubelet·이벤트 | `… describe pod <pod>` · `… logs <pod> --previous` |
| **노드/런타임 레벨** | k3s journald | `journalctl -u k3s -n 200` |

```bash title="라이브로 잡기 — 로그를 따라가며 재현"
k3s kubectl -n secure-path-dev logs -f deploy/frontend     # 게이트웨이(요청 라우팅)
k3s kubectl -n secure-path-dev logs -f deploy/file-service # 업로드 관련이면 여기
# 그리고 문제 동작을 다시 실행 → 그 순간 찍히는 줄을 본다
```

!!! tip "어느 파드부터?"
    `frontend`(게이트웨이)에서 어디로 라우팅됐는지 보고, 해당 서비스(`user`/`transaction`/`status`/`settings`/`file-service`)와 `vulnbank-db`를 본다. "Permission denied"는 보통 ① DB 권한(vulnbank-db 로그의 `Access denied for user`) ② 파일 권한(업로드 경로 EACCES) ③ 앱 authz(403) 셋 중 하나다.

## 3. CI → DefectDojo 연동 (어떻게 꽂았나)

별도 Jenkins 잡 **`secubank-sast-defectdojo-test`** 가 스캔 리포트를 DefectDojo의 `import-scan` API로 POST한다.

```bash title="실제 호출 (Jenkins 잡)"
DD_URL='http://10.0.1.134:8080'
curl -s -X POST "$DD_URL/api/v2/import-scan/" \
  -H "Authorization: Token $DD_TOKEN" \   # Jenkins 크리덴셜
  -F "scan_type=Trivy Scan" \             # ★ 도구별 파서 (이 값만 바꿔 4종 입수)
  -F "engagement=$ENGAGEMENT_ID" \        # =1
  -F "file=@reports/trivy-fs-report.json" \
  -F "active=true" -F "verified=false" -F "close_old_findings=false" -F "scan_date=$(date +%F)"
```

| scan_type | 파일 | 실행 결과(2026-05-28) |
| --- | --- | --- |
| `Gitleaks Scan` | gitleaks-report.json | High 1 (test 3) |
| `Checkov Scan` | checkov-report.json | Medium 4 (test 5) |
| `Trivy Scan` | trivy-fs-report.json | 45건 · Crit 6·High 22·Med 15·Low 2 (test 6) |
| `CycloneDX Scan` | syft-cyclonedx.json | SBOM 인벤토리 (test 9) |

모델은 **Product(VulnBank id 1) → Engagement(id 1) → Test(import마다 생성)**. 응답에 dedup·생애주기 통계(`active/verified/duplicate/false_p/is_mitigated/risk_accepted`)가 함께 온다. `active=true, verified=false`로 들이므로 *트리아지 대기* 상태로 쌓인다.

!!! warning "정직한 경계"
    import이 **동작하는 건 4종**(Gitleaks·Checkov·Trivy·CycloneDX) — 위가 그 증거다. 단 이건 **별도 잡**이고 자체 `reports/*.json`(demo-sast)을 쓰며, 메인 파이프라인의 `reports/dev/<build>/<도구>/` 규약과 SonarQube import은 **아직 통합 전**이다.

## 4. 알아둘 클러스터 상태

- **상시 egress 정책**: `secure-path-dev`에 `secure-path-dev-egress-baseline`(Cilium) 적용 중 — *클러스터 내부는 허용, 외부(world)는 차단*. 앱은 정상 동작(검증됨). 외부 API 호출 기능을 추가하면 이 정책에 allow를 더해야 한다.
  ```bash
  k3s kubectl get cnp -n secure-path-dev          # 확인
  k3s kubectl delete cnp secure-path-dev-egress-baseline -n secure-path-dev   # 롤백(필요 시)
  ```
- **컨테이너 root 실행**: VulnBank 컨테이너는 root(uid 0)로 돈다(의도된 취약 상태). Falco가 셸 spawn을 탐지한다.
- **인증서 만료**: k3s leaf 인증서 `2027-05-28` 만료 → `k3s certificate rotate`. CA는 2036.
