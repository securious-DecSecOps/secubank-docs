---
title: 12화 · 웹쉘이 떴는데 아무도 몰랐어요
---

# 12화 · "웹쉘이 떴는데 아무도 몰랐어요"

11화의 egress 차단은, 악성코드가 *바깥으로 나가려* 할 때 작동했다. 그런데 모든 공격이 바깥으로 나가는 건 아니다. A는 5화를 떠올렸다 — DAST로 자기 서비스를 공격했을 때, 업로드한 PHP 웹쉘이 *게이트웨이를 거쳐 실행*됐다. 운영에서 공격자가 똑같이 한다면? 웹쉘을 심고, 컨테이너 안에서 셸을 띄우고, 조용히 자리를 잡는다. 데이터를 당장 빼돌리지 않으면 — egress 로그엔 아무것도 안 뜬다.

> A: "웹쉘이 컨테이너 안에 떠서 돌고 있는데… 우리가 그걸 어떻게 알죠? 로그에도 안 남는데."

이게 런타임 보안의 마지막 빈틈이다. 코드도, 이미지도, 네트워크도 봤다. 그런데 *실행 중인 컨테이너 안에서 벌어지는 행위* — 셸 실행, 파일 쓰기, 권한 변경 — 는 여전히 깜깜하다. 그걸 보려면, 컨테이너가 커널에 요청하는 *시스템 콜*을 들여다봐야 한다.

## 컨테이너의 모든 행위는 syscall로 드러난다

Falco가 하는 일이다. 컨테이너 안 프로세스가 무엇을 하든 — 셸을 띄우든, 파일을 쓰든, 네트워크를 열든 — 결국 커널에 *시스템 콜*을 보낸다. Falco는 eBPF로 그 syscall 스트림을 실시간으로 보고 룰과 대조한다. "이 컨테이너에서 셸이 떴다"처럼, *정상 운영엔 없어야 할 행위*를 잡아낸다.

A는 VulnBank용 룰 두 개를 심었다.

```yaml title="VulnBank 런타임 룰 ① — 셸 실행 탐지"
- rule: Shell spawned in VulnBank container
  desc: VulnBank 컨테이너 안에서 셸이 실행됨(정상 운영엔 없어야 함)
  condition: spawned_process and container
    and container.image contains "vulnbank-msa"
    and proc.name in (sh, bash, dash)
  output: "Shell spawned in VulnBank container
    (user=%user.name cmdline=%proc.cmdline image=%container.image
     k8s_pod=%k8s.pod.name k8s_ns=%k8s.ns.name)"
  priority: WARNING
```

VulnBank 컨테이너에서 `sh`/`bash`가 뜨면 경보다. 웹 서비스 컨테이너가 셸을 띄울 일은 정상 운영엔 거의 없으니, 그 자체가 침해 징후다. 그런데 둘째 룰 — *웹 루트에 .php가 생기는지* 보는 룰 — 에서 진짜 이야기가 시작된다.

## 룰이 *안 울렸다* — 그리고 그게 더 중요한 사건

A가 웹쉘을 업로드해 봤다. 첫 룰(셸 실행)은 울렸다. 그런데 둘째 룰은 **침묵했다.** 분명 웹쉘이 올라갔는데, 경보가 없다.

여기서 A가 한 일이, 도구를 까는 것보다 백 배 중요했다. *왜 안 울렸는지를 파고들었다.* 그리고 두 가지 근본 원인을 실측으로 규명했다.

**(a) 룰의 버그.** 처음 룰은 `open_write`(파일 쓰기 열림) syscall만 감시했다. 그런데 PHP의 `move_uploaded_file()`은 업로드 임시파일을 *옮기는* 동작이라, 내부적으로 `open_write`가 아니라 **`rename` 계열 syscall**을 쓴다. 룰이 보는 syscall과 공격이 실제로 내는 syscall이 *어긋나* 있었던 것이다. 그래서 룰을 고쳤다.

```yaml title="고친 condition — rename 계열을 추가"
(open_write and fd.name endswith ".php")
  or (evt.type in (rename, renameat, renameat2)
      and evt.dir=< and fs.path.target endswith ".php")
```

`rename`/`renameat`/`renameat2`를 추가하고, 이동의 *목적지* 경로(`fs.path.target`)가 `.php`로 끝나는지 본다. 경로 접두사도 떼어냈다 — PHP가 상대경로로 옮기는 경우까지 잡기 위해.

**(b) Falco의 attach 한계.** 룰을 고쳤는데도 한동안 안 울렸다. 두 번째 원인 — Falco를 *나중에* 켜면, *이미 떠 있던* PHP 워커 프로세스의 syscall을 컨테이너에 *귀속시키지 못한다*(`cannot attach container_id`). Falco가 그 프로세스의 시작을 못 봤기 때문이다. 워크로드(file-service)를 *재시작*해 Falco가 처음부터 추적하게 하자, 비로소 정상 귀속됐다.

## 그제서야 울린 경보 — 실측

두 원인을 잡고 다시 웹쉘을 업로드하자, 경보가 떴다.

```text title="Falco 런타임 탐지 — AWS 라이브 (ns secure-path-dev)"
16:31:58  Warning   Shell spawned in VulnBank container
  user=root  cmdline=sh -c id  image=…/vulnbank-msa-file-service:3
  k8s_pod=file-service-694db65b97-2q627  k8s_ns=secure-path-dev

18:31:55  Critical  PHP file written/moved in VulnBank web root
  target=/var/www/html/uploads/1_msa-webshell.php  proc=php
  image=…/vulnbank-msa-file-service:3
  k8s_pod=file-service-7979bd4d5c-xhkxk  k8s_ns=secure-path-dev
```

`18:31:55 Critical` — 웹쉘(`/var/www/html/uploads/1_msa-webshell.php`)이 `php` 프로세스에 의해 웹 루트에 쓰인 *그 순간*, 어느 파드·어느 네임스페이스인지까지 찍혀 경보가 울렸다. 그 위 `16:31:58`엔 셸 실행(`sh -c id`)이 root로 잡혔다. 컨테이너 안에서 벌어진 두 침해 행위가, 실시간으로 보인 것이다.

## 안 울리는 룰은, 없는 룰보다 나쁘다

A가 이 장에서 얻은 가장 무거운 교훈. **룰이 *있다*는 것과 룰이 *운다*는 것은 다르다.** 만약 A가 룰을 심고 "탐지 깔았다"며 넘어갔다면 — 그 룰은 영영 침묵했을 것이고, 웹쉘이 떠도 아무도 몰랐을 것이다. 더 나쁜 건 *"우리는 Falco로 웹쉘을 탐지한다"는 거짓 확신*이다. 안 울리는 룰은 없는 룰보다 위험하다 — 없으면 경계하지만, 있다고 믿으면 방심하니까. 그래서 탐지 룰은 *반드시 실제로 공격을 쏴서 울리는지 검증*해야 한다.

운영 교훈도 하나 건졌다. **Falco는 워크로드보다 먼저 떠야 한다**(또는 워크로드를 재시작해야 한다). 안 그러면 이미 도는 프로세스의 침해 행위를 놓친다. 침해는 종종 *이미 돌고 있는* 프로세스에서 나오므로, 이 순서는 단순한 팁이 아니라 탐지의 사각을 만드는 함정이다.

그리고 정직하게 — Falco는 *탐지*하지 *차단*하지 않는다. 웹쉘이 뜨는 걸 *알려줄* 뿐, 막지는 않는다. 그 가치는 "보이게 하는 것"이다. 앞의 모든 통제가 놓친 *실행 중인 침해*를 비로소 눈에 보이게 한다. 탐지가 곧 대응은 아니지만, 보이지 않는 건 대응할 수도 없다.

## A가 정리한 자리들

기술적으로 Falco는 eBPF로 컨테이너의 syscall을 실시간 관측해 셸 실행·웹쉘 쓰기 같은 *런타임 침해 행위*를 룰로 탐지한다 — 단 룰이 실제 공격의 syscall(예: rename)과 맞아야 하고, Falco가 워크로드보다 먼저 떠야 귀속이 된다. 규제로 옮기면, 런타임 위협 탐지·로깅은 ISMS-P 2.11(사고 예방·대응)·2.10(악성코드 통제)·2.9(로그·모니터링)에 닿고, 침해 시도의 실시간 증적은 사고 대응의 출발점이 된다. 정책의 영역에서, "무엇을 이상 행위로 볼 것인가"(룰셋)가 곧 정책이며, 그 룰이 *검증된 채로* 운영되는지가 정책의 실효성이다. 관리의 영역에서, 경보를 누가 받고 어떻게 트리아지하는지, 룰셋을 누가 유지·검증하는지가 거버넌스다 — 그리고 이 장이 보여줬듯, *탐지 룰을 주기적으로 실사격 검증하는 절차*가 있는 조직과 없는 조직은 같은 Falco를 써도 전혀 다른 보안 수준에 있다.

A가 12화에서 얻은 문장. **탐지는 깔았다고 되는 게 아니라, 울리는 걸 확인해야 되는 것이다.**

---

이제 A의 손엔 모든 게 있다 — SAST의 0/4, DAST의 3/4, Trivy의 CVE 6천, SBOM의 신규 CVE, 게이트 판정, Hubble의 DROPPED, Falco의 웹쉘 경보. 그런데 이것들이 *제각각 다른 화면*에 흩어져 있다. 보안팀이 "지금 우리 위험이 뭐냐"고 물으면, A는 일곱 개 탭을 열어야 한다.

> 다음 → **13화 · "보안팀은 이걸 어디서 봐요?"** — 흩어진 증적을 한 화면으로, DefectDojo
