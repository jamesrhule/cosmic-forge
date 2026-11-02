"""Observability hooks (PROMPT 10 v2 §B).

Two layers:

  - **OpenTelemetry traces** — :func:`traced` decorates a coroutine
    or a sync function and emits a span tagged with
    ``provenance_ref`` (when present in the kwargs) plus the
    function's qualified name. The OTel SDK is SOFT-IMPORTED;
    when it's missing the decorator is a transparent no-op so
    PROMPT 10 audits stay green in the sandbox.
  - **Prometheus metrics** — :class:`MetricsRegistry` exposes
    histograms for run wallclock, audit pass count by domain,
    and calibration-drift events. ``/metrics`` is mounted on the
    FastAPI app via :func:`mount_metrics_route`.

Both layers stay process-wide singletons so the request handlers
+ background pipelines emit into the same registry.
"""

from __future__ import annotations

import contextlib
import functools
import inspect
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator


# ── Metrics ─────────────────────────────────────────────────────


@dataclass
class _Histogram:
    """Tiny in-memory histogram; mirrors the Prometheus counter-pair."""

    buckets: list[float]
    counts: list[int] = field(default_factory=list)
    total: float = 0.0
    n: int = 0

    def __post_init__(self) -> None:
        if not self.counts:
            self.counts = [0] * (len(self.buckets) + 1)

    def observe(self, value: float) -> None:
        self.n += 1
        self.total += float(value)
        for i, edge in enumerate(self.buckets):
            if value <= edge:
                self.counts[i] += 1
                return
        self.counts[-1] += 1

    def render(self, name: str, labels: dict[str, str]) -> list[str]:
        lbl = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        prefix = f"{name}{{{lbl}}}" if lbl else name
        out: list[str] = []
        cumulative = 0
        for edge, count in zip(self.buckets, self.counts[:-1]):
            cumulative += count
            edge_repr = "+Inf" if edge == float("inf") else f"{edge}"
            out.append(
                f"{name}_bucket{{le=\"{edge_repr}\"{(',' + lbl) if lbl else ''}}} {cumulative}"
            )
        cumulative += self.counts[-1]
        out.append(
            f"{name}_bucket{{le=\"+Inf\"{(',' + lbl) if lbl else ''}}} {cumulative}"
        )
        out.append(f"{name}_count{{{lbl}}} {self.n}" if lbl else f"{name}_count {self.n}")
        out.append(f"{name}_sum{{{lbl}}} {self.total}" if lbl else f"{name}_sum {self.total}")
        _ = prefix
        return out


class MetricsRegistry:
    """Process-wide metrics registry (PROMPT 10 v2 §B)."""

    _RUN_WALLCLOCK_BUCKETS = [
        0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0,
        60.0, 300.0, float("inf"),
    ]
    _AUDIT_PASS_BUCKETS = [
        1, 2, 5, 10, 20, 50, 100, 200, float("inf"),
    ]

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # (metric_name, labelset) → _Histogram
        self._histograms: dict[tuple[str, frozenset[tuple[str, str]]], _Histogram] = {}
        # (metric_name, labelset) → counter int
        self._counters: dict[tuple[str, frozenset[tuple[str, str]]], int] = {}
        # Pre-register the canonical metrics so /metrics is non-empty
        # even before the first observation lands.
        self._touch_histogram(
            "qcompass_run_wallclock_seconds",
            {"domain": "_init"},
            buckets=self._RUN_WALLCLOCK_BUCKETS,
        )
        self._touch_histogram(
            "qcompass_audit_pass_count",
            {"domain": "_init"},
            buckets=self._AUDIT_PASS_BUCKETS,
        )
        self._touch_counter("qcompass_calibration_drift_total", {"provider": "_init"})

    # ── recorders ─────────────────────────────────────────────

    def observe_run_wallclock(self, *, domain: str, seconds: float) -> None:
        self._histogram(
            "qcompass_run_wallclock_seconds",
            {"domain": domain},
            self._RUN_WALLCLOCK_BUCKETS,
        ).observe(seconds)

    def observe_audit_pass_count(self, *, domain: str, count: int) -> None:
        self._histogram(
            "qcompass_audit_pass_count",
            {"domain": domain},
            self._AUDIT_PASS_BUCKETS,
        ).observe(count)

    def increment_calibration_drift(self, *, provider: str) -> None:
        key = ("qcompass_calibration_drift_total", _label_key({"provider": provider}))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1

    def increment_router_decision(self, *, provider: str, status: str) -> None:
        key = (
            "qcompass_router_decisions_total",
            _label_key({"provider": provider, "status": status}),
        )
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1

    # ── render ─────────────────────────────────────────────────

    def render_prometheus(self) -> str:
        out: list[str] = []
        with self._lock:
            for (name, labels_key), hist in sorted(
                self._histograms.items(), key=lambda kv: kv[0],
            ):
                labels = dict(labels_key)
                out.extend(hist.render(name, labels))
            for (name, labels_key), val in sorted(
                self._counters.items(), key=lambda kv: kv[0],
            ):
                labels = dict(labels_key)
                lbl = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                out.append(f"{name}{{{lbl}}} {val}" if lbl else f"{name} {val}")
        return "\n".join(out) + "\n"

    # ── internals ─────────────────────────────────────────────

    def _histogram(
        self, name: str, labels: dict[str, str], buckets: list[float],
    ) -> _Histogram:
        return self._touch_histogram(name, labels, buckets=buckets)

    def _touch_histogram(
        self,
        name: str,
        labels: dict[str, str],
        *,
        buckets: list[float],
    ) -> _Histogram:
        key = (name, _label_key(labels))
        with self._lock:
            hist = self._histograms.get(key)
            if hist is None:
                hist = _Histogram(buckets=list(buckets))
                self._histograms[key] = hist
            return hist

    def _touch_counter(
        self, name: str, labels: dict[str, str],
    ) -> None:
        key = (name, _label_key(labels))
        with self._lock:
            self._counters.setdefault(key, 0)


_REGISTRY: MetricsRegistry | None = None
_REGISTRY_LOCK = threading.Lock()


def get_metrics_registry() -> MetricsRegistry:
    global _REGISTRY
    with _REGISTRY_LOCK:
        if _REGISTRY is None:
            _REGISTRY = MetricsRegistry()
        return _REGISTRY


def reset_metrics_registry() -> None:
    """Drop the singleton — primarily for tests."""
    global _REGISTRY
    with _REGISTRY_LOCK:
        _REGISTRY = None


# ── OpenTelemetry trace wrapper ────────────────────────────────


def _otel_tracer() -> Any | None:
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
        return trace.get_tracer("ucgle_f1.m8_agent")
    except ImportError:
        return None


@contextlib.contextmanager
def span(
    name: str, *, attributes: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Emit an OpenTelemetry span when the SDK is available; otherwise pass through.

    The span carries ``provenance_ref`` as an attribute when the
    caller passes it in. The contract documented in audit A9:
    every span MUST surface ``provenance_ref`` when one was supplied.
    """
    tracer = _otel_tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(name) as s:
        for k, v in (attributes or {}).items():
            try:
                s.set_attribute(k, v)
            except Exception:
                continue
        yield


def traced(
    name: str | None = None,
    *,
    extract_provenance: Callable[..., str | None] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: wrap a function in an OTel span + record wallclock.

    ``extract_provenance(*args, **kwargs)`` returns the
    provenance_ref to attach to the span; defaults to looking up
    a ``provenance_ref`` keyword argument.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        span_name = name or fn.__qualname__

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def awrapper(*args: Any, **kwargs: Any) -> Any:
                pref = (
                    extract_provenance(*args, **kwargs)
                    if extract_provenance
                    else kwargs.get("provenance_ref")
                )
                attrs: dict[str, Any] = {"function": fn.__qualname__}
                if pref:
                    attrs["provenance_ref"] = pref
                start = time.perf_counter()
                with span(span_name, attributes=attrs):
                    out = await fn(*args, **kwargs)
                # Optional metric: wallclock per call. The audit A9
                # asserts that wrapping any qcompass route hits the
                # qcompass_run_wallclock_seconds histogram.
                domain = kwargs.get("domain") or "unspecified"
                get_metrics_registry().observe_run_wallclock(
                    domain=str(domain),
                    seconds=time.perf_counter() - start,
                )
                return out
            return awrapper

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            pref = (
                extract_provenance(*args, **kwargs)
                if extract_provenance
                else kwargs.get("provenance_ref")
            )
            attrs: dict[str, Any] = {"function": fn.__qualname__}
            if pref:
                attrs["provenance_ref"] = pref
            start = time.perf_counter()
            with span(span_name, attributes=attrs):
                out = fn(*args, **kwargs)
            domain = kwargs.get("domain") or "unspecified"
            get_metrics_registry().observe_run_wallclock(
                domain=str(domain),
                seconds=time.perf_counter() - start,
            )
            return out

        return wrapper

    return decorator


# ── /metrics route ──────────────────────────────────────────────


def mount_metrics_route(app: Any) -> None:
    """Mount ``GET /metrics`` (Prometheus text format)."""
    from fastapi.responses import PlainTextResponse

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        return get_metrics_registry().render_prometheus()


# ── helpers ─────────────────────────────────────────────────────


def _label_key(labels: dict[str, str]) -> frozenset[tuple[str, str]]:
    return frozenset((str(k), str(v)) for k, v in labels.items())


__all__ = [
    "MetricsRegistry",
    "get_metrics_registry",
    "mount_metrics_route",
    "reset_metrics_registry",
    "span",
    "traced",
]
