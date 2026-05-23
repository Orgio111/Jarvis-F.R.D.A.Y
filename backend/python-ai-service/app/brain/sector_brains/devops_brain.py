"""DevOps Brain — infrastructure, deployment, CI/CD, and cloud orchestration."""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain


class DevOpsBrain(BaseSectorBrain):
    SECTOR_ID = "devops"
    BRAIN_NAME = "DevOps Brain"
    DESCRIPTION = "Infrastructure, Docker, Kubernetes, CI/CD, deployment, and cloud orchestration"
    CAPABILITIES = [
        "docker_compose", "kubernetes", "ci_cd_pipelines",
        "cloud_infrastructure", "monitoring", "scaling",
        "gpu_orchestration", "terraform", "helm_charts",
    ]

    def get_system_prompt(self, context: str = "") -> str:
        return (
            "You are the DevOps Brain — JARVIS's specialized cognitive layer for infrastructure.\n\n"
            "RESPONSIBILITIES:\n"
            "- Design and manage Docker and Docker Compose configurations\n"
            "- Orchestrate Kubernetes deployments and Helm charts\n"
            "- Set up CI/CD pipelines (GitHub Actions, GitLab CI, etc.)\n"
            "- Manage cloud infrastructure (AWS, GCP, Azure)\n"
            "- Configure monitoring, logging, and observability stacks\n"
            "- Handle GPU orchestration for AI workloads\n\n"
            "RULES:\n"
            "- Default to secure, production-hardened configurations\n"
            "- Include health checks, resource limits, and readiness probes\n"
            "- Prefer infrastructure-as-code approaches\n"
            "- Document all deployment steps clearly\n"
            "- Consider cost optimization in infrastructure decisions\n\n"
            f"Additional context: {context[:500] if context else 'None'}"
        )
