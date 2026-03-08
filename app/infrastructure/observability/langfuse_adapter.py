"""Langfuse observability adapter with graceful fallback when disabled."""

from typing import Any, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


class NoOpSpan:
    """No-op span used when Langfuse is disabled."""

    def __init__(self, name: str = "") -> None:
        self.name = name

    def update(self, **_: Any) -> None:
        pass

    def end(self, **_: Any) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_: Any) -> None:
        pass


class NoOpTrace:
    """No-op trace used when Langfuse is disabled."""

    def __init__(self, name: str = "") -> None:
        self.id = "noop"
        self.name = name

    def span(self, name: str, **_: Any) -> NoOpSpan:
        return NoOpSpan(name)

    def update(self, **_: Any) -> None:
        pass

    def generation(self, **_: Any) -> NoOpSpan:
        return NoOpSpan()


class ObservabilityAdapter:
    """Wraps Langfuse for tracing with a clean no-op fallback.

    Usage:
        obs = ObservabilityAdapter(enabled=True, public_key=..., secret_key=...)
        with obs.trace("run_creation", run_id=run_id) as trace:
            with obs.span(trace, "ideation") as span:
                ...
    """

    def __init__(
        self,
        enabled: bool = False,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: str = "https://cloud.langfuse.com",
    ) -> None:
        self.enabled = enabled
        self._client = None

        if enabled:
            self._init_client(public_key, secret_key, host)

    def _init_client(
        self,
        public_key: Optional[str],
        secret_key: Optional[str],
        host: str,
    ) -> None:
        try:
            from langfuse import Langfuse  # type: ignore[import-untyped]
            if not public_key or not secret_key:
                logger.warning("langfuse_keys_missing_disabling")
                self.enabled = False
                return
            self._client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            logger.info("langfuse_initialized", host=host)
        except ImportError:
            logger.warning("langfuse_not_installed_disabling")
            self.enabled = False

    def start_trace(self, name: str, **metadata: Any) -> Any:
        """Start a new trace."""
        if not self.enabled or not self._client:
            return NoOpTrace(name)
        try:
            return self._client.trace(name=name, metadata=metadata)
        except Exception as e:
            logger.warning("langfuse_trace_error", error=str(e))
            return NoOpTrace(name)

    def start_span(self, trace: Any, name: str, **kwargs: Any) -> Any:
        """Start a span within a trace."""
        if not self.enabled or isinstance(trace, NoOpTrace):
            return NoOpSpan(name)
        try:
            return trace.span(name=name, **kwargs)
        except Exception as e:
            logger.warning("langfuse_span_error", error=str(e))
            return NoOpSpan(name)

    def record_generation(
        self,
        trace: Any,
        name: str,
        prompt: str,
        completion: str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Record an LLM generation event."""
        if not self.enabled or isinstance(trace, NoOpTrace):
            return
        try:
            trace.generation(
                name=name,
                input=prompt,
                output=completion,
                model=model,
                **kwargs,
            )
        except Exception as e:
            logger.warning("langfuse_generation_error", error=str(e))

    def flush(self) -> None:
        """Flush pending events to Langfuse."""
        if self.enabled and self._client:
            try:
                self._client.flush()
            except Exception as e:
                logger.warning("langfuse_flush_error", error=str(e))
