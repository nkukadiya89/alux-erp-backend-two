from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination


class Pagination(PageNumberPagination):
    page_size = 10  # per page record
    page_size_query_param = "pagesize"
    page_query_param = "page"

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view)
        except NotFound:
            # Reset to page 1 if the page is not found
            request.query_params._mutable = True  # Make query_params mutable
            request.query_params[self.page_query_param] = 1
            request.query_params._mutable = False  # Make query_params immutable again
            return super().paginate_queryset(queryset, request, view)
