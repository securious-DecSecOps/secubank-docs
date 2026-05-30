---
title: 5화 · 남의 거래내역이 보여요
---

# 5화 · "남의 거래내역이 보여요"

## 🎬 사건

고객센터로 항의가 들어왔다.

> **고객**: "제 화면에… 모르는 사람의 회원정보 수정 화면이 떠요. 계좌번호만 바꿨더니 *남의 정보가* 보여요."

A는 굳었다. **IDOR**(Insecure Direct Object Reference) — 요청에 담긴 ID만 바꾸면 *남의 자원*에 접근된다. 인가(authorization) 검증이 빠진 것이다. 4화에서 봤듯 SAST는 이런 걸 **0/4**로 놓쳤다. 코드를 *읽는* 것으로는 "이 요청자가 이 자원의 주인인가"를 알 수 없으니까.

> **A**: (결심) "그럼 방법은 하나다. **직접 공격해본다.**"

## 💡 해결책 — DAST, "공격자처럼 실제 요청을 쏜다"

**왜 DAST인가?** SAST가 코드를 *읽는다*면, DAST(Dynamic)는 **떠 있는 앱에 실제 HTTP 요청을 쏜다.** 인가·비즈니스 로직 결함은 *실행해봐야* 드러난다. A는 `verify.sh`(커스텀 DAST)로 자기 서비스를 공격한다.

```bash title="scripts/test-msa-integration.sh — 실제 공격 시퀀스 (발췌)"
# 1) 로그인해서 토큰을 얻고
curl_form "login" "/api/v1/auth/login" \
  --data-urlencode "username=${LOGIN_USERNAME}" \
  --data-urlencode "password=${LOGIN_PASSWORD}"
# 2) 음수 송금 — 금액에 -10을 넣는다 (NEGATIVE_AMOUNT=-10)
curl_form "negative-transfer" "/api/v1/transactions/transfer" \
  --data-urlencode "amount=${NEGATIVE_AMOUNT}"
# 3) IDOR — 남의 ID(IDOR_TARGET_ID=2)로 회원정보 수정을 시도
curl_form "idor-user-update" "/api/v1/settings/infoupdate" ...
```

### 🔌 파이프라인에 어떻게 꽂히나
- SAST·SCA와 달리 DAST는 **떠 있는 앱**이 대상이다. `verify.sh`가 frontend 게이트웨이로 요청을 쏘고, 요청/응답을 `reports/dev/.../evidence/`에 캡처한다(증적).
- 즉 빌드 시점이 아니라 *배포된 서비스*를 친다 — 그래서 런타임/스테이징 환경과 엮인다.

## 🔍 돌려봤더니 — 0/4가 3/4로

A가 AWS에 떠 있는 frontend(ClusterIP)로 공격을 쏘자 — *실제로 뚫렸다.* (이 프로젝트에서 직접 실행한 결과)

```
PASS: negative transfer request accepted          # 음수송금 — 잔액 조작 (VULN-1)
PASS: IDOR user update request accepted (user id 2) # 남의 회원정보 수정 (VULN-3)
PASS: uploaded PHP file executed through frontend   # 웹쉘 RCE 실행 (VULN-4)
```

**SAST 0/4 → DAST 3/4.** SAST가 손도 못 댄 음수송금·IDOR·웹쉘 RCE를 DAST가 *실제 요청으로* 재현했다. (나머지 1개, 거래내역 IDOR은 스크립트에 미포함 → 케이스 추가 시 4/4)

> 📓 **A의 깨달음**: 이게 **계층방어의 정량적 증거**다. "도구를 많이 붙였다"가 아니라, *SAST가 0인 칸을 DAST가 3으로 메운다*를 숫자로 보였다.

## ⚠️ 한계 — 면접관이 찌른다

- **"DAST면 다 잡나요?"** → 아니다. DAST는 *공격 표면(엔드포인트)*을 알아야 잘 쏜다. OpenAPI/명세가 없으면 사각이 생긴다. 그리고 **원인(코드 위치)을 못 짚는다** — SAST와 정반대다. "뚫렸다"는 알지만 "어느 줄 때문"인지는 모른다.
- **"3/4면 1개는 왜 못 잡았죠?"** → 거래내역 IDOR은 *공격 스크립트에 케이스가 없어서*다(도구의 한계가 아니라 커버리지의 한계). 정직하게 3/4다.
- **"운영에 공격을 쏜다고요?"** → DAST는 스테이징/격리 환경에 쏘는 게 원칙. 운영 직격은 신중해야 한다.

## 🧭 시니어의 4가지 렌즈

| 렌즈 | 이 통제가 의미하는 것 |
| --- | --- |
| **기술 (Tech)** | 실행 기반 — 인가(IDOR)·비즈니스 로직(음수송금)을 *실제 요청*으로 검출. SAST의 0/4 사각을 3/4로 메움 |
| **규제 (Regulation)** | ISMS-P 2.6 접근통제(응용 인가 결함)·2.11 사고예방(취약점 점검) / PCI-DSS Req 6.x·11.x(테스트) / 전자금융 보호대책 |
| **정책 (Policy)** | "배포 전 인가·로직 검증을 통과해야 한다"를 *공격 시나리오*로 정의. 무엇을 공격할지(표면)가 정책의 일부 |
| **관리 (Governance)** | 공격 표면·시나리오는 *누가* 관리하나? 발견된 결함의 조치 SLA·재현 증적(evidence)을 누가 추적하나. DAST 결과는 0/4→3/4의 *계층방어 보고*의 핵심 |

> 🎤 **면접 한 줄**: *"SAST 0/4를 DAST 3/4로 메운 게 계층방어의 정량 근거입니다. 단일 도구로 다 막으려는 게 착각이고, SAST(원인)와 DAST(실증)는 서로의 사각을 메우는 짝입니다."*

---

코드도 봤고(SAST), 실행도 해봤다(DAST). 그런데 A가 배포 매니페스트를 열어보니 — 컨테이너가 **root로 돌고 있다.** 앱이 멀쩡해도, *컨테이너 설정*이 뚫려 있으면?

> 다음 → **6화 · "컨테이너가 root로 돌아요"** — Checkov·Kubescape
