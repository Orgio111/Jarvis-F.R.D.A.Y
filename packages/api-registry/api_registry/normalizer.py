from __future__ import annotations

from typing import Any


class ResponseNormalizer:
    """Normalizes API responses into a unified format regardless of source."""

    @staticmethod
    def normalize(
        data: Any,
        source_format: str = "auto",
        expected_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Convert diverse API responses into a standard dict format."""
        if data is None:
            return {"value": None, "error": "empty_response"}

        if source_format == "auto":
            return ResponseNormalizer._auto_normalize(data, expected_keys)

        if source_format == "list":
            return ResponseNormalizer._from_list(data)
        elif source_format == "nested":
            return ResponseNormalizer._from_nested(data)
        elif source_format == "flat":
            return ResponseNormalizer._from_flat(data)

        return {"value": data}

    @staticmethod
    def _auto_normalize(data: Any, expected_keys: list[str] | None) -> dict[str, Any]:
        if isinstance(data, list):
            return ResponseNormalizer._from_list(data)
        if isinstance(data, dict):
            # If expected keys provided, extract those
            if expected_keys:
                return {k: data.get(k) for k in expected_keys if k in data}
            # If nested with a results/data envelope, unwrap it
            for envelope_key in ("data", "results", "result", "items", "records", "response"):
                if envelope_key in data and isinstance(data[envelope_key], (list, dict)):
                    inner = data[envelope_key]
                    if isinstance(inner, list):
                        return {"items": inner, "total": len(inner)}
                    return {"data": inner}
            return {"data": data}
        return {"value": str(data)}

    @staticmethod
    def _from_list(data: list) -> dict[str, Any]:
        return {"items": data, "total": len(data)}

    @staticmethod
    def _from_nested(data: dict[str, Any]) -> dict[str, Any]:
        # Flatten one level of nesting
        flat: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}_{sub_key}"] = sub_value
            else:
                flat[key] = value
        return {"data": flat}

    @staticmethod
    def _from_flat(data: dict[str, Any]) -> dict[str, Any]:
        return {"data": data}
