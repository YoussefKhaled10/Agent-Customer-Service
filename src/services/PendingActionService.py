from __future__ import annotations

from typing import Any, Literal

ConfirmationDecision = Literal[
    "confirm",
    "reject",
    "modify",
    "unclear",
]


class PendingActionService:
    CONFIRM_PHRASES = {
        "yes", "confirm", "confirmed", "ok", "okay",
        "نعم", "ايوه", "أيوه", "اكد", "أكد", "موافق",
        "تمام اكد", "تمام أكد", "نفذ", "نفّذ",
    }
    REJECT_PHRASES = {
        "no", "cancel", "reject", "stop",
        "لا", "الغى", "ألغي", "الغي", "إلغاء",
        "مش موافق", "مش عاوز", "خلاص لا",
    }
    MODIFY_MARKERS = {
        "بدل", "غير", "غيّر", "عدل", "عدّل",
        "خلي", "خلّي", "change", "modify", "instead",
    }

    @classmethod
    def classify(cls, message: str) -> ConfirmationDecision:
        normalized = " ".join(
            message.strip().casefold().split()
        )
        if normalized in cls.CONFIRM_PHRASES:
            return "confirm"
        if normalized in cls.REJECT_PHRASES:
            return "reject"
        if any(
            marker in normalized
            for marker in cls.MODIFY_MARKERS
        ):
            return "modify"
        return "unclear"

    @staticmethod
    def confirmation_message(
        pending_action: dict[str, Any],
    ) -> str:
        tool_name = pending_action.get("tool_name")
        arguments = pending_action.get("arguments", {})
        if tool_name == "order_creation":
            items = arguments.get("items", [])
            count = sum(
                int(item.get("quantity", 0))
                for item in items
                if isinstance(item, dict)
            )
            return (
                f"تمام، العملية جاهزة وفيها {count} قطعة. "
                "اكتب «أكد» للتنفيذ أو «لا» للإلغاء."
            )
        if tool_name == "order_cancellation":
            number = arguments.get("order_number", "")
            return (
                f"هل تؤكد إلغاء الطلب {number}؟ "
                "اكتب «أكد» للتنفيذ أو «لا» للتراجع."
            )
        return "اكتب «أكد» للتنفيذ أو «لا» للإلغاء."
