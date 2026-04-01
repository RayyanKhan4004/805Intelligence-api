from rest_framework import serializers
from django.db.models import Count
from .models import County, City, Farm


class CountySerializer(serializers.ModelSerializer):
    cities_count = serializers.SerializerMethodField()
    farms_count = serializers.SerializerMethodField()

    class Meta:
        model = County
        fields = ['id', 'name', 'code', 'cities_count', 'farms_count']

    def get_cities_count(self, obj):
        return obj.cities.count()

    def get_farms_count(self, obj):
        return Farm.objects.filter(city__county=obj).count()


class CitySerializer(serializers.ModelSerializer):
    county = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name', 'city_code', 'county']


class FarmSerializer(serializers.ModelSerializer):
    city = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Farm
        fields = ['id', 'name', 'city']