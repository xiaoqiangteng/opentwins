from app.models.schemas import TraceCreate
from app.services.trace_service import TraceService


def test_trace_service_roundtrip(tmp_path):
    service = TraceService(str(tmp_path / "trace.sqlite"))
    service.add(
        TraceCreate(
            trace_id="trace_test",
            stage="mqtt",
            status="ok",
            message="message received",
            payload={"topic": "telemetry/test"},
        )
    )

    result = service.get("trace_test")

    assert result.trace_id == "trace_test"
    assert len(result.steps) == 1
    assert result.steps[0].stage == "mqtt"
    assert result.steps[0].payload == {"topic": "telemetry/test"}
