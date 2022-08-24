from ast import Store
from django.contrib import admin
from .models import Stream, StoreFile

admin.site.register(Stream)
admin.site.register(StoreFile)