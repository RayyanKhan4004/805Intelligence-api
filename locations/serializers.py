from rest_framework import serializers
from .models import County, City, Farm


class CountySerializer(serializers.ModelSerializer):
    class Meta:
        model = County
        fields = ['id', 'name', 'code']


class CitySerializer(serializers.ModelSerializer):
    county = CountySerializer(read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name', 'city_code', 'county']


class FarmSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = Farm
        fields = ['id', 'name', 'city']