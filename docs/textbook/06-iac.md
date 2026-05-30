---
title: 6화 · 컨테이너가 root로 돌아요
---

# 6화 · "컨테이너가 root로 돌아요"

## 🎬 사건

보안팀 정기 점검에서 지적이 날아왔다.

> **보안팀**: "결제 서비스 컨테이너들… 전부 **root(uid 0)로** 돌고 있네요. 만약 앱이 뚫리면, 공격자가 컨테이너 안에서 *루트 권한*을 그대로 쥐는 거예요."

A는 당황했다. 앱 코드(SAST·DAST)는 그렇게 봤는데, *컨테이너와 K8s 설정*은 들여다본 적이 없었다. Dockerfile에 `USER`도 없고, 매니페스트에 `runAsNonRoot`도, 권한 제한도 없었다.

> **A**: "코드 말고… *설정*은 누가 검사하지?"

## 💡 해결책 — Checkov(IaC) + Kubescape(K8s 프레임워크)

두 도구는 겹치지만 *같은 질문을 하지 않는다.*

- **Checkov** — Dockerfile·Helm·K8s 매니페스트의 *알려진 미스컨피그*를 룰로 본다(컨테이너 root, 권한 과다, 미설정 등).
- **Kubescape** — K8s 리소스를 **NSA·MITRE ATT&CK·CIS** 같은 *보안 프레임워크* 기준으로 점수화한다.

```bash title="devsecops-path/scripts (실제) — Kubescape는 프레임워크별로 차트를 스캔"
kubescape scan framework "${framework}" "${HELM_CHART_DIR}" \
  --format json --output "${output_json}"
# framework = nsa, mitre, cis 각각에 대해 실행 → REPORT_DIR/kubescape/
```

### 🔌 파이프라인에 어떻게 꽂히나
- **스테이지**: `Checkov IaC Scan`, `Kubescape K8s Manifest Scan` (2화 파이프라인의 두 칸)
- **대상**: 둘 다 `HELM_CHART_DIR`(gitops 레포에서 체크아웃한 Helm 차트)을 본다 — *배포되기 전의 선언*을 검사
- **출력**: `REPORT_DIR/checkov/*.json`, `REPORT_DIR/kubescape/*.json` → 게이트가 `CHECKOV_MAX_CRITICAL`로 판정

## 🔍 돌려봤더니

```
Checkov   : 30 findings (컨테이너 root 실행 등 — CWE-250/732, CIS Docker)
Kubescape : NSA  14/20 통과 (6 실패)
            MITRE 16/17 통과 (1 실패)
            CIS  26/33 통과 (2 실패)
```

(Build #3 실측) 컨테이너가 root로 돈다는 보안팀의 지적은 **사실**이었다 — Checkov가 정확히 짚었고, Kubescape의 CIS 점수도 그 빚을 드러냈다.

## ⚠️ 한계 — 면접관이 찌른다

- **"프레임워크 점수가 높으면 안전한가요?"** → 아니다. 설정 점검은 *선언된 매니페스트*를 본다 — **런타임에 실제로 무슨 일이 일어나는지**(프로세스·네트워크 행위)는 못 본다. CIS 26/33은 "설정 위생"이지 "공격 차단"이 아니다.
- **"Checkov랑 Kubescape 둘 다 필요해요?"** → 관점이 다르다(IaC 미스컨피그 vs K8s 프레임워크 정합). 겹치는 부분은 *교차검증*, 안 겹치는 부분이 각자의 가치.
- **"30건·6실패를 다 고쳐요?"** → 전부가 같은 위험은 아니다. root 실행처럼 *공격 시 권한 상승*으로 이어지는 것부터 우선순위로 — 트리아지가 필요하다.

## 🧭 시니어의 4가지 렌즈

| 렌즈 | 이 통제가 의미하는 것 |
| --- | --- |
| **기술 (Tech)** | 배포 *전* 선언(Dockerfile·Helm)의 미스컨피그를 점검 — root 실행·권한 과다 등. 런타임 행위는 못 봄 |
| **규제 (Regulation)** | ISMS-P 2.10 시스템·서비스 보안관리(K8s 보안설정)·2.6 접근통제 / CIS Kubernetes Benchmark / 전자금융 정보처리시스템 보호 |
| **정책 (Policy)** | "컨테이너는 비루트·최소권한"을 *조직 기준선*으로 정하고 매니페스트 단계에서 강제 — Pod Security·CIS 프로파일이 곧 정책 |
| **관리 (Governance)** | NSA/MITRE/CIS 점수는 *경영 보고용 지표*로 추세 관리. 어느 실패를 언제까지 고칠지(예외·만료)는 보안책임자가 소유 |

> 🎤 **면접 한 줄**: *"Checkov·Kubescape는 '설정 위생'을 자동화합니다. 다만 CIS 점수가 높다고 안전한 게 아니라 — 그건 선언일 뿐, 런타임에 실제로 막히는지는 Falco·Cilium(뒤 장)이 증명합니다."*

---

코드(SAST)도, 실행(DAST)도, 설정(IaC)도 봤다. 이제 A는 *빌드된 이미지 안*을 들여다본다. Trivy를 돌리자 — 화면에 CVE가 **수천 개** 뜬다.

> 다음 → **7화 · "이미지에 CVE가 6천 개?"** — Trivy·SBOM
