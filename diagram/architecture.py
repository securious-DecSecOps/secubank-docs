#!/usr/bin/env python3
"""SecuBank DevSecOps Golden Path — diagram-as-code.

준비:
  sudo apt-get install -y graphviz          # 1회 (시스템 바이너리)
  ../.diagram-venv/bin/pip install diagrams  # 이미 설치됨
  bash fetch_icons.sh                        # 도구 로고 다운로드(없는 건 라벨 박스로 대체)
실행:
  ../.diagram-venv/bin/python architecture.py
출력:
  architecture.png   (3-VM target 아키텍처, VulnBank on k3s)
"""
import os
from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.generic.blank import Blank
from diagrams.aws.management import SystemsManagerParameterStore
from diagrams.aws.integration import SimpleNotificationServiceSns
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import Jenkins
from diagrams.onprem.gitops import Argocd
from diagrams.onprem.registry import Harbor
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.security import Trivy
from diagrams.onprem.database import MariaDB

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, "icons")


def tool(label, slug):
    """로고 PNG가 있으면 실제 아이콘(Custom), 없으면 라벨 박스(Blank)로 폴백."""
    p = os.path.join(ICONS, slug + ".png")
    return Custom(label, p) if os.path.exists(p) else Blank(label)


graph_attr = {"fontsize": "20", "bgcolor": "white", "pad": "0.6", "splines": "spline", "nodesep": "0.6", "ranksep": "1.0"}

with Diagram(
    "SecuBank DevSecOps Golden Path",
    filename=os.path.join(HERE, "architecture"),
    outformat="png",
    direction="LR",
    show=False,
    graph_attr=graph_attr,
):
    dev = Blank("Developer\n(git push)")

    with Cluster("GitHub"):
        gh = Github("repos\n(devsecops / app-source / gitops)")

    ssm = SystemsManagerParameterStore("SSM Parameter Store\n(secrets · planned)")
    sns = SimpleNotificationServiceSns("SNS\n(alerts · planned)")

    with Cluster("AWS VPC (ap-northeast-2)"):

        with Cluster("CI / Supply Chain VM"):
            jenkins = Jenkins("Jenkins\n18-stage")
            with Cluster("Security Scanners"):
                scanners = [
                    tool("SonarQube (SAST)", "sonarqube"),
                    tool("Gitleaks", "gitleaks"),
                    tool("Checkov", "checkov"),
                    tool("Kubescape", "kubescape"),
                    Trivy("Trivy"),
                    tool("Syft (SBOM)", "syft"),
                ]
            harbor = Harbor("Harbor\nRegistry")
            jenkins >> scanners
            jenkins >> harbor

        with Cluster("Runtime VM — k3s"):
            argo = Argocd("ArgoCD")
            with Cluster("VulnBank MSA (6 svc)"):
                app = Blank("frontend · user · tx\nstatus · file · settings")
                db = MariaDB("MariaDB (PVC)")
                app >> db
            cilium = tool("Cilium / Hubble", "cilium")
            falco = tool("Falco", "falco")
            kbench = Blank("kube-bench")
            zap = tool("OWASP ZAP", "zap")
            with Cluster("Observability (planned)"):
                prom = Prometheus("Prometheus")
                graf = Grafana("Grafana")
                prom >> graf
            argo >> app
            cilium >> Edge(color="firebrick", label="L3-L7 / egress") >> app
            falco >> Edge(color="firebrick", label="runtime detect") >> app
            zap >> Edge(style="dashed", label="DAST") >> app

        with Cluster("Evidence VM"):
            dd = tool("DefectDojo", "defectdojo")

    dev >> gh >> jenkins
    harbor >> Edge(label="image pull") >> argo
    jenkins >> Edge(label="import-scan") >> dd
    ssm >> Edge(style="dashed", color="gray") >> jenkins
    jenkins >> Edge(style="dashed", color="gray") >> sns
