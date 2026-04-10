from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Report, ReportResult, ReportFarm
from .serializers import (
    CreateReportSerializer,
    ReportDetailSerializer,
    ReportGridSerializer,
    ReportListViewSerializer,
)
from .calculator import calculate_metrics
from locations.models import County, City, Farm
from locations.serializers import CitySerializer, FarmSerializer


# -------------------------
# Cascading Dropdowns
# -------------------------

class CitiesByCountyAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, county_id):
        county = get_object_or_404(County, id=county_id)
        cities = City.objects.filter(county=county).order_by('name')
        return Response({"county": county.name, "cities": CitySerializer(cities, many=True).data})


class FarmsByCityAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, city_id):
        city = get_object_or_404(City, id=city_id)
        farms = Farm.objects.filter(city=city).order_by('name')
        return Response({"city": city.name, "farms": FarmSerializer(farms, many=True).data})


# -------------------------
# Helper: run calculation and save results
# -------------------------
# Old key → New key mapping (backward compatibility)
# -------------------------
METRIC_ALIAS_MAP = {
    'median_sale_price':  None,           # removed, no equivalent
    'days_on_market':     'avg_dom',
    'list_to_sale_ratio': None,           # removed, no equivalent
    'price_reductions':   'price_decreased_pct',
    'new_vs_closed':      None,           # removed, no equivalent
    'price_decreased':    'price_decreased_pct',
    'price_increased':    'price_increased_pct',
    'median_new_listing_price': 'median_price_new_listings',
}

VALID_METRICS = {m[0] for m in Report.METRIC_CHOICES}


def _normalize_metrics(metrics):
    """Remap old metric keys to new ones, drop invalid/removed ones."""
    normalized = []
    for key in metrics:
        if key in VALID_METRICS:
            normalized.append(key)
        elif key in METRIC_ALIAS_MAP:
            new_key = METRIC_ALIAS_MAP[key]
            if new_key and new_key not in normalized:
                normalized.append(new_key)
        # else: silently drop unknown/removed keys
    return normalized


# -------------------------
def _calculate_and_save(report, selected_metrics):
    # Auto-remap any old keys before calculating
    selected_metrics = _normalize_metrics(selected_metrics)

    # Persist normalized keys back to report if they changed
    if selected_metrics != report.metrics:
        report.metrics = selected_metrics
        report.save(update_fields=['metrics'])

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
            'inventory':                  metric_data.get('inventory'),
            'avg_dom':                    metric_data.get('avg_dom'),
            'median_dom':                 metric_data.get('median_dom'),
            'price_per_sqft':             metric_data.get('price_per_sqft'),
            'price_decreased_pct':        metric_data.get('price_decreased_pct'),
            'price_increased_pct':        metric_data.get('price_increased_pct'),
            'median_list_price':          metric_data.get('median_list_price'),
            'median_price_new_listings':  metric_data.get('median_price_new_listings'),
        }
    )


# -------------------------
# Reports List + Create
# GET  /api/reports/?view=grid&sort=az
# GET  /api/reports/?view=list&sort=za
# GET  /api/reports/?view=grid&sort=views
# POST /api/reports/
# -------------------------

class ReportListCreateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = Report.objects.filter(user=request.user)

        # ---- Recalculate all reports with latest data ----
        for report in reports.filter(status='generated'):
            _calculate_and_save(report, report.metrics)

        # ---- Sorting ----
        sort = request.query_params.get('sort', 'latest').lower()

        if sort == 'az':
            # A to Z by report name
            reports = reports.order_by('name')
        elif sort == 'za':
            # Z to A by report name
            reports = reports.order_by('-name')
        elif sort == 'views':
            # Most recently viewed first, unviewed reports go to bottom
            reports = reports.order_by('-last_viewed_at', '-created_at')
        else:
            # Default: latest created first
            reports = reports.order_by('-created_at')

        # ---- View type ----
        view_type = request.query_params.get('view', 'grid').lower()

        if view_type == 'list':
            serializer = ReportGridSerializer(reports, many=True)
        else:
            serializer = ReportListViewSerializer(reports, many=True)

        return Response({
            "view": view_type,
            "sort": sort,
            "count": reports.count(),
            "reports": serializer.data,
        })

        # ---- Filtering ----
        county_id = request.query_params.get('county_id')
        city_id   = request.query_params.get('city_id')
        farm_id   = request.query_params.get('farm_id')

        if county_id:
            reports = reports.filter(county_id=county_id)
        if city_id:
            reports = reports.filter(city_id=city_id)
        if farm_id:
            farm_report_ids = ReportFarm.objects.filter(
                farm_id=farm_id
            ).values_list('report_id', flat=True)
            reports = reports.filter(id__in=farm_report_ids)

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


# -------------------------
# Report Detail, Edit, Delete
# GET    /api/reports/<id>/  → also tracks view
# PATCH  /api/reports/<id>/
# DELETE /api/reports/<id>/
# -------------------------

class ReportDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, report_id):
        return get_object_or_404(Report, id=report_id, user=request.user)

    def get(self, request, report_id):
        report = self.get_object(request, report_id)

        # Recalculate metrics with latest data every time report is viewed
        _calculate_and_save(report, report.metrics)

        # Track the view
        report.views_count += 1
        report.last_viewed_at = timezone.now()
        report.save(update_fields=['views_count', 'last_viewed_at'])

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


# -------------------------
# Report Form Options
# -------------------------
class ReportOptionsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from locations.serializers import CountySerializer
        counties = County.objects.all().order_by('name')

        return Response({
            "counties": CountySerializer(counties, many=True).data,
            "metrics": [
                {"key": "inventory",                 "label": "Inventory"},
                {"key": "avg_dom",                   "label": "Avg DOM"},
                {"key": "median_dom",                "label": "Median DOM"},
                {"key": "price_per_sqft",            "label": "Price Per Sq. Ft."},
                {"key": "price_decreased_pct",       "label": "Price Decreased %"},
                {"key": "price_increased_pct",       "label": "Price Increased %"},
                {"key": "median_list_price",         "label": "Median List Price"},
                {"key": "median_price_new_listings", "label": "Median Price of New Listings"},
            ],
            "formats": [
                {"key": "pdf",   "label": "PDF"},
                {"key": "web",   "label": "Web"},
                {"key": "email", "label": "Email"},
            ],
            "visibility_options": [
                {"key": "private", "label": "Private"},
                {"key": "shared",  "label": "Shared"},
                {"key": "public",  "label": "Public"},
            ],
            "schedule_options": [
                {"key": "one_time", "label": "One Time"},
                {"key": "weekly",   "label": "Weekly"},
                {"key": "monthly",  "label": "Monthly"},
            ],
        })

class ReportFilterOptionsAPI(APIView):
    """
    GET /api/reports/filter-options/
    Returns only counties, cities and farms that exist
    in the logged-in user's reports.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from locations.models import County, City, Farm

        user_reports = Report.objects.filter(user=request.user)

        # Collect unique IDs from user's reports
        county_ids = user_reports.exclude(
            county_id__isnull=True
        ).values_list('county_id', flat=True).distinct()

        city_ids = user_reports.exclude(
            city_id__isnull=True
        ).values_list('city_id', flat=True).distinct()

        farm_ids = ReportFarm.objects.filter(
            report__in=user_reports
        ).values_list('farm_id', flat=True).distinct()

        # Fetch actual objects
        counties = County.objects.filter(id__in=county_ids).order_by('name')
        cities   = City.objects.filter(id__in=city_ids).order_by('name')
        farms    = Farm.objects.filter(id__in=farm_ids).order_by('name')

        return Response({
            "counties": [{"id": c.id, "name": c.name} for c in counties],
            "cities":   [{"id": c.id, "name": c.name, "county_id": c.county_id} for c in cities],
            "farms":    [{"id": f.id, "name": f.name, "city_id": f.city_id} for f in farms],
        })