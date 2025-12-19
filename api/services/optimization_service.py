# api/services/optimization_service.py

import logging
import pyomo.environ as pyo
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

class SecurityOptimizationService:
    def __init__(self):
        """Initialise le service d'optimisation avec détection automatique du solveur"""
        self.solver = None
        self.solver_name = None
        self.solver_io = None
        
        # Liste des solveurs à essayer dans l'ordre de préférence
        solvers_to_try = [
            ('glpk', 'lp'),      # Open source, disponible via pip
            ('cbc', 'lp'),       # Open source
            ('ipopt', 'nl'),     # Open source
            ('bonmin', 'nl'),    # Commercial
        ]
        
        for solver_name, io_mode in solvers_to_try:
            try:
                test_solver = pyo.SolverFactory(solver_name, validate=False)
                
                if test_solver.available():
                    self.solver = test_solver
                    self.solver_name = solver_name
                    self.solver_io = io_mode
                    logger.info(f"✅ Solveur {solver_name} initialisé avec succès")
                    break
            except Exception as e:
                logger.debug(f"❌ Impossible d'initialiser {solver_name}: {e}")
                continue
        
        if self.solver is None:
            logger.error("❌ Aucun solveur disponible. Installez GLPK : pip install glpk")
    
    def _is_measure_valid(self, mesure):
        """
        Vérifie si une mesure est valide pour l'optimisation
        
        Critères de validation :
        - Coût total sur 3 ans > 0
        - Efficacité > 0
        - Nature de mesure définie
        """
        cout_total = mesure.cout_total_3_ans
        efficacite = mesure.efficacite if mesure.efficacite else Decimal('0')
        nature_valide = mesure.nature_mesure and mesure.nature_mesure.strip() != ''
        
        is_valid = (
            cout_total > 0 and 
            efficacite > 0 and 
            nature_valide
        )
        
        if not is_valid:
            logger.debug(
                f"⚠️  Mesure {mesure.mesure_code} INVALIDE : "
                f"coût_total={cout_total}, "
                f"efficacité={efficacite}, "
                f"nature={mesure.nature_mesure}"
            )
        
        return is_valid
    
    def _build_complete_measure_object(self, mesure, menace, attr_menace, attribut, menace_mesure=None):
        """
        ✅ NOUVELLE MÉTHODE : Construit un objet mesure complet avec TOUTES les informations
        
        Args:
            mesure: Instance de MesureDeControle
            menace: Instance de Menace
            attr_menace: Instance de AttributMenace
            attribut: Instance de AttributSecurite
            menace_mesure: Instance de MenaceMesure (optionnel)
        
        Returns:
            dict: Objet mesure complet avec tous les détails
        """
        return {
            # ✅ Informations de base de la mesure
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
            
            # ✅ Technique
            'technique': {
                'id': str(mesure.technique.id),
                'code': mesure.technique.technique_code,
                'nom': mesure.technique.nom,
                'type': mesure.technique.type_technique,
                'complexite': mesure.technique.complexite,
                'famille': mesure.technique.famille,
                'priorite': mesure.technique.priorite
            },
            
            # ✅ Menace
            'menace': {
                'id': str(menace.id),
                'nom': menace.nom,
                'severite': menace.severite,
                'type_menace': menace.type_menace,
                'probabilite': float(attr_menace.probabilite),
                'impact': float(attr_menace.impact),
                'risque_financier': attr_menace.risque_financier
            },
            
            # ✅ Association menace-mesure (si disponible)
            'menace_mesure': {
                'efficacite': float(menace_mesure.efficacite) if menace_mesure and menace_mesure.efficacite else float(mesure.efficacite),
                'statut_conformite': menace_mesure.statut_conformite if menace_mesure else 'NON_CONFORME'
            }
        }
    
    def _optimize_attribut_security(self, attribut):
        """
        ✅ OPTIMISATION AVEC CONSTRUCTION D'OBJETS COMPLETS
        Optimise la sélection de mesures pour un attribut de sécurité
        """
        try:
            # Récupérer toutes les menaces de cet attribut
            menaces = attribut.menaces.select_related('menace').all()
            
            if not menaces.exists():
                return {
                    'status': 'no_menaces',
                    'message': 'Aucune menace associée à cet attribut',
                    'attribut_id': str(attribut.id),
                    'attribut_type': attribut.type_attribut,
                    'actif_nom': attribut.actif.nom
                }
            
            # ✅ Collecter toutes les mesures disponibles avec TOUS les détails
            all_measures_complete = []
            measures_rejected = 0
            menaces_analyzed = 0
            
            for attr_menace in menaces:
                menace = attr_menace.menace
                menaces_analyzed += 1
                
                # Récupérer les mesures via MenaceMesure
                for menace_mesure in menace.mesures_controle.select_related(
                    'mesure_controle', 
                    'mesure_controle__technique'
                ).all():
                    mesure = menace_mesure.mesure_controle
                    
                    # ✅ FILTRAGE STRICT : Vérifier la validité de la mesure
                    if not self._is_measure_valid(mesure):
                        measures_rejected += 1
                        continue
                    
                    # ✅ Construire l'objet mesure COMPLET
                    complete_measure = self._build_complete_measure_object(
                        mesure=mesure,
                        menace=menace,
                        attr_menace=attr_menace,
                        attribut=attribut,
                        menace_mesure=menace_mesure
                    )
                    
                    all_measures_complete.append(complete_measure)
            
            logger.info(
                f"📊 Attribut {attribut.type_attribut} ({attribut.actif.nom}) : "
                f"{len(all_measures_complete)} mesures VALIDES, "
                f"{measures_rejected} mesures REJETÉES, "
                f"{menaces_analyzed} menaces analysées"
            )
            
            # ✅ Vérifier qu'il y a des mesures valides
            if not all_measures_complete:
                return {
                    'status': 'no_valid_measures',
                    'message': (
                        f'Aucune mesure avec coût et efficacité valides. '
                        f'{measures_rejected} mesures rejetées car incomplètes.'
                    ),
                    'attribut_id': str(attribut.id),
                    'attribut_type': attribut.type_attribut,
                    'actif_nom': attribut.actif.nom,
                    'menaces_analyzed': menaces_analyzed,
                    'measures_rejected': measures_rejected
                }
            
            # ✅ Dédupliquer les mesures par ID
            unique_measures = {}
            for measure in all_measures_complete:
                measure_id = measure['id']
                if measure_id not in unique_measures:
                    unique_measures[measure_id] = measure
            
            measures_list = list(unique_measures.values())
            
            logger.info(
                f"✅ {len(measures_list)} mesures UNIQUES validées pour l'optimisation"
            )
            
            # ✅ Créer le modèle d'optimisation
            model = pyo.ConcreteModel()
            
            # Indices des mesures
            measure_indices = range(len(measures_list))
            model.measures = pyo.Set(initialize=measure_indices)
            
            # Variables de décision binaires
            model.x = pyo.Var(model.measures, domain=pyo.Binary)
            
            # Fonction objectif : minimiser le coût total
            def objective_rule(model):
                return sum(
                    model.x[i] * measures_list[i]['cout_total_3_ans'] 
                    for i in model.measures
                )
            model.objective = pyo.Objective(rule=objective_rule, sense=pyo.minimize)
            
            # Contrainte : efficacité totale >= seuil minimum (70%)
            efficacite_minimale = 70.0
            
            def efficacite_constraint_rule(model):
                return sum(
                    model.x[i] * measures_list[i]['efficacite'] 
                    for i in model.measures
                ) >= efficacite_minimale
            
            model.efficacite_constraint = pyo.Constraint(rule=efficacite_constraint_rule)
            
            # ✅ Résoudre le modèle
            if self.solver is None:
                return {
                    'status': 'solver_unavailable',
                    'message': 'Aucun solveur disponible. Installez GLPK : pip install glpk',
                    'attribut_id': str(attribut.id)
                }
            
            results = self.solver.solve(model, tee=False)
            
            # ✅ Vérifier le statut de la solution
            if results.solver.termination_condition == pyo.TerminationCondition.optimal:
                # ✅ Extraire les mesures sélectionnées AVEC TOUS LES DÉTAILS
                selected_measures = []
                total_cost = 0
                total_efficacite = 0
                
                for i in model.measures:
                    if pyo.value(model.x[i]) > 0.5:  # Sélectionnée
                        measure = measures_list[i].copy()
                        selected_measures.append(measure)
                        
                        total_cost += measure['cout_total_3_ans']
                        total_efficacite += measure['efficacite']
                
                logger.info(
                    f"✅ Solution optimale : {len(selected_measures)} mesures sélectionnées, "
                    f"coût total = {total_cost:.2f}$, efficacité = {total_efficacite:.2f}%"
                )
                
                return {
                    'status': 'optimal',
                    'attribut_id': str(attribut.id),
                    'attribut_type': attribut.type_attribut,
                    'actif_id': str(attribut.actif.id),
                    'actif_nom': attribut.actif.nom,
                    'architecture_id': str(attribut.actif.architecture.id),
                    'architecture_nom': attribut.actif.architecture.nom,
                    
                    # ✅ Mesures sélectionnées AVEC TOUS LES DÉTAILS
                    'mesures': selected_measures,
                    
                    'total_cost': round(total_cost, 2),
                    'total_efficacite': round(total_efficacite, 2),
                    'objective_value': round(pyo.value(model.objective), 2),
                    'measures_count': len(selected_measures),
                    'total_measures_available': len(measures_list),
                    'measures_rejected': measures_rejected,
                    'menaces_analyzed': menaces_analyzed,
                    'risk_threshold': float(attribut.cout_compromission)
                }
            
            else:
                return {
                    'status': 'infeasible',
                    'message': f'Aucune solution trouvée : {results.solver.termination_condition}',
                    'attribut_id': str(attribut.id),
                    'measures_analyzed': len(measures_list),
                    'measures_rejected': measures_rejected
                }
        
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de l'optimisation de l'attribut {attribut.id}: {str(e)}",
                exc_info=True
            )
            return {
                'status': 'error',
                'error': str(e),
                'attribut_id': str(attribut.id)
            }
    
    def _optimize_global_budget(self, measures, budget_max):
        """
        ✅ Optimisation globale avec contrainte de budget
        Retourne directement les objets mesures complets au lieu des IDs
        """
        try:
            measures_list = list(measures)
            
            if not measures_list:
                return {
                    'status': 'no_measures',
                    'message': 'Aucune mesure disponible pour l\'optimisation globale'
                }
            
            # ✅ CORRECTION: Convertir budget_max en float dès le début
            budget_max_float = float(budget_max) if budget_max is not None else 0
            
            # Créer le modèle d'optimisation
            model = pyo.ConcreteModel()
            
            # Indices des mesures
            measure_indices = range(len(measures_list))
            model.measures = pyo.Set(initialize=measure_indices)
            
            # Variables de décision binaires
            model.x = pyo.Var(model.measures, domain=pyo.Binary)
            
            # Fonction objectif : maximiser l'efficacité totale
            def objective_rule(model):
                return sum(
                    model.x[i] * measures_list[i]['efficacite'] 
                    for i in model.measures
                )
            model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)
            
            # Contrainte de budget
            def budget_constraint_rule(model):
                return sum(
                    model.x[i] * measures_list[i]['cout_total_3_ans'] 
                    for i in model.measures
                ) <= budget_max_float  # ✅ Utiliser la version float
            
            model.budget_constraint = pyo.Constraint(rule=budget_constraint_rule)
            
            # Résoudre le modèle
            if self.solver is None:
                return {
                    'status': 'solver_unavailable',
                    'message': 'Aucun solveur disponible'
                }
            
            results = self.solver.solve(model, tee=False)
            
            # Vérifier le statut de la solution
            if results.solver.termination_condition == pyo.TerminationCondition.optimal:
                # ✅ Extraire les mesures sélectionnées COMPLÈTES
                selected_measures = []
                total_cost = 0
                total_efficacite = 0
                
                for i in model.measures:
                    if pyo.value(model.x[i]) > 0.5:  # Sélectionnée
                        # ✅ VÉRIFICATION: S'assurer que c'est un dict
                        measure = measures_list[i]
                        
                        if isinstance(measure, str):
                            logger.error(f"❌ La mesure à l'index {i} est une string : {measure[:100]}")
                            continue
                        
                        if not isinstance(measure, dict):
                            logger.error(f"❌ La mesure à l'index {i} n'est pas un dict : {type(measure)}")
                            continue
                        
                        # ✅ Ajouter l'objet dict complet
                        selected_measures.append(measure)
                        
                        # ✅ Utiliser float() pour éviter les problèmes de types
                        total_cost += float(measure['cout_total_3_ans'])
                        total_efficacite += float(measure['efficacite'])
                
                # ✅ Calculer le pourcentage avec float
                budget_used_percentage = (total_cost / budget_max_float * 100) if budget_max_float > 0 else 0
                
                logger.info(
                    f"✅ Optimisation globale réussie : {len(selected_measures)} mesures sélectionnées, "
                    f"coût = {total_cost:.2f}$, efficacité = {total_efficacite:.2f}%"
                )
                
                return {
                    'status': 'optimal',
                    'selected_measures': selected_measures,  # ✅ Liste de dicts complets
                    'total_cost': round(total_cost, 2),
                    'budget_used_percentage': round(budget_used_percentage, 2),
                    'measures_count': len(selected_measures),
                    'total_measures_analyzed': len(measures_list),
                    'total_efficacite': round(total_efficacite, 2),
                    'message': (
                        'Budget suffisant pour toutes les mesures' 
                        if total_cost <= budget_max_float 
                        else 'Optimisation réussie avec contrainte de budget'
                    )
                }
            else:
                return {
                    'status': 'infeasible',
                    'message': f'Aucune solution trouvée : {results.solver.termination_condition}',
                    'total_measures_analyzed': len(measures_list)
                }
        
        except Exception as e:
            logger.error(f"❌ Erreur optimisation globale: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
        
        
    def optimize_architecture_security(self, architecture_id, budget_max=None):
        """
        ✅ Optimise la sécurité de toute l'architecture avec objets complets
        """
        from api.models import Architecture
        
        try:
            architecture = Architecture.objects.get(id=architecture_id)
            
            logger.info(
                f"🚀 Début optimisation pour architecture {architecture.nom} "
                f"(budget max: {budget_max if budget_max else 'illimité'})"
            )
            
            # Résultats pour chaque attribut
            results = []
            all_measures_complete = {}  # Pour stocker les mesures complètes
            
            total_actifs = 0
            total_attributs = 0
            successful_optimizations = 0
            total_measures_rejected = 0
            
            # Pour chaque actif de l'architecture
            for actif in architecture.actifs.all():
                total_actifs += 1
                
                # Pour chaque attribut de sécurité
                for attribut in actif.attributs_securite.all():
                    total_attributs += 1
                    
                    # Optimiser cet attribut
                    result = self._optimize_attribut_security(attribut)
                    
                    if result.get('status') == 'optimal':
                        successful_optimizations += 1
                        
                        # ✅ Collecter les mesures complètes
                        if result.get('mesures'):
                            for measure in result['mesures']:
                                measure_id = measure['id']
                                if measure_id not in all_measures_complete:
                                    all_measures_complete[measure_id] = measure
                    
                    if result.get('measures_rejected'):
                        total_measures_rejected += result['measures_rejected']
                    
                    results.append(result)
            
            logger.info(
                f"📊 Optimisation terminée : {successful_optimizations}/{total_attributs} attributs optimisés, "
                f"{total_measures_rejected} mesures rejetées au total"
            )
            
            # ✅ Préparer les recommandations
            recommendations = []
            total_cost = 0
            
            for result in results:
                if result.get('status') == 'optimal' and result.get('mesures'):
                    recommendations.append({
                        'actif': result.get('actif_nom', 'N/A'),
                        'attribut': result.get('attribut_type', 'N/A'),
                        'measures_count': result.get('measures_count', 0),
                        'cost': result.get('total_cost', 0)
                    })
                    total_cost += result.get('total_cost', 0)
            
            # ✅ Grouper par nature
            measures_by_nature = {}
            for measure in all_measures_complete.values():
                nature = measure.get('nature_mesure', 'INCONNU')
                measures_by_nature[nature] = measures_by_nature.get(nature, 0) + 1
            
            # Compiler les résultats
            optimization_result = {
                'architecture_id': str(architecture_id),
                'architecture_nom': architecture.nom,
                'optimization_type': 'individual_by_attribute',
                'budget_max': float(budget_max) if budget_max else None,
                'total_actifs_processed': total_actifs,
                'total_attributs_processed': total_attributs,
                'successful_optimizations': successful_optimizations,
                'total_measures_rejected': total_measures_rejected,
                'results': results,
                'recommended_measures': {
                    'total_measures': len(all_measures_complete),
                    'total_cost': round(total_cost, 2),
                    'measures_by_nature': measures_by_nature,
                    'recommendations': recommendations,
                    'mesures_completes': list(all_measures_complete.values())  # ✅ Toutes les mesures complètes
                }
            }
            
            # Optimisation globale si budget spécifié
            if budget_max:
                global_result = self._optimize_global_budget(
                    all_measures_complete.values(),
                    budget_max
                )
                optimization_result['global_optimization'] = global_result
            
            return optimization_result
        
        except Exception as e:
            logger.error(f"❌ Erreur optimisation architecture: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'architecture_id': str(architecture_id)
            }
    
    def create_implementation_plan(self, optimization_result, responsable_id=None):
        """
        ✅ Crée un plan d'implémentation à partir des résultats d'optimisation
        """
        from api.models import ImplementationMesure, MesureDeControle, AttributMenace, User
        
        try:
            responsable = None
            if responsable_id:
                try:
                    responsable = User.objects.get(id=responsable_id)
                except User.DoesNotExist:
                    logger.warning(f"Responsable {responsable_id} non trouvé")
            
            implementation_ids = []
            implementations_created = 0
            
            # Parcourir les résultats d'optimisation
            for result_item in optimization_result.get('results', []):
                if result_item.get('status') != 'optimal':
                    continue
                
                # ✅ Utiliser les mesures complètes
                selected_measures = result_item.get('mesures', [])
                attribut_id = result_item.get('attribut_id')
                
                if not attribut_id or not selected_measures:
                    continue
                
                # Pour chaque mesure sélectionnée
                for measure in selected_measures:
                    try:
                        mesure_controle = MesureDeControle.objects.get(id=measure['id'])
                        
                        # Trouver l'association attribut-menace appropriée
                        # ✅ Utiliser l'ID de la menace depuis l'objet mesure complet
                        menace_id = measure.get('menace', {}).get('id')
                        
                        attribut_menace = AttributMenace.objects.filter(
                            attribut_securite_id=attribut_id,
                            menace_id=menace_id
                        ).first()
                        
                        if not attribut_menace:
                            logger.warning(f"Aucune association trouvée pour attribut {attribut_id} et menace {menace_id}")
                            continue
                        
                        # Créer l'implémentation
                        implementation = ImplementationMesure.objects.create(
                            attribut_menace=attribut_menace,
                            mesure_controle=mesure_controle,
                            statut='PLANIFIE',
                            responsable=responsable,
                            date_debut_prevue=timezone.now(),
                            pourcentage_avancement=Decimal('0.00'),
                            commentaires=f"Créé automatiquement par optimisation"
                        )
                        
                        implementation_ids.append(str(implementation.id))
                        implementations_created += 1
                        
                    except Exception as e:
                        logger.error(f"Erreur création implémentation: {str(e)}")
                        continue
            
            return {
                'status': 'success',
                'implementations_created': implementations_created,
                'implementation_ids': implementation_ids
            }
        
        except Exception as e:
            logger.error(f"Erreur création plan d'implémentation: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }