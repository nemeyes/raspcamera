"""raspi_stream_restful URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from streams.views import StreamViewSet, StreamStartAPIView, StreamStopAPIView
from streams.views import StoreFileViewSet, StoreFileStartAPIView, StoreFileStopAPIView
from streams.views import StatusAPIView, LastImageView

router = routers.DefaultRouter()
# router.register(r'api/stream/start', StreamStartAPIView.as_view())
router.register(r"streams", StreamViewSet)
router.register(r"storefiles", StoreFileViewSet)

urlpatterns = [
    path("api/stream/start", StreamStartAPIView.as_view()),
    path("api/stream/stop", StreamStopAPIView.as_view()),
    path("api/stream/storestart", StoreFileStartAPIView.as_view()),
    path("api/stream/storestop", StoreFileStopAPIView.as_view()),
    path("api/stream/info", StatusAPIView.as_view()),
    path("api/stream/lastimage", LastImageView.as_view()),
    path("", include(router.urls)),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path("admin/", admin.site.urls),
]
