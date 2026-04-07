from rest_framework import serializers
from .models import Report, ReportResult, ReportFarm
from locations.models import County, City, Farm


class ReportResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportResult
        fields = [
            'calculated_at',
            'median_list_price',
            'median_sale_price',
            'price_per_sqft',
            'days_on_market',
            'inventory',
            'list_to_sale_ratio',
            'price_reductions_pct',
            'new_listings',
            'closed_sales',
        ]


class ReportListSerializer(serializers.ModelSerializer):
    county_name = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ['id', 'name', 'status', 'format', 'visibility', 'county_name', 'city_name', 'created_at']

    def get_county_name(self, obj):
        county = obj.county
        return county.name if county else None

    def get_city_name(self, obj):
        city = obj.city
        return city.name if city else None


class ReportDetailSerializer(serializers.ModelSerializer):
    county_name = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()
    farm_names = serializers.SerializerMethodField()
    result = ReportResultSerializer(read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'status',
            'county_id', 'county_name',
            'city_id', 'city_name',
            'farm_names', 'metrics',
            'format', 'visibility', 'schedule',
            'agent_name', 'agent_logo_url',
            'created_at', 'updated_at',
            'result',
        ]

    def get_county_name(self, obj):
        county = obj.county
        return county.name if county else None

    def get_city_name(self, obj):
        city = obj.city
        return city.name if city else None

    def get_farm_names(self, obj):
        return list(obj.farms.values_list('name', flat=True))


class CreateReportSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    county_id = serializers.IntegerField()
    city_id = serializers.IntegerField(required=False, allow_null=True)
    farm_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    metrics = serializers.ListField(child=serializers.CharField())
    format = serializers.ChoiceField(choices=[c[0] for c in Report.FORMAT_CHOICES], default='pdf')
    visibility = serializers.ChoiceField(choices=[c[0] for c in Report.VISIBILITY_CHOICES], default='private')
    schedule = serializers.ChoiceField(choices=[c[0] for c in Report.SCHEDULE_CHOICES], default='one_time')
    agent_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    agent_logo_url = serializers.URLField(required=False, allow_blank=True, default='')

    def validate_county_id(self, value):
        if not County.objects.filter(id=value).exists():
            raise serializers.ValidationError("County not found.")
        return value

    def validate_city_id(self, value):
        if value and not City.objects.filter(id=value).exists():
            raise serializers.ValidationError("City not found.")
        return value

    def validate_metrics(self, value):
        valid_keys = {m[0] for m in Report.METRIC_CHOICES}
        invalid = [m for m in value if m not in valid_keys]
        if invalid:
            raise serializers.ValidationError(f"Invalid metrics: {invalid}. Valid: {sorted(valid_keys)}")
        if not value:
            raise serializers.ValidationError("Select at least one metric.")
        return value

    def validate(self, data):
        city_id = data.get('city_id')
        county_id = data.get('county_id')
        if city_id:
            city = City.objects.filter(id=city_id).first()
            if city and city.county_id != county_id:
                raise serializers.ValidationError("Selected city does not belong to the selected county.")
        return data


# -------------------------
# Grid View Serializer — compact card view
# -------------------------
class ReportGridSerializer(serializers.ModelSerializer):
    county_name = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()
    farm_names = serializers.SerializerMethodField()
    result = ReportResultSerializer(read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'status', 'format', 'visibility', 'schedule',
            'county_name', 'city_name', 'farm_names',
            'metrics', 'agent_name',
            'created_at', 'updated_at',
            'result',
        ]

    def get_county_name(self, obj):
        county = obj.county
        return county.name if county else None

    def get_city_name(self, obj):
        city = obj.city
        return city.name if city else None

    def get_farm_names(self, obj):
        return list(obj.farms.values_list('name', flat=True))


# -------------------------
# List View Serializer — detailed with metrics
# -------------------------
class ReportListViewSerializer(serializers.ModelSerializer):
    county_name = serializers.SerializerMethodField()
    city_name = serializers.SerializerMethodField()
    farm_names = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'status', 'format',
            'visibility', 'county_name', 'city_name',
            'farm_names', 'created_at',
        ]

    def get_county_name(self, obj):
        county = obj.county
        return county.name if county else None

    def get_city_name(self, obj):
        city = obj.city
        return city.name if city else None

    def get_farm_names(self, obj):
        return list(obj.farms.values_list('name', flat=True))