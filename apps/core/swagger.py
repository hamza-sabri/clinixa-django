"""
Swagger/OpenAPI documentation helpers.

Common parameters and schemas used across API documentation.
"""

from drf_yasg import openapi


# Common pagination parameters for list endpoints
PAGINATION_PARAMETERS = [
    openapi.Parameter(
        'page',
        openapi.IN_QUERY,
        description='Page number for pagination (default: 1)',
        type=openapi.TYPE_INTEGER,
        default=1
    ),
    openapi.Parameter(
        'page_size',
        openapi.IN_QUERY,
        description='Number of items per page (default: 20, max: 100)',
        type=openapi.TYPE_INTEGER,
        default=20
    ),
]


def get_paginated_response_schema(item_schema_ref: str) -> openapi.Schema:
    """
    Returns a schema for paginated response.
    
    Args:
        item_schema_ref: Reference to the item schema (e.g., '#/definitions/ClinicList')
    
    Returns:
        openapi.Schema for paginated response
    """
    return openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'count': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Total number of items'
            ),
            'next': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_URI,
                description='URL for next page',
                x_nullable=True
            ),
            'previous': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_URI,
                description='URL for previous page',
                x_nullable=True
            ),
            'page': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Current page number'
            ),
            'page_size': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Number of items per page'
            ),
            'total_pages': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Total number of pages'
            ),
            'results': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(ref=item_schema_ref)
            ),
        }
    )


# Commonly used pagination description text
PAGINATION_DESCRIPTION = '''

**Pagination:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

Response includes: `count`, `next`, `previous`, `page`, `page_size`, `total_pages`, and `results`.
'''


