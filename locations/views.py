from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .models import County, City, Farm
from .serializers import CountySerializer, CitySerializer, FarmSerializer


class SearchAPI(APIView):
    """
    Unified search endpoint across County, City, and Farm.

    Usage:
        GET /api/search/?type=county&q=ventura
        GET /api/search/?type=city&q=westlake
        GET /api/search/?type=farm&q=oxnard
    """

    def get(self, request):
        search_type = request.query_params.get('type', '').lower().strip()
        query = request.query_params.get('q', '').strip()

        if not search_type:
            return Response(
                {"error": "Please provide a 'type' parameter: county, city, or farm"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not query:
            return Response(
                {"error": "Please provide a search query using the 'q' parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if search_type == 'county':
            results = County.objects.prefetch_related('cities', 'cities__farms').filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            )
            serializer = CountySerializer(results, many=True)

        elif search_type == 'city':
            results = City.objects.select_related('county').filter(
                Q(name__icontains=query) | Q(city_code__icontains=query)
            )
            serializer = CitySerializer(results, many=True)

        elif search_type == 'farm':
            results = Farm.objects.select_related('city__county').filter(
                Q(name__icontains=query)
            )
            serializer = FarmSerializer(results, many=True)

        else:
            return Response(
                {"error": "Invalid type. Must be one of: county, city, farm"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "type": search_type,
                "query": query,
                "count": len(serializer.data),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK
        )