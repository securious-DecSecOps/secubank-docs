#!/usr/bin/env python3
"""Evidence & Triage 흐름 — 아키텍처 다이어그램과 동일한 스타일(실제 아이콘 + 그룹 프레임).

scan/생성 → Security Gate → 증적 보관 → DefectDojo 통합 → Triage 결정,
+ 런타임 증적·SBOM 재평가 측면 입력.

실행:  ../.diagram-venv/bin/python evidence.py
출력:  evidence.png
"""
import os, glob, graphviz

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.abspath(os.path.join(HERE, "..", ".diagram-venv", "lib", "python3.12", "site-packages", "resources"))
ICONS = os.path.join(HERE, "icons")

def _find(base, name):
    g = glob.glob(os.path.join(base, "**", name), recursive=True); return g[0] if g else ""
def onp(rel):
    p = os.path.join(RES, "onprem", rel); return p if os.path.exists(p) else _find(os.path.join(RES, "onprem"), os.path.basename(rel))
def loc(n): return os.path.join(ICONS, n + ".png")

C_SCAN = "#0E7490"; C_GATE = "#D97706"; C_STORE = "#5A6B86"; C_DOJO = "#8C4FFF"
C_SEC = "#DD344C"; C_OK = "#16A34A"; C_GRAY = "#64748B"; C_BLUE = "#2563EB"

def frame(text, color):
    return (f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
            f'<TR><TD><FONT POINT-SIZE="13" COLOR="{color}"><B>{text}</B></FONT></TD></TR></TABLE>>')

def cattr(text, color, bg):
    return dict(label=frame(text, color), labelloc="t", labeljust="l", style="rounded",
                color=color, penwidth="2.2", bgcolor=bg, margin="14", fontname="Pretendard")

def inode(g, nid, icon, name):
    g.node(nid, shape="plaintext", margin="0",
           label=(f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
                  f'<TR><TD FIXEDSIZE="TRUE" WIDTH="44" HEIGHT="44"><IMG SCALE="TRUE" SRC="{icon}"/></TD></TR>'
                  f'<TR><TD><FONT POINT-SIZE="9" FACE="Pretendard">{name}</FONT></TD></TR></TABLE>>'))

def pill(g, nid, name, color, fill="white"):
    g.node(nid, shape="box", style="rounded,filled", fillcolor=fill, color=color, penwidth="1.6",
           fontname="Pretendard", fontsize="10", fontcolor=color, label=name, height="0.5", margin="0.16,0.07")

g = graphviz.Digraph("evidence", format="png")
g.attr(rankdir="LR", bgcolor="white", fontname="Pretendard", pad="0.6",
       nodesep="0.45", ranksep="0.95", dpi="170", compound="true",
       labelloc="t", fontsize="20", label="Evidence & Triage Flow · 무엇을 검사하고 어떻게 판단·추적하는가")
g.attr("edge", fontname="Pretendard", fontsize="10", color="#5A6B86")

# 1) CI 스캔 · 생성
with g.subgraph(name="cluster_scan") as s:
    s.attr(**cattr("CI 스캔 · 생성 (shift-left)", C_SCAN, "#ECFAFE"))
    inode(s, "sonar", loc("sonarqube"), "SonarQube · SAST")
    inode(s, "trivy", loc("trivy"), "Trivy · SCA")
    inode(s, "gitleaks", loc("git"), "Gitleaks · secret")
    inode(s, "checkov", loc("checkov"), "Checkov · IaC")
    inode(s, "kubescape", loc("kubescape"), "Kubescape · K8s")
    inode(s, "syft", onp("container/docker.png") if os.path.exists(onp("container/docker.png") or "") else loc("trivy"), "Syft · SBOM")

# 2) Security Gate
pill(g, "gate", "Security Gate\n(CRIT 0 · HIGH ≤3 정책)", C_GATE, "#FEF6E7")

# 3) 증적 보관
with g.subgraph(name="cluster_store") as st:
    st.attr(**cattr("증적 보관 (immutable)", C_STORE, "#F3F5F8"))
    inode(st, "jenkins", onp("ci/jenkins.png"), "Jenkins archive\nreports/dev/&lt;build&gt;/")
    inode(st, "harbor", loc("harbor"), "Harbor\nimage @ digest")

# 4) DefectDojo
inode(g, "dojo", loc("defectdojo"), "DefectDojo\nASOC 통합 · dedup · SLA")

# 5) Triage 결정
with g.subgraph(name="cluster_triage") as t:
    t.attr(**cattr("Triage 결정 (근거 있는 상태 전환)", C_DOJO, "#F6F2FE"))
    pill(t, "t_block", "Block", C_SEC)
    pill(t, "t_warn", "Warn & continue", C_GATE)
    pill(t, "t_accept", "Accepted Risk", C_GRAY)
    pill(t, "t_fp", "False Positive", C_GRAY)
    pill(t, "t_na", "Not Affected (VEX)", C_BLUE)

# 측면 입력
with g.subgraph(name="cluster_rt") as r:
    r.attr(**cattr("런타임 증적", C_SEC, "#FDEEF0"))
    inode(r, "falco", loc("falco"), "Falco events")
    inode(r, "hubble", loc("cilium"), "Hubble flows\n(DROPPED)")
    inode(r, "zap", loc("zap"), "DAST · verify.sh")

# 흐름
g.edge("kubescape", "gate", ltail="cluster_scan", label="findings", color=C_SCAN)
g.edge("syft", "jenkins", lhead="cluster_store", label="SBOM 저장", color=C_SCAN, style="dashed")
g.edge("gate", "jenkins", lhead="cluster_store", label="pass → archive", color=C_GATE)
g.edge("harbor", "dojo", ltail="cluster_store", label="import-scan", color=C_DOJO)
g.edge("dojo", "t_block", lhead="cluster_triage", color=C_DOJO)
g.edge("zap", "dojo", ltail="cluster_rt", label="런타임 findings", color=C_SEC, style="dashed")
g.edge("jenkins", "dojo", label="신규 CVE 재평가 (SBOM 재스캔)", color=C_BLUE, style="dotted", constraint="false")

out = g.render(filename=os.path.join(HERE, "evidence"), format="png", cleanup=True)
print("rendered:", out)
