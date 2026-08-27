"""
API Performance Monitoring Middleware
Tracks response times and logs slow queries for Item Category and other APIs
"""

import logging
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("file")

# Thresholds for logging (in seconds)
SLOW_QUERY_THRESHOLD = 0.1  # 100ms
SLOW_API_THRESHOLD = 0.3  # 300ms
CRITICAL_API_THRESHOLD = 1.0  # 1 second


class APIPerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to monitor API response times and log performance metrics.
    Tracks slow queries and API endpoints for performance optimization.
    """

    def process_request(self, request):
        """Record start time for request"""
        request._start_time = time.time()
        return None

    def process_response(self, request, response):
        """Log response time and performance metrics"""
        if hasattr(request, "_start_time"):
            duration = time.time() - request._start_time

            # Only log API endpoints (not static files, admin, etc.)
            if request.path.startswith("/api/"):
                self._log_performance(request, response, duration)

                # Add response time header for client monitoring
                response["X-Response-Time"] = f"{duration:.3f}s"

                # Add warning header if response is slow
                if duration > CRITICAL_API_THRESHOLD:
                    response["X-Performance-Warning"] = "CRITICAL"
                elif duration > SLOW_API_THRESHOLD:
                    response["X-Performance-Warning"] = "SLOW"

        return response

    def _log_performance(self, request, response, duration):
        """Log performance metrics based on thresholds"""
        path = request.path
        method = request.method
        status_code = response.status_code

        # Extract module name from path (e.g., /api/v1/item-categories/ -> item-categories)
        module_name = "Unknown"
        if "/item-categories" in path:
            module_name = "Item Category"
        elif "/departments" in path:
            module_name = "Department"
        elif "/section-types" in path:
            module_name = "Section Type"
        elif "/plants" in path:
            module_name = "Plant"
        elif "/customer" in path:
            module_name = "Customer"

        # Log based on severity
        if duration > CRITICAL_API_THRESHOLD:
            logger.error(
                "CRITICAL API response time exceeded",
                extra={
                    "module_name": module_name,
                    "path": path,
                    "method": method,
                    "status_code": status_code,
                    "duration": round(duration, 3),
                    "threshold": CRITICAL_API_THRESHOLD,
                    "user_id": (
                        getattr(request.user, "id", None)
                        if hasattr(request, "user")
                        else None
                    ),
                },
                exc_info=False,
            )
        elif duration > SLOW_API_THRESHOLD:
            logger.warning(
                "Slow API response time",
                extra={
                    "module_name": module_name,
                    "path": path,
                    "method": method,
                    "status_code": status_code,
                    "duration": round(duration, 3),
                    "threshold": SLOW_API_THRESHOLD,
                    "user_id": (
                        getattr(request.user, "id", None)
                        if hasattr(request, "user")
                        else None
                    ),
                },
            )
        else:
            # Log all API calls at info level for monitoring
            logger.info(
                "API request processed",
                extra={
                    "module_name": module_name,
                    "path": path,
                    "method": method,
                    "status_code": status_code,
                    "duration": round(duration, 3),
                    "user_id": (
                        getattr(request.user, "id", None)
                        if hasattr(request, "user")
                        else None
                    ),
                },
            )
