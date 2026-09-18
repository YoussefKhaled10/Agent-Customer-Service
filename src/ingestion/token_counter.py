import re


class TokenCounter:
    _pattern = re.compile(r"\w+|[^\w\s]", re.UNICODE)

    @classmethod
    def estimate(cls, text: str) -> int:
        if not text:
            return 0
        return max(1, round(len(cls._pattern.findall(text)) * 1.25))
