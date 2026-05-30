---
title: 2화 · 근데 이걸 누가 다 돌려요?
---

# 2화 · "근데 이걸 누가 다 돌려요?"

## 🎬 사건

작업장이 섰고(1화), A는 도구를 깔았다. Gitleaks, SonarQube, Checkov, Trivy… 하나씩 돌려보니 다 된다. 그런데 시니어가 묻는다.

> **시니어**: "그래서, 개발자가 push할 때마다 그거 *네가 일곱 개를 손으로* 돌릴 거야? 결과는 어디 모으고? 누가 '이건 막아야 한다'를 종합 판정하지?"

A는 또 막혔다. **도구가 있는 것**과 **도구가 엮여 자동으로 판단하는 것**은 다르다. 깔려만 있으면 그냥 "딸깍"이다. 필요한 건 — push 한 번에 일곱 검사가 *순서대로* 돌고, 결과가 *한곳에 모이고*, 기준에 따라 *막거나 통과*시키는 **파이프라인**이다.

![STAGE 2 · 파이프라인이 도구를 엮는다](../assets/img/textbook/textbook-stage2.png){ loading=lazy }

## 💡 해결책 — Jenkins 파이프라인 (Jenkinsfile)

A는 Jenkins에서 **Pipeline Job**을 하나 만들고, `Jenkinsfile.aws-ci`를 가리킨다. 핵심은 *코드를 안 고치고 **파라미터로 연결**한다*는 것 — 이 파라미터가 바로 "어느 설정을 바꿔 잇는가"의 답이다.

```groovy title="Jenkinsfile.aws-ci — 연결은 전부 파라미터로"
parameters {
  string(name: 'APP_SOURCE_REPO_URL', defaultValue: '…/app-source-repo.git')  // 검사할 앱 소스
  string(name: 'GITOPS_REPO_URL',     defaultValue: '…/gitops-manifest-repo.git') // 배포 매니페스트
  string(name: 'SERVICES', defaultValue: 'user-service,transaction-service,…')   // 빌드·스캔 대상
  string(name: 'REGISTRY_URL',  defaultValue: '10.0.1.169:8082')                 // Harbor 연결
  string(name: 'SONAR_HOST_URL', defaultValue: 'http://localhost:9000')          // SonarQube 연결
  password(name: 'SONAR_TOKEN')                                                  // (Jenkins credential)
  booleanParam(name: 'ENFORCE_GATE', defaultValue: false)                        // 막을까, 기록만 할까
}
```

### 연결 1 — 세 레포를 끌어온다 (소스/운영 분리)

CI 레포에는 앱 소스도, 매니페스트도 *중복으로 들고 있지 않는다.* 필요할 때 추가로 checkout한다.

```groovy title="Jenkinsfile.aws-ci"
dir('app-source-repo')      { checkout([..., userRemoteConfigs: [[url: "${APP_SOURCE_REPO_URL}"]]]) }
dir('gitops-manifest-repo') { checkout([..., userRemoteConfigs: [[url: "${GITOPS_REPO_URL}"]]]) }
```

### 연결 2 — 모든 도구가 *같은 칸*에 결과를 쓴다 (이게 핵심 계약)

A가 진짜 "아하"한 부분. 빌드마다 결과를 모을 **약속된 폴더 구조**를 먼저 판다.

```bash title="Jenkinsfile.aws-ci — Prepare Metadata"
REPORT_DIR="reports/dev/${BUILD_NUMBER}"
mkdir -p "${REPORT_DIR}"/{gate,registry,checkov,gitleaks,sonarqube,kubescape,sbom,trivy}
```

이제 규약은 단순하다 — **Gitleaks는 `…/gitleaks/`에, Trivy는 `…/trivy/`에, 각자 자기 칸에 JSON을 쓴다.** 도구끼리 직접 대화하지 않는다. *파일 시스템의 약속*으로 느슨하게 연결된다. 새 도구를 끼우고 싶으면? 자기 칸에 결과만 쓰면 끝.

### 연결 3 — 게이트가 그 칸들을 읽어 *판단을 코드화*한다

마지막 한 스테이지가 모든 칸을 읽어 종합한다.

```groovy title="Jenkinsfile.aws-ci"
stage('Security Gate') { steps { sh 'bash scripts/security-gate-services.sh' } }
```

```python title="security-gate-services.sh — 각 도구 칸을 glob으로 읽는다"
files = glob.glob(os.path.join(gitleaks_dir, "*.json"))   # …/gitleaks/*.json 전부
# 임계값과 비교 — 시크릿 0개, CRITICAL 0개, HIGH 3개 초과면 BLOCK
print(f"GITLEAKS_GATE_RESULT={'BLOCK' if blocked else 'PASS'}")
```

임계값도 파라미터다 — `GATE_MAX_CRITICAL=0`, `GATE_MAX_HIGH=3`, `GITLEAKS_MAX_FINDINGS=0`. 결과는 `…/gate/aggregated-summary.txt`로 종합되고, `ENFORCE_GATE=true`면 push 전에 빌드를 *실패*시킨다.

## 🔍 결과

A가 push 한 번을 하자 — 18개 스테이지가 순서대로 돌고, `reports/dev/3/` 아래 도구별 칸에 증적이 쌓이고, 게이트가 종합 판정을 내렸다. **딸깍이 아니라, 흐름이 생겼다.**

> 🎤 이제 A는 한 문장으로 설명한다. *"개발자 push → 다중 레포 체크아웃 → 7종 검사가 각자 REPORT_DIR에 기록 → 게이트가 임계값으로 종합 판정 → 통과분만 레지스트리로."*

## ⚠️ 한계 — 면접관이 찌른다

- **"파라미터에 토큰을 평문으로?"** → 아니다. `SONAR_TOKEN`·레지스트리 비번은 **Jenkins Credentials**로 주입해야 한다(파라미터 기본값에 박으면 안 됨).
- **"이게 CD까지인가요?"** → 아니다. 이 파이프라인은 **이미지 push까지**다. GitOps 태그 자동 갱신 스테이지는 *없다* — CD는 도입사가 붙인다([8화에서 다룬다]).
- **"도구가 죽으면요?"** → 각 스캔이 빈/에러 JSON이라도 자기 칸에 남기게 설계됐지만, 게이트가 "결과 없음"을 *통과*로 오인하지 않도록 검증이 필요하다.

## 🧭 시니어의 4가지 렌즈

| 렌즈 | 이 통제가 의미하는 것 |
| --- | --- |
| **기술 (Tech)** | `REPORT_DIR` 규약으로 도구를 *느슨하게* 결합 — 추가·교체가 파이프라인 수정 없이. 게이트가 흩어진 결과를 한 판정으로 |
| **규제 (Regulation)** | ISMS-P 2.8 개발보안·2.9 변경관리 / PCI-DSS Req 6.x / 전자금융 보호대책 — "배포 전 검증 절차의 표준화·기록" |
| **정책 (Policy)** | 게이트 임계값(`CRITICAL 0`·`HIGH 3`·`시크릿 0`)이 곧 **조직의 위험 허용선(risk appetite)을 코드로 박은 것**. `ENFORCE_GATE`는 "차단할까, 기록만 할까"의 정책 스위치 |
| **관리 (Governance)** | 그 임계값과 예외(`ENFORCE_GATE=false`)는 *누가* 정하나 → **보안책임자의 리스크 수용 결정**이다(엔지니어가 임의로 끄면 안 됨). `REPORT_DIR` 증적은 감사·경영 보고의 원천 |

> 🎤 **면접 한 줄**: *"게이트 임계값은 기술 설정이 아니라 조직의 위험 허용선입니다. 그래서 그 숫자와 예외 승인은 보안책임자가 소유하고, 파이프라인은 그 정책을 집행할 뿐입니다."*

---

뼈대가 섰다. 이제 그 첫 관문에 무엇이 걸리는지 보자 — push 한 번에, A의 코드에서 비밀번호가 튀어나온다.

> 다음 → **3화 · "API 키가 깃허브에 올라갔어요"**
