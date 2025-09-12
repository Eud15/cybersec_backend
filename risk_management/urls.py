# ================================================================
# risk_management/urls.py - URLs principales avec Swagger
# ================================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Configuration Swagger/OpenAPI
schema_view = get_schema_view(
    openapi.Info(
        title="API Gestion des Risques NIST - Hiérarchique",
        default_version='v1',
        description="""
        API pour la gestion hiérarchique des risques selon le framework NIST.
        
        ## Navigation Hiérarchique
        
        L'API suit une logique de navigation hiérarchique stricte :
        
        **1. Architecture** → Point d'entrée du système
        - `/architectures/` : Liste des architectures
        - `/architectures/{id}/actifs/` : Actifs d'une architecture
        
        **2. Actifs** → Composants de l'architecture
        - `/actifs/{id}/attributs_securite/` : Attributs de sécurité d'un actif
        - `/actifs/{id}/rapport_complet/` : Rapport hiérarchique complet
        
        **3. Attributs de Sécurité** → CIA Triad pour chaque actif
        - `/attributs-securite/{id}/menaces/` : Menaces liées à un attribut
        
        **4. Menaces** → Risques identifiés pour les attributs
        - `/attribut-menaces/{id}/controles_nist/` : Contrôles NIST pour traiter une menace
        
        **5. Contrôles NIST** → Standards de sécurité
        - `/menace-controles/{id}/techniques/` : Techniques d'implémentation
        
        **6. Techniques** → Méthodes d'implémentation des contrôles
        - `/techniques/{id}/mesures_controle/` : Mesures concrètes pour une technique
        
        **7. Mesures de Contrôle** → Actions concrètes avec coûts et efficacité
        - `/mesures-controle/{id}/implementations/` : Suivi des implémentations
        
        ## Workflow Typique
        
        1. Créer une **Architecture**
        2. Ajouter des **Actifs** à l'architecture
        3. Définir les **Attributs de sécurité** pour chaque actif
        4. Associer des **Menaces** aux attributs avec probabilités
        5. Lier des **Contrôles NIST** aux menaces
        6. Sélectionner des **Techniques** d'implémentation
        7. Choisir des **Mesures de contrôle** avec coûts/efficacité
        8. Planifier et suivre les **Implémentations**
        
        ## Authentification
        Utilisez l'authentification par token :
        `Authorization: Token your_token_here`
        
        ## Dashboard
        - `/dashboard/statistiques_globales/` : Métriques globales
        - `/dashboard/top_risques_critiques/` : Top 10 des risques
        - `/dashboard/implementations_urgentes/` : Implémentations prioritaires
        """,
        terms_of_service="https://www.exemple.com/policies/terms/",
        contact=openapi.Contact(email="admin@exemple.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=[
        path('api/v1/', include('api.urls')),
    ],
)

urlpatterns = [
    # Administration Django
    path('admin/', admin.site.urls),
    
    # API principale
    path('api/v1/', include('api.urls')),
    
    # Documentation Swagger
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Documentation par défaut
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui-root'),
]

# Ajout des fichiers statiques en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)