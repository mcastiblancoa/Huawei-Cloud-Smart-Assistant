from config.logging import get_logger

logger = get_logger("tools.discovery")

logger.warning(
    "tools/discovery.py is deprecated. Use tools/services_discovery.py instead. "
    "This module is kept as a stub only."
)
