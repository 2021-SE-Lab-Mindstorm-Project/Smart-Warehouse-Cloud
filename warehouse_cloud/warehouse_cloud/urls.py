"""warehouse_cloud URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions

import cloud.api
from cloud import views

router = routers.DefaultRouter()
router.register('sensory', cloud.api.SensoryViewSet)
router.register('message', cloud.api.MessageViewSet)
router.register('order', cloud.api.OrderViewSet)

schema_url_patterns = [
    path('api/', include((router.urls, 'cloud'), namespace='api')),
]

schema_view = get_schema_view(
    openapi.Info(
        title="Django API",
        default_version='v1',
        terms_of_service="https://www.google.com/policies/terms/",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=schema_url_patterns,
)

urlpatterns = [
    path('', cloud.views.index, name='index'),
    path('api/', include((router.urls, 'cloud'), namespace='api')),
    path('api/doc/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('data/', cloud.views.data, name='data'),
]
