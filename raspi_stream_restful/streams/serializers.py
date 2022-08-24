from dataclasses import fields
from .models import Stream, StoreFile
from rest_framework import serializers

class StreamSerializer(serializers.HyperlinkedModelSerializer) :
    class Meta :
        model = Stream
        fields = '__all__'
        # fields = [ 'name', 'requestFrom', 'startdate', 'enddate' ]

class StreamResponseSerializer(serializers.Serializer) :
    name = serializers.CharField(max_length=200)
    requestFrom = serializers.CharField(max_length=200)
    start_date = serializers.DateTimeField()


class StoreFileSerializer(serializers.HyperlinkedModelSerializer) :
    class Meta : 
        model = StoreFile
        fields = '__all__'

class StoreFileResponseSerializer(serializers.Serializer) :
    name = serializers.CharField(max_length=256)
    filepath = serializers.CharField(max_length=4096)
    start_date = serializers.DateTimeField()
