"""OpenTelemetry tracing wired to Honeycomb.

When ``HONEYCOMB_API_KEY`` is set, spans are exported to Honeycomb over OTLP/HTTP.
Otherwise spans are printed to the console, so the instrumentation is observable
in local development without any account.
"""

import logging
import sys

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import (  # pyright: ignore[reportMissingTypeStubs]
    FastAPIInstrumentor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)

from app.config import settings

logger = logging.getLogger(__name__)

HONEYCOMB_ENDPOINT = "https://api.honeycomb.io/v1/traces"


def setup_telemetry(app: FastAPI) -> None:
    # Under pytest, skip span export: the console exporter would write to
    # pytest's captured stdout after it closes, raising at interpreter exit.
    if "pytest" in sys.modules:
        FastAPIInstrumentor.instrument_app(app)
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    exporter: SpanExporter
    if settings.honeycomb_api_key:
        exporter = OTLPSpanExporter(
            endpoint=HONEYCOMB_ENDPOINT,
            headers={
                "x-honeycomb-team": settings.honeycomb_api_key,
                # Required for Honeycomb Classic teams to route traces into a
                # named dataset; ignored by Environments & Services teams
                # (which derive the dataset from service.name).
                "x-honeycomb-dataset": settings.otel_service_name,
            },
        )
        logger.info("Telemetry: exporting traces to Honeycomb")
    else:
        exporter = ConsoleSpanExporter()
        logger.info("Telemetry: HONEYCOMB_API_KEY unset, printing spans to console")

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument every FastAPI request with a server span.
    FastAPIInstrumentor.instrument_app(app)


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(settings.otel_service_name)
