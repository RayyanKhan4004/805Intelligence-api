from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Report, ReportResult, ReportFarm
from .serializers import CreateReportSerializer, ReportListSerializer, ReportDetailSerializer
from .calculator import calculate_metrics
from locations.models import County, City, Farm
from locations.serializers import CitySerializer, FarmSerializer


# -------------------------
# Cascading Dropdowns
# -------------------------

class CitiesByCountyAPI(APIView):
    """GET /api/counties/<county_id>/cities/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, county_id):
        county = get_object_or_404(County, id=county_id)
        cities = City.objects.filter(county=county).order_by('name')
        serializer = CitySerializer(cities, many=True)
        return Response({"county": county.name, "cities": serializer.data})


class FarmsByCityAPI(APIView):
    """GET /api/cities/<city_id>/farms/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, city_id):
        city = get_object_or_404(City, id=city_id)
        farms = Farm.objects.filter(city=city).order_by('name')
        serializer = FarmSerializer(farms, many=True)
        return Response({"city": city.name, "farms": serializer.data})


# -------------------------
# Helper: run calculation and save results
# -------------------------
def _calculate_and_save(report, selected_metrics):
    from properties.models import Property
    props = Property.objects.all()
    if report.county_id:
        props = props.filter(county_id=report.county_id)
    if report.city_id:
        props = props.filter(city_id=report.city_id)
    farm_ids = list(ReportFarm.objects.filter(report=report).values_list('farm_id', flat=True))
    if farm_ids:
        props = props.filter(farm_id__in=farm_ids)

    metric_data = calculate_metrics(props, selected_metrics)

    ReportResult.objects.update_or_create(
        report=report,
        defaults={
            'median_list_price':    metric_data.get('median_list_price'),
            'median_sale_price':    metric_data.get('median_sale_price'),
            'price_per_sqft':       metric_data.get('price_per_sqft'),
            'days_on_market':       metric_data.get('days_on_market'),
            'inventory':            metric_data.get('inventory'),
            'list_to_sale_ratio':   metric_data.get('list_to_sale_ratio'),
            'price_reductions_pct': metric_data.get('price_reductions_pct'),
            'new_listings':         metric_data.get('new_listings'),
            'closed_sales':         metric_data.get('closed_sales'),
        }
    )


# -------------------------
# Reports CRUD
# -------------------------

class ReportListCreateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = Report.objects.filter(user=request.user).order_by('-created_at')
        serializer = ReportListSerializer(reports, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CreateReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        farm_ids = data.pop('farm_ids', [])

        report = Report.objects.create(user=request.user, status='draft', **data)
        report.set_farms(farm_ids)

        _calculate_and_save(report, report.metrics)

        report.status = 'generated'
        report.save()

        return Response(
            {"message": "Report generated successfully", "report": ReportDetailSerializer(report).data},
            status=status.HTTP_201_CREATED
        )


class ReportDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, report_id):
        return get_object_or_404(Report, id=report_id, user=request.user)

    def get(self, request, report_id):
        report = self.get_object(request, report_id)
        return Response(ReportDetailSerializer(report).data)

    def patch(self, request, report_id):
        report = self.get_object(request, report_id)
        serializer = CreateReportSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        farm_ids = data.pop('farm_ids', None)

        for attr, value in data.items():
            setattr(report, attr, value)
        report.save()

        if farm_ids is not None:
            report.set_farms(farm_ids)

        _calculate_and_save(report, report.metrics)
        report.status = 'generated'
        report.save()

        return Response(
            {"message": "Report updated successfully", "report": ReportDetailSerializer(report).data}
        )

    def delete(self, request, report_id):
        report = self.get_object(request, report_id)
        report.delete()
        return Response({"message": "Report deleted successfully"}, status=status.HTTP_200_OK)