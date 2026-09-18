from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request
from pydantic import BaseModel

from src.services.RetrievalService import RetrievalService


class RetrievalDebugRoutes:
    MIN_LIMIT = 1
    MAX_CANDIDATE_LIMIT = 50
    MAX_FINAL_LIMIT = 20

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self.retrieval_service = retrieval_service or RetrievalService()

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return {
                str(key): RetrievalDebugRoutes._serialize(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [RetrievalDebugRoutes._serialize(item) for item in value]
        return value

    @staticmethod
    def _debug_only() -> tuple[Any, int] | None:
        if current_app.debug:
            return None
        return jsonify({"success": False, "error": "not_found"}), 404

    @classmethod
    def _positive_int(cls, value: Any, name: str, maximum: int) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be an integer.")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be an integer.") from error
        if parsed < cls.MIN_LIMIT or parsed > maximum:
            raise ValueError(
                f"{name} must be between {cls.MIN_LIMIT} and {maximum}."
            )
        return parsed

    @staticmethod
    def _optional_document_id(value: Any) -> int | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            raise ValueError("document_id must be a positive integer.")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError("document_id must be a positive integer.") from error
        if parsed < 1:
            raise ValueError("document_id must be a positive integer.")
        return parsed

    def search(self):
        blocked = self._debug_only()
        if blocked is not None:
            return blocked

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"success": False, "error": "invalid_json"}), 400

        query = str(payload.get("query") or "").strip()
        if not query:
            return jsonify({"success": False, "error": "query_required"}), 400

        try:
            candidate_limit = self._positive_int(
                payload.get("candidate_limit", 8),
                "candidate_limit",
                self.MAX_CANDIDATE_LIMIT,
            )
            final_limit = self._positive_int(
                payload.get("final_limit", 5),
                "final_limit",
                self.MAX_FINAL_LIMIT,
            )
            if final_limit > candidate_limit:
                raise ValueError("final_limit cannot exceed candidate_limit.")
            document_id = self._optional_document_id(payload.get("document_id"))

            result = self.retrieval_service.retrieve(
                user_query=query,
                candidate_limit=candidate_limit,
                final_limit=final_limit,
                document_id=document_id,
            )
        except ValueError as error:
            return jsonify({"success": False, "error": str(error)}), 400
        except Exception:
            current_app.logger.exception("Retrieval debug request failed.")
            return jsonify({
                "success": False,
                "error": "retrieval_unavailable",
            }), 503

        serialized = self._serialize(result)
        return jsonify({
            "success": True,
            "document_id": document_id,
            "candidate_limit": candidate_limit,
            "final_limit": final_limit,
            "result": serialized,
        }), 200


def create_retrieval_debug_blueprint(
    retrieval_service: RetrievalService | None = None,
) -> Blueprint:
    routes = RetrievalDebugRoutes(retrieval_service)
    blueprint = Blueprint(
        "retrieval_debug",
        __name__,
        url_prefix="/api/retrieval",
    )
    blueprint.add_url_rule(
        "/search",
        endpoint="search",
        view_func=routes.search,
        methods=["POST"],
    )
    return blueprint
