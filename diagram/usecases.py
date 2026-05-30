#!/usr/bin/env python3
"""VulnBank DevSecOps Golden Path — UML 유스케이스 다이어그램 (graphviz).
액터 + 시스템 경계 + 도메인(4단계) 유스케이스 + include/extend 관계.
실행: ../.diagram-venv/bin/python usecases.py   출력: usecases.png
"""
import os
import graphviz

HERE = os.path.dirname(os.path.abspath(__file__))

C_CLOUD = "#232F3E"
C_ACTOR = "#5A6B86"
C_ATTACK = "#DD344C"
C_CI = "#2563EB"
C_DEPLOY = "#558B0F"
C_RUNTIME = "#DD344C"
C_GOV = "#7C3AED"
INK = "#0F1B2D"

g = graphviz.Digraph("usecases", format="png")
g.attr(rankdir="LR", bgcolor="white", fontname="Helvetica",
       labelloc="t", fontsize="22", fontcolor=INK, pad="0.3",
       label="VulnBank DevSecOps Golden Path — 유스케이스 다이어그램",
       nodesep="0.30", ranksep="1.25", splines="spline")
g.attr("edge", color="#8A97A8", fontname="Helvetica", fontsize="10", fontcolor="#6B7888")


def actor(nid, name, fill, stereo, stereo_col):
    label = (f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2">'
             f'<TR><TD><FONT POINT-SIZE="9" COLOR="{stereo_col}">«{stereo}»</FONT></TD></TR>'
             f'<TR><TD><FONT POINT-SIZE="13" COLOR="white"><B>{name}</B></FONT></TD></TR></TABLE>>')
    g.node(nid, label=label, shape="box", style="filled,rounded",
           fillcolor=fill, color=fill, margin="0.18,0.11")


def uc(nid, text, color, fill):
    g.node(nid, label=text, shape="ellipse", style="filled",
           fillcolor=fill, color=color, fontcolor=INK, fontname="Helvetica",
           fontsize="11", penwidth="1.7", margin="0.10,0.05")


# ---- 액터 (좌: 정상 행위자 / 우측 하단: 위협) ----
actor("dev", "개발자", C_ACTOR, "actor", "#9FB0C3")
actor("plat", "플랫폼 엔지니어\\n(주니어 A)", C_ACTOR, "actor", "#9FB0C3")
actor("sec", "보안담당자", C_ACTOR, "actor", "#9FB0C3")
actor("aud", "감사자", C_ACTOR, "actor", "#9FB0C3")
actor("atk", "공격자", C_ATTACK, "threat", "#FFD7DD")

# 액터 세로 정렬
g.body.append('{rank=same; dev; plat; sec; aud;}')

# ---- 4단계 위상 클러스터 (옅은 배경으로 경계 가시화) ----
def phase(name, label, color, bg, ucs):
    with g.subgraph(name=name) as c:
        c.attr(label=label, labelloc="t", fontname="Helvetica", fontsize="14",
               fontcolor=color, pencolor=color, color=color, penwidth="2.0",
               style="rounded", bgcolor=bg, margin="16")
        # 같은 위상의 UC를 세로 정렬해 박스가 또렷하게 잡히도록
        c.attr(rank="same")
        for nid, text in ucs:
            uc(nid, text, color, "white")

phase("cluster_ci", "① CI 검사", C_CI, "#EEF4FF", [
    ("uc1", "UC1 코드 푸시·CI 트리거"),
    ("uc2", "UC2 시크릿 스캔 (Gitleaks)"),
    ("uc3", "UC3 정적분석 SAST"),
    ("uc4", "UC4 이미지·SBOM·CVE (Trivy)"),
    ("uc5", "UC5 IaC·K8s 스캔"),
    ("uc6", "UC6 보안 게이트 판정"),
    ("uc7", "UC7 예외 승인·등록"),
])
phase("cluster_deploy", "② 배포", C_DEPLOY, "#F0F7E8", [
    ("uc8", "UC8 레지스트리 푸시 (Harbor)"),
    ("uc9", "UC9 GitOps 배포 (ArgoCD)"),
])
phase("cluster_runtime", "③ 런타임 방어", C_RUNTIME, "#FDEEF0", [
    ("uc10", "UC10 행위 탐지 (Falco)"),
    ("uc11", "UC11 egress C2 차단 (Cilium)"),
    ("uc12", "UC12 SBOM 시간축 재평가"),
])
phase("cluster_gov", "④ 검증·거버넌스", C_GOV, "#F4EEFE", [
    ("uc13", "UC13 DAST 공격 검증"),
    ("uc14", "UC14 증적 트리아지 (DefectDojo)"),
    ("uc15", "UC15 증적 보관·감사"),
])

# ---- 연관(association) ----
assoc = [("dev", "uc1"),
         ("sec", "uc6"), ("sec", "uc7"), ("sec", "uc14"),
         ("plat", "uc9"), ("plat", "uc12"),
         ("aud", "uc15")]
for a, u in assoc:
    g.edge(a, u, arrowhead="none", penwidth="1.3")
for u in ["uc10", "uc11"]:
    g.edge("plat", u, arrowhead="none", penwidth="1.1", color="#B6C0CE")

# ---- 공격자: 공격이 검증·탐지·차단된다 ----
for u in ["uc13", "uc10", "uc11"]:
    g.edge("atk", u, arrowhead="none", color=C_ATTACK, penwidth="1.3")

# ---- include : CI 트리거가 검사·게이트를 포함 ----
for u in ["uc2", "uc3", "uc4", "uc5", "uc6"]:
    g.edge("uc1", u, style="dashed", arrowhead="vee", label="«include»")

# ---- 파이프라인 흐름 (게이트 PASS → 배포) ----
g.edge("uc6", "uc8", arrowhead="vee", color=C_DEPLOY, penwidth="1.6", label="PASS")
g.edge("uc8", "uc9", arrowhead="vee", color=C_DEPLOY, penwidth="1.4")
g.edge("uc6", "uc15", style="dashed", arrowhead="vee", label="«include»\\n증적")

# ---- extend : 예외는 게이트를 선택적으로 확장 ----
g.edge("uc7", "uc6", style="dashed", arrowhead="vee", label="«extend»",
       color=C_GOV, fontcolor=C_GOV, penwidth="1.3")

g.render(os.path.join(HERE, "usecases"), cleanup=True)
print("OK usecases.png")
