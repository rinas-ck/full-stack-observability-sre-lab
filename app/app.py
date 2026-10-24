
import os
import time
import logging

from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)

# Application configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "observability-api")

# Logging configuration for Docker stdout/stderr and Loki
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("observability-api")

app = Flask(__name__)

# Prometheus metrics
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"],
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "endpoint"],
)

# OpenTelemetry tracing
resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)

otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if otlp_endpoint:
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=otlp_endpoint)
        )
    )

trace.set_tracer_provider(provider)
FlaskInstrumentor().instrument_app(app)


@app.before_request
def start_timer():
    request.start_time = time.perf_counter()


@app.after_request
def record_metrics(response):
    elapsed = time.perf_counter() - getattr(
        request, "start_time", time.perf_counter()
    )

    endpoint = request.url_rule.rule if request.url_rule else "unknown"

    # Update Prometheus metrics
    REQUESTS.labels(
        SERVICE_NAME,
        request.method,
        endpoint,
        str(response.status_code),
    ).inc()

    LATENCY.labels(SERVICE_NAME, endpoint).observe(elapsed)

    # Emit structured request logs for Promtail and Loki
    logger.info(
        "http_request method=%s path=%s status=%s duration_seconds=%.4f",
        request.method,
        request.path,
        response.status_code,
        elapsed,
    )

    return response


@app.get("/")
def index():
    return jsonify(
        service=SERVICE_NAME,
        message="Observability SRE Lab is running",
        endpoints=["/health", "/work", "/metrics"],
    )


@app.get("/health")
def health():
    return jsonify(status="healthy", service=SERVICE_NAME), 200


@app.get("/work")
def work():
    delay = min(float(request.args.get("delay", "0.05")), 2.0)
    time.sleep(max(delay, 0))
    return jsonify(status="completed", delay_seconds=delay)


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {
        "Content-Type": CONTENT_TYPE_LATEST
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
