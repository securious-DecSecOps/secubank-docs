---
title: 4화 · 음수로 송금했더니 잔액이 늘어요
---

# 4화 · "음수로 송금했더니 잔액이 늘어요"

금요일 오후, QA 담당자가 A의 자리로 왔다. 표정이 묘했다.

> "이거… 버그 같은데, 좀 무서워요."

화면에는 송금 요청이 하나 떠 있었다. 금액 칸에 적힌 숫자는 **−1,000**. 그리고 요청을 보낸 뒤, 보낸 사람의 잔액이 *늘어 있었다.*

A는 송금 처리 코드를 열었다. `app-source-repo`의 `transaction-service/public/api.php`.

```php title="transaction-service/public/api.php (실제 코드)"
function transactionSendLocal($sender, $recipient, $amount, $comment) {
    if (empty($amount))
        responseSend(FALSE, sprintf(MSG_VALID_PARAM_FAIL, "amount"), ...);  // ① 금액이 '비었나'만 본다
    if ($_SESSION["amount"] < $amount)
        responseSend(FALSE, MSG_TRANSACTION_LOWMONEY, ...);                 // ② 잔액이 '부족한가'만 본다
    // … 어디에도 amount > 0 을 확인하는 줄은 없다
}
```

검증이 *없는* 게 아니었다. 가드가 두 줄이나 있었다. 문제는 둘 다 **음수를 통과시킨다**는 것이다. `empty($amount)`는 `""`나 `"0"`엔 참이지만 `-10`엔 거짓이라 ①을 빠져나간다. ②는 "잔액 < 송금액"을 보는데, 잔액이 +5,000이고 송금액이 −10이면 `5000 < -10`은 거짓 — 부족이 아니니 ②도 통과한다. 가드는 있지만 둘 다 *음수라는 경우의 수*를 빼먹었다. 그 결과 −10을 보내면 받는 계좌에서 보내는 계좌로 돈이 역류한다. 인터넷뱅킹에서 마음만 먹으면 남의 돈을 끌어올 수 있다는 뜻이다.

명백한 결함이었다. 그리고 A는 자신이 있었다. *"이런 건 SAST가 당연히 잡지. 코드를 통째로 분석하는 도구잖아."* 마침 파이프라인의 세 번째 관문이 SonarQube였다. 그는 의도적으로 취약점 네 개(음수송금, 거래내역 IDOR, 회원정보 IDOR, 웹쉘 업로드)를 심어둔 코드에 SAST를 돌렸다.

## 코드를 실행하지 않고 '읽는다'는 것

SonarQube 같은 SAST(Static Application Security Testing)는 프로그램을 *돌리지 않는다.* 대신 소스를 파서로 읽어 추상 구문 트리(AST)를 만들고, 값이 어디서 와서 어디로 흐르는지를 추적한다(data-flow, taint analysis). "외부에서 들어온 값이 검증 없이 SQL 쿼리에 박히는가" 같은 질문에 강하다. 그런 결함은 *코드의 모양*에 드러나기 때문이다.

파이프라인에서는 이렇게 부른다.

```bash title="devsecops-path/scripts/sonarqube-scan-services.sh (발췌)"
sonar-scanner \
  -Dsonar.projectKey="vulnbank-msa" \
  -Dsonar.host.url="${SONAR_HOST_URL}" \   # 결과는 별도 SonarQube 서버에 쌓인다
  -Dsonar.token="${SONAR_TOKEN}"           # 토큰은 Jenkins credential로 주입
```

다른 스캐너와 한 가지가 다르다. Gitleaks나 Trivy는 결과 JSON을 `REPORT_DIR/<도구>/`에 떨구고 끝이지만, SonarQube는 **서버형**이다. 분석 결과·보안등급·Quality Gate가 전부 SonarQube 서버에 산다. 그래서 2화에서 본 파라미터 중 `SONAR_HOST_URL`과 `SONAR_TOKEN`이 따로 있었던 것이다 — 스캐너가 서버에 결과를 올리고, 게이트 통과 여부를 서버에 *되물어*본다.

## 0 / 4 — 그리고 그게 왜 당연한가

결과가 떴다. 심어둔 취약점 네 개 중 SAST가 잡은 것은 — **0개.**

A는 한참을 들여다봤다. 그리고 천천히, 이게 우연이 아니라는 걸 이해했다.

SAST에게 음수송금 코드는 *틀린 것처럼 생기지 않았다.* `balance -= amount`는 문법적으로 완벽한 뺄셈이다. amount가 음수면 안 된다는 것은 **비즈니스 규칙**이지 코드의 문법이 아니다. "이 도메인에서 송금액은 0보다 커야 한다"는 의도를, 정적분석기는 알지 못한다. 알 방법이 없다. 그에게는 그냥 정상적인 산술 연산이다.

IDOR은 더 미묘하다. `getTransactions($accountId)`에서 `$accountId`가 요청 파라미터에서 온다는 사실은 SAST도 본다. 운이 좋으면 "외부 입력이 조회에 쓰인다"고 hotspot으로 띄울 수도 있다. 하지만 *진짜 버그*는 거기에 "이 요청자가 이 계좌의 주인인가"를 확인하는 줄이 **없다**는 것이다. 없는 코드를 지적할 수는 없다. 인가(authorization)는 *있어야 할 것의 부재*이고, 정적분석은 *있는 것*을 본다. 그래서 인가 결함은 SAST의 구조적 사각이다.

그런데 SAST가 논 것은 아니었다. 결과를 더 내려보니 정확히 짚은 게 있었다. `getstatus.php`에서 외부 결제 게이트웨이를 호출할 때 **TLS 인증서·호스트명 검증을 꺼둔 것**(rule `php:S4830`·`php:S5527`, CWE-295/297). 약한 해시와 예측 가능한 난수(CWE-328/338)도 함께 걸렸다. 이건 SAST의 홈그라운드다. "인증서 검증을 false로" 같은 건 *코드의 모양*에 또렷이 드러나니까.

> 그래서 0/4는 SAST의 실패가 아니다. **담당 레이어가 다르다**는 증거다. 암호·설정처럼 코드에 드러나는 결함엔 강하고, 인가·비즈니스 로직처럼 의도를 알아야 보이는 결함엔 약하다. 단일 도구로 전부 막으려는 생각 자체가 틀렸다는 것 — 이 한 장이 이 교본 전체의 뼈대다.

## 더 무서운 한 줄 — 등급은 D인데 게이트는 PASS

화면 위쪽에 작은 글씨가 있었다. 전체 보안등급(security_rating): **D**. 그런데 바로 옆, Quality Gate: **Passed.**

A는 이게 0/4보다 더 무서웠다. *어떻게 D인데 통과지?*

지어낸 이야기가 아니다. 지금도 살아있는 SonarQube 서버에 물어보면 그대로 나온다.

```json title="SonarQube API 실측 — /api/measures/component (lastAnalysis 2026-05-28)"
"security_rating":   "4.0",   // 4.0 = 등급 D  (1.0=A … 5.0=E)
"vulnerabilities":   "2",     // SAST가 실제로 잡은 것 = TLS·암호 결함 2건
"security_hotspots": "45",
"ncloc":             "9319",
"alert_status":      "OK"     // ← Quality Gate = PASS
```

```json title="/api/qualitygates/project_status — 게이트가 '무엇을' 봤나"
"conditions": [
  { "metricKey": "new_security_rating",      "status": "OK", "errorThreshold": "1", "actualValue": "1" },
  { "metricKey": "new_reliability_rating",   "status": "OK", ... },
  { "metricKey": "new_maintainability_rating","status": "OK", ... }
]   // 조건이 전부 new_* — '신규 코드'만 평가했다는 실측 증거
```

보안등급은 `4.0`(D), 그런데 `alert_status`는 `OK`(통과). 그리고 게이트가 본 조건은 전부 `new_*`다. SonarQube의 기본 Quality Gate는 *전체 코드*가 아니라 **새로 바뀐 코드(New Code)**의 등급(`new_security_rating`)을 본다. "이번 변경이 새 위험을 들였는가"를 묻는 것이다. 기존 코드가 아무리 D여도, 이번 커밋이 깨끗하면 게이트는 초록불을 켠다. 사실 합리적인 설계다 — 매번 전체를 막으면 레거시를 떠안은 팀은 아무것도 배포하지 못하니까.

하지만 그 합리성이 함정이 된다. "게이트 PASS"라는 글자를 본 사람이 그걸 "안전하다"로 읽는 순간, 보안등급 D짜리 코드가 통과해버린다. 그리고 이건 도구의 버그가 아니라 **정책의 선택**이다. 게이트가 전체를 볼지 신규만 볼지, CRITICAL 임계값을 0으로 둘지 3으로 둘지 — 그 숫자 하나하나가 조직이 받아들이기로 한 위험의 크기다.

그래서 이 숫자들은 엔지니어가 편의로 정할 게 아니라, *위험을 책임지는 사람*이 정하고 주기적으로 검토해야 한다. 게이트를 켰다는 사실보다 **게이트가 무엇을 평가하도록 설계했는가**가 실제 보안 수준을 정한다. 감사에서도 "SAST 돌렸습니다"는 약하다. "전체 등급이 D임을 인지했고, 신규 코드 기준으로 회귀를 막고 있으며, 기존 D는 위험 수용 절차로 만료일과 함께 관리 중입니다" — 이 문장을 말할 수 있는지가 거버넌스의 성숙도다.

규제의 언어로도 정리된다. SAST가 잡은 TLS·암호 결함은 ISMS-P 2.7(암호화 적용)과 PCI-DSS의 보안 코딩 요구를 뒷받침하고, SAST를 게이트에 둔 행위 자체는 2.8(정보시스템 도입 및 개발 보안)을 이행한다. 하지만 0/4와 D-PASS가 보여주듯, *통제를 갖췄다*와 *통제가 효과적이고 관리된다*는 다르다. 그 간극을 인지하는 것이 이 직무의 시작이다.

## A가 내린 결론

코드를 *읽는* 것만으로는 음수송금도, IDOR도 잡히지 않는다. 의도와 인가는 코드의 표면에 없으니까. 그렇다면 남은 길은 하나뿐이었다 — 코드를 실제로 *실행해서*, 공격자가 하듯 요청을 직접 쏴보는 것.

A는 처음으로 자기 서비스를 공격하기로 한다.

> 다음 → **5화 · "남의 거래내역이 보여요"** — SAST가 놓친 0/4를, 공격으로 메운다
