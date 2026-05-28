# VulnBank MSA DevSecOps Golden Path Docs

MkDocs Material 기반 기술문서 사이트입니다. 문서의 목적은 VulnBank MSA PoC를 단순 도구 목록이 아니라 보안담당자의 판단, 차단, 재평가, 증적 흐름으로 설명하는 것입니다.

## Local preview

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

브라우저에서 `http://127.0.0.1:8000`으로 확인합니다.

## Static build

```bash
mkdocs build --strict
```

## Deploy

`main` 브랜치에 push되면 GitHub Actions가 `mkdocs gh-deploy`를 실행해 `gh-pages` 브랜치로 배포합니다.

## Content rules

- 문서에는 비밀번호, 토큰, PAT, 실제 민감 IP를 쓰지 않습니다.
- CI, GitOps, Runtime 수치는 코드와 reports 증적에 근거한 값만 기록합니다.
- 정탐률, 오탐률처럼 분석이 필요한 항목은 근거가 생길 때까지 TODO로 둡니다.
