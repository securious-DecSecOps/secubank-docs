---
title: 1화 · 그거 어디서 돌릴 건데요?
---

# 1화 · "그거 어디서 돌릴 건데요?"

## 🎬 사건

미션을 받은 A는 의욕이 넘쳤다. 노트북에 `trivy`를 깔고, 첫 스캔을 돌리려는 순간 — 시니어가 모니터를 들여다본다.

> **시니어**: "그거 어디서 돌릴 건데?"
> **A**: "어… 제 노트북에서요?"
> **시니어**: "다음 사람은? 너 휴가 가면? 그리고 운영 서버엔 어떻게 접속할 건데. SSH 키 슬랙으로 돌릴 거야?"

A는 말문이 막혔다. 보안 도구를 *돌리기도 전에* 두 개의 벽에 부딪혔다 — **(1) 검사를 돌릴 일관된 공간이 없다.** "내 노트북에선 됐는데"는 사고의 시작이다. **(2) 서버 접속이 안전하지 않다.** 키는 새고, 누가 들어왔는지 남지 않는다.

## 💡 해결책 1 — "인프라를 코드로" (terraform)

시니어가 저장소 하나를 가리킨다. `infra-terraform-repo`. A가 `terraform apply` 한 줄을 치자, 몇 분 뒤 AWS에 **VM 세 대**가 떴다.

![STAGE 1 · 빈 작업장](../assets/img/textbook/textbook-stage1.png){ loading=lazy }

> 아직은 **빈 VM 세 대**다 — CI용, 런타임(k3s)용, 증적(DefectDojo)용. 12화 동안 여기에 무기가 하나씩 쌓인다.

A가 친 한 줄이 *무엇을* 만들었는지, 코드로 보자.

```hcl title="infra-terraform-repo/envs/dev/main.tf"
module "network"         { source = "../../modules/network" ... }  # VPC · 서브넷 · IGW
module "iam"             { source = "../../modules/iam"     ... }  # VM이 달 IAM Role
module "security_groups" {
  source             = "../../modules/security-groups"
  allowed_admin_cidr = var.allowed_admin_cidr                      # ← 관리 접근을 '내 IP'로 제한
}
module "ec2" {
  ci_user_data      = file(".../scripts/user-data/ci-server.sh")   # VM이 켜지며 스스로 무장
  runtime_user_data = file(".../scripts/user-data/runtime-server.sh")
}
```

**왜 terraform인가?** 손으로 세팅한 서버는 *다음에 똑같이 못 만든다*. 코드로 박으면 누가, 언제, 무엇을 깔았는지 git에 남고, 날려도 한 줄로 재현된다. "내 노트북에선 됐는데"가 사라진다.

그리고 `ci_user_data` — VM은 켜지면서 **스스로 도구를 깐다.**

```bash title="infra-terraform-repo/scripts/user-data/ci-server.sh (발췌)"
dnf install -y docker git jq java-21-amazon-corretto jenkins   # Java 17로 깔면 Jenkins 안 뜸(실제 함정)
usermod -aG docker jenkins                                     # 파이프라인이 호스트 docker로 빌드

# 다음 화부터 등장할 무기들이 여기서 설치된다
curl -sfL .../trivy/install.sh   | sh   # 이미지·SBOM 취약점
curl -sSfL .../syft/install.sh   | sh   # SBOM 생성
# gitleaks(시크릿) · kubescape(K8s) 도 함께
```

## 💡 해결책 2 — "SSH를 없앤다" (SSM)

작업장은 섰다. A는 습관대로 접속을 시도한다. `ssh ec2-user@…` — **안 된다.** 22번 포트가 닫혀 있다.

> **A**: "어… SSH가 안 되는데요?"
> **시니어**: "응, 없앴어. 이거 써."

```bash
aws ssm start-session --target i-05d583e02dcb52aef
```

세션이 열린다. **왜 SSH를 없앴나?** 키는 분실·유출·공유의 온상이고, 누가 언제 들어왔는지 추적도 약하다. SSM은 **키 없이 IAM 권한으로** 들어가고(그래서 아까 `module.iam`이 필요했다), **모든 접속이 CloudTrail에 기록**된다.

<div class="sb-key" markdown>
📓 **A의 깨달음**: 보안의 시작은 도구를 더 까는 게 아니라 *"누가 무엇을 했는지 남는가"*다. 핵심은 "SSH를 없앴다"가 아니라 **"접근을 IAM + 감사 로그로 통제했다"**.
</div>

## ⚠️ 한계 — 면접관이 여기를 찌른다

미화하지 말자. 이 작업장에도 빈틈이 있다.

- **"SSM이면 완벽한가요?"** → 아니다. SSM 에이전트가 죽거나 IAM이 꼬이면 *들어갈 길이 없다.* 실무는 **비상(break-glass) 경로**를 따로 둔다.
- **"VM이 퍼블릭 서브넷에 있네요?"** → 그렇다. `allowed_admin_cidr`로 관리 접근을 내 IP로 좁혔지만, 프로덕션이라면 **프라이빗 서브넷 + Bastion/VPN**이 정석이다. PoC라 단순화한 것 — 그 트레이드오프를 *아는 게* 실력이다.
- **"레지스트리를 http로요?"** → 그렇다. 사설망 안이라 감수했지만 **TLS가 없다.** 공급망 무결성 관점의 갭이고, 뒤 화에서 다시 만난다.

> A는 첫날 배운다 — **"세웠다"와 "안전하다"는 다르다.** 이 교본은 그 거리를 좁히는 이야기다.

## 📋 이건 '좋은 습관'이 아니라 규제 요구다

나중에 A는 알게 된다 — SSH를 없애고 접속을 IAM·로그로 통제한 게 단지 깔끔해서가 아니라, **감사에서 요구되는 통제**라는 걸.

| 프레임워크 | 항목 | 이 장의 통제가 충족하는 것 |
| --- | --- | --- |
| **ISMS-P** | 2.6 접근통제 · 2.5 인증·권한관리 | SSH 제거 + IAM 기반 접속 + `allowed_admin_cidr` = 시스템 접근권한 최소화·인증 통제 |
| **ISMS-P** | 2.9/2.11 접속기록 | SSM → CloudTrail 접속 로깅 = 접근 기록 보관·감사 추적 |
| **PCI-DSS** | Req 7·8·10 | 최소권한 접근 · 공유 SSH키 금지 · 접속 감사로그 |
| **전자금융감독규정** | 접근통제·접속기록 관리 | 관리자 접근 통제 및 기록 |

> 🎤 **면접 한 줄**: *"SSM을 택한 건 편해서가 아니라, ISMS-P 2.6 접근통제와 접속기록 요구를 키 없이·로그와 함께 충족하기 때문입니다."*

---

작업장은 섰다. A는 뿌듯한 마음으로 *첫 스캔*을 돌린다. 그런데 결과가 뜨자마자 — 자기 회사 코드에서 **비밀번호가 튀어나온다.**

> 다음 → **2화 · "API 키가 깃허브에 올라갔어요"**
