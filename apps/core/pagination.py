"""
Custom pagination classes for the API.

Provides a standardized pagination format with configurable page size
and proper OpenAPI/Swagger documentation support.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination class with configurable page size.
    
    Query Parameters:
        - page: Page number (default: 1)
        - page_size: Number of items per page (default: 20, max: 100)
    
    Response Format:
        {
            "count": 100,           # Total number of items
            "next": "http://...",   # URL for next page (null if none)
            "previous": "http://...",  # URL for previous page (null if none)
            "page": 1,              # Current page number
            "page_size": 20,        # Items per page
            "total_pages": 5,       # Total number of pages
            "results": [...]        # List of items
        }
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'total_pages': self.page.paginator.num_pages,
            'results': data
        })
    
    def get_paginated_response_schema(self, schema):
        """
        Return the schema for the paginated response.
        This is used by drf_yasg to generate proper documentation.
        """
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'description': 'Total number of items',
                    'example': 100
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'description': 'URL for next page',
                    'example': 'http://api.example.org/resource/?page=2'
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'description': 'URL for previous page',
                    'example': 'http://api.example.org/resource/?page=1'
                },
                'page': {
                    'type': 'integer',
                    'description': 'Current page number',
                    'example': 1
                },
                'page_size': {
                    'type': 'integer',
                    'description': 'Number of items per page',
                    'example': 20
                },
                'total_pages': {
                    'type': 'integer',
                    'description': 'Total number of pages',
                    'example': 5
                },
                'results': schema
            },
            'required': ['count', 'next', 'previous', 'page', 'page_size', 'total_pages', 'results']
        }


class LargeResultsPagination(StandardResultsPagination):
    """
    Pagination class for endpoints that typically return large datasets.
    Allows up to 500 items per page.
    """
    page_size = 50
    max_page_size = 500


class SmallResultsPagination(StandardResultsPagination):
    """
    Pagination class for endpoints where smaller page sizes are preferred.
    Allows up to 50 items per page.
    """
    page_size = 10
    max_page_size = 50


