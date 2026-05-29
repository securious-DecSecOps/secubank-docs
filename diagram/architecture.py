#!/usr/bin/env python3
"""SecuBank DevSecOps Golden Path — AWS 공식 스타일 아키텍처 (graphviz HTML 프레임).

mingrammer diagrams 의 클러스터(그냥 네모) 대신, graphviz HTML 라벨로 AWS 공식
그룹 프레임(모서리에 AWS 공식 아이콘 + 규약 색 테두리)을 직접 그린다.
- 공식 AWS 리소스 아이콘: diagrams 패키지 번들(resources/aws/**) 재사용
- 도구 로고: diagrams onprem 번들 + diagram/icons/*.png(직접 확보)
- 생략 없이 전체 보안 스택을 표시

실행:  ../.diagram-venv/bin/python architecture.py   (graphviz 필요)
출력:  architecture.png
"""
import os, glob, graphviz

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", ".diagram-venv", "lib", "python3.12", "site-packages", "resources")
RES = os.path.abspath(RES)
ICONS = os.path.join(HERE, "icons")

def aws(rel):  # 공식 AWS 아이콘
    p = os.path.join(RES, "aws", rel)
    return p if os.path.exists(p) else _find(os.path.join(RES, "aws"), os.path.basename(rel))
def onp(rel):
    p = os.path.join(RES, "onprem", rel)
    return p if os.path.exists(p) else _find(os.path.join(RES, "onprem"), os.path.basename(rel))
def loc(name):  # 직접 확보 로고
    return os.path.join(ICONS, name + ".png")
def _find(base, name):
    g = glob.glob(os.path.join(base, "**", name), recursive=True)
    return g[0] if g else ""

# --- AWS 색상 규약 ---
C_CLOUD = "#232F3E"; C_VPC = "#8C4FFF"; C_SUBNET = "#7AA116"
C_EC2 = "#ED7100"; C_MGMT = "#5A6B86"; C_SEC = "#DD344C"

def frame(icon, text, color):
    """AWS 그룹 프레임 라벨(모서리 아이콘 + 굵은 텍스트)."""
    return (f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
            f'<TR><TD FIXEDSIZE="TRUE" WIDTH="24" HEIGHT="24"><IMG SCALE="TRUE" SRC="{icon}"/></TD>'
            f'<TD><FONT POINT-SIZE="13" COLOR="{color}"><B>  {text}</B></FONT></TD></TR></TABLE>>')

def cluster(parent, cid, icon, text, color, bg):
    sub = parent.subgraph(name="cluster_" + cid)
    return sub, dict(label=frame(icon, text, color), labelloc="t", labeljust="l",
                     style="rounded", color=color, penwidth="2.2", bgcolor=bg,
                     margin="16", fontname="Helvetica")

def inode(g, nid, icon, name):
    """아이콘 위 + 라벨 아래 (실제 로고 노드)."""
    g.node(nid, shape="plaintext", margin="0",
           label=(f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
                  f'<TR><TD FIXEDSIZE="TRUE" WIDTH="46" HEIGHT="46"><IMG SCALE="TRUE" SRC="{icon}"/></TD></TR>'
                  f'<TR><TD><FONT POINT-SIZE="9" FACE="Helvetica">{name}</FONT></TD></TR></TABLE>>'))

def chip(g, nid, name, color=C_EC2):
    """로고 없는 도구: 통일된 칩."""
    g.node(nid, shape="box", style="rounded,filled", fillcolor="white",
           color=color, penwidth="1.4", fontname="Helvetica", fontsize="9",
           label=name, height="0.5", margin="0.12,0.06")

def grid_node(g, nid, title, items, cols=3, color=C_EC2):
    """여러 도구를 한 패널(아이콘 그리드)로 — 박스가 세로로 길어지는 것 방지."""
    cells = (f'<TR><TD COLSPAN="{cols}"><FONT POINT-SIZE="9" COLOR="{color}">'
             f'<B>{title}</B></FONT></TD></TR>')
    for i in range(0, len(items), cols):
        cells += "<TR>"
        for icon, name in items[i:i + cols]:
            inner = (f'<IMG SCALE="TRUE" SRC="{icon}"/>' if icon else "")
            cells += (f'<TD CELLPADDING="5"><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">'
                      f'<TR><TD FIXEDSIZE="TRUE" WIDTH="36" HEIGHT="36">{inner}</TD></TR>'
                      f'<TR><TD><FONT POINT-SIZE="8">{name}</FONT></TD></TR></TABLE></TD>')
        cells += "</TR>"
    g.node(nid, shape="box", style="rounded", color=color, penwidth="1.3",
           label=f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" CELLPADDING="2">{cells}</TABLE>>')

g = graphviz.Digraph("architecture", format="png")
g.attr(rankdir="LR", bgcolor="white", fontname="Helvetica", pad="0.6",
       nodesep="0.4", ranksep="0.9", dpi="170", compound="true",
       labelloc="t", fontsize="20",
       label="SecuBank DevSecOps Golden Path · AWS (ap-northeast-2)")
g.attr("node", fontname="Helvetica")
g.attr("edge", fontname="Helvetica", fontsize="10", color="#5A6B86")

# 외부
inode(g, "dev", aws("general/user.png") or aws("general/users.png"), "개발자")
inode(g, "gh", onp("vcs/github.png"), "GitHub · 3 repos")

with g.subgraph(name="cluster_cloud") as cloud:
    cloud.attr(**cluster(g, "cloud", aws("aws.png"), "AWS Cloud · ap-northeast-2", C_CLOUD, "#FFFFFF")[1])

    inode(cloud, "igw", aws("network/internet-gateway.png"), "Internet Gateway")

    # 관리 · 보안
    with cloud.subgraph(name="cluster_mgmt") as m:
        m.attr(**cluster(cloud, "mgmt", aws("security/identity-and-access-management-iam-role.png"),
                         "관리 · 보안 (Management &amp; Security)", C_MGMT, "#F3F5F8")[1])
        inode(m, "iam", aws("security/identity-and-access-management-iam-role.png"), "IAM Role<BR/>SSH 미사용")
        inode(m, "ssm", aws("management/systems-manager.png"), "SSM<BR/>Session Manager")
        inode(m, "param", aws("management/systems-manager-parameter-store.png"), "Parameter Store<BR/><FONT POINT-SIZE='7'>planned</FONT>")
        inode(m, "sns", aws("integration/simple-notification-service-sns.png"), "SNS<BR/><FONT POINT-SIZE='7'>planned</FONT>")
        inode(m, "cw", aws("management/cloudwatch.png"), "CloudWatch<BR/><FONT POINT-SIZE='7'>planned</FONT>")

    # VPC
    with cloud.subgraph(name="cluster_vpc") as vpc:
        vpc.attr(**cluster(cloud, "vpc", aws("network/vpc.png"), "VPC · 10.0.0.0/16", C_VPC, "#F5F1FE")[1])

        with vpc.subgraph(name="cluster_subnet") as sn:
            sn.attr(**cluster(vpc, "subnet", aws("network/public-subnet.png"),
                              "Public Subnet · 10.0.1.0/24", C_SUBNET, "#F2F7E8")[1])

            # EC2 — CI / Supply Chain
            with sn.subgraph(name="cluster_ci") as ci:
                ci.attr(**cluster(sn, "ci", aws("compute/ec2-instance.png"),
                                  "EC2 · CI / Supply Chain  (t3.xlarge)", C_EC2, "#FDF2E8")[1])
                inode(ci, "jenkins", onp("ci/jenkins.png"), "Jenkins<BR/>18-stage")
                inode(ci, "harbor", loc("harbor"), "Harbor<BR/>Registry")
                grid_node(ci, "scanners", "Security Scanners (shift-left)", [
                    (loc("sonarqube"), "SonarQube<BR/>SAST"),
                    (loc("trivy"), "Trivy<BR/>SCA·image"),
                    (loc("git"), "Gitleaks<BR/>secret"),
                    (loc("checkov"), "Checkov<BR/>IaC"),
                    (loc("kubescape"), "Kubescape<BR/>K8s"),
                    (None, "Syft<BR/>SBOM"),
                ], cols=3)

            # EC2 — Runtime k3s
            with sn.subgraph(name="cluster_rt") as rt:
                rt.attr(**cluster(sn, "rt", aws("compute/ec2-instance.png"),
                                  "EC2 · Runtime  (t3.xlarge · k3s)", C_EC2, "#FDF2E8")[1])
                inode(rt, "argo", onp("gitops/argocd.png"), "ArgoCD<BR/>GitOps")
                inode(rt, "cilium", loc("cilium"), "Cilium · Hubble")
                inode(rt, "falco", loc("falco"), "Falco")
                chip(rt, "kbench", "kube-bench · CIS")
                inode(rt, "zap", loc("zap"), "OWASP ZAP<BR/>DAST")
                inode(rt, "vb", onp("container/k3s.png"), "VulnBank MSA<BR/>6 services")
                inode(rt, "db", onp("database/mariadb.png"), "MariaDB · PVC")

            # EC2 — DefectDojo
            with sn.subgraph(name="cluster_dd") as dd:
                dd.attr(**cluster(sn, "dd", aws("compute/ec2-instance.png"),
                                  "EC2 · DefectDojo  (t3.medium)", C_EC2, "#FDF2E8")[1])
                inode(dd, "defectdojo", loc("defectdojo"), "DefectDojo<BR/>ASOC 증적")

# --- 데이터 플로우 ---
g.edge("dev", "gh", label="git push")
g.edge("gh", "jenkins", label="webhook / poll")
g.edge("jenkins", "scanners", label="runs", color=C_MGMT, style="dashed")
g.edge("jenkins", "harbor", label="build·scan·gate", color=C_EC2)
g.edge("harbor", "argo", label="image pull", color=C_SUBNET, lhead="cluster_rt")
g.edge("argo", "vb", color=C_SUBNET)
g.edge("vb", "db", color="#9AA4B2")
g.edge("cilium", "vb", label="L3-L7 / egress", color=C_SEC, style="dashed")
g.edge("falco", "vb", label="runtime detect", color=C_SEC, style="dashed")
g.edge("zap", "vb", label="DAST", color=C_SEC, style="dashed")
g.edge("jenkins", "defectdojo", label="import-scan", color=C_VPC, lhead="cluster_dd")
g.edge("igw", "jenkins", color="#9AA4B2", style="dashed")

out = g.render(filename=os.path.join(HERE, "architecture"), format="png", cleanup=True)
print("rendered:", out)
