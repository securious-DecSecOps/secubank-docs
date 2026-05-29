#!/usr/bin/env python3
"""SecuBank DevSecOps Golden Path — AWS reference architecture (diagram-as-code).

AWS 공식 아이콘 + AWS 색상 규약(VPC 보라 / Public Subnet 초록 / EC2 주황 틴트)으로
terraform 실제 구조(VPC 10.0.0.0/16, public subnet 10.0.1.0/24, IGW, EC2 3대, IAM/SSM)를
AWS 기술 블로그 스타일로 렌더한다.

실행:  ../.diagram-venv/bin/python architecture.py   (graphviz 필요)
출력:  architecture.png
"""
import os
from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.compute import EC2Instance
from diagrams.aws.network import VPC, PublicSubnet, InternetGateway
from diagrams.aws.management import SystemsManager, SystemsManagerParameterStore
from diagrams.aws.security import IAMRole
from diagrams.aws.integration import SimpleNotificationServiceSns
from diagrams.aws.general import Users
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import Jenkins
from diagrams.onprem.gitops import Argocd
from diagrams.onprem.container import K3S
from diagrams.onprem.database import MariaDB

HERE = os.path.dirname(os.path.abspath(__file__))
IC = os.path.join(HERE, "icons")
def ic(name): return os.path.join(IC, name + ".png")

# AWS reference-architecture color conventions
AWS_DARK   = "#232F3E"
VPC_PURPLE = "#8C4FFF"
SUBNET_GRN = "#7AA116"
EC2_ORANGE = "#ED7100"
SEC_RED    = "#DD344C"

graph_attr = {
    "fontname": "Sans-Serif", "fontsize": "22", "labelloc": "t",
    "bgcolor": "white", "pad": "0.6", "nodesep": "0.55", "ranksep": "1.0",
    "dpi": "168", "splines": "ortho",
}
node_attr = {"fontname": "Sans-Serif", "fontsize": "12"}

def box(pen, bg):
    # 클러스터: pencolor=테두리, bgcolor=연한 배경, style=rounded (filled 쓰면 솔리드로 꽉 참)
    return {"fontname": "Sans-Serif", "fontsize": "13", "labelloc": "t", "labeljust": "l",
            "pencolor": pen, "penwidth": "2", "style": "rounded", "bgcolor": bg, "margin": "18"}

with Diagram(
    "SecuBank DevSecOps Golden Path · AWS (ap-northeast-2)",
    filename=os.path.join(HERE, "architecture"),
    outformat="png", direction="LR", show=False,
    graph_attr=graph_attr, node_attr=node_attr,
):
    dev = Users("개발자")
    gh = Github("GitHub\n3 repos")

    with Cluster("AWS Cloud · ap-northeast-2", graph_attr=box(AWS_DARK, "#FFFFFF")):
        igw = InternetGateway("Internet\nGateway")

        with Cluster("관리 · 보안 (Management & Security)", graph_attr=box("#5A6B86", "#F3F5F8")):
            iam = IAMRole("EC2 SSM Role\nSSH 미사용")
            ssm = SystemsManager("SSM\nSession Manager")
            param = SystemsManagerParameterStore("Parameter Store\nplanned")
            sns = SimpleNotificationServiceSns("SNS\nplanned")

        with Cluster("VPC · 10.0.0.0/16", graph_attr=box(VPC_PURPLE, "#F4F0FE")):
            with Cluster("Public Subnet · 10.0.1.0/24",
                         graph_attr=box(SUBNET_GRN, "#F1F7E7")):

                with Cluster("EC2 · CI / Supply Chain  (t3.xlarge)",
                             graph_attr=box(EC2_ORANGE, "#FDF1E7")):
                    jenkins = Jenkins("Jenkins\n18-stage")
                    harbor = Custom("Harbor", ic("harbor"))

                with Cluster("EC2 · Runtime  (t3.xlarge · k3s)",
                             graph_attr=box(EC2_ORANGE, "#FDF1E7")):
                    argo = Argocd("ArgoCD")
                    cilium = Custom("Cilium / Hubble", ic("cilium"))
                    falco = Custom("Falco", ic("falco"))
                    vb = K3S("VulnBank MSA\n6 svc")
                    db = MariaDB("MariaDB\nPVC")

                with Cluster("EC2 · DefectDojo  (t3.medium)",
                             graph_attr=box(EC2_ORANGE, "#FDF1E7")):
                    dd = Custom("DefectDojo", ic("defectdojo"))

    # --- data flows ---
    dev >> Edge(label="git push", color=AWS_DARK) >> gh
    gh >> Edge(label="webhook / poll", color=AWS_DARK) >> jenkins
    jenkins >> Edge(label="build·scan·gate", color=EC2_ORANGE) >> harbor
    harbor >> Edge(label="image pull (GitOps)", color=SUBNET_GRN) >> argo
    argo >> Edge(color=SUBNET_GRN) >> vb
    vb >> Edge(color="#888888") >> db
    cilium >> Edge(label="L3-L7 / egress", color=SEC_RED, style="dashed") >> vb
    falco >> Edge(label="runtime detect", color=SEC_RED, style="dashed") >> vb
    jenkins >> Edge(label="import-scan", color=VPC_PURPLE) >> dd
    igw >> Edge(color="#888888") >> jenkins
