import threading
import time
import uuid
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.auth.security import get_current_user


class SlidingWindowRateLimiter:
    """
    사용자별 슬라이딩 윈도우 레이트 리미터 (인메모리, 단일 인스턴스용).

    LLM 호출이 포함된 고비용 엔드포인트의 남용을 막는 것이 목적이다.
    다중 인스턴스로 확장하면 Redis 등 공유 저장소 기반으로 교체해야 한다.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True


# 식물 상담(RAG/LLM) 엔드포인트: 사용자당 분당 6회
chat_limiter = SlidingWindowRateLimiter(max_requests=6, window_seconds=60.0)


def rate_limit_chat(current_user_id: uuid.UUID = Depends(get_current_user)) -> None:
    if not chat_limiter.allow(str(current_user_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="상담 요청이 너무 잦습니다. 잠시 후 다시 시도해주세요.",
            headers={"Retry-After": "60"},
        )
