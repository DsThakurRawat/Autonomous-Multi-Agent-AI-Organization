"""
Artifacts Store
Manages all generated files, URLs, and deliverables produced by the system.
Backed by local filesystem (dev) and S3 (production).
"""

from datetime import UTC, datetime
import json
import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class Artifact:
    def __init__(
        self,
        artifact_type: str,  # code, docker_image, url, document, report
        name: str,
        content: Any,
        agent_role: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.id = f"{artifact_type}_{name}_{int(datetime.now(UTC).timestamp())}"
        self.artifact_type = artifact_type
        self.name = name
        self.content = content
        self.agent_role = agent_role
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now(UTC)
        self.s3_uri: str | None = None
        self.local_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        content_preview = (
            str(self.content)[:300]
            if not isinstance(self.content, bytes)
            else "<binary>"
        )
        return {
            "id": self.id,
            "type": self.artifact_type,
            "name": self.name,
            "agent_role": self.agent_role,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "s3_uri": self.s3_uri,
            "local_path": self.local_path,
            "content_preview": content_preview,
        }


class ArtifactsStore:
    """
    Central repository for all agent-produced deliverables.
    Provides typed storage and fast lookup by type, tag, or agent.
    """

    def __init__(self, project_id: str, output_dir: str = "./output", s3_client=None):
        self.project_id = project_id
        self.output_dir = os.path.join(output_dir, project_id)
        self._s3 = s3_client
        self._artifacts: dict[str, Artifact] = {}
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(
            "ArtifactsStore initialized",
            project_id=project_id,
            output_dir=self.output_dir,
        )

    def save(
        self,
        artifact_type: str,
        name: str,
        content: Any,
        agent_role: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        file_extension: str = ".txt",
    ) -> Artifact:
        """Save an artifact and persist to disk."""
        artifact = Artifact(artifact_type, name, content, agent_role, tags, metadata)

        # Persist to local filesystem
        safe_name = name.replace("/", "_").replace(" ", "_")
        local_path = os.path.join(
            self.output_dir, artifact_type, f"{safe_name}{file_extension}"
        )
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        with open(local_path, "w", encoding="utf-8") as f:
            if isinstance(content, (dict, list)):
                json.dump(content, f, indent=2, default=str)
            else:
                f.write(str(content))

        artifact.local_path = local_path
        self._artifacts[artifact.id] = artifact

        logger.info(
            "Artifact saved",
            artifact_id=artifact.id,
            type=artifact_type,
            name=name,
            agent=agent_role,
        )
        return artifact

    def save_code_file(self, file_path: str, content: str, agent_role: str) -> Artifact:
        """Specialized method for saving generated code files."""
        ext = os.path.splitext(file_path)[1] or ".py"
        return self.save(
            artifact_type="code",
            name=file_path,
            content=content,
            agent_role=agent_role,
            tags=["code", ext.lstrip(".")],
            file_extension=ext,
        )

    def get_by_type(self, artifact_type: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if a.artifact_type == artifact_type]

    def get_by_tag(self, tag: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if tag in a.tags]

    def get_deployment_url(self) -> str | None:
        """Get the public URL from the most recent deployment artifact."""
        urls = self.get_by_type("url")
        if urls:
            return urls[-1].content
        return None

    def get_all_code_files(self) -> dict[str, str]:
        """Returns {file_path: content} for all generated code."""
        return {a.name: a.content for a in self.get_by_type("code")}

    def manifest(self) -> dict[str, Any]:
        """Full artifact index for display/download."""
        by_type: dict[str, list] = {}
        for a in self._artifacts.values():
            by_type.setdefault(a.artifact_type, []).append(a.to_dict())
        return {
            "project_id": self.project_id,
            "total_artifacts": len(self._artifacts),
            "by_type": by_type,
            "output_dir": self.output_dir,
        }
