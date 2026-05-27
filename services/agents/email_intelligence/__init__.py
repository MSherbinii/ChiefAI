from .deep_scanner import deep_scan_inbox, get_scan_status

try:
    from .entity_clusterer import cluster_entities
except ImportError:
    cluster_entities = None  # type: ignore[assignment]

try:
    from .subscription_detector import detect_subscriptions
except ImportError:
    detect_subscriptions = None  # type: ignore[assignment]

__all__ = [
    'deep_scan_inbox', 'get_scan_status',
    'cluster_entities',
    'detect_subscriptions',
]
