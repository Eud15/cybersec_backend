# api/urls_optimization.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OptimizationViewSet

# Router pour l'optimisation
optimization_router = DefaultRouter()
optimization_router.register(r'optimization', OptimizationViewSet, basename='optimization')

urlpatterns = [
    path('', include(optimization_router.urls)),
]

# Puis dans votre api/urls.py principal, ajoutez :
# path('', include('api.urls_optimization')),