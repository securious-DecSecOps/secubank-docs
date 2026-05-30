#!/usr/bin/env python3
"""실전 교본 — '성장하는' 아키텍처 (AWS 공식 아이콘, graphviz).
STAGE 환경변수(1~6)에 따라 컴포넌트가 누적된다.
  1 인프라  2 +CI파이프라인  3 +레지스트리/게이트  4 +GitOps/런타임  5 +런타임보안  6 +증적/공급망
실행: STAGE=1 ../.diagram-venv/bin/python textbook-arch.py
출력: textbook-stage<N>.png
"""
import os, glob, graphviz

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.abspath(os.path.join(HERE, "..", ".diagram-venv", "lib", "python3.12", "site-packages", "resources"))
ICONS = os.path.join(HERE, "icons")
STAGE = int(os.environ.get("STAGE", "1"))

def _find(base, name):
    g = glob.glob(os.path.join(base, "**", name), recursive=True)
    return g[0] if g else ""
def aws(rel):
    p = os.path.join(RES, "aws", rel)
    return p if os.path.exists(p) else _find(os.path.join(RES, "aws"), os.path.basename(rel))
def onp(rel):
    p = os.path.join(RES, "onprem", rel)
    return p if os.path.exists(p) else _find(os.path.join(RES, "onprem"), os.path.basename(rel))
def loc(name):
    return os.path.join(ICONS, name + ".png")

C_CLOUD="#232F3E"; C_VPC="#8C4FFF"; C_SUBNET="#7AA116"; C_EC2="#ED7100"; C_MGMT="#5A6B86"; C_SEC="#DD344C"

def frame(icon, text, color):
    return (f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
            f'<TR><TD FIXEDSIZE="TRUE" WIDTH="22" HEIGHT="22"><IMG SCALE="TRUE" SRC="{icon}"/></TD>'
            f'<TD><FONT POINT-SIZE="12" COLOR="{color}"><B>  {text}</B></FONT></TD></TR></TABLE>>')
def cattr(icon, text, color, bg):
    return dict(label=frame(icon, text, color), labelloc="t", labeljust="l", style="rounded",
                color=color, penwidth="2", bgcolor=bg, margin="13", fontname="Pretendard")
def inode(g, nid, icon, name):
    g.node(nid, shape="plaintext", margin="0",
        label=(f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
               f'<TR><TD FIXEDSIZE="TRUE" WIDTH="40" HEIGHT="40"><IMG SCALE="TRUE" SRC="{icon}"/></TD></TR>'
               f'<TR><TD><FONT POINT-SIZE="8" FACE="Pretendard">{name}</FONT></TD></TR></TABLE>>'))
def chip(g, nid, name, color=C_EC2):
    g.node(nid, shape="box", style="rounded,filled", fillcolor="white", color=color, penwidth="1.2",
           fontname="Pretendard", fontsize="7.5", label=name, height="0.34", margin="0.08,0.04")

g = graphviz.Digraph("tb", format="png")
g.attr(rankdir="LR", bgcolor="white", fontname="Pretendard", pad="0.5", nodesep="0.35", ranksep="0.8",
       dpi="170", compound="true", labelloc="t", fontsize="16",
       label=f"골든패스 아키텍처 · STAGE {STAGE}")
g.attr("node", fontname="Pretendard"); g.attr("edge", fontname="Pretendard", fontsize="9", color=C_MGMT)

inode(g, "dev", aws("general/user.png"), "개발자")
if STAGE >= 2:
    inode(g, "gh", onp("vcs/github.png"), "GitHub")

with g.subgraph(name="cluster_cloud") as cloud:
    cloud.attr(**cattr(aws("aws.png"), "AWS Cloud · ap-northeast-2", C_CLOUD, "#FFFFFF"))
    inode(cloud, "igw", aws("network/internet-gateway.png"), "Internet GW")
    with cloud.subgraph(name="cluster_mgmt") as m:
        m.attr(**cattr(aws("security/identity-and-access-management-iam-role.png"), "관리·보안", C_MGMT, "#F3F5F8"))
        inode(m, "iam", aws("security/identity-and-access-management-iam-role.png"), "IAM Role")
        inode(m, "ssm", aws("management/systems-manager.png"), "SSM<BR/>(SSH 미사용)")
        if STAGE >= 6:
            inode(m, "sns", aws("integration/simple-notification-service-sns.png"), "SNS 알림")
    with cloud.subgraph(name="cluster_vpc") as vpc:
        vpc.attr(**cattr(aws("network/vpc.png"), "VPC · 10.0.0.0/16", C_VPC, "#F5F1FE"))
        with vpc.subgraph(name="cluster_sn") as sn:
            sn.attr(**cattr(aws("network/public-subnet.png"), "Public Subnet · 10.0.1.0/24", C_SUBNET, "#F2F7E8"))
            # CI VM
            with sn.subgraph(name="cluster_ci") as ci:
                ci.attr(**cattr(aws("compute/ec2-instance.png"), "EC2 · CI", C_EC2, "#FDF2E8"))
                if STAGE >= 2:
                    inode(ci, "jenkins", onp("ci/jenkins.png"), "Jenkins")
                    chip(ci, "scan", "Gitleaks·SonarQube·Checkov·Kubescape", C_MGMT)
                if STAGE >= 3:
                    inode(ci, "harbor", loc("harbor"), "Harbor")
                    chip(ci, "gate", "Trivy·SBOM·Gate", C_EC2)
                if STAGE == 1:
                    inode(ci, "ci0", aws("compute/ec2-instance.png"), "(빈 VM)")
            # Runtime VM
            with sn.subgraph(name="cluster_rt") as rt:
                rt.attr(**cattr(aws("compute/ec2-instance.png"), "EC2 · Runtime (k3s)", C_EC2, "#FDF2E8"))
                if STAGE >= 4:
                    inode(rt, "argo", loc("argo"), "ArgoCD")
                    inode(rt, "app", onp("container/k3s.png"), "VulnBank<BR/>6 svc")
                if STAGE >= 5:
                    inode(rt, "cilium", loc("cilium"), "Cilium")
                    inode(rt, "falco", loc("falco"), "Falco")
                    chip(rt, "kb", "kube-bench·ZAP", C_SEC)
                if STAGE <= 3:
                    inode(rt, "rt0", aws("compute/ec2-instance.png"), "(빈 VM)")
            # DefectDojo VM
            with sn.subgraph(name="cluster_dd") as dd:
                dd.attr(**cattr(aws("compute/ec2-instance.png"), "EC2 · DefectDojo", C_EC2, "#FDF2E8"))
                if STAGE >= 6:
                    inode(dd, "dojo", loc("defectdojo"), "DefectDojo")
                else:
                    inode(dd, "dd0", aws("compute/ec2-instance.png"), "(빈 VM)")

g.edge("dev", "ssm", label="SSM 접속", style="dashed", lhead="cluster_mgmt")
if STAGE >= 2:
    g.edge("dev", "gh", label="git push"); g.edge("gh", "jenkins", label="webhook")
if STAGE >= 3:
    g.edge("jenkins", "harbor", label="build·scan·gate", color=C_EC2)
if STAGE >= 4:
    g.edge("harbor", "app", label="image pull", color=C_SUBNET, lhead="cluster_rt")
    g.edge("argo", "app", color=C_SUBNET)
if STAGE >= 5:
    g.edge("falco", "app", label="런타임 탐지", color=C_SEC, style="dashed")
if STAGE >= 6:
    g.edge("jenkins", "dojo", label="import", color=C_VPC, style="dashed", lhead="cluster_dd")

out = g.render(filename=os.path.join(HERE, f"textbook-stage{STAGE}"), format="png", cleanup=True)
print("rendered:", out)
