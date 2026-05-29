# 코드 · 설정 맵 (Repository & File Map)

> 오픈소스 사용자를 위해 **"어떤 기능이 어느 repo의 어느 파일에 있는가"** 를 정리한다. 파이프라인·IaC·매니페스트는 공개 대상이다. (비밀번호·토큰·민감 IP는 저장소에 두지 않으며, 본 문서에도 포함하지 않는다.)

## 4개 repo 역할

| Repo | 역할 |
| --- | --- |
| [`app-source-repo`](https://github.com/securious-DecSecOps/app-source-repo) | VulnBank MSA 애플리케이션 소스(6 서비스) |
| [`infra-terraform-repo`](https://github.com/securious-DecSecOps/infra-terraform-repo) | AWS 인프라(Terraform) + EC2 부트스트랩(user-data) |
| [`devsecops-path`](https://github.com/securious-DecSecOps/devsecops-path) | CI 파이프라인(Jenkinsfile) + 스캐너/게이트/배포 스크립트 |
| [`gitops-manifest-repo`](https://github.com/securious-DecSecOps/gitops-manifest-repo) | Helm 차트 · ArgoCD App · 런타임 플랫폼 매니페스트 |

## ★ 파이프라인 단계 → 구현 파일 (가장 빠른 길)

`Jenkinsfile.aws-ci`(`devsecops-path`)의 각 stage가 호출하는 스크립트:

| Stage | 무엇 | 파일 (`devsecops-path/`) |
| --- | --- | --- |
| Checkout (App/GitOps) | 멀티 repo 체크아웃 | `Jenkinsfile.aws-ci` |
| Gitleaks Secret Scan | 시크릿 스캔 | `scripts/gitleaks-scan-repos.sh` |
| SonarQube SAST | 코드 정적분석 | `scripts/sonarqube-scan-services.sh` |
| Checkov IaC Scan | IaC 설정 점검 | `scripts/checkov-scan-services.sh` |
| Kubescape K8s Scan | K8s 프레임워크 점검 | `scripts/kubescape-scan.sh` |
| Docker Build | 6 서비스 이미지 빌드 | `scripts/build-services.sh` |
| Generate SBOM | 부품명세 생성 | `scripts/generate-sbom.sh` |
| Trivy Scan | 이미지 CVE | `scripts/trivy-scan-services.sh` |
| Security Gate | 집계·차단 판정 | `scripts/security-gate-services.sh` |
| Registry Login / Push | Harbor push | `scripts/registry-login.sh` · `scripts/push-services.sh` |
| **Notify (SNS)** | 게이트 결과 알림 | `scripts/notify-sns.sh` |
| Collect / Archive | 증적 수집·아카이브 | `scripts/collect-msa-evidence.sh` |
| *(배포; CD)* | GitOps 태그 갱신·ArgoCD | `scripts/update-gitops-services.sh` · `scripts/deploy-argocd.sh` |
| *(비즈로직 DAST)* | 음수송금·IDOR·웹쉘 재현 | `scripts/test-msa-integration.sh`, `bootstrap/local-wsl/verify.sh` |

## 인프라 (Terraform) — `infra-terraform-repo`

| 무엇 | 경로 |
| --- | --- |
| VPC·Subnet·IGW·라우팅 | `modules/network/` |
| IAM(EC2 SSM 역할) | `modules/iam/` |
| Security Group(역할별) | `modules/security-groups/` |
| EC2(CI·runtime·DefectDojo) | `modules/ec2/` |
| 환경 조립·변수·출력 | `envs/dev/{main,variables,outputs}.tf` |
| **CI VM 부트스트랩** | `scripts/user-data/ci-server.sh` (docker·Harbor·Jenkins·스캐너6·helm·aws-cli v2) |
| **Runtime VM 부트스트랩** | `scripts/user-data/runtime-server.sh` (k3s·Cilium·ArgoCD·GitOps root app) |
| DefectDojo VM 부트스트랩 | `scripts/user-data/defectdojo-server.sh` |

## 런타임 / GitOps — `gitops-manifest-repo`

| 무엇 | 경로 |
| --- | --- |
| VulnBank Helm 차트 | `helm/vulnbank-msa/` (`templates/{deployment,service,database,db-init-*}.yaml`) |
| 환경별 values | `apps/vulnbank-msa/dev/values.yaml` · `apps/vulnbank-msa/aws-dev/values.yaml` |
| ArgoCD app-of-apps(root) | `argocd/root/aws-dev.yaml` |
| ArgoCD 자식 앱 | `argocd/aws-apps/*.yaml` (vulnbank·cilium-hubble·falco·kube-bench·owasp-zap) |
| 런타임 플랫폼 | `platform/cilium-hubble/` · `platform/falco/` · `platform/kube-bench/` · `platform/owasp-zap/` |
| 제로트러스트 정책 | `platform/cilium-hubble/network-policies/{default-deny,allow-vulnbank}.yaml` |

## 애플리케이션 — `app-source-repo`

| 무엇 | 경로 |
| --- | --- |
| 6 MSA 서비스 | `examples/vulnbank-msa/services/{user,transaction,status,file,settings,frontend}-service/` |
| 서비스별 Dockerfile | `examples/vulnbank-msa/services/<svc>/Dockerfile` |
| 의도된 취약점 위치 | transaction(음수송금)·transaction/settings(IDOR)·file(업로드 RCE) — 상세 [탐지 효능](detection-efficacy.md) |

## 이 문서 사이트 — `secubank-docs`

| 무엇 | 경로 |
| --- | --- |
| 아키텍처 다이어그램(diagram-as-code) | `diagram/architecture.py` |
| 증적 흐름 다이어그램 | `diagram/evidence.py` |
| 페이지 콘텐츠 | `docs/*.md` |
| 커스텀 랜딩 템플릿·스타일 | `overrides/home.html` · `docs/stylesheets/extra.css` |
| 사이트 설정·배포 | `mkdocs.yml` · `.github/workflows/docs.yml` |

!!! note "재현성"
    인프라는 `terraform apply` + user-data로 1회 부트스트랩되고, 배포는 GitOps(ArgoCD)로 선언적으로 동기화된다. 다이어그램조차 코드(`diagram/*.py`)로 생성되어 재현 가능하다. 새 워크로드 온보딩 방법은 코드/설정으로 새 워크로드 온보딩(아래 표) 참고.
