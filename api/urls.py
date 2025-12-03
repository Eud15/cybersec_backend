# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    # Hiérarchie principale
    ArchitectureViewSet, ActifViewSet, AttributSecuriteViewSet,
    AttributMenaceViewSet, MenaceControleViewSet, TechniqueViewSet,
    MesureDeControleViewSet, ImplementationMesureViewSet,  CategorieActifViewSet,
    TypeActifViewSet,
    
    
    # Catalogues globaux
    TypeActifViewSet, MenaceViewSet, ControleNISTViewSet,
    
    # Système
    UserViewSet, LogActiviteViewSet, DashboardViewSet
)

# Configuration du router pour les ViewSets
router = DefaultRouter()

router.register(r'categories-actifs', CategorieActifViewSet, basename='categorie-actif')
router.register(r'types-actifs', TypeActifViewSet, basename='type-actif')

# Hiérarchie principale (dans l'ordre de navigation)
router.register(r'architectures', ArchitectureViewSet, basename='architecture')
router.register(r'actifs', ActifViewSet, basename='actif')
router.register(r'attributs-securite', AttributSecuriteViewSet, basename='attributsecurite')
router.register(r'attribut-menaces', AttributMenaceViewSet, basename='attributmenace')
router.register(r'menace-controles', MenaceControleViewSet, basename='menacecontrole')
router.register(r'techniques', TechniqueViewSet, basename='technique')
router.register(r'mesures-controle', MesureDeControleViewSet, basename='mesuredecontrole')
router.register(r'implementations', ImplementationMesureViewSet, basename='implementation')

# Catalogues globaux
router.register(r'types-actifs', TypeActifViewSet, basename='typeactif')
router.register(r'menaces', MenaceViewSet, basename='menace')
router.register(r'controles-nist', ControleNISTViewSet, basename='controlenist')

# Système et administration
router.register(r'utilisateurs', UserViewSet, basename='user')
router.register(r'logs', LogActiviteViewSet, basename='logactivite')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')


urlpatterns = [
    # Routes de l'API
    path('', include(router.urls)),
    
    # Authentification par token
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    
    # Routes d'authentification DRF
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    path('', include('api.urls_optimization')),
]

