# api/urls.py - MODIFICATIONS

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    # Hiérarchie principale
    ArchitectureViewSet, ActifViewSet, AttributSecuriteViewSet,
    AttributMenaceViewSet, MenaceMesureViewSet, TechniqueViewSet,  # MenaceMesureViewSet remplace MenaceControleViewSet
    MesureDeControleViewSet, ImplementationMesureViewSet, CategorieActifViewSet,
    TypeActifViewSet,
    
    # Catalogues globaux
    MenaceViewSet,  # ControleNISTViewSet SUPPRIMÉ
    
    # Système
    UserViewSet, LogActiviteViewSet, DashboardViewSet, OptimizationViewSet
)

# Configuration du router pour les ViewSets
router = DefaultRouter()

# Catégories et types d'actifs
router.register(r'categories-actifs', CategorieActifViewSet, basename='categorie-actif')
router.register(r'types-actifs', TypeActifViewSet, basename='type-actif')

# Hiérarchie principale (dans l'ordre de navigation)
router.register(r'architectures', ArchitectureViewSet, basename='architecture')
router.register(r'actifs', ActifViewSet, basename='actif')
router.register(r'attributs-securite', AttributSecuriteViewSet, basename='attributsecurite')
router.register(r'attribut-menaces', AttributMenaceViewSet, basename='attributmenace')
router.register(r'menace-mesures', MenaceMesureViewSet, basename='menacemesure')  # NOUVEAU
router.register(r'techniques', TechniqueViewSet, basename='technique')
router.register(r'mesures-controle', MesureDeControleViewSet, basename='mesuredecontrole')
router.register(r'implementations', ImplementationMesureViewSet, basename='implementation')

# Catalogues globaux
router.register(r'menaces', MenaceViewSet, basename='menace')
# ControleNIST SUPPRIMÉ

# Système et administration
router.register(r'utilisateurs', UserViewSet, basename='user')
router.register(r'logs', LogActiviteViewSet, basename='logactivite')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'optimization', OptimizationViewSet, basename='optimization')

urlpatterns = [
    # Routes de l'API
    path('', include(router.urls)),
    
    # Authentification par token
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    
    # Routes d'authentification DRF
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
]