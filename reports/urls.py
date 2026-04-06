from django.urls import path
from .views import ReportListCreateAPI, ReportDetailAPI, CitiesByCountyAPI, FarmsByCityAPI

urlpatterns = [
    # Cascading dropdowns
    path('counties/<int:county_id>/cities/', CitiesByCountyAPI.as_view(), name='cities-by-county'),
    path('cities/<int:city_id>/farms/', FarmsByCityAPI.as_view(), name='farms-by-city'),

    # Reports CRUD
    path('reports/', ReportListCreateAPI.as_view(), name='reports'),
    path('reports/<int:report_id>/', ReportDetailAPI.as_view(), name='report-detail'),
]