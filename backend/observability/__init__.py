import time
import threading
from dataclasses import dataclass, field
from typing import Any

from config.logging import get_logger

logger = get_logger("observability.tracer")


@dataclass
class Span:
    name: str
    started_at: float = field(default_factory=time.perf_counter)
    ended_at: float = 0.0
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "ok"

    def finish(self, status: str = "ok") -> None:
        self.ended_at = time.perf_counter()
        self.duration_ms = int((self.ended_at - self.started_at) * 1000)
        self.status = status


class Tracer:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, max_spans: int = 500):
        self._spans: list[Span] = []
        self._max = max_spans
        self._active: dict[str, Span] = {}

    @classmethod
    def get(cls) -> "Tracer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_span(self, name: str, metadata: dict | None = None) -> Span:
        span = Span(name=name, metadata=metadata or {})
        with self._lock:
            self._active[name] = span
        return span

    def end_span(self, name: str, status: str = "ok") -> Span | None:
        with self._lock:
            span = self._active.pop(name, None)
        if span is None:
            return None
        span.finish(status)
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > self._max:
                self._spans = self._spans[-self._max:]
        logger.debug(
            "Span completed",
            extra={"structured_extra": {
                "name": name, "duration_ms": span.duration_ms, "status": status,
            }},
        )
        return span

    def get_recent_spans(self, limit: int = 20) -> list[dict]:
        with self._lock:
            recent = self._spans[-limit:]
        return [
            {
                "name": s.name,
                "duration_ms": s.duration_ms,
                "status": s.status,
                "metadata": s.metadata,
            }
            for s in recent
        ]

    def get_slow_spans(self, threshold_ms: int = 5000) -> list[dict]:
        with self._lock:
            slow = [s for s in self._spans if s.duration_ms > threshold_ms]
        return [
            {"name": s.name, "duration_ms": s.duration_ms, "metadata": s.metadata}
            for s in slow
        ]


@dataclass
class Metrics:
    total_requests: int = 0
    fast_path_hits: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    total_latency_ms: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_requests if self.total_requests else 0.0

    @property
    def fast_path_ratio(self) -> float:
        return self.fast_path_hits / self.total_requests if self.total_requests else 0.0


class MetricsCollector:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._metrics = Metrics()

    @classmethod
    def get(cls) -> "MetricsCollector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_request(self, latency_ms: int, is_fast_path: bool = False, tool_calls: int = 0, error: bool = False) -> None:
        with self._lock:
            m = self._metrics
            m.total_requests += 1
            m.total_latency_ms += latency_ms
            if is_fast_path:
                m.fast_path_hits += 1
            m.tool_calls += tool_calls
            if error:
                m.errors += 1

    def record_llm_call(self) -> None:
        with self._lock:
            self._metrics.llm_calls += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self._metrics.cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._metrics.cache_misses += 1

    def snapshot(self) -> dict:
        with self._lock:
            m = self._metrics
            return {
                "total_requests": m.total_requests,
                "fast_path_hits": m.fast_path_hits,
                "fast_path_ratio": round(m.fast_path_ratio, 3),
                "llm_calls": m.llm_calls,
                "tool_calls": m.tool_calls,
                "cache_hits": m.cache_hits,
                "cache_misses": m.cache_misses,
                "errors": m.errors,
                "avg_latency_ms": round(m.avg_latency_ms, 1),
            }
