# api/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg, Q
from django.db import models 
from django.utils import timezone
from decimal import Decimal
from django.db import transaction        
import logging  
import pyomo.environ as pyo

from .services.optimization_service import SecurityOptimizationService
from .serializers import (
    OptimizationRequestSerializer, FullOptimizationResultSerializer,
    ImplementationPlanSerializer, OptimizationStatusSerializer,
    QuickOptimizationSerializer
)

from .models import (
    CategorieActif,
    TypeActif, Architecture, Actif, AttributSecurite, Menace, AttributMenace,
     Technique, MesureDeControle, MenaceMesure,
    ImplementationMesure, LogActivite
)
from .serializers import (
    CategorieActifListSerializer, CategorieActifCreateSerializer,
    TypeActifSerializer, ArchitectureListSerializer, ArchitectureSerializer,
    ArchitectureCreateSerializer, ActifListSerializer, ActifSerializer, ActifCreateSerializer,
    AttributSecuriteListSerializer, AttributSecuriteSerializer, AttributSecuriteCreateSerializer,
    AttributMenaceSerializer, AttributMenaceCreateSerializer,MenaceCreateSerializer, TypeActifListSerializer, TypeActifCreateSerializer,
   
    TechniqueSerializer, TechniqueCreateSerializer,TechniqueListSerializer,
    MesureDeControleSerializer, MesureDeControleCreateSerializer,
    ImplementationMesureSerializer, MenaceListSerializer, MenaceSerializer, 
     CategorieActifSerializer,
    LogActiviteSerializer, UserSerializer, DashboardStatsSerializer, MenaceSimpleCreateSerializer, MenaceMesureSerializer, MenaceMesureCreateSerializer
)
from .utils import log_activity

logger = logging.getLogger(__name__)



# ============================================================================
# NIVEAU 0: GESTION DES CATÉGORIES ET TYPES D'ACTIFS (NOUVEAUX)
# ============================================================================

class CategorieActifViewSet(viewsets.ModelViewSet):
    """Gestion des catégories d'actifs"""
    queryset = CategorieActif.objects.all().order_by('nom')
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'code', 'description']
    ordering_fields = ['nom', 'code', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CategorieActifListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CategorieActifCreateSerializer
        return CategorieActifSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(
            self.request.user, 
            'CREATE', 
            'CategorieActif', 
            str(instance.id), 
            {'nom': instance.nom, 'code': instance.code}
        )
    
    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(
            self.request.user, 
            'UPDATE', 
            'CategorieActif', 
            str(instance.id), 
            {'nom': instance.nom, 'code': instance.code}
        )
    
    def perform_destroy(self, instance):
        if instance.types_actifs.exists():
            raise serializers.ValidationError(
                f"Impossible de supprimer cette catégorie car elle contient {instance.types_actifs.count()} type(s) d'actif"
            )
        
        log_activity(
            self.request.user, 
            'DELETE', 
            'CategorieActif', 
            str(instance.id), 
            {'nom': instance.nom}
        )
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def types_actifs(self, request, pk=None):
        """Récupère tous les types d'actifs d'une catégorie"""
        categorie = self.get_object()
        types = categorie.types_actifs.all().order_by('nom')
        
        search = request.query_params.get('search')
        if search:
            types = types.filter(nom__icontains=search)
        
        serializer = TypeActifListSerializer(types, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ajouter_type(self, request, pk=None):
        """Ajoute un nouveau type d'actif à cette catégorie"""
        categorie = self.get_object()
        data = request.data.copy()
        data['categorie'] = str(categorie.id)
        
        serializer = TypeActifCreateSerializer(data=data)
        if serializer.is_valid():
            type_actif = serializer.save()
            log_activity(
                request.user, 
                'ADD_TYPE', 
                'CategorieActif', 
                str(categorie.id),
                {'type_nom': type_actif.nom, 'type_code': type_actif.code}
            )
            return Response(
                TypeActifSerializer(type_actif).data, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def statistiques(self, request, pk=None):
        """Statistiques détaillées pour une catégorie"""
        categorie = self.get_object()
        
        stats = {
            'categorie': CategorieActifListSerializer(categorie).data,
            'total_types': categorie.types_actifs.count(),
            'total_actifs': sum(
                type_actif.actifs.count() 
                for type_actif in categorie.types_actifs.all()
            ),
            'types_detail': []
        }
        
        for type_actif in categorie.types_actifs.all():
            actifs = type_actif.actifs.all()
            stats['types_detail'].append({
                'type': TypeActifListSerializer(type_actif).data,
                'actifs_count': actifs.count(),
                'actifs_par_criticite': dict(
                    actifs.values('criticite')
                    .annotate(count=Count('id'))
                    .values_list('criticite', 'count')
                ),
                'cout_total': sum(float(actif.cout) for actif in actifs)
            })
        
        return Response(stats)

class TypeActifViewSet(viewsets.ModelViewSet):
    """Gestion des types d'actifs"""
    queryset = TypeActif.objects.select_related('categorie').all().order_by('categorie', 'nom')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categorie']
    search_fields = ['nom', 'code', 'description', 'categorie__nom']
    ordering_fields = ['nom', 'code', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TypeActifListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TypeActifCreateSerializer
        return TypeActifSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(
            self.request.user, 
            'CREATE', 
            'TypeActif', 
            str(instance.id), 
            {
                'nom': instance.nom, 
                'code': instance.code,
                'categorie': instance.categorie.nom
            }
        )
    
    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(
            self.request.user, 
            'UPDATE', 
            'TypeActif', 
            str(instance.id), 
            {
                'nom': instance.nom, 
                'code': instance.code,
                'categorie': instance.categorie.nom
            }
        )
    
    def perform_destroy(self, instance):
        if instance.actifs.exists():
            raise serializers.ValidationError(
                f"Impossible de supprimer ce type car il est utilisé par {instance.actifs.count()} actif(s)"
            )
        
        log_activity(
            self.request.user, 
            'DELETE', 
            'TypeActif', 
            str(instance.id), 
            {'nom': instance.nom}
        )
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def actifs(self, request, pk=None):
        """Récupère tous les actifs de ce type"""
        type_actif = self.get_object()
        actifs = type_actif.actifs.select_related('architecture', 'proprietaire').all()
        
        architecture = request.query_params.get('architecture')
        criticite = request.query_params.get('criticite')
        
        if architecture:
            actifs = actifs.filter(architecture_id=architecture)
        if criticite:
            actifs = actifs.filter(criticite=criticite)
        
        from .serializers import ActifListSerializer
        serializer = ActifListSerializer(actifs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistiques(self, request, pk=None):
        """Statistiques pour un type d'actif"""
        type_actif = self.get_object()
        actifs = type_actif.actifs.all()
        
        stats = {
            'type_actif': TypeActifSerializer(type_actif).data,
            'total_actifs': actifs.count(),
            'actifs_par_criticite': dict(
                actifs.values('criticite')
                .annotate(count=Count('id'))
                .values_list('criticite', 'count')
            ),
            'actifs_par_architecture': dict(
                actifs.values('architecture__nom')
                .annotate(count=Count('id'))
                .values_list('architecture__nom', 'count')
            ),
            'cout_total': sum(float(actif.cout) for actif in actifs),
            'cout_moyen': (
                sum(float(actif.cout) for actif in actifs) / actifs.count()
                if actifs.count() > 0 else 0
            )
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def par_categorie(self, request):
        """Types d'actifs groupés par catégorie"""
        categories = CategorieActif.objects.prefetch_related('types_actifs').all()
        
        result = []
        for categorie in categories:
            result.append({
                'categorie': CategorieActifListSerializer(categorie).data,
                'types': TypeActifListSerializer(
                    categorie.types_actifs.all(), 
                    many=True
                ).data
            })
        
        return Response(result)

# ============================================================================
# NIVEAU 1: GESTION DES ARCHITECTURES
# ============================================================================

class ArchitectureViewSet(viewsets.ModelViewSet):
    """Gestion des architectures - Point d'entrée du système"""
    queryset = Architecture.objects.all().order_by('nom')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'risque_tolere', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArchitectureListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ArchitectureCreateSerializer
        return ArchitectureSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'Architecture', str(instance.id), 
                    {'nom': instance.nom})
    
    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'UPDATE', 'Architecture', str(instance.id), 
                    {'nom': instance.nom})
    
    @action(detail=True, methods=['get'])
    def actifs(self, request, pk=None):
        """Récupère tous les actifs d'une architecture avec leurs risques"""
        architecture = self.get_object()
        actifs = architecture.actifs.select_related('type_actif', 'proprietaire').all()
        
        # Filtres optionnels
        type_actif = request.query_params.get('type_actif')
        criticite = request.query_params.get('criticite')
        risque_min = request.query_params.get('risque_min')
        
        if type_actif:
            actifs = actifs.filter(type_actif__id=type_actif)
        if criticite:
            actifs = actifs.filter(criticite=criticite)
        
        # Filtrer par risque financier minimum
        if risque_min:
            actifs_filtres = []
            for actif in actifs:
                risque_total = sum(attr.risque_financier_attribut for attr in actif.attributs_securite.all())
                if risque_total >= float(risque_min):
                    actifs_filtres.append(actif)
            actifs = actifs_filtres
        
        serializer = ActifListSerializer(actifs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ajouter_actif(self, request, pk=None):
        """Ajoute un nouvel actif à l'architecture"""
        architecture = self.get_object()
        data = request.data.copy()
        data['architecture'] = str(architecture.id)
        
        serializer = ActifCreateSerializer(data=data)
        if serializer.is_valid():
            actif = serializer.save()
            log_activity(request.user, 'ADD_ACTIF', 'Architecture', str(architecture.id),
                        {'actif_nom': actif.nom})
            return Response(ActifListSerializer(actif).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def analyse_risques_financiers(self, request, pk=None):
        """Analyse détaillée des risques financiers pour cette architecture"""
        architecture = self.get_object()
        
        analyse = {
            'architecture': ArchitectureSerializer(architecture).data,
            'risque_financier_total': architecture.risque_financier_total,
            'risque_tolere': float(architecture.risque_tolere),
            'depasse_tolerance': architecture.risque_depasse_tolerance,
            'pourcentage_tolerance_utilise': architecture.pourcentage_tolerance_utilise
        }
        
        # Détail par actif avec top menaces
        actifs_detail = []
        for actif in architecture.actifs.all():
            risque_actif = 0
            top_menaces = []
            
            for attr_secu in actif.attributs_securite.all():
                for menace_link in attr_secu.menaces.all():
                    risque_actif += menace_link.risque_financier
                    top_menaces.append({
                        'menace': menace_link.menace.nom,
                        'risque_financier': menace_link.risque_financier,
                        'attribut': attr_secu.type_attribut
                    })
            
            # Trier les menaces par risque décroissant
            top_menaces.sort(key=lambda x: x['risque_financier'], reverse=True)
            
            actifs_detail.append({
                'actif': ActifListSerializer(actif).data,
                'risque_financier': round(risque_actif, 2),
                'pourcentage_du_total': round(
                    (risque_actif / architecture.risque_financier_total) * 100, 2
                ) if architecture.risque_financier_total > 0 else 0,
                'top_menaces': top_menaces[:5]  # Top 5 menaces
            })
        
        # Trier par risque décroissant
        actifs_detail.sort(key=lambda x: x['risque_financier'], reverse=True)
        analyse['actifs_detail'] = actifs_detail
        
        # Recommandations
        if architecture.risque_depasse_tolerance:
            analyse['recommandations'] = [
                'AUGMENTER_BUDGET_RISQUE',
                'IMPLEMENTER_MESURES_PROTECTION',
                'AUDIT_COMPLET_NECESSAIRE'
            ]
        elif architecture.pourcentage_tolerance_utilise > 80:
            analyse['recommandations'] = [
                'SURVEILLANCE_RENFORCEE',
                'EVALUATION_MESURES_PREVENTIVES'
            ]
        else:
            analyse['recommandations'] = [
                'SITUATION_ACCEPTABLE',
                'MAINTENIR_SURVEILLANCE'
            ]
        
        return Response(analyse)
    
    @action(detail=True, methods=['post'])
    def ajuster_tolerance_risque(self, request, pk=None):
        """Ajuste le seuil de tolérance au risque"""
        architecture = self.get_object()
        
        nouveau_seuil = request.data.get('nouveau_seuil')
        justification = request.data.get('justification', '')
        
        if not nouveau_seuil:
            return Response({'error': 'nouveau_seuil requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            nouveau_seuil = Decimal(str(nouveau_seuil))
            if nouveau_seuil < 0:
                return Response({'error': 'Le seuil doit être positif'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Format de seuil invalide'}, status=status.HTTP_400_BAD_REQUEST)
        
        ancien_seuil = architecture.risque_tolere
        architecture.risque_tolere = nouveau_seuil
        architecture.save()
        
        log_activity(
            request.user, 
            'ADJUST_RISK_TOLERANCE', 
            'Architecture', 
            str(architecture.id),
            {
                'ancien_seuil': float(ancien_seuil),
                'nouveau_seuil': float(nouveau_seuil),
                'justification': justification
            }
        )
        
        return Response({
            'message': 'Seuil de tolérance mis à jour',
            'ancien_seuil': float(ancien_seuil),
            'nouveau_seuil': float(nouveau_seuil),
            'statut_tolerance': 'CONFORME' if not architecture.risque_depasse_tolerance else 'DEPASSEMENT'
        })


    @action(detail=True, methods=['get'])
    def mesures_controle(self, request, pk=None):
        """Récupère toutes les mesures de contrôle pour une architecture"""
        architecture = self.get_object()
        
        # ÉTAPE 1: Récupérer les IDs des menaces liées à cette architecture
        attributs_menaces = AttributMenace.objects.filter(
            attribut_securite__actif__architecture=architecture
        ).select_related(
            'menace',
            'attribut_securite',
            'attribut_securite__actif'
        ).values_list('menace_id', flat=True).distinct()
        
        # ÉTAPE 2: Récupérer les mesures liées à ces menaces avec FILTRES
        mesures = MesureDeControle.objects.filter(
            menaces_traitees__menace_id__in=attributs_menaces
        ).select_related('technique').prefetch_related(
            'menaces_traitees__menace'
        ).distinct()
        
        # ✅ FILTRES: Exclure les mesures avec nature, efficacité ou coût vides
        mesures = mesures.exclude(
            models.Q(nature_mesure__isnull=True) | models.Q(nature_mesure='') |
            models.Q(efficacite__isnull=True) | models.Q(efficacite=0) |
            models.Q(cout_mise_en_oeuvre__isnull=True)
        )
        
        mesures_data = []
        menaces_dict = {}
        attributs_dict = {}
        
        for mesure in mesures:
            # Pour chaque mesure, trouver les menaces et attributs liés
            for menace_mesure in mesure.menaces_traitees.filter(
                menace_id__in=attributs_menaces
            ).select_related('menace'):
                
                menace = menace_mesure.menace
                
                # Récupérer les attributs de sécurité impactés par cette menace dans cette architecture
                attributs_securite_lies = AttributMenace.objects.filter(
                    menace=menace,
                    attribut_securite__actif__architecture=architecture
                ).select_related('attribut_securite', 'attribut_securite__actif')
                
                for attr_menace in attributs_securite_lies:
                    attribut = attr_menace.attribut_securite
                    
                    # Compteurs pour statistiques
                    if menace.nom not in menaces_dict:
                        menaces_dict[menace.nom] = 0
                    menaces_dict[menace.nom] += 1
                    
                    attribut_key = f"{attribut.actif.nom} - {attribut.type_attribut}"
                    if attribut_key not in attributs_dict:
                        attributs_dict[attribut_key] = 0
                    attributs_dict[attribut_key] += 1
                    
                    # ✅ Construction de l'objet mesure avec attribut de sécurité
                    mesures_data.append({
                        'id': str(mesure.id),
                        'mesure_code': mesure.mesure_code,
                        'nom': mesure.nom,
                        'description': mesure.description,
                        'nature_mesure': mesure.nature_mesure,
                        'efficacite': float(mesure.efficacite) if mesure.efficacite else 0,
                        'cout_mise_en_oeuvre': float(mesure.cout_mise_en_oeuvre) if mesure.cout_mise_en_oeuvre else 0,
                        'cout_maintenance_annuel': float(mesure.cout_maintenance_annuel) if mesure.cout_maintenance_annuel else 0,
                        'cout_total_3_ans': float(mesure.cout_total_3_ans) if mesure.cout_total_3_ans else 0,
                        'duree_implementation': mesure.duree_implementation,
                        'ressources_necessaires': mesure.ressources_necessaires,
                        
                        # ✅ Attribut de sécurité
                        'attribut_securite': {
                            'id': str(attribut.id),
                            'type_attribut': attribut.type_attribut,
                            'cout_compromission': float(attribut.cout_compromission),
                            'priorite': attribut.priorite,
                            'actif_nom': attribut.actif.nom,
                            'actif_id': str(attribut.actif.id),
                            'risque_financier_attribut': attribut.risque_financier_attribut,
                            'niveau_alerte': attribut.niveau_alerte
                        },
                        
                        # Technique
                        'technique': {
                            'id': str(mesure.technique.id),
                            'code': mesure.technique.technique_code,
                            'nom': mesure.technique.nom,
                            'type': mesure.technique.type_technique,
                            'complexite': mesure.technique.complexite,
                            'famille': mesure.technique.famille,
                            'priorite': mesure.technique.priorite
                        },
                        
                        # Menace
                        'menace': {
                            'id': str(menace.id),
                            'nom': menace.nom,
                            'severite': menace.severite,
                            'type_menace': menace.type_menace,
                            'probabilite': float(attr_menace.probabilite),
                            'impact': float(attr_menace.impact),
                            'risque_financier': attr_menace.risque_financier
                        },
                        
                        # Association menace-mesure
                        'menace_mesure': {
                            'efficacite': float(menace_mesure.efficacite) if menace_mesure.efficacite else 0,
                            'statut_conformite': menace_mesure.statut_conformite
                        }
                    })
        
        # Statistiques enrichies
        total_mesures = len(mesures_data)
        efficacite_moyenne = round(
            sum(m['efficacite'] for m in mesures_data) / total_mesures, 2
        ) if total_mesures > 0 else 0
        
        cout_total_mise_en_oeuvre = sum(m['cout_mise_en_oeuvre'] for m in mesures_data)
        cout_total_maintenance = sum(m['cout_maintenance_annuel'] for m in mesures_data)
        cout_total_3_ans = sum(m['cout_total_3_ans'] for m in mesures_data)
        
        par_nature = {}
        par_priorite_attribut = {}
        par_niveau_alerte = {}
        
        for mesure in mesures_data:
            # Par nature
            nature = mesure['nature_mesure']
            par_nature[nature] = par_nature.get(nature, 0) + 1
            
            # Par priorité d'attribut
            priorite = mesure['attribut_securite']['priorite']
            par_priorite_attribut[priorite] = par_priorite_attribut.get(priorite, 0) + 1
            
            # Par niveau d'alerte
            niveau_alerte = mesure['attribut_securite']['niveau_alerte']
            par_niveau_alerte[niveau_alerte] = par_niveau_alerte.get(niveau_alerte, 0) + 1
        
        return Response({
            'architecture_id': str(architecture.id),
            'architecture_nom': architecture.nom,
            'mesures': mesures_data,
            'statistiques': {
                'total_mesures': total_mesures,
                'mesures_uniques': mesures.count(),
                'efficacite_moyenne': efficacite_moyenne,
                'cout_total_mise_en_oeuvre': round(cout_total_mise_en_oeuvre, 2),
                'cout_total_maintenance': round(cout_total_maintenance, 2),
                'cout_total_3_ans': round(cout_total_3_ans, 2),
                'par_nature': par_nature,
                'par_menace': menaces_dict,
                'par_attribut': attributs_dict,
                'par_priorite_attribut': par_priorite_attribut,
                'par_niveau_alerte': par_niveau_alerte
            }
        }, status=status.HTTP_200_OK)

# ============================================================================
# NIVEAU 2: GESTION DES ACTIFS
# ============================================================================

class ActifViewSet(viewsets.ModelViewSet):
    """Gestion des actifs"""
    queryset = Actif.objects.select_related('type_actif', 'architecture', 'proprietaire').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_actif', 'architecture', 'criticite', 'proprietaire']
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'cout', 'criticite', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ActifListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ActifCreateSerializer
        return ActifSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'Actif', str(instance.id), 
                    {'nom': instance.nom})
    
    @action(detail=True, methods=['get'])
    def attributs_securite(self, request, pk=None):
        """Récupère tous les attributs de sécurité d'un actif"""
        actif = self.get_object()
        attributs = actif.attributs_securite.all().order_by('type_attribut')
        
        # Filtres optionnels
        type_attribut = request.query_params.get('type_attribut')
        priorite = request.query_params.get('priorite')
        niveau_alerte = request.query_params.get('niveau_alerte')
        
        if type_attribut:
            attributs = attributs.filter(type_attribut=type_attribut)
        if priorite:
            attributs = attributs.filter(priorite=priorite)
        if niveau_alerte:
            attributs_filtres = [attr for attr in attributs if attr.niveau_alerte == niveau_alerte]
            attributs = attributs_filtres
        
        serializer = AttributSecuriteListSerializer(attributs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ajouter_attribut(self, request, pk=None):
        """Ajoute un nouvel attribut de sécurité à l'actif"""
        actif = self.get_object()
        data = request.data.copy()
        data['actif'] = str(actif.id)
        
        serializer = AttributSecuriteCreateSerializer(data=data)
        if serializer.is_valid():
            attribut = serializer.save()
            log_activity(request.user, 'ADD_ATTRIBUT', 'Actif', str(actif.id),
                        {'type_attribut': attribut.type_attribut})
            return Response(AttributSecuriteListSerializer(attribut).data, 
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def rapport_complet(self, request, pk=None):
        """Génère un rapport complet de l'actif avec analyse des risques"""
        actif = self.get_object()
        
        # Construire le rapport hiérarchique avec analyses
        attributs_data = []
        risque_total_actif = 0
        
        for attribut in actif.attributs_securite.all():
            menaces_data = []
            risque_attribut = 0
            
            for attr_menace in attribut.menaces.all():
                risque_attribut += attr_menace.risque_financier
                
                # Solutions recommandées pour cette menace
                solutions = []
                for controle_link in attr_menace.menace.controles_nist.all():
                    for technique in controle_link.controle_nist.techniques.all():
                        for mesure in technique.mesures_controle.all():
                            if mesure.efficacite and mesure.cout_total_3_ans > 0:
                                ratio = float(mesure.efficacite) / mesure.cout_total_3_ans
                                solutions.append({
                                    'mesure_nom': mesure.nom,
                                    'efficacite': float(mesure.efficacite),
                                    'cout_3_ans': mesure.cout_total_3_ans,
                                    'ratio_efficacite_cout': round(ratio, 4)
                                })
                
                # Trier et prendre les 3 meilleures
                solutions.sort(key=lambda x: x['ratio_efficacite_cout'], reverse=True)
                
                menaces_data.append({
                    **AttributMenaceSerializer(attr_menace).data,
                    'top_solutions': solutions[:3]
                })
            
            risque_total_actif += risque_attribut
            attributs_data.append({
                **AttributSecuriteListSerializer(attribut).data,
                'menaces_detaillees': menaces_data,
                'risque_financier_attribut': round(risque_attribut, 2)
            })
        
        rapport = {
            **ActifSerializer(actif).data,
            'attributs_securite_detailles': attributs_data,
            'risque_financier_total_actif': round(risque_total_actif, 2),
            'analyse_criticite': self._analyser_criticite_actif(actif, risque_total_actif)
        }
        
        return Response(rapport)
    
    def _analyser_criticite_actif(self, actif, risque_financier):
        """Analyse la criticité de l'actif"""
        criticite_actuel = actif.criticite
        
        # Suggérer une criticité basée sur le risque financier
        if risque_financier >= 100000:
            criticite_suggeree = 'CRITIQUE'
        elif risque_financier >= 50000:
            criticite_suggeree = 'ELEVE'
        elif risque_financier >= 20000:
            criticite_suggeree = 'MOYEN'
        else:
            criticite_suggeree = 'FAIBLE'
        
        return {
            'criticite_actuelle': criticite_actuel,
            'criticite_suggeree': criticite_suggeree,
            'alignement': criticite_actuel == criticite_suggeree,
            'recommandation': 'REVOIR_CRITICITE' if criticite_actuel != criticite_suggeree else 'CRITICITE_ADEQUATE'
        }

# ============================================================================
# NIVEAU 3: GESTION DES ATTRIBUTS DE SECURITE
# ============================================================================

class AttributSecuriteViewSet(viewsets.ModelViewSet):
    """Gestion des attributs de sécurité"""
    queryset = AttributSecurite.objects.select_related('actif').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['actif', 'type_attribut', 'priorite']
    ordering_fields = ['type_attribut', 'cout_compromission', 'created_at']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AttributSecuriteCreateSerializer
        elif self.action == 'list':
            return AttributSecuriteListSerializer
        return AttributSecuriteSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'AttributSecurite', str(instance.id), 
                    {'type_attribut': instance.type_attribut})
    
    @action(detail=True, methods=['get'])
    def menaces(self, request, pk=None):
        """Récupère toutes les menaces liées à cet attribut avec solutions"""
        attribut = self.get_object()
        menaces_links = attribut.menaces.select_related('menace').all()
        
        # Filtres optionnels
        severite = request.query_params.get('severite')
        type_menace = request.query_params.get('type_menace')
        risque_min = request.query_params.get('risque_min')
        
        if severite:
            menaces_links = menaces_links.filter(menace__severite=severite)
        if type_menace:
            menaces_links = menaces_links.filter(menace__type_menace=type_menace)
        if risque_min:
            menaces_links = [m for m in menaces_links if m.risque_financier >= float(risque_min)]
        
        serializer = AttributMenaceSerializer(menaces_links, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def associer_menace(self, request, pk=None):
        """Associe une menace à cet attribut de sécurité"""
        attribut = self.get_object()
        data = request.data.copy()
        data['attribut_securite'] = str(attribut.id)
        
        serializer = AttributMenaceCreateSerializer(data=data)
        if serializer.is_valid():
            association = serializer.save()
            log_activity(request.user, 'ASSOCIATE_MENACE', 'AttributSecurite', str(attribut.id),
                        {'menace_nom': association.menace.nom})
            return Response(AttributMenaceSerializer(association).data, 
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def analyse_risque_financier(self, request, pk=None):
        """Analyse détaillée du risque financier pour cet attribut"""
        attribut = self.get_object()
        
        analyse = {
            'attribut': AttributSecuriteSerializer(attribut).data,
            'cout_compromission_defini': float(attribut.cout_compromission),
            'risque_financier_calcule': attribut.risque_financier_attribut,
            'ratio_risque_cout': attribut.ratio_risque_cout,
            'niveau_alerte': attribut.niveau_alerte
        }
        
        # Détail par menaces avec solutions
        menaces_detail = []
        for menace_link in attribut.menaces.all():
            # Trouver les meilleures solutions pour cette menace
            solutions = []
            for controle_link in menace_link.menace.controles_nist.all():
                for technique in controle_link.controle_nist.techniques.all():
                    for mesure in technique.mesures_controle.all():
                        if mesure.efficacite and mesure.cout_total_3_ans > 0:
                            ratio = float(mesure.efficacite) / mesure.cout_total_3_ans
                            solutions.append({
                                'mesure_id': mesure.id,
                                'mesure_nom': mesure.nom,
                                'efficacite': float(mesure.efficacite),
                                'cout_3_ans': mesure.cout_total_3_ans,
                                'ratio_efficacite_cout': round(ratio, 4),
                                'reduction_risque_estimee': round(
                                    (float(mesure.efficacite) / 100) * menace_link.risque_financier, 2
                                )
                            })
            
            solutions.sort(key=lambda x: x['ratio_efficacite_cout'], reverse=True)
            
            menaces_detail.append({
                'menace': menace_link.menace.nom,
                'type_menace': menace_link.menace.type_menace,
                'severite': menace_link.menace.severite,
                'probabilite': float(menace_link.probabilite),
                'cout_impact': float(menace_link.cout_impact),
                'risque_financier': menace_link.risque_financier,
                'contribution_pourcentage': round(
                    (menace_link.risque_financier / attribut.risque_financier_attribut) * 100, 2
                ) if attribut.risque_financier_attribut > 0 else 0,
                'top_solutions': solutions[:3]
            })
        
        # Trier par risque financier décroissant
        menaces_detail.sort(key=lambda x: x['risque_financier'], reverse=True)
        analyse['menaces_detail'] = menaces_detail
        
        # Recommandations stratégiques
        analyse['plan_action'] = self._generer_plan_action(attribut, menaces_detail)
        
        return Response(analyse)
    
    def _generer_plan_action(self, attribut, menaces_detail):
        """Génère un plan d'action basé sur l'analyse"""
        niveau_alerte = attribut.niveau_alerte
        budget_total_requis = 0
        actions_recommandees = []
        
        for menace in menaces_detail[:3]:  # Top 3 menaces
            if menace['top_solutions']:
                meilleure_solution = menace['top_solutions'][0]
                budget_total_requis += meilleure_solution['cout_3_ans']
                actions_recommandees.append({
                    'priorite': 1 if menace['severite'] == 'CRITIQUE' else 2,
                    'action': f"Implémenter {meilleure_solution['mesure_nom']}",
                    'menace_ciblee': menace['menace'],
                    'cout_estime': meilleure_solution['cout_3_ans'],
                    'reduction_risque': meilleure_solution['reduction_risque_estimee']
                })
        
        return {
            'urgence': niveau_alerte,
            'budget_total_requis': round(budget_total_requis, 2),
            'roi_estime': round(
                (attribut.risque_financier_attribut - budget_total_requis) / budget_total_requis * 100, 2
            ) if budget_total_requis > 0 else 0,
            'actions_recommandees': sorted(actions_recommandees, key=lambda x: x['priorite'])
        }
    
    @action(detail=False, methods=['get'])
    def attributs_critique_alerte(self, request):
        """Liste des attributs avec niveau d'alerte critique ou élevé"""
        attributs_critiques = []
        
        for attribut in self.get_queryset():
            if attribut.niveau_alerte in ['CRITIQUE', 'ELEVE']:
                attributs_critiques.append({
                    'attribut': AttributSecuriteListSerializer(attribut).data,
                    'cout_compromission': float(attribut.cout_compromission),
                    'risque_financier_calcule': attribut.risque_financier_attribut,
                    'ratio_risque_cout': attribut.ratio_risque_cout,
                    'niveau_alerte': attribut.niveau_alerte,
                    'actif_nom': attribut.actif.nom,
                    'architecture_nom': attribut.actif.architecture.nom,
                    'depassement_montant': max(0, attribut.risque_financier_attribut - float(attribut.cout_compromission))
                })
        
        # Trier par ratio risque/coût décroissant
        attributs_critiques.sort(key=lambda x: x['ratio_risque_cout'], reverse=True)
        
        return Response(attributs_critiques)

    @action(detail=True, methods=['post'])
    def creer_menace(self, request, pk=None):
        """
        Crée et associe une menace simplifiée avec seulement 3 champs :
        - nom : nom de la menace
        - description : description de la menace  
        - probabilite : probabilité d'occurrence (%)
        
        L'impact et le coût d'impact sont calculés automatiquement
        basés sur le coût de compromission de l'attribut.
        """
        attribut = self.get_object()
        
        # Validation avec le serializer
        serializer = MenaceSimpleCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        nom = validated_data['nom']
        description = validated_data.get('description', '')
        probabilite = validated_data['probabilite']
        
        # ✅ RÉCUPÉRER LE TYPE_MENACE DU FORMULAIRE
        type_menace = request.data.get('type_menace', 'Spoofing')  # Valeur par défaut cohérente
        
        try:
            with transaction.atomic():
                # 1. Créer ou récupérer la menace
                menace, created = Menace.objects.get_or_create(
                    nom=nom,
                    defaults={
                        'description': description,
                        'type_menace': type_menace,  # ✅ UTILISER LA VALEUR DU FORMULAIRE
                        'severite': 'MOYEN',     
                        'attribut_securite_principal': attribut
                    }
                )
                
                # Si la menace existe déjà, vérifier qu'elle n'est pas déjà associée
                if not created:
                    existing_association = AttributMenace.objects.filter(
                        attribut_securite=attribut, 
                        menace=menace
                    ).first()
                    
                    if existing_association:
                        return Response({
                            'error': f'La menace "{nom}" est déjà associée à cet attribut',
                            'existing_association_id': existing_association.id
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # ✅ METTRE À JOUR TOUS LES CHAMPS SI NÉCESSAIRE
                    updated = False
                    if description and description != menace.description:
                        menace.description = description
                        updated = True
                    if type_menace and type_menace != menace.type_menace:
                        menace.type_menace = type_menace
                        updated = True
                    
                    if updated:
                        menace.save()
                
                # 2. Créer l'association AttributMenace
                association = AttributMenace.objects.create(
                    attribut_securite=attribut,
                    menace=menace,
                    probabilite=probabilite,
                    impact=Decimal('100.0'),  
                    cout_impact=attribut.cout_compromission
                )
                
                # 3. Préparer la réponse avec les données complètes
                response_data = {
                    'id': association.id,
                    'menace': menace.id,
                    'menace_nom': menace.nom,
                    'menace_severite': menace.severite,
                    'menace_detail': {
                        'id': menace.id,
                        'nom': menace.nom,
                        'description': menace.description,
                        'type_menace': menace.type_menace,  # ✅ RETOURNER LE BON TYPE
                        'severite': menace.severite,
                        'total_controles': menace.controles_nist.count(),
                        'total_techniques': sum(
                            controle.controle_nist.techniques.count() 
                            for controle in menace.controles_nist.all()
                        ),
                        'total_mesures': sum(
                            technique.mesures_controle.count()
                            for controle in menace.controles_nist.all()
                            for technique in controle.controle_nist.techniques.all()
                        )
                    },
                    'attribut_securite': attribut.id,
                    'attribut_nom': attribut.actif.nom,
                    'attribut_type': attribut.type_attribut,
                    'probabilite': float(association.probabilite),
                    'impact': float(association.impact),
                    'cout_impact': float(association.cout_impact),
                    'niveau_risque_calculated': association.niveau_risque,
                    'risque_financier_calculated': association.risque_financier,
                    'created_at': association.created_at.isoformat(),
                    
                    # Informations calculées
                    'calculs': {
                        'cout_compromission_attribut': float(attribut.cout_compromission),
                        'formule_risque': f"{probabilite}% × {float(attribut.cout_compromission)}$",
                        'menace_creee': created
                    }
                }
                
                # 4. Log de l'activité
                log_activity(
                    request.user, 
                    'CREATE_MENACE_SIMPLE', 
                    'AttributSecurite', 
                    str(attribut.id),
                    {
                        'menace_nom': menace.nom,
                        'menace_id': str(menace.id),
                        'type_menace': menace.type_menace,  # ✅ LOGGER LE BON TYPE
                        'probabilite': float(probabilite),
                        'risque_financier': association.risque_financier,
                        'menace_creee': created
                    }
                )
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Erreur lors de la création de menace simple: {str(e)}")
            return Response(
                {'error': f'Erreur interne lors de la création : {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def optimiser_mesures(self, request, pk=None):
        """
        Optimise les mesures de sécurité pour cet attribut spécifique
        
        POST /api/attributs-securite/{id}/optimiser_mesures/
        {
            "budget_max": 10000.00,  // optionnel
            "creer_implementations": true,  // optionnel
            "responsable_id": "uuid"  // optionnel
        }
        """
        attribut = self.get_object()
        
        budget_max = request.data.get('budget_max')
        creer_implementations = request.data.get('creer_implementations', False)
        responsable_id = request.data.get('responsable_id')
        
        try:
            # Initialiser le service d'optimisation
            optimization_service = SecurityOptimizationService()
            
            # Lancer l'optimisation
            result = optimization_service._optimize_attribut_security(attribut)
            
            # Créer les implémentations si demandé et si l'optimisation a réussi
            if creer_implementations and result.get('status') == 'optimal':
                # Formater pour create_implementation_plan
                formatted_result = {
                    'optimization_type': 'individual_by_attribute',
                    'results': [{
                        'attribut': attribut,
                        'result': result
                    }]
                }
                
                implementation_plan = optimization_service.create_implementation_plan(
                    optimization_result=formatted_result,
                    responsable_id=responsable_id
                )
                result['implementation_plan'] = implementation_plan
            
            # Log de l'activité
            log_activity(
                request.user, 
                'ATTRIBUT_OPTIMIZATION', 
                'AttributSecurite', 
                str(attribut.id),
                {
                    'status': result.get('status'),
                    'measures_count': result.get('measures_count', 0),
                    'total_cost': result.get('total_cost', 0),
                    'implementations_created': creer_implementations
                }
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de l'attribut {attribut.id}: {str(e)}")
            return Response(
                {'error': f'Erreur d\'optimisation: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ============================================================================
# NIVEAU 4: GESTION DES ASSOCIATIONS ATTRIBUT-MENACE
# ============================================================================

class AttributMenaceViewSet(viewsets.ModelViewSet):
    """Gestion des associations attribut-menace avec solutions intégrées"""
    queryset = AttributMenace.objects.select_related(
        'attribut_securite', 'menace', 'attribut_securite__actif'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['attribut_securite', 'menace', 'menace__severite']
    ordering_fields = ['niveau_risque', 'risque_financier', 'created_at']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AttributMenaceCreateSerializer
        return AttributMenaceSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'AttributMenace', str(instance.id), 
                    {'menace_nom': instance.menace.nom})
    
    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'UPDATE', 'AttributMenace', str(instance.id), 
                    {'menace_nom': instance.menace.nom})
    def get_object(self):
        """Override pour débugger les problèmes d'ID"""
        obj = super().get_object()
        print(f"DEBUG: Objet trouvé avec ID {obj.id}")
        return obj
    
    # NOUVELLE MÉTHODE : Update spécialisé pour les menaces
    @action(detail=True, methods=['put', 'patch'])
    def update_menace_data(self, request, pk=None):
        """
        Méthode spécialisée pour mettre à jour une association menace
        avec mise à jour des données de la menace elle-même
        """
        try:
            association = self.get_object()
            
            # Données de l'association (probabilité)
            if 'probabilite' in request.data:
                association.probabilite = request.data['probabilite']
                association.save()
            
            # Données de la menace (nom, description, type_menace)
            menace = association.menace
            menace_updated = False
            
            if 'nom' in request.data and request.data['nom'] != menace.nom:
                # Vérifier que le nouveau nom n'existe pas déjà
                if Menace.objects.filter(nom=request.data['nom']).exclude(id=menace.id).exists():
                    return Response(
                        {'error': 'Une menace avec ce nom existe déjà'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                menace.nom = request.data['nom']
                menace_updated = True
            
            if 'description' in request.data:
                menace.description = request.data['description']
                menace_updated = True
            
            if 'type_menace' in request.data:
                menace.type_menace = request.data['type_menace']
                menace_updated = True
            
            if menace_updated:
                menace.save()
            
            # Log de l'activité
            log_activity(
                request.user, 
                'UPDATE_MENACE_ASSOCIATION', 
                'AttributMenace', 
                str(association.id),
                {
                    'menace_nom': menace.nom,
                    'probabilite': float(association.probabilite),
                    'menace_updated': menace_updated
                }
            )
            
            # Retourner les données mises à jour
            return Response({
                'id': association.id,
                'menace': menace.id,
                'menace_nom': menace.nom,
                'menace_detail': {
                    'id': menace.id,
                    'nom': menace.nom,
                    'description': menace.description,
                    'type_menace': menace.type_menace,
                    'severite': menace.severite
                },
                'probabilite': float(association.probabilite),
                'impact': float(association.impact),
                'cout_impact': float(association.cout_impact),
                'niveau_risque_calculated': association.niveau_risque,
                'risque_financier_calculated': association.risque_financier,
                'updated_at': association.updated_at.isoformat()
            })
            
        except AttributMenace.DoesNotExist:
            return Response(
                {'error': 'Association menace non trouvée'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'association menace: {str(e)}")
            return Response(
                {'error': f'Erreur interne: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

    def update(self, request, *args, **kwargs):
        """Override de la méthode update standard pour gérer les champs de menace"""
        instance = self.get_object()
        
        # Séparer les données de l'association et de la menace
        association_data = {}
        menace_data = {}
        
        # Champs de l'association AttributMenace
        association_fields = ['probabilite', 'impact', 'cout_impact']
        # Champs de la Menace
        menace_fields = ['nom', 'description', 'type_menace', 'severite']
        
        for key, value in request.data.items():
            if key in association_fields:
                association_data[key] = value
            elif key in menace_fields:
                menace_data[key] = value
        
        try:
            with transaction.atomic():
                # Mettre à jour l'association
                for field, value in association_data.items():
                    if hasattr(instance, field):
                        setattr(instance, field, value)
                
                if association_data:
                    instance.save()
                
                # Mettre à jour la menace si nécessaire
                if menace_data:
                    menace = instance.menace
                    menace_updated = False
                    
                    for field, value in menace_data.items():
                        if hasattr(menace, field) and getattr(menace, field) != value:
                            # Vérification spéciale pour le nom (unicité)
                            if field == 'nom':
                                if Menace.objects.filter(nom=value).exclude(id=menace.id).exists():
                                    return Response(
                                        {'error': 'Une menace avec ce nom existe déjà'}, 
                                        status=status.HTTP_400_BAD_REQUEST
                                    )
                            
                            setattr(menace, field, value)
                            menace_updated = True
                    
                    if menace_updated:
                        menace.save()
                
                # Log de l'activité
                log_activity(
                    request.user, 
                    'UPDATE_MENACE_ASSOCIATION', 
                    'AttributMenace', 
                    str(instance.id),
                    {
                        'menace_nom': instance.menace.nom,
                        'association_updated': bool(association_data),
                        'menace_updated': bool(menace_data)
                    }
                )
                
                # Retourner la réponse avec les données mises à jour
                serializer = self.get_serializer(instance)
                return Response(serializer.data)
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour: {str(e)}")
            return Response(
                {'error': f'Erreur lors de la mise à jour: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
   
    @action(detail=True, methods=['get'])
    def plan_mitigation(self, request, pk=None):
        """Génère un plan de mitigation complet pour ce risque"""
        attr_menace = self.get_object()
        
        # Budget disponible (optionnel)
        budget_max = request.query_params.get('budget_max')
        duree_max = request.query_params.get('duree_max')
        
        # Récupérer toutes les solutions possibles
        solutions = []
        for controle_link in attr_menace.menace.controles_nist.all():
            for technique in controle_link.controle_nist.techniques.all():
                for mesure in technique.mesures_controle.all():
                    # Filtrer par budget et durée si spécifiés
                    if budget_max and mesure.cout_total_3_ans > float(budget_max):
                        continue
                    if duree_max and mesure.duree_implementation > int(duree_max):
                        continue
                    
                    if mesure.efficacite and mesure.cout_total_3_ans > 0:
                        score_efficacite = float(mesure.efficacite) / 100
                        score_cout = 1 - min(mesure.cout_total_3_ans / 100000, 1)
                        score_temps = 1 - min(mesure.duree_implementation / 365, 1)
                        score_conformite = {
                            'CONFORME': 1.0,
                            'PARTIELLEMENT': 0.7,
                            'NON_CONFORME': 0.3,
                            'NON_APPLICABLE': 0.0
                        }.get(controle_link.statut_conformite, 0.3)
                        
                        score_global = (
                            score_efficacite * 0.4 +
                            score_cout * 0.3 +
                            score_temps * 0.2 +
                            score_conformite * 0.1
                        )
                        
                        solutions.append({
                            'mesure_id': mesure.id,
                            'mesure_nom': mesure.nom,
                            'technique_nom': technique.nom,
                            'controle_code': controle_link.controle_nist.code,
                            'efficacite': float(mesure.efficacite),
                            'cout_3_ans': mesure.cout_total_3_ans,
                            'duree_implementation': mesure.duree_implementation,
                            'nature_mesure': mesure.nature_mesure,
                            'score_global': round(score_global, 3),
                            'reduction_risque_estimee': round(
                                (float(mesure.efficacite) / 100) * attr_menace.risque_financier, 2
                            )
                        })
        
        # Trier par score global décroissant
        solutions.sort(key=lambda x: x['score_global'], reverse=True)
        
        # Générer le plan de mitigation
        plan = {
            'risque': {
                'attribut': attr_menace.attribut_securite.actif.nom,
                'type_attribut': attr_menace.attribut_securite.type_attribut,
                'menace': attr_menace.menace.nom,
                'probabilite': float(attr_menace.probabilite),
                'impact': float(attr_menace.impact),
                'cout_impact': float(attr_menace.cout_impact),
                'risque_financier': attr_menace.risque_financier,
                'niveau_risque': attr_menace.niveau_risque
            },
            'solutions_analysees': len(solutions),
            'solutions_optimales': solutions[:5],  # Top 5
            'strategie_recommandee': self._generer_strategie_mitigation(attr_menace, solutions),
            'planning_suggere': self._generer_planning_mitigation(solutions[:3]),
            'analyse_cout_benefice': self._analyser_cout_benefice(attr_menace, solutions[:3])
        }
        
        return Response(plan)
    
    def _generer_strategie_mitigation(self, attr_menace, solutions):
        """Génère une stratégie de mitigation"""
        niveau_risque = attr_menace.niveau_risque
        risque_financier = attr_menace.risque_financier
        
        if niveau_risque >= 80 or risque_financier >= 50000:
            return {
                'priorite': 'CRITIQUE',
                'approche': 'IMMEDIATE',
                'nombre_mesures_recommandees': min(3, len(solutions)),
                'justification': 'Risque critique nécessitant une action immédiate',
                'delai_max': '30 jours'
            }
        elif niveau_risque >= 50 or risque_financier >= 20000:
            return {
                'priorite': 'ELEVE',
                'approche': 'PRIORITAIRE', 
                'nombre_mesures_recommandees': min(2, len(solutions)),
                'justification': 'Risque élevé à traiter en priorité',
                'delai_max': '90 jours'
            }
        else:
            return {
                'priorite': 'NORMALE',
                'approche': 'PLANIFIEE',
                'nombre_mesures_recommandees': min(1, len(solutions)),
                'justification': 'Risque modéré, traitement planifiable',
                'delai_max': '180 jours'
            }
    
    def _generer_planning_mitigation(self, solutions):
        """Génère un planning de mitigation"""
        if not solutions:
            return {}
        
        duree_totale = sum(s['duree_implementation'] for s in solutions)
        
        return {
            'duree_totale_jours': duree_totale,
            'duree_totale_mois': round(duree_totale / 30, 1),
            'phases': [
                {
                    'phase': i + 1,
                    'description': f"Phase {i + 1}: {sol['mesure_nom']}",
                    'duree_jours': sol['duree_implementation'],
                    'mesure_id': sol['mesure_id'],
                    'cout_estime': sol['cout_3_ans']
                }
                for i, sol in enumerate(solutions)
            ]
        }
    
    def _analyser_cout_benefice(self, attr_menace, solutions):
        """Analyse coût-bénéfice des solutions"""
        if not solutions:
            return {}
        
        cout_total = sum(s['cout_3_ans'] for s in solutions)
        reduction_totale = sum(s['reduction_risque_estimee'] for s in solutions)
        
        # Appliquer les rendements décroissants
        reduction_effective = min(reduction_totale * 0.8, attr_menace.risque_financier * 0.95)
        
        return {
            'cout_total_solutions': cout_total,
            'reduction_risque_estimee': round(reduction_effective, 2),
            'benefice_net_3_ans': round((reduction_effective * 3) - cout_total, 2),
            'roi_pourcentage': round(
                (((reduction_effective * 3) - cout_total) / cout_total) * 100, 2
            ) if cout_total > 0 else 0,
            'temps_retour_investissement_mois': round(
                cout_total / (reduction_effective / 12), 1
            ) if reduction_effective > 0 else 0
        }
    
    @action(detail=True, methods=['post'])
    def implementer_solution(self, request, pk=None):
        """Implémente une solution complète avec planning"""
        attr_menace = self.get_object()
        
        mesure_controle_id = request.data.get('mesure_controle_id')
        responsable_id = request.data.get('responsable_id')
        date_debut_prevue = request.data.get('date_debut_prevue')
        date_fin_prevue = request.data.get('date_fin_prevue')
        equipe = request.data.get('equipe', '')
        commentaires = request.data.get('commentaires', '')
        
        if not mesure_controle_id:
            return Response(
                {'error': 'mesure_controle_id requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que la mesure existe et est liée à cette menace
        try:
            mesure = MesureDeControle.objects.get(id=mesure_controle_id)
        except MesureDeControle.DoesNotExist:
            return Response(
                {'error': 'Mesure de contrôle non trouvée'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Créer l'implémentation
        implementation_data = {
            'attribut_menace': attr_menace.id,
            'mesure_controle': mesure.id,
            'statut': 'PLANIFIE',
            'responsable': responsable_id,
            'date_debut_prevue': date_debut_prevue,
            'date_fin_prevue': date_fin_prevue,
            'equipe': equipe,
            'commentaires': commentaires,
            'pourcentage_avancement': 0
        }
        
        serializer = ImplementationMesureSerializer(data=implementation_data)
        if serializer.is_valid():
            implementation = serializer.save()
            
            log_activity(
                request.user, 
                'IMPLEMENT_SOLUTION', 
                'AttributMenace', 
                str(attr_menace.id),
                {
                    'mesure_nom': mesure.nom,
                    'responsable_id': responsable_id
                }
            )
            
            return Response({
                'message': 'Solution planifiée avec succès',
                'implementation': ImplementationMesureSerializer(implementation).data,
                'risque_residuel_estime': implementation.risque_residuel
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




# ============================================================================
# NIVEAU 7: GESTION DES MESURES DE CONTROLE
# ============================================================================



class MesureDeControleViewSet(viewsets.ModelViewSet):
    """Gestion des mesures de contrôle"""
    queryset = MesureDeControle.objects.select_related('technique').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['technique', 'nature_mesure']
    search_fields = ['nom', 'description', 'mesure_code']  # mesure_code ajouté à la recherche
    ordering_fields = ['nom', 'mesure_code', 'efficacite', 'cout_mise_en_oeuvre', 'created_at']  # mesure_code ajouté
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MesureDeControleCreateSerializer
        return MesureDeControleSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'MesureDeControle', str(instance.id), 
                    {'nom': instance.nom, 'mesure_code': instance.mesure_code})  # mesure_code ajouté au log
    
    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'UPDATE', 'MesureDeControle', str(instance.id), 
                    {'nom': instance.nom, 'mesure_code': instance.mesure_code})  # mesure_code ajouté au log


    @action(detail=False, methods=['post'])
    def import_mesures(self, request):
        """Import de mesures de contrôle depuis un fichier CSV/Excel"""
        
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Fichier requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        
        # Vérifier l'extension du fichier
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_extension not in ['csv', 'xlsx', 'xls']:
            return Response(
                {'error': 'Format de fichier non supporté. Utilisez CSV, XLSX ou XLS'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Import selon le type de fichier
            if file_extension == 'csv':
                import_result = self._import_mesures_from_csv(uploaded_file, request.user)
            else:
                import_result = self._import_mesures_from_excel(uploaded_file, request.user)
            
            return Response(import_result, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import de mesures de contrôle: {str(e)}")
            return Response(
                {'error': f'Erreur lors de l\'import: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _import_mesures_from_excel(self, excel_file, user):
        """Import de mesures de contrôle depuis un fichier Excel"""
        import pandas as pd
        from decimal import Decimal
        
        try:
            # Lire le fichier Excel
            df = pd.read_excel(excel_file)
            
            # Mapping flexible des noms de colonnes
            column_mapping = {
                # Variations pour 'technique_code'
                'technique_code': 'technique_code',
                'code_technique': 'technique_code',
                'technique': 'technique_code',
                
                # Variations pour 'mesure_code'
                'mesure_code': 'mesure_code',
                'code_mesure': 'mesure_code',
                'code': 'mesure_code',
                
                # Variations pour 'nom'
                'nom': 'nom',
                'name': 'nom',
                'titre': 'nom',
                
                # Variations pour 'description'
                'description': 'description',
                'desc': 'description',
                
                # Variations pour 'nature_mesure'
                'nature_mesure': 'nature_mesure',
                'nature': 'nature_mesure',
                'type_mesure': 'nature_mesure',
                'categorie': 'nature_mesure',
                
                # Variations pour les coûts
                'cout_mise_en_oeuvre': 'cout_mise_en_oeuvre',
                'cout_implementation': 'cout_mise_en_oeuvre',
                'cout_initial': 'cout_mise_en_oeuvre',
                'cout_maintenance_annuel': 'cout_maintenance_annuel',
                'cout_maintenance': 'cout_maintenance_annuel',
                
                # Variations pour 'efficacite'
                'efficacite': 'efficacite',
                'efficacity': 'efficacite',
                'effectiveness': 'efficacite',
                
                # Variations pour 'duree_implementation'
                'duree_implementation': 'duree_implementation',
                'duree': 'duree_implementation',
                'duration': 'duree_implementation',
                
                # Variations pour 'ressources_necessaires'
                'ressources_necessaires': 'ressources_necessaires',
                'ressources': 'ressources_necessaires',
                'resources': 'ressources_necessaires'
            }
            
            # Renommer les colonnes selon le mapping
            df = df.rename(columns=column_mapping)
            
            # Vérifier les colonnes OBLIGATOIRES
            required_columns = ['technique_code', 'nom', 'mesure_code']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'message': f'Colonnes obligatoires manquantes: {", ".join(missing_columns)}',
                    'mesures_creees': 0,
                    'erreurs': [{
                        'ligne': 1,
                        'erreur': f'Colonnes obligatoires manquantes: {", ".join(missing_columns)}. Colonnes disponibles: {", ".join(df.columns.tolist())}'
                    }],
                    'total_erreurs': 1,
                    'colonnes_disponibles': df.columns.tolist(),
                    'colonnes_obligatoires': required_columns
                }
            
            mesures_creees = 0
            mesures_errors = []
            
            # Nettoyer les données avant traitement
            df = df.fillna('')  # Remplacer NaN par chaîne vide
            
            for index, row in df.iterrows():
                try:
                    # Récupérer les champs obligatoires
                    technique_code = str(row.get('technique_code', '')).strip()
                    mesure_code = str(row.get('mesure_code', '')).strip()
                    nom = str(row.get('nom', '')).strip()
                    
                    # Récupérer les champs optionnels
                    description = str(row.get('description', '')).strip()
                    nature_mesure = str(row.get('nature_mesure', '')).strip()
                    cout_mise_en_oeuvre = str(row.get('cout_mise_en_oeuvre', '0')).strip()
                    cout_maintenance_annuel = str(row.get('cout_maintenance_annuel', '0')).strip()
                    efficacite = str(row.get('efficacite', '0')).strip()
                    duree_implementation = str(row.get('duree_implementation', '30')).strip()
                    ressources_necessaires = str(row.get('ressources_necessaires', '')).strip()
                    
                    # Validation des champs obligatoires
                    if not all([technique_code, nom, mesure_code]):
                        mesures_errors.append({
                            'ligne': index + 2,
                            'erreur': 'Champs obligatoires manquants: technique_code, nom, mesure_code',
                            'donnees_recues': {
                                'technique_code': technique_code,
                                'nom': nom,
                                'mesure_code': mesure_code
                            }
                        })
                        continue
                    
                   
                    try:
                        technique = Technique.objects.get(technique_code=technique_code)
                    except Technique.DoesNotExist:
                        mesures_errors.append({
                            'ligne': index + 2,
                            'erreur': f'Technique avec le code {technique_code} non trouvée'
                        })
                        continue
                    
                    # Vérifier l'unicité du mesure_code
                    # if MesureDeControle.objects.filter(nom=nom).exists():
                    #     mesures_errors.append({
                    #         'ligne': index + 2,
                    #         'erreur': f'Une mesure avec le code {nom} existe déjà'
                    #     })
                    #     continue
                    
                    # Traitement des champs optionnels
                    # Description (optionnel)
                    if not description or description.lower() in ['', 'nan', 'null', 'none']:
                        description = f"Mesure de contrôle {mesure_code}: {nom}"
                    
                    # Nature de mesure (optionnel)
                    valid_natures = ['ORGANISATIONNEL', 'TECHNIQUE', 'PHYSIQUE', 'JURIDIQUE']
                    if not nature_mesure or nature_mesure.upper() not in valid_natures:
                        nature_mesure = 'TECHNIQUE'  # Valeur par défaut
                    else:
                        nature_mesure = nature_mesure.upper()
                    
                    # Traitement des coûts (optionnel)
                    try:
                        cout_mise_en_oeuvre_val = Decimal(cout_mise_en_oeuvre.replace(',', '.')) if cout_mise_en_oeuvre and cout_mise_en_oeuvre != '' else Decimal('0.00')
                    except (ValueError, TypeError):
                        cout_mise_en_oeuvre_val = Decimal('0.00')
                    
                    try:
                        cout_maintenance_val = Decimal(cout_maintenance_annuel.replace(',', '.')) if cout_maintenance_annuel and cout_maintenance_annuel != '' else Decimal('0.00')
                    except (ValueError, TypeError):
                        cout_maintenance_val = Decimal('0.00')
                    
                    # Traitement de l'efficacité (optionnel)
                    try:
                        efficacite_val = Decimal(efficacite.replace(',', '.')) if efficacite and efficacite != '' else Decimal('0.00')
                        if efficacite_val < 0 or efficacite_val > 100:
                            efficacite_val = Decimal('0.00')
                    except (ValueError, TypeError):
                        efficacite_val = Decimal('0.00')
                    
                    # Traitement de la durée (optionnel)
                    try:
                        duree_val = int(duree_implementation) if duree_implementation and duree_implementation != '' else 30
                        if duree_val < 1:
                            duree_val = 30
                    except (ValueError, TypeError):
                        duree_val = 30
                    
                    # Ressources nécessaires (optionnel)
                    if not ressources_necessaires or ressources_necessaires.lower() in ['', 'nan', 'null', 'none']:
                        ressources_necessaires = None
                    
                    # Préparer les données
                    data = {
                        'technique': technique,
                        'mesure_code': mesure_code,
                        'nom': nom,
                        'description': description,
                        'nature_mesure': nature_mesure,
                        'cout_mise_en_oeuvre': cout_mise_en_oeuvre_val,
                        'cout_maintenance_annuel': cout_maintenance_val,
                        'efficacite': efficacite_val,
                        'duree_implementation': duree_val,
                        'ressources_necessaires': ressources_necessaires
                    }
                    
                    # Créer la mesure de contrôle
                    mesure = MesureDeControle.objects.create(**data)
                    mesures_creees += 1
                    
                    # Log de l'activité
                    log_activity(
                        user, 
                        'IMPORT_MESURE', 
                        'MesureDeControle', 
                        str(mesure.id),
                        {
                            'nom': mesure.nom,
                            'mesure_code': mesure.mesure_code,
                            'technique_code': technique_code,
                            'ligne': index + 2
                        }
                    )
                    
                except Exception as e:
                    mesures_errors.append({
                        'ligne': index + 2,
                        'erreur': str(e)
                    })
            
            return {
                'message': f'Import terminé: {mesures_creees} mesures créées',
                'mesures_creees': mesures_creees,
                'erreurs': mesures_errors,
                'total_erreurs': len(mesures_errors),
                'colonnes_detectees': df.columns.tolist()
            }
            
        except Exception as e:
            raise Exception(f'Erreur lors de la lecture du fichier Excel: {str(e)}')

    def _import_mesures_from_csv(self, csv_file, user):
        """Import de mesures de contrôle depuis un fichier CSV"""
        import csv
        import io
        from decimal import Decimal
        
        # Lire le fichier CSV
        file_content = csv_file.read().decode('utf-8')
        csv_data = csv.DictReader(io.StringIO(file_content))
        
        mesures_creees = 0
        mesures_errors = []
        
        for row_num, row in enumerate(csv_data, start=2):
            try:
                # Récupérer les champs obligatoires
                technique_code = row.get('technique_code', '').strip()
                mesure_code = row.get('mesure_code', '').strip()
                nom = row.get('nom', '').strip()
                
                # Validation des champs requis
                if not all([technique_code, nom, mesure_code]):
                    mesures_errors.append({
                        'ligne': row_num,
                        'erreur': 'Champs requis manquants: technique_code, nom, mesure_code'
                    })
                    continue
                
                # Vérifier que la technique existe
                try:
                    technique = Technique.objects.get(technique_code=technique_code)
                except Technique.DoesNotExist:
                    mesures_errors.append({
                        'ligne': row_num,
                        'erreur': f'Technique avec le code {technique_code} non trouvée'
                    })
                    continue
                
                # Vérifier l'unicité du mesure_code
                
                
                # Traitement des champs optionnels
                description = row.get('description', '').strip()
                if not description:
                    description = f"Mesure de contrôle {mesure_code}: {nom}"
                
                nature_mesure = row.get('nature_mesure', 'TECHNIQUE').strip().upper()
                if nature_mesure not in ['ORGANISATIONNEL', 'TECHNIQUE', 'PHYSIQUE', 'JURIDIQUE']:
                    nature_mesure = 'TECHNIQUE'
                
                # Traitement des valeurs numériques
                try:
                    cout_mise_en_oeuvre = Decimal(row.get('cout_mise_en_oeuvre', '0').replace(',', '.'))
                except:
                    cout_mise_en_oeuvre = Decimal('0.00')
                
                try:
                    cout_maintenance = Decimal(row.get('cout_maintenance_annuel', '0').replace(',', '.'))
                except:
                    cout_maintenance = Decimal('0.00')
                
                try:
                    efficacite = Decimal(row.get('efficacite', '0').replace(',', '.'))
                    if efficacite < 0 or efficacite > 100:
                        efficacite = Decimal('0.00')
                except:
                    efficacite = Decimal('0.00')
                
                try:
                    duree = int(row.get('duree_implementation', '30'))
                    if duree < 1:
                        duree = 30
                except:
                    duree = 30
                
                # Créer la mesure
                data = {
                    'technique': technique,
                    'mesure_code': mesure_code,
                    'nom': nom,
                    'description': description,
                    'nature_mesure': nature_mesure,
                    'cout_mise_en_oeuvre': cout_mise_en_oeuvre,
                    'cout_maintenance_annuel': cout_maintenance,
                    'efficacite': efficacite,
                    'duree_implementation': duree,
                    'ressources_necessaires': row.get('ressources_necessaires', None)
                }
                
                mesure = MesureDeControle.objects.create(**data)
                mesures_creees += 1
                
                # Log de l'activité
                log_activity(
                    user, 
                    'IMPORT_MESURE', 
                    'MesureDeControle', 
                    str(mesure.id),
                    {'nom': mesure.nom, 'ligne': row_num}
                )
                
            except Exception as e:
                mesures_errors.append({
                    'ligne': row_num,
                    'erreur': str(e)
                })
        
        return {
            'message': f'Import terminé: {mesures_creees} mesures créées',
            'mesures_creees': mesures_creees,
            'erreurs': mesures_errors,
            'total_erreurs': len(mesures_errors)
        }

    @action(detail=False, methods=['get'])
    def export_mesures(self, request):
        """Export des mesures de contrôle au format CSV ou Excel"""
        
        format_export = request.query_params.get('format', 'csv').lower()
        technique_code = request.query_params.get('technique_code')
        nature_mesure = request.query_params.get('nature_mesure')
        
        # Filtrer les mesures
        queryset = self.get_queryset()
        if technique_code:
            queryset = queryset.filter(technique__technique_code=technique_code)
        if nature_mesure:
            queryset = queryset.filter(nature_mesure=nature_mesure)
        
        if format_export == 'excel' or format_export == 'xlsx':
            return self._export_mesures_to_excel(queryset)
        else:
            return self._export_mesures_to_csv(queryset)

    def _export_mesures_to_csv(self, queryset):
        """Export mesures au format CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mesures_controle.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'technique_code', 'mesure_code', 'nom', 'description', 'nature_mesure',
            'cout_mise_en_oeuvre', 'cout_maintenance_annuel', 'efficacite',
            'duree_implementation', 'ressources_necessaires'
        ])
        
        for mesure in queryset:
            writer.writerow([
                mesure.technique.technique_code,
                mesure.mesure_code,
                mesure.nom,
                mesure.description,
                mesure.nature_mesure,
                float(mesure.cout_mise_en_oeuvre),
                float(mesure.cout_maintenance_annuel),
                float(mesure.efficacite),
                mesure.duree_implementation,
                mesure.ressources_necessaires or ''
            ])
        
        return response

    def _export_mesures_to_excel(self, queryset):
        """Export mesures au format Excel"""
        import pandas as pd
        from django.http import HttpResponse
        import io
        
        # Préparer les données
        data = []
        for mesure in queryset:
            data.append({
                'technique_code': mesure.technique.technique_code,
                'mesure_code': mesure.mesure_code,
                'nom': mesure.nom,
                'description': mesure.description,
                'nature_mesure': mesure.nature_mesure,
                'cout_mise_en_oeuvre': float(mesure.cout_mise_en_oeuvre),
                'cout_maintenance_annuel': float(mesure.cout_maintenance_annuel),
                'efficacite': float(mesure.efficacite),
                'duree_implementation': mesure.duree_implementation,
                'ressources_necessaires': mesure.ressources_necessaires or ''
            })
        
        df = pd.DataFrame(data)
        
        # Créer le fichier Excel en mémoire
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        response = HttpResponse(
            excel_buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="mesures_controle.xlsx"'
        
        return response

    @action(detail=False, methods=['get'])
    def template_import_mesures(self, request):
        """Génère un template Excel pour l'import de mesures de contrôle"""
        import pandas as pd
        from django.http import HttpResponse
        import io
        
        # Données d'exemple
        template_data = [
            {
                'technique_code': 'AC-02.1',
                'mesure_code': 'AC-02.1.01',
                'nom': 'Automated Account Creation',
                'description': 'Mise en place d\'un système automatisé de création de comptes',
                'nature_mesure': 'TECHNIQUE',
                'cout_mise_en_oeuvre': 15000.00,
                'cout_maintenance_annuel': 3000.00,
                'efficacite': 85.50,
                'duree_implementation': 45,
                'ressources_necessaires': 'Administrateur système, Développeur'
            },
            {
                'technique_code': 'AC-02.1',
                'mesure_code': 'AC-02.1.02',
                'nom': 'Account Review Process',
                'description': '',  # Description vide pour montrer que c'est optionnel
                'nature_mesure': '',  # Nature vide pour montrer que c'est optionnel
                'cout_mise_en_oeuvre': '',  # Coût vide pour montrer que c'est optionnel
                'cout_maintenance_annuel': '',
                'efficacite': '',
                'duree_implementation': '',
                'ressources_necessaires': ''
            },
            {
                'technique_code': 'SI-04.1',
                'mesure_code': 'SI-04.1.01',
                'nom': 'Network Monitoring Tools',
                'description': 'Déploiement d\'outils de surveillance réseau',
                'nature_mesure': 'TECHNIQUE',
                'cout_mise_en_oeuvre': 25000.00,
                'cout_maintenance_annuel': 5000.00,
                'efficacite': 90.00,
                'duree_implementation': 60,
                'ressources_necessaires': 'Équipe réseau, Analyste sécurité'
            }
        ]
        
        df = pd.DataFrame(template_data)
        
        # Créer le fichier Excel en mémoire
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        response = HttpResponse(
            excel_buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="template_import_mesures_controle.xlsx"'
        
        return response

# ============================================================================
# GESTION DES IMPLEMENTATIONS
# ============================================================================

class ImplementationMesureViewSet(viewsets.ModelViewSet):
    """Suivi des implémentations de mesures"""
    queryset = ImplementationMesure.objects.select_related(
        'attribut_menace', 'mesure_controle', 'responsable'
    ).all()
    serializer_class = ImplementationMesureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['statut', 'responsable', 'mesure_controle']
    ordering_fields = ['statut', 'pourcentage_avancement', 'date_fin_prevue', 'created_at']
    
    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.statut == 'IMPLEMENTE' and not instance.date_implementation:
            instance.date_implementation = timezone.now()
            instance.save()
        
        log_activity(self.request.user, 'UPDATE_IMPLEMENTATION', 'ImplementationMesure', 
                    str(instance.id), {'statut': instance.statut})
    
    @action(detail=False, methods=['get'])
    def tableau_bord(self, request):
        """Tableau de bord des implémentations"""
        implementations = self.get_queryset()
        
        # Filtres optionnels
        responsable = request.query_params.get('responsable')
        statut = request.query_params.get('statut')
        
        if responsable:
            implementations = implementations.filter(responsable_id=responsable)
        if statut:
            implementations = implementations.filter(statut=statut)
        
        # Statistiques
        stats = {
            'total_implementations': implementations.count(),
            'par_statut': dict(
                implementations.values('statut').annotate(count=Count('id')).values_list('statut', 'count')
            ),
            'en_retard': implementations.filter(
                date_fin_prevue__lt=timezone.now().date(),
                statut__in=['PLANIFIE', 'EN_COURS']
            ).count(),
            'completees_ce_mois': implementations.filter(
                date_implementation__month=timezone.now().month,
                statut='IMPLEMENTE'
            ).count()
        }
        
        return Response({
            'statistiques': stats,
            'implementations_critiques': ImplementationMesureSerializer(
                implementations.filter(statut='EN_COURS').order_by('date_fin_prevue')[:10],
                many=True
            ).data
        })

# ============================================================================
# CATALOGUES GLOBAUX
# ============================================================================

# ============================================================================
# MODIFIER: TechniqueViewSet
# ============================================================================

class TechniqueViewSet(viewsets.ModelViewSet):
    """Gestion des techniques d'implémentation (maintenant indépendantes)"""
    queryset = Technique.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_technique', 'complexite', 'famille', 'priorite']
    search_fields = ['technique_code', 'nom', 'description']
    ordering_fields = ['technique_code', 'nom', 'complexite', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TechniqueListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TechniqueCreateSerializer
        return TechniqueSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'Technique', str(instance.id), 
                    {'technique_code': instance.technique_code, 'nom': instance.nom})
    
    @action(detail=True, methods=['get'])
    def menaces_traitees(self, request, pk=None):
        """Liste les menaces traitées par cette technique via ses mesures"""
        technique = self.get_object()
        
        # Récupérer toutes les menaces traitées via les mesures
        menaces_ids = set()
        mesures_par_menace = {}
        
        for mesure in technique.mesures_controle.all():
            for menace_mesure in mesure.menaces_traitees.select_related('menace').all():
                menace = menace_mesure.menace
                if menace.id not in menaces_ids:
                    menaces_ids.add(menace.id)
                    mesures_par_menace[menace.id] = []
                
                mesures_par_menace[menace.id].append({
                    'mesure_code': mesure.mesure_code,
                    'mesure_nom': mesure.nom,
                    'efficacite': float(menace_mesure.efficacite),
                    'statut_conformite': menace_mesure.statut_conformite
                })
        
        # Récupérer les objets menaces
        menaces = Menace.objects.filter(id__in=menaces_ids)
        
        result = []
        for menace in menaces:
            result.append({
                'menace': MenaceListSerializer(menace).data,
                'mesures': mesures_par_menace[menace.id]
            })
        
        return Response({
            'technique': TechniqueListSerializer(technique).data,
            'menaces_traitees': result,
            'total_menaces': len(result)
        })


    @action(detail=False, methods=['post'])
    def import_techniques(self, request):
        """
        Importe des techniques depuis un fichier Excel
        Format attendu: capability_id, attack_object_id, attack_object_name
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        # Vérifier le type de fichier
        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            return Response(
                {'error': 'Format de fichier non supporté. Utilisez Excel (.xlsx, .xls) ou CSV'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Lire le fichier selon le format
            if file.name.endswith('.csv'):
                import csv
                import io
                decoded_file = file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(decoded_file))
                data = list(csv_reader)
            else:
                # Excel
                import pandas as pd
                df = pd.read_excel(file)
                data = df.to_dict('records')
            
            # Compteurs
            created_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            # Traiter chaque ligne
            with transaction.atomic():
                for idx, row in enumerate(data, start=1):
                    try:
                        # Extraire les données
                        # Le fichier contient: capability_id (ex: CM-03), attack_object_id (ex: T1666), attack_object_name
                        technique_code = row.get('attack_object_id', '').strip()
                        nom = row.get('attack_object_name', '').strip()
                        famille = row.get('capability_id', '').strip()  # On utilise capability_id comme famille
                        
                        if not technique_code or not nom:
                            skipped_count += 1
                            errors.append(f"Ligne {idx}: Données manquantes (technique_code ou nom)")
                            continue
                        
                        # Vérifier si la technique existe déjà
                        if Technique.objects.filter(technique_code=technique_code).exists():
                            skipped_count += 1
                            errors.append(f"Ligne {idx}: Technique {technique_code} existe déjà")
                            continue
                        
                        # Déterminer le type de technique basé sur le code
                        # Les techniques MITRE ATT&CK sont généralement de type TECHNIQUE
                        type_technique = 'TECHNIQUE'
                        
                        # Déterminer la complexité basée sur le code (heuristique simple)
                        # Les techniques avec sous-techniques (ex: T1556.009) sont souvent plus complexes
                        if '.' in technique_code:
                            complexite = 'ELEVE'
                        else:
                            complexite = 'MOYEN'
                        
                        # Déterminer la priorité basée sur le code famille (capability_id)
                        # AC (Access Control), IA (Identification and Authentication) = P1
                        # SC (System and Communications Protection), SI (System and Information Integrity) = P1
                        # CM (Configuration Management), CP (Contingency Planning) = P2
                        # Autres = P2
                        priorite_mapping = {
                            'AC': 'P1', 'IA': 'P1', 'SC': 'P1', 'SI': 'P1',
                            'CM': 'P2', 'CP': 'P2', 'MA': 'P2', 'PE': 'P2',
                            'PS': 'P3', 'SA': 'P3', 'CA': 'P3'
                        }
                        priorite = priorite_mapping.get(famille.split('-')[0] if '-' in famille else famille, 'P2')
                        
                        # Créer la technique
                        Technique.objects.create(
                            technique_code=technique_code,
                            nom=nom,
                            description=f"Technique MITRE ATT&CK: {nom}",
                            type_technique=type_technique,
                            complexite=complexite,
                            famille=famille,
                            priorite=priorite
                        )
                        
                        created_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Ligne {idx}: {str(e)}")
            
            # Préparer la réponse
            response_data = {
                'success': True,
                'message': f'Import terminé: {created_count} créées, {skipped_count} ignorées, {error_count} erreurs',
                'details': {
                    'created': created_count,
                    'skipped': skipped_count,
                    'errors': error_count,
                    'total_processed': len(data)
                }
            }
            
            if errors and len(errors) <= 50:  # Limiter le nombre d'erreurs retournées
                response_data['error_details'] = errors[:50]
            
            log_activity(
                request.user,
                'IMPORT_TECHNIQUES',
                'Technique',
                '',
                {
                    'created': created_count,
                    'skipped': skipped_count,
                    'errors': error_count
                }
            )
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import: {str(e)}")
            return Response(
                {'error': f'Erreur lors de l\'import: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

# api/views.py - Modification de MenaceViewSet


# ============================================================================
# NOUVEAU VIEWSET: MenaceMesureViewSet
# ============================================================================

class MenaceViewSet(viewsets.ModelViewSet):
    """Catalogue global des menaces avec mesures directement liées"""
    queryset = Menace.objects.prefetch_related(
        'attributs_impactes__attribut_securite__actif__architecture',
        'mesures_controle__mesure_controle__technique'
    ).all().order_by('nom')
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_menace', 'severite']
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'severite', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MenaceListSerializer
        return MenaceSerializer
    
    @action(detail=True, methods=['get'])
    def vue_complete(self, request, pk=None):
        """
        Vue complète d'une menace avec toutes ses relations:
        - Mesures de contrôle (via MenaceMesure)
        - Techniques (via mesures)
        - Attributs impactés
        - Métriques consolidées
        
        GET /api/v1/menaces/{id}/vue_complete/
        """
        menace = self.get_object()
        
        # Serializer de base avec relations préchargées
        menace_data = MenaceSerializer(menace).data
        
        # Enrichir avec les techniques et mesures organisées
        techniques_map = {}
        mesures_list = []
        
        # Parcourir les MenaceMesure pour extraire techniques et mesures
        for menace_mesure in menace.mesures_controle.select_related(
            'mesure_controle__technique'
        ).prefetch_related(
            'mesure_controle__technique__mesures_controle'
        ).all():
            
            mesure = menace_mesure.mesure_controle
            technique = mesure.technique
            
            # Ajouter la technique si pas encore présente
            if technique.technique_code not in techniques_map:
                techniques_map[technique.technique_code] = {
                    'id': str(technique.id),
                    'technique_code': technique.technique_code,
                    'nom': technique.nom,
                    'description': technique.description,
                    'type_technique': technique.type_technique,
                    'complexite': technique.complexite,
                    'famille': technique.famille,
                    'priorite': technique.priorite,
                    'efficacite': float(mesure.efficacite) if mesure.efficacite else 0,
                    'mesures_count': 0,
                    'mesures_controle': []
                }
            
            # Ajouter la mesure à la technique
            mesure_data = {
                'id': str(mesure.id),
                'mesure_code': mesure.mesure_code,
                'nom': mesure.nom,
                'description': mesure.description,
                'nature_mesure': mesure.nature_mesure,
                'efficacite': float(mesure.efficacite) if mesure.efficacite else 0,
                'cout_mise_en_oeuvre': float(mesure.cout_mise_en_oeuvre) if mesure.cout_mise_en_oeuvre else 0,
                'cout_maintenance_annuel': float(mesure.cout_maintenance_annuel) if mesure.cout_maintenance_annuel else 0,
                'cout_total_3_ans': mesure.cout_total_3_ans,
                'duree_implementation': mesure.duree_implementation,
                'ressources_necessaires': mesure.ressources_necessaires,
                'technique_code': technique.technique_code,
                'technique_nom': technique.nom,
                'created_at': mesure.created_at.isoformat() if mesure.created_at else None
            }
            
            techniques_map[technique.technique_code]['mesures_controle'].append(mesure_data)
            techniques_map[technique.technique_code]['mesures_count'] += 1
            mesures_list.append(mesure_data)
        
        # Convertir le dictionnaire de techniques en liste
        techniques_list = list(techniques_map.values())
        
        # Calculer l'efficacité moyenne des techniques
        for technique in techniques_list:
            if technique['mesures_count'] > 0:
                efficacite_moyenne = sum(
                    m['efficacite'] for m in technique['mesures_controle']
                ) / technique['mesures_count']
                technique['efficacite'] = round(efficacite_moyenne, 2)
        
        # Ajouter les données enrichies
        menace_data['techniques'] = techniques_list
        menace_data['mesures_controle_detaillees'] = mesures_list
        
        # Métriques consolidées
        menace_data['metriques'] = {
            'total_techniques': len(techniques_list),
            'total_mesures': len(mesures_list),
            'efficacite_moyenne': round(
                sum(m['efficacite'] for m in mesures_list) / len(mesures_list), 2
            ) if mesures_list else 0,
            'cout_total_mise_en_oeuvre': sum(
                m['cout_mise_en_oeuvre'] for m in mesures_list
            ),
            'cout_total_3_ans': sum(
                m['cout_total_3_ans'] for m in mesures_list
            )
        }
        
        # Log de l'activité
        log_activity(
            request.user,
            'VIEW_MENACE_COMPLETE',
            'Menace',
            str(menace.id),
            {'nom': menace.nom}
        )
        
        return Response(menace_data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def mesures_disponibles(self, request, pk=None):
        """Recherche les mesures de contrôle disponibles (non encore associées à cette menace)"""
        menace = self.get_object()
        
        search_query = request.query_params.get('search', '').strip()
        technique_code = request.query_params.get('technique_code', '')
        nature_mesure = request.query_params.get('nature_mesure', '')
        
        # Récupérer les IDs des mesures déjà associées
        mesures_associees_ids = MenaceMesure.objects.filter(menace=menace).values_list('mesure_controle_id', flat=True)
        
        # Rechercher dans toutes les mesures
        queryset = MesureDeControle.objects.exclude(id__in=mesures_associees_ids)
        
        # Filtres de recherche
        if search_query:
            queryset = queryset.filter(
                Q(mesure_code__icontains=search_query) |
                Q(nom__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if technique_code:
            queryset = queryset.filter(technique__technique_code=technique_code)
        
        if nature_mesure:
            queryset = queryset.filter(nature_mesure=nature_mesure)
        
        # Limiter les résultats pour la performance
        queryset = queryset.select_related('technique').order_by('mesure_code')[:20]
        
        # Sérialiser les résultats
        mesures_data = []
        for mesure in queryset:
            mesures_data.append({
                'id': mesure.id,
                'mesure_code': mesure.mesure_code,
                'nom': mesure.nom,
                'nature_mesure': mesure.nature_mesure,
                'efficacite': float(mesure.efficacite),
                'cout_total_3_ans': mesure.cout_total_3_ans,
                'description': mesure.description[:200] + '...' if len(mesure.description) > 200 else mesure.description,
                'technique': {
                    'code': mesure.technique.technique_code,
                    'nom': mesure.technique.nom,
                    'famille': mesure.technique.famille
                },
                'created_at': mesure.created_at.isoformat()
            })
        
        return Response({
            'results': mesures_data,
            'count': len(mesures_data),
            'menace_id': str(menace.id),
            'search_query': search_query
        })
    
    @action(detail=True, methods=['post'])
    def associer_mesure(self, request, pk=None):
        """Associe une mesure de contrôle à cette menace"""
        menace = self.get_object()
        mesure_controle_id = request.data.get('mesure_controle_id')
        efficacite = request.data.get('efficacite', 0)
        statut_conformite = request.data.get('statut_conformite', 'NON_CONFORME')
        commentaires = request.data.get('commentaires', '')
        
        if not mesure_controle_id:
            return Response(
                {'error': 'mesure_controle_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            mesure = MesureDeControle.objects.get(id=mesure_controle_id)
        except MesureDeControle.DoesNotExist:
            return Response(
                {'error': 'Mesure de contrôle non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier si l'association existe déjà
        if MenaceMesure.objects.filter(menace=menace, mesure_controle=mesure).exists():
            return Response(
                {'error': 'Cette mesure est déjà associée à cette menace'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer l'association
        association = MenaceMesure.objects.create(
            menace=menace,
            mesure_controle=mesure,
            efficacite=efficacite,
            statut_conformite=statut_conformite,
            commentaires=commentaires
        )
        
        log_activity(
            request.user,
            'ASSOCIATE_MEASURE',
            'Menace',
            str(menace.id),
            {'mesure_nom': mesure.nom}
        )
        
        serializer = MenaceMesureSerializer(association)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class MenaceMesureViewSet(viewsets.ModelViewSet):
    """Gestion des associations directes menace-mesure"""
    queryset = MenaceMesure.objects.select_related('menace', 'mesure_controle').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['menace', 'mesure_controle', 'statut_conformite']
    ordering_fields = ['efficacite', 'statut_conformite', 'created_at']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MenaceMesureCreateSerializer
        return MenaceMesureSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'MenaceMesure', str(instance.id), 
                    {'mesure_code': instance.mesure_controle.mesure_code})
    
    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'UPDATE', 'MenaceMesure', str(instance.id), 
                    {'mesure_code': instance.mesure_controle.mesure_code})
    
    @action(detail=False, methods=['post'])
    def associer_menace_mesure(self, request):
        """Associe une mesure de contrôle à une menace"""
        menace_id = request.data.get('menace_id')
        mesure_controle_id = request.data.get('mesure_controle_id')
        efficacite = request.data.get('efficacite', 0)
        statut_conformite = request.data.get('statut_conformite', 'NON_CONFORME')
        commentaires = request.data.get('commentaires', '')
        
        if not all([menace_id, mesure_controle_id]):
            return Response(
                {'error': 'menace_id et mesure_controle_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            menace = Menace.objects.get(id=menace_id)
            mesure = MesureDeControle.objects.get(id=mesure_controle_id)
        except (Menace.DoesNotExist, MesureDeControle.DoesNotExist) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier si l'association existe déjà
        if MenaceMesure.objects.filter(menace=menace, mesure_controle=mesure).exists():
            return Response(
                {'error': 'Cette association existe déjà'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer l'association
        association = MenaceMesure.objects.create(
            menace=menace,
            mesure_controle=mesure,
            efficacite=efficacite,
            statut_conformite=statut_conformite,
            commentaires=commentaires
        )
        
        log_activity(
            request.user,
            'ASSOCIATE_MENACE_MESURE',
            'MenaceMesure',
            str(association.id),
            {
                'menace_nom': menace.nom,
                'mesure_nom': mesure.nom
            }
        )
        
        serializer = MenaceMesureSerializer(association)
        return Response(serializer.data, status=status.HTTP_201_CREATED)





class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Consultation des utilisateurs"""
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email']

class LogActiviteViewSet(viewsets.ReadOnlyModelViewSet):
    """Consultation des logs d'activité"""
    queryset = LogActivite.objects.select_related('utilisateur').all().order_by('-created_at')
    serializer_class = LogActiviteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['utilisateur', 'action', 'objet_type']
    ordering_fields = ['created_at']

# ============================================================================
# DASHBOARD ET STATISTIQUES
# ============================================================================

class DashboardViewSet(viewsets.ViewSet):
    """Dashboard avec métriques globales"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def statistiques_globales(self, request):
        """Statistiques globales du système"""
        
        # Compteurs principaux
        stats = {
            'total_architectures': Architecture.objects.count(),
            'total_actifs': Actif.objects.count(),
            'total_attributs': AttributSecurite.objects.count(),
            'total_menaces': Menace.objects.count(),
            
            'total_techniques': Technique.objects.count(),
            'total_mesures': MesureDeControle.objects.count(),
        }
        
        # Calculs de risques financiers
        architectures = Architecture.objects.all()
        risque_financier_total = sum(arch.risque_financier_total for arch in architectures)
        budget_risque_total = sum(float(arch.risque_tolere) for arch in architectures)
        architectures_hors_tolerance = len([arch for arch in architectures if arch.risque_depasse_tolerance])
        
        stats.update({
            'risque_financier_total': round(risque_financier_total, 2),
            'budget_risque_total': round(budget_risque_total, 2),
            'architectures_hors_tolerance': architectures_hors_tolerance
        })
        
        # Conformité
       
        
        implementations_en_cours = ImplementationMesure.objects.filter(
            statut__in=['PLANIFIE', 'EN_COURS']
        ).count()
        
        stats.update({
            
            'implementations_en_cours': implementations_en_cours
        })
        
        # Répartitions
        stats['actifs_par_criticite'] = dict(
            Actif.objects.values('criticite').annotate(count=Count('id')).values_list('criticite', 'count')
        )
        
        stats['menaces_par_severite'] = dict(
            Menace.objects.values('severite').annotate(count=Count('id')).values_list('severite', 'count')
        )
        
        stats['implementations_par_statut'] = dict(
            ImplementationMesure.objects.values('statut').annotate(count=Count('id')).values_list('statut', 'count')
        )
        
        stats['risque_par_architecture'] = {
            arch.nom: round(arch.risque_financier_total, 2) 
            for arch in architectures
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def architectures_hors_tolerance(self, request):
        """Architectures qui dépassent leur seuil de tolérance"""
        architectures = Architecture.objects.all()
        architectures_critiques = []
        
        for arch in architectures:
            if arch.risque_depasse_tolerance:
                architectures_critiques.append({
                    'architecture': ArchitectureListSerializer(arch).data,
                    'depassement_montant': round(arch.risque_financier_total - float(arch.risque_tolere), 2),
                    'depassement_pourcentage': round(
                        ((arch.risque_financier_total - float(arch.risque_tolere)) / float(arch.risque_tolere)) * 100, 2
                    ) if float(arch.risque_tolere) > 0 else 100
                })
        
        # Trier par montant de dépassement décroissant
        architectures_critiques.sort(key=lambda x: x['depassement_montant'], reverse=True)
        
        return Response(architectures_critiques)
    
    @action(detail=False, methods=['get'])
    def analyse_cout_benefice(self, request):
        """Analyse coût-bénéfice globale"""
        
        # Calcul du coût total des implémentations
        implementations = ImplementationMesure.objects.filter(
            statut__in=['PLANIFIE', 'EN_COURS', 'IMPLEMENTE']
        ).select_related('mesure_controle')
        
        cout_total_implementations = sum(
            impl.mesure_controle.cout_total_3_ans 
            for impl in implementations
        )
        
        # Calcul de la réduction de risque attendue
        reduction_risque_attendue = 0
        for impl in implementations:
            if impl.statut in ['IMPLEMENTE', 'VERIFIE']:
                risque_initial = impl.attribut_menace.niveau_risque * float(impl.attribut_menace.cout_impact) / 100
                reduction_risque_attendue += risque_initial * (float(impl.mesure_controle.efficacite) / 100)
        
        analyse = {
            'cout_total_implementations': round(cout_total_implementations, 2),
            'reduction_risque_attendue': round(reduction_risque_attendue, 2),
            'roi_securite': round(
                (reduction_risque_attendue - cout_total_implementations) / cout_total_implementations * 100, 2
            ) if cout_total_implementations > 0 else 0,
            'ratio_cout_benefice': round(
                reduction_risque_attendue / cout_total_implementations, 2
            ) if cout_total_implementations > 0 else 0,
            'implementations_analysees': implementations.count()
        }
        
        return Response(analyse)
    
# ============================================================================
# MODÈLES DE DONNÉES Optimisation
# ============================================================================

class OptimizationViewSet(viewsets.ViewSet):
    """ViewSet pour les opérations d'optimisation de sécurité"""
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._optimization_service = None  # Instancié à la demande
    
    @property
    def optimization_service(self):
        """Instancie le service seulement quand nécessaire"""
        if self._optimization_service is None:
            from .services.optimization_service import SecurityOptimizationService
            self._optimization_service = SecurityOptimizationService()
        return self._optimization_service
    
    @action(detail=False, methods=['post'])
    def optimize_architecture(self, request):
        """
        Optimise la sécurité d'une architecture
        POST /api/optimization/optimize_architecture/
        """
        try:
            architecture_id = request.data.get('architecture_id')
            budget_max = request.data.get('budget_max')
            include_implementation_plan = request.data.get('include_implementation_plan', False)
            
            if not architecture_id:
                return Response(
                    {'error': 'architecture_id requis'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convertir budget_max en Decimal si fourni
            if budget_max is not None:
                try:
                    budget_max = Decimal(str(budget_max))
                except:
                    return Response(
                        {'error': 'budget_max doit être un nombre valide'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Exécuter l'optimisation
            from api.services.optimization_service import SecurityOptimizationService
            
            optimizer = SecurityOptimizationService()
            result = optimizer.optimize_architecture_security(
                architecture_id=architecture_id,
                budget_max=budget_max
            )
            
            # ✅ CORRECTION : Convertir les Decimal en float pour la sérialisation JSON
            def convert_decimals(obj):
                """Convertit récursivement les Decimal en float"""
                if isinstance(obj, dict):
                    return {key: convert_decimals(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                else:
                    return obj
            
            result = convert_decimals(result)
            
            # Créer plan d'implémentation si demandé
            if include_implementation_plan and result.get('global_optimization'):
                implementation_result = optimizer.create_implementation_plan(
                    optimization_result=result,
                    responsable_id=request.user.id if request.user.is_authenticated else None
                )
                result['implementation_plan'] = implementation_result
            
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['post'])
    def optimize_attribut(self, request):
        """
        Optimise la sélection de mesures pour un attribut de sécurité spécifique
        
        POST /api/optimization/optimize_attribut/
        {
            "attribut_securite_id": "uuid",
            "budget_max": 10000.00,  // optionnel
            "create_implementations": true,  // optionnel
            "responsable_id": "uuid"  // optionnel
        }
        """
        serializer = QuickOptimizationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        attribut_id = str(data['attribut_securite_id'])
        
        try:
            # Vérifier que l'attribut existe
            try:
                attribut = AttributSecurite.objects.get(id=attribut_id)
            except AttributSecurite.DoesNotExist:
                return Response(
                    {'error': f'Attribut de sécurité {attribut_id} non trouvé'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Lancer l'optimisation
            optimization_result = self.optimization_service._optimize_attribut_security(attribut)
            
            # Créer les implémentations si demandé et si l'optimisation a réussi
            if (data.get('create_implementations', False) and 
                optimization_result.get('status') == 'optimal'):
                
                # Simuler le format attendu par create_implementation_plan
                formatted_result = {
                    'optimization_type': 'individual_by_attribute',
                    'results': [{
                        'attribut': attribut,
                        'result': optimization_result
                    }]
                }
                
                implementation_plan = self.optimization_service.create_implementation_plan(
                    optimization_result=formatted_result,
                    responsable_id=str(data['responsable_id']) if data.get('responsable_id') else None
                )
                optimization_result['implementation_plan'] = implementation_plan
            
            # Log de l'activité
            log_activity(
                request.user, 
                'OPTIMIZATION_ATTRIBUT', 
                'AttributSecurite', 
                attribut_id,
                {
                    'status': optimization_result.get('status'),
                    'measures_count': optimization_result.get('measures_count', 0),
                    'total_cost': optimization_result.get('total_cost', 0)
                }
            )
            
            return Response(optimization_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de l'attribut {attribut_id}: {str(e)}")
            return Response(
                {'error': f'Erreur interne: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_implementation_plan(self, request):
        """
        Crée un plan d'implémentation à partir de résultats d'optimisation
        
        POST /api/optimization/create_implementation_plan/
        {
            "optimization_result": {...},  // Résultat d'optimisation complet
            "responsable_id": "uuid"  // optionnel
        }
        """
        optimization_result = request.data.get('optimization_result')
        responsable_id = request.data.get('responsable_id')
        
        if not optimization_result:
            return Response(
                {'error': 'optimization_result requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            implementation_plan = self.optimization_service.create_implementation_plan(
                optimization_result=optimization_result,
                responsable_id=responsable_id
            )
            
            # Log de l'activité
            log_activity(
                request.user, 
                'CREATE_IMPLEMENTATION_PLAN', 
                'Architecture', 
                optimization_result.get('architecture_id', 'unknown'),
                {
                    'implementations_created': implementation_plan.get('implementations_created', 0),
                    'responsable_id': responsable_id
                }
            )
            
            serializer = ImplementationPlanSerializer(implementation_plan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du plan d'implémentation: {str(e)}")
            return Response(
                {'error': f'Erreur interne: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def diagnostic(self, request):
        """
        Diagnostic détaillé pour comprendre pourquoi l'optimisation échoue
        
        POST /api/v1/optimization/diagnostic/
        {
            "architecture_id": "uuid"
        }
        """
        architecture_id = request.data.get('architecture_id')
        
        if not architecture_id:
            return Response({'error': 'architecture_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from .services.optimization_service import SecurityOptimizationService
            from .models import Architecture
            
            architecture = Architecture.objects.get(id=architecture_id)
            service = SecurityOptimizationService()
            
            diagnostic_info = {
                'architecture': {
                    'id': str(architecture.id),
                    'nom': architecture.nom,
                    'actifs_count': architecture.actifs.count()
                },
                'solver': {
                    'available': service.solver is not None,
                    'name': service.solver_name,
                    'io_mode': service.solver_io
                },
                'actifs': []
            }
            
            # Pour chaque actif
            for actif in architecture.actifs.all():
                actif_info = {
                    'nom': actif.nom,
                    'attributs': []
                }
                
                # Pour chaque attribut
                for attribut in actif.attributs_securite.all():
                    attribut_info = {
                        'type': attribut.type_attribut,
                        'cout_compromission': float(attribut.cout_compromission),
                        'menaces_count': attribut.menaces.count(),
                        'menaces': []
                    }
                    
                    # Pour chaque menace
                    for attr_menace in attribut.menaces.all():
                        menace = attr_menace.menace
                        menace_info = {
                            'nom': menace.nom,
                            'probabilite': float(attr_menace.probabilite),
                            'cout_impact': float(attr_menace.cout_impact),
                            'controles_count': menace.controles_nist.count(),
                            'mesures_disponibles': 0
                        }
                        
                        # Compter les mesures disponibles
                        for menace_controle in menace.controles_nist.all():
                            for technique in menace_controle.controle_nist.techniques.all():
                                menace_info['mesures_disponibles'] += technique.mesures_controle.count()
                        
                        attribut_info['menaces'].append(menace_info)
                    
                    # Tester l'optimisation pour cet attribut
                    if attribut.menaces.exists():
                        result = service._optimize_attribut_security(attribut)
                        attribut_info['optimization_result'] = {
                            'status': result.get('status'),
                            'message': result.get('message', result.get('error', '')),
                            'measures_count': result.get('measures_count', 0),
                            'total_cost': result.get('total_cost', 0)
                        }
                    else:
                        attribut_info['optimization_result'] = {
                            'status': 'no_menaces',
                            'message': 'Aucune menace associée'
                        }
                    
                    actif_info['attributs'].append(attribut_info)
                
                diagnostic_info['actifs'].append(actif_info)
            
            return Response(diagnostic_info, status=status.HTTP_200_OK)
            
        except Architecture.DoesNotExist:
            return Response({'error': 'Architecture non trouvée'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Erreur diagnostic: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Retourne le statut du service d'optimisation
        
        GET /api/optimization/status/
        """
        try:
            # Vérifier la disponibilité du solveur
            solver_available = True
            solver_name = 'bonmin'
            
            try:
                test_service = SecurityOptimizationService()
                if hasattr(test_service.solver, 'name'):
                    solver_name = test_service.solver.name()
            except Exception as e:
                solver_available = False
                logger.warning(f"Solveur non disponible: {e}")
            
            # Statistiques d'utilisation (basées sur les logs)
            optimization_logs = LogActivite.objects.filter(
                action__in=['OPTIMIZATION_RUN', 'OPTIMIZATION_ATTRIBUT']
            )
            
            total_optimizations = optimization_logs.count()
            architectures_optimized = optimization_logs.filter(
                action='OPTIMIZATION_RUN'
            ).values('objet_id').distinct().count()
            
            last_optimization = optimization_logs.first()
            
            status_data = {
                'solver_available': solver_available,
                'solver_name': solver_name,
                'last_optimization_time': last_optimization.created_at if last_optimization else None,
                'total_optimizations_run': total_optimizations,
                'architectures_optimized': architectures_optimized
            }
            
            serializer = OptimizationStatusSerializer(status_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut d'optimisation: {str(e)}")
            return Response(
                {'error': f'Erreur interne: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def optimization_history(self, request):
        """
        Historique des optimisations
        
        GET /api/optimization/optimization_history/
        """
        try:
            # Filtres optionnels
            architecture_id = request.query_params.get('architecture_id')
            limit = int(request.query_params.get('limit', 20))
            
            # Récupérer les logs d'optimisation
            logs_query = LogActivite.objects.filter(
                action__in=['OPTIMIZATION_RUN', 'OPTIMIZATION_ATTRIBUT']
            ).select_related('utilisateur').order_by('-created_at')
            
            if architecture_id:
                logs_query = logs_query.filter(objet_id=architecture_id)
            
            logs = logs_query[:limit]
            
            # Formatter l'historique
            history = []
            for log in logs:
                details = log.details or {}
                history.append({
                    'id': log.id,
                    'date': log.created_at,
                    'utilisateur': log.utilisateur.username if log.utilisateur else 'Système',
                    'action': log.action,
                    'objet_type': log.objet_type,
                    'objet_id': log.objet_id,
                    'optimization_type': details.get('optimization_type'),
                    'successful_optimizations': details.get('successful_optimizations'),
                    'budget_max': details.get('budget_max'),
                    'total_cost': details.get('total_cost'),
                    'measures_count': details.get('measures_count')
                })
            
            return Response({
                'count': len(history),
                'results': history
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique: {str(e)}")
            return Response(
                {'error': f'Erreur interne: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )