import logging

request_logger = logging.getLogger('debug.request')

class DebugRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_logger.debug("IN %s %s user=%s",
                             request.method,
                             request.get_full_path(),
                             getattr(request.user, 'id', None)
                             )
        return self.get_response(request)