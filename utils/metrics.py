"""
Prometheus metrics collection
"""
from prometheus_client import Counter, Histogram, Gauge
import logging

logger = logging.getLogger(__name__)


# Request counters
REQUEST_COUNT = Counter(
    "ai_gateway_requests_total",
    "Total number of requests to the gateway",
    ["model", "status", "lob"]
)

RATE_LIMIT_HITS = Counter(
    "ai_gateway_rate_limit_hits_total",
    "Total number of rate limit hits",
    ["user_id", "lob"]
)

TOKEN_VALIDATION_FAILURES = Counter(
    "ai_gateway_token_validation_failures_total",
    "Total number of token validation failures",
    ["reason"]
)

MODEL_ROUTING_FALLBACKS = Counter(
    "ai_gateway_model_routing_fallbacks_total",
    "Total number of model routing fallbacks",
    ["primary_model", "fallback_model"]
)

# Latency metrics
REQUEST_LATENCY = Histogram(
    "ai_gateway_request_duration_seconds",
    "Request latency in seconds",
    ["model", "status"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# Token usage metrics
TOKENS_USED = Histogram(
    "ai_gateway_tokens_used",
    "Number of tokens used per request",
    ["model"],
    buckets=(10, 50, 100, 500, 1000, 2000)
)

# Current metrics
ACTIVE_REQUESTS = Gauge(
    "ai_gateway_active_requests",
    "Number of currently active requests",
    ["model"]
)

RATE_LIMIT_REMAINING = Gauge(
    "ai_gateway_rate_limit_remaining",
    "Remaining rate limit for users",
    ["user_id"]
)

# Cost metrics
COST_ACCUMULATED = Counter(
    "ai_gateway_cost_accumulated",
    "Accumulated cost of API calls",
    ["model", "lob"]
)


class MetricsRecorder:
    """Helper class to record metrics"""
    
    @staticmethod
    def record_request(model: str, status: str, lob: str):
        """Record API request"""
        REQUEST_COUNT.labels(model=model, status=status, lob=lob).inc()
    
    @staticmethod
    def record_latency(model: str, status: str, latency_seconds: float):
        """Record request latency"""
        REQUEST_LATENCY.labels(model=model, status=status).observe(latency_seconds)
    
    @staticmethod
    def record_tokens(model: str, tokens: int):
        """Record token usage"""
        TOKENS_USED.labels(model=model).observe(tokens)
    
    @staticmethod
    def set_active_requests(model: str, count: int):
        """Set number of active requests"""
        ACTIVE_REQUESTS.labels(model=model).set(count)
    
    @staticmethod
    def record_rate_limit_hit(user_id: str, lob: str):
        """Record rate limit hit"""
        RATE_LIMIT_HITS.labels(user_id=user_id, lob=lob).inc()
    
    @staticmethod
    def record_token_validation_failure(reason: str):
        """Record token validation failure"""
        TOKEN_VALIDATION_FAILURES.labels(reason=reason).inc()
    
    @staticmethod
    def record_model_fallback(primary_model: str, fallback_model: str):
        """Record model routing fallback"""
        MODEL_ROUTING_FALLBACKS.labels(
            primary_model=primary_model,
            fallback_model=fallback_model
        ).inc()
    
    @staticmethod
    def set_rate_limit_remaining(user_id: str, remaining: int):
        """Set remaining rate limit for user"""
        RATE_LIMIT_REMAINING.labels(user_id=user_id).set(remaining)
    
    @staticmethod
    def record_cost(model: str, lob: str, cost: float):
        """Record accumulated cost"""
        COST_ACCUMULATED.labels(model=model, lob=lob).inc(cost)
