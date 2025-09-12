# api/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from decimal import Decimal
import logging

from .models import (
    TypeActif, Architecture, Actif, AttributSecurite, Menace, AttributMenace,
    ControleNIST, MenaceControle, Technique, MesureDeControle, 
    ImplementationMesure, LogActivite
)
from .serializers import (
    TypeActifSerializer, ArchitectureListSerializer, ArchitectureSerializer,
    ArchitectureCreateSerializer, ActifListSerializer, ActifSerializer, ActifCreateSerializer,
    AttributSecuriteListSerializer, AttributSecuriteSerializer, AttributSecuriteCreateSerializer,
    AttributMenaceSerializer, AttributMenaceCreateSerializer,MenaceCreateSerializer,
    MenaceControleSerializer, MenaceControleCreateSerializer,
    TechniqueSerializer, TechniqueCreateSerializer,
    MesureDeControleSerializer, MesureDeControleCreateSerializer,
    ImplementationMesureSerializer, MenaceListSerializer, MenaceSerializer, 
    ControleNISTListSerializer, ControleNISTSerializer,
    LogActiviteSerializer, UserSerializer, DashboardStatsSerializer
)
from .utils import log_activity

logger = logging.getLogger(__name__)

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
# NIVEAU 5: GESTION DES CONTROLES NIST
# ============================================================================

class MenaceControleViewSet(viewsets.ModelViewSet):
    """Gestion des associations menace-contrôle NIST"""
    queryset = MenaceControle.objects.select_related('menace', 'controle_nist').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['menace', 'controle_nist', 'statut_conformite']
    ordering_fields = ['efficacite', 'statut_conformite', 'created_at']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MenaceControleCreateSerializer
        return MenaceControleSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'MenaceControle', str(instance.id), 
                    {'controle_code': instance.controle_nist.code})

# ============================================================================
# NIVEAU 6: GESTION DES TECHNIQUES
# ============================================================================

class TechniqueViewSet(viewsets.ModelViewSet):
    """Gestion des techniques d'implémentation"""
    queryset = Technique.objects.select_related('controle_nist').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['controle_nist', 'type_technique', 'complexite']
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'complexite', 'created_at']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TechniqueCreateSerializer
        return TechniqueSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'Technique', str(instance.id), 
                    {'nom': instance.nom})
    
    @action(detail=True, methods=['post'])
    def ajouter_mesure(self, request, pk=None):
        """Ajoute une nouvelle mesure de contrôle à cette technique"""
        technique = self.get_object()
        data = request.data.copy()
        data['technique'] = str(technique.id)
        
        serializer = MesureDeControleCreateSerializer(data=data)
        if serializer.is_valid():
            mesure = serializer.save()
            log_activity(request.user, 'ADD_MESURE', 'Technique', str(technique.id),
                        {'mesure_nom': mesure.nom})
            return Response(MesureDeControleSerializer(mesure).data, 
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============================================================================
# NIVEAU 7: GESTION DES MESURES DE CONTROLE
# ============================================================================

class MesureDeControleViewSet(viewsets.ModelViewSet):
    """Gestion des mesures de contrôle"""
    queryset = MesureDeControle.objects.select_related('technique', 'technique__controle_nist').all()
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

class TypeActifViewSet(viewsets.ModelViewSet):
    """Gestion des types d'actifs"""
    queryset = TypeActif.objects.all().order_by('nom')
    serializer_class = TypeActifSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'description']
    ordering_fields = ['nom', 'created_at']

# api/views.py - Modification de MenaceViewSet

class MenaceViewSet(viewsets.ModelViewSet):
    """Catalogue global des menaces avec vue consolidée"""
    # Optimiser le queryset pour précharger les relations nécessaires
    queryset = Menace.objects.prefetch_related(
        'attributs_impactes__attribut_securite__actif__architecture',
        'controles_nist__controle_nist__techniques__mesures_controle'
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
        """Vue complète d'une menace avec tous ses contrôles, techniques et mesures"""
        menace = self.get_object()
        serializer = MenaceSerializer(menace)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'CREATE', 'Menace', str(instance.id), 
                    {'nom': instance.nom})
    
    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, 'UPDATE', 'Menace', str(instance.id), 
                    {'nom': instance.nom})
    
    @action(detail=True, methods=['post'])
    def definir_contexte_principal(self, request, pk=None):
        """Définit le contexte principal (attribut de sécurité) pour cette menace"""
        menace = self.get_object()
        attribut_securite_id = request.data.get('attribut_securite_id')
        
        if not attribut_securite_id:
            return Response(
                {'error': 'attribut_securite_id requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attribut = AttributSecurite.objects.get(id=attribut_securite_id)
        except AttributSecurite.DoesNotExist:
            return Response(
                {'error': 'Attribut de sécurité non trouvé'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier que cette menace est bien associée à cet attribut
        if not menace.attributs_impactes.filter(attribut_securite=attribut).exists():
            return Response(
                {'error': 'Cette menace n\'est pas associée à cet attribut de sécurité'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        menace.attribut_securite_principal = attribut
        menace.save()
        
        log_activity(
            request.user, 
            'SET_MAIN_CONTEXT', 
            'Menace', 
            str(menace.id),
            {
                'attribut_securite_id': str(attribut.id),
                'actif_nom': attribut.actif.nom,
                'architecture_nom': attribut.actif.architecture.nom
            }
        )
        
        return Response({
            'message': 'Contexte principal défini avec succès',
            'contexte': menace.contexte_hierarchique_complet
        })
    
    @action(detail=True, methods=['get'])
    def contextes_disponibles(self, request, pk=None):
        """Retourne tous les contextes (attributs de sécurité) disponibles pour cette menace"""
        menace = self.get_object()
        
        contextes = []
        for attr_menace in menace.attributs_impactes.select_related(
            'attribut_securite__actif__architecture'
        ).all():
            attribut = attr_menace.attribut_securite
            contextes.append({
                'attribut_securite_id': str(attribut.id),
                'est_principal': attribut == menace.attribut_securite_principal,
                'architecture': {
                    'id': str(attribut.actif.architecture.id),
                    'nom': attribut.actif.architecture.nom
                },
                'actif': {
                    'id': str(attribut.actif.id),
                    'nom': attribut.actif.nom,
                    'criticite': attribut.actif.criticite
                },
                'attribut': {
                    'type_attribut': attribut.type_attribut,
                    'priorite': attribut.priorite
                },
                'risque_dans_ce_contexte': {
                    'probabilite': float(attr_menace.probabilite),
                    'impact': float(attr_menace.impact),
                    'cout_impact': float(attr_menace.cout_impact),
                    'risque_financier': attr_menace.risque_financier,
                    'niveau_risque': attr_menace.niveau_risque
                }
            })
        
        return Response({
            'menace': menace.nom,
            'contexte_principal_actuel': menace.contexte_hierarchique_complet,
            'contextes_disponibles': contextes,
            'total_contextes': len(contextes)
        })
    
    @action(detail=False, methods=['get'])
    def par_architecture(self, request):
        """Menaces groupées par architecture"""
        architecture_id = request.query_params.get('architecture_id')
        
        if architecture_id:
            # Filtrer par architecture spécifique
            menaces = self.get_queryset().filter(
                attribut_securite_principal__actif__architecture_id=architecture_id
            )
        else:
            # Toutes les menaces avec contexte
            menaces = self.get_queryset().filter(
                attribut_securite_principal__isnull=False
            )
        
        # Grouper par architecture
        menaces_par_arch = {}
        for menace in menaces:
            arch_nom = menace.architecture_nom
            if arch_nom not in menaces_par_arch:
                menaces_par_arch[arch_nom] = {
                    'architecture': {
                        'id': str(menace.architecture_id),
                        'nom': arch_nom
                    },
                    'menaces': [],
                    'risque_financier_total': 0
                }
            
            menace_data = MenaceListSerializer(menace).data
            menaces_par_arch[arch_nom]['menaces'].append(menace_data)
            menaces_par_arch[arch_nom]['risque_financier_total'] += menace.risque_financier_calculated or 0
        
        # Convertir en liste et trier
        result = list(menaces_par_arch.values())
        result.sort(key=lambda x: x['risque_financier_total'], reverse=True)
        
        return Response({
            'architectures_trouvees': len(result),
            'menaces_par_architecture': result
        })
    
    @action(detail=False, methods=['get']) 
    def sans_contexte(self, request):
        """Menaces sans contexte principal défini"""
        menaces_sans_contexte = self.get_queryset().filter(
            attribut_securite_principal__isnull=True
        )
        
        # Proposer des contextes pour chaque menace
        suggestions = []
        for menace in menaces_sans_contexte:
            attr_menaces = menace.attributs_impactes.select_related(
                'attribut_securite__actif__architecture'
            ).order_by('-risque_financier')
            
            if attr_menaces.exists():
                # Proposer l'attribut avec le plus haut risque
                meilleur_attr = attr_menaces.first().attribut_securite
                suggestions.append({
                    'menace': MenaceListSerializer(menace).data,
                    'contexte_suggere': {
                        'attribut_securite_id': str(meilleur_attr.id),
                        'architecture_nom': meilleur_attr.actif.architecture.nom,
                        'actif_nom': meilleur_attr.actif.nom,
                        'type_attribut': meilleur_attr.type_attribut,
                        'risque_financier': attr_menaces.first().risque_financier
                    },
                    'autres_contextes': len(attr_menaces) - 1
                })
        
        return Response({
            'total_sans_contexte': len(suggestions),
            'suggestions_contexte': suggestions
        })

class ControleNISTViewSet(viewsets.ModelViewSet):
    """Catalogue global des contrôles NIST"""
    queryset = ControleNIST.objects.all().order_by('code')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['famille', 'priorite']
    search_fields = ['code', 'nom', 'description']
    ordering_fields = ['code', 'nom', 'priorite', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ControleNISTListSerializer
        return ControleNISTSerializer
    
    @action(detail=True, methods=['post'])
    def ajouter_technique(self, request, pk=None):
        """Ajoute une nouvelle technique à ce contrôle NIST"""
        controle = self.get_object()
        data = request.data.copy()
        data['controle_nist'] = str(controle.id)
        
        serializer = TechniqueCreateSerializer(data=data)
        if serializer.is_valid():
            technique = serializer.save()
            log_activity(request.user, 'ADD_TECHNIQUE', 'ControleNIST', str(controle.id),
                        {'technique_nom': technique.nom})
            return Response(TechniqueSerializer(technique).data, 
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
            'total_controles_nist': ControleNIST.objects.count(),
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
        menace_controles = MenaceControle.objects.all()
        if menace_controles:
            conformes = menace_controles.filter(statut_conformite='CONFORME').count()
            taux_conformite = (conformes / menace_controles.count()) * 100
        else:
            taux_conformite = 0
        
        implementations_en_cours = ImplementationMesure.objects.filter(
            statut__in=['PLANIFIE', 'EN_COURS']
        ).count()
        
        stats.update({
            'taux_conformite_moyen': round(taux_conformite, 2),
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