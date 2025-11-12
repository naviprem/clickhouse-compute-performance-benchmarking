#!/usr/bin/env python3
"""
Synthetic OTEL metrics generator.
Sends metrics via OTLP/gRPC to collector.
"""

import time
import random
import os
from datetime import datetime
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

# Configuration
OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT", "otel-collector:4317")
SERVICE_NAME = os.getenv("SERVICE_NAME", "demo-service")
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "5"))

# Service attributes
resource = Resource.create({
    "service.name": SERVICE_NAME,
    "service.version": "1.0.0",
    "deployment.environment": "demo",
    "host.name": os.getenv("HOSTNAME", "unknown"),
})

# Setup OTLP exporter
exporter = OTLPMetricExporter(
    endpoint=OTEL_ENDPOINT,
    insecure=True,  # No TLS for demo
)

# Setup meter provider
reader = PeriodicExportingMetricReader(
    exporter=exporter,
    export_interval_millis=INTERVAL_SECONDS * 1000,
)
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)

# Create meter
meter = metrics.get_meter(__name__)

# Metric state (for observable gauges)
current_cpu = 50.0
current_memory = 2048.0

def generate_cpu_usage():
    """Generate realistic CPU usage with occasional spikes."""
    base = random.uniform(20, 60)
    if random.random() < 0.1:  # 10% chance of spike
        return random.uniform(80, 95)
    return base

def generate_memory_usage():
    """Generate realistic memory usage with gradual increase."""
    return random.uniform(1000, 4096)

def generate_response_time():
    """Generate realistic response times with outliers."""
    if random.random() < 0.05:  # 5% chance of slow response
        return random.uniform(1000, 5000)
    return random.uniform(10, 200)

# Callback functions for observable gauges
def cpu_callback(options):
    global current_cpu
    current_cpu = generate_cpu_usage()
    yield metrics.Observation(current_cpu)

def memory_callback(options):
    global current_memory
    current_memory = generate_memory_usage()
    yield metrics.Observation(current_memory)

# Create observable gauges
cpu_gauge = meter.create_observable_gauge(
    name="system.cpu.usage",
    callbacks=[cpu_callback],
    description="CPU usage percentage",
    unit="percent",
)

memory_gauge = meter.create_observable_gauge(
    name="system.memory.usage",
    callbacks=[memory_callback],
    description="Memory usage",
    unit="MB",
)

# Create counter and histogram
request_counter = meter.create_counter(
    name="http.requests.total",
    description="Total HTTP requests",
    unit="1",
)

response_time_histogram = meter.create_histogram(
    name="http.request.duration",
    description="HTTP request duration",
    unit="ms",
)

def main():
    print(f"Starting metrics generator: {SERVICE_NAME}")
    print(f"OTLP endpoint: {OTEL_ENDPOINT}")
    print(f"Interval: {INTERVAL_SECONDS}s")
    print()

    request_count = 0

    while True:
        try:
            # Simulate multiple requests
            num_requests = random.randint(5, 20)
            for _ in range(num_requests):
                request_counter.add(1)
                response_time_histogram.record(generate_response_time())
                request_count += 1

            print(f"[{datetime.now().isoformat()}] Generated metrics (CPU: {current_cpu:.1f}%, Memory: {current_memory:.1f}MB, Requests: {request_count})")

            time.sleep(INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()