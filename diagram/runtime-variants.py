#!/usr/bin/env python3
"""Runtime VM 아키텍처 변형 — AWS 공식 아이콘 (graphviz HTML 프레임).
보안 계층(Cilium·Falco·kube-bench·ArgoCD)은 모든 변형에 공통임을 보인다.
실행: ../.diagram-venv/bin/python runtime-variants.py
출력: runtime-variants.png
"""
import os, glob, graphviz

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.abspath(os.path.join(HERE, "..", ".diagram-venv", "lib", "python3.12", "site-packages", "resources"))
ICONS = os.path.join(HERE, "icons")

def _find(base, name):
    g = glob.glob(os.path.join(base, "**", name), recursive=True)
    return g[0] if g else ""
def aws(rel):
    p = os.path.join(RES, "aws", rel)
    return p if os.path.exists(p) else _find(os.path.join(RES, "aws"), os.path.basename(rel))
def onp(rel):
    p = os.path.join(RES, "onprem", rel)
    return p if os.path.exists(p) else _find(os.path.join(RES, "onprem"), os.path.basename(rel))

C_EC2 = "#ED7100"; C_SEC = "#DD344C"; C_ONP = "#5A6B86"

def frame(icon, text, color):
    return (f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
            f'<TR><TD FIXEDSIZE="TRUE" WIDTH="22" HEIGHT="22"><IMG SCALE="TRUE" SRC="{icon}"/></TD>'
            f'<TD><FONT POINT-SIZE="12" COLOR="{color}"><B>  {text}</B></FONT></TD></TR></TABLE>>')

def inode(g, nid, icon, name):
    g.node(nid, shape="plaintext", margin="0",
           label=(f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
                  f'<TR><TD FIXEDSIZE="TRUE" WIDTH="44" HEIGHT="44"><IMG SCALE="TRUE" SRC="{icon}"/></TD></TR>'
                  f'<TR><TD><FONT POINT-SIZE="8.5" FACE="Pretendard">{name}</FONT></TD></TR></TABLE>>'))

def sec_chip(g, nid):
    g.node(nid, shape="box", style="rounded,filled", fillcolor="#FDECEF", color=C_SEC, penwidth="1.3",
           fontname="Pretendard", fontsize="8", height="0.42", margin="0.1,0.05",
           label="보안 계층(공통)\\nCilium · Falco · kube-bench · ArgoCD")

g = graphviz.Digraph("runtime-variants", format="png")
g.attr(rankdir="LR", bgcolor="white", fontname="Pretendard", pad="0.5",
       nodesep="0.35", ranksep="0.7", dpi="170", compound="true", labelloc="t", fontsize="17",
       label="Runtime VM 아키텍처 변형 — 보안 계층은 모든 변형에 그대로 이식된다")
g.attr("node", fontname="Pretendard")
g.attr("edge", fontname="Pretendard", fontsize="9", color=C_SEC)

def variant(cid, icon, title, color, bg, computes):
    with g.subgraph(name="cluster_" + cid) as c:
        c.attr(label=frame(icon, title, color), labelloc="t", labeljust="l", style="rounded",
               color=color, penwidth="2", bgcolor=bg, margin="14", fontname="Pretendard")
        for i, (ic, nm) in enumerate(computes):
            inode(c, f"{cid}c{i}", ic, nm)
        sec_chip(c, cid + "sec")
        c.edge(f"{cid}c0", cid + "sec", style="dashed", arrowhead="none")

variant("v1", aws("compute/ec2-instance.png"), "① 단일노드 k3s (현재 PoC)", C_EC2, "#FDF7F0",
        [(aws("compute/ec2-instance.png"), "EC2 · k3s<BR/>노드 1대")])
variant("v2", aws("compute/ec2-instances.png"), "② 멀티노드 k8s (자가관리 HA)", C_EC2, "#FDF7F0",
        [(aws("compute/ec2-instance.png"), "control-plane"), (aws("compute/ec2-instances.png"), "worker ×N")])
variant("v3", aws("compute/elastic-kubernetes-service.png"), "③ EKS (매니지드)", C_EC2, "#FDF7F0",
        [(aws("compute/elastic-kubernetes-service.png"), "EKS<BR/>control plane"), (aws("compute/ec2-instances.png"), "managed nodes")])
variant("v4", onp("compute/server.png"), "④ 하이브리드 / 온프레", C_ONP, "#F3F5F8",
        [(onp("compute/server.png"), "온프레 k8s"), (aws("compute/ec2-instance.png"), "클라우드 CI")])

# 변형 간 좌→우 정렬용 보이지 않는 연결
for a, b in (("v1", "v2"), ("v2", "v3"), ("v3", "v4")):
    g.edge(a + "sec", b + "c0", style="invis")

out = g.render(filename=os.path.join(HERE, "runtime-variants"), format="png", cleanup=True)
print("rendered:", out)
