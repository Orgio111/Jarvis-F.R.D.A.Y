"""Prompt Library data models."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class PromptVersion:
    """One version of a prompt template."""
    version:    int   = 1
    body:       str   = ""
    variables:  list[str] = field(default_factory=list)   # {{var}} placeholders
    created_at: float = field(default_factory=time.time)
    notes:      str   = ""

    def render(self, **kwargs: str) -> str:
        """Fill {{variable}} placeholders."""
        result = self.body
        for k, v in kwargs.items():
            result = result.replace(f"{{{{{k}}}}}", v)
        return result

    def to_dict(self) -> dict:
        return {
            "version":    self.version,
            "body":       self.body,
            "variables":  self.variables,
            "created_at": self.created_at,
            "notes":      self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PromptVersion":
        return cls(
            version=d.get("version", 1),
            body=d.get("body", ""),
            variables=d.get("variables", []),
            created_at=d.get("created_at", time.time()),
            notes=d.get("notes", ""),
        )


@dataclass
class PromptTemplate:
    """A named, versioned prompt template."""
    template_id:  str   = field(default_factory=lambda: f"tpl_{uuid4().hex[:10]}")
    name:         str   = "Untitled"
    description:  str   = ""
    category:     str   = "general"      # general | code | research | creative | system
    tags:         list[str] = field(default_factory=list)
    versions:     list[PromptVersion] = field(default_factory=list)
    active_version: int = 1
    created_at:   float = field(default_factory=time.time)
    updated_at:   float = field(default_factory=time.time)
    usage_count:  int   = 0
    metadata:     dict[str, Any] = field(default_factory=dict)

    @property
    def current(self) -> PromptVersion | None:
        for v in self.versions:
            if v.version == self.active_version:
                return v
        return self.versions[-1] if self.versions else None

    def add_version(self, body: str, notes: str = "") -> PromptVersion:
        import re
        variables = re.findall(r"\{\{(\w+)\}\}", body)
        next_ver = max((v.version for v in self.versions), default=0) + 1
        ver = PromptVersion(version=next_ver, body=body, variables=list(set(variables)), notes=notes)
        self.versions.append(ver)
        self.active_version = next_ver
        self.updated_at = time.time()
        return ver

    def render(self, **kwargs: str) -> str:
        v = self.current
        if not v:
            raise ValueError("No versions available")
        self.usage_count += 1
        return v.render(**kwargs)

    def to_dict(self, include_versions: bool = True) -> dict:
        d: dict[str, Any] = {
            "template_id":    self.template_id,
            "name":           self.name,
            "description":    self.description,
            "category":       self.category,
            "tags":           self.tags,
            "active_version": self.active_version,
            "version_count":  len(self.versions),
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "usage_count":    self.usage_count,
            "metadata":       self.metadata,
        }
        if include_versions:
            d["versions"] = [v.to_dict() for v in self.versions]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PromptTemplate":
        tpl = cls(
            template_id=d["template_id"],
            name=d.get("name", "Untitled"),
            description=d.get("description", ""),
            category=d.get("category", "general"),
            tags=d.get("tags", []),
            active_version=d.get("active_version", 1),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
            usage_count=d.get("usage_count", 0),
            metadata=d.get("metadata", {}),
        )
        for v in d.get("versions", []):
            tpl.versions.append(PromptVersion.from_dict(v))
        return tpl
