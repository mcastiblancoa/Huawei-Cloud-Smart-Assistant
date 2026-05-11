from fastapi import APIRouter

from models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/metrics")
def metrics():
    from observability import MetricsCollector, Tracer
    m = MetricsCollector.get()
    t = Tracer.get()
    return {
        "metrics": m.snapshot(),
        "slow_spans": t.get_slow_spans(),
        "recent_spans": t.get_recent_spans(10),
    }
