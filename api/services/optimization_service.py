# api/services/optimization_service.py
import pyomo.environ as pyo
from decimal import Decimal
from django.db import transaction
import logging
from typing import List, Dict, Optional
import platform
import sys
import io
from django.conf import settings 

from ..models import (
    Architecture, Actif, AttributSecurite, AttributMenace, 
    MenaceControle, MesureDeControle, ImplementationMesure
)

logger = logging.getLogger(__name__)

class SecurityOptimizationService:
    """Service d'optimisation pour la sélection de mesures de sécurité"""
    
    def __init__(self, solver_path: Optional[str] = None):
        """
        Initialise le service d'optimisation avec support Windows amélioré
        et test silencieux des solveurs
        """
        self.solver_path = solver_path or getattr(settings, 'PYOMO_SOLVER_PATH', None)
        self.solver = None
        self.solver_name = None
        self.solver_io = None
        
        is_windows = platform.system() == 'Windows'
        
        solvers_to_try = []
        
        if self.solver_path:
            solvers_to_try.append(('bonmin', self.solver_path, None))
        
        if is_windows:
            solvers_to_try.extend([
                ('glpk', None, 'lp'),
                ('cbc', None, None),
                ('ipopt', None, None),
            ])
        else:
            solvers_to_try.extend([
                ('glpk', None, None),
                ('cbc', None, None),
                ('ipopt', None, None),
            ])
        
        for solver_name, executable, solver_io in solvers_to_try:
            try:
                solver_kwargs = {}
                if executable:
                    solver_kwargs['executable'] = executable
                if solver_io:
                    solver_kwargs['solver_io'] = solver_io
                
                solver = pyo.SolverFactory(solver_name, **solver_kwargs)
                
                if solver.available():
                    if self._test_solver_silently(solver, solver_name):
                        self.solver = solver
                        self.solver_name = solver_name
                        self.solver_io = solver_io
                        logger.info(
                            f"Solveur {solver_name} initialisé et testé avec succès "
                            f"(mode: {solver_io or 'default'}, OS: {platform.system()})"
                        )
                        break
                        
            except Exception as e:
                logger.debug(f"Échec d'initialisation de {solver_name}: {e}")
                continue
        
        if self.solver is None:
            logger.warning(
                "ATTENTION : Aucun solveur d'optimisation disponible. "
                "Les fonctionnalités d'optimisation seront désactivées. "
                f"OS: {platform.system()}, "
                "Pour installer : conda install -c conda-forge glpk"
            )
    
    def _test_solver_silently(self, solver, solver_name: str) -> bool:
        """Teste un solveur avec un modèle simple sans afficher les erreurs"""
        try:
            test_model = pyo.ConcreteModel()
            test_model.x = pyo.Var([1, 2], domain=pyo.NonNegativeReals)
            test_model.obj = pyo.Objective(
                expr=test_model.x[1] + test_model.x[2], 
                sense=pyo.minimize
            )
            test_model.constraint = pyo.Constraint(
                expr=test_model.x[1] + test_model.x[2] >= 1
            )
            
            old_stderr = sys.stderr
            old_stdout = sys.stdout
            sys.stderr = io.StringIO()
            sys.stdout = io.StringIO()
            
            try:
                result = solver.solve(test_model, tee=False, keepfiles=False)
                
                if result.solver.termination_condition in [
                    pyo.TerminationCondition.optimal,
                    pyo.TerminationCondition.feasible
                ]:
                    try:
                        val1 = pyo.value(test_model.x[1])
                        val2 = pyo.value(test_model.x[2])
                        if val1 is not None and val2 is not None:
                            return True
                    except:
                        pass
                
                return False
                    
            finally:
                sys.stderr = old_stderr
                sys.stdout = old_stdout
                
        except Exception as e:
            logger.debug(f"Test du solveur {solver_name} échoué: {e}")
            return False
    
    def _solve_model(self, model):
        """Résout un modèle Pyomo avec les bons paramètres selon le solveur"""
        solve_options = {
            'tee': False,
            'keepfiles': False,
        }
        
        if self.solver_name == 'glpk':
            solve_options.update({
                'symbolic_solver_labels': True,
            })
        
        try:
            result = self.solver.solve(model, **solve_options)
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la résolution du modèle: {e}")
            raise
    
    def optimize_architecture_security(self, architecture_id: str, budget_max: Optional[float] = None) -> Dict:
        """
        Optimise la sélection de mesures de sécurité pour une architecture complète
        """
        if self.solver is None:
            return {
                'error': 'Aucun solveur d\'optimisation disponible. Installez un solveur (glpk, cbc, etc.)',
                'status': 'solver_unavailable',
                'help': 'Pour installer : conda install -c conda-forge glpk',
                'platform': platform.system()
            }
        
        try:
            architecture = Architecture.objects.get(id=architecture_id)
            
            optimization_results = []
            
            # Traiter chaque actif de l'architecture
            for actif in architecture.actifs.all():
                logger.info(f"Optimisation de l'actif: {actif.nom}")
                
                # Traiter chaque attribut de sécurité
                for attribut in actif.attributs_securite.all():
                    if attribut.menaces.exists():
                        result = self._optimize_attribut_security(attribut)
                        if result['status'] == 'optimal' and result.get('selected_measures'):
                            optimization_results.append({
                                'actif_id': str(actif.id),
                                'actif_nom': actif.nom,
                                'actif_criticite': actif.criticite,
                                'attribut_id': str(attribut.id),
                                'attribut_type': attribut.type_attribut,
                                'attribut_priorite': attribut.priorite,
                                'cout_compromission': float(attribut.cout_compromission),
                                'optimization_status': result['status'],
                                'measures_count': result['measures_count'],
                                'total_cost': result['total_cost'],
                                'estimated_risk_reduction': result.get('estimated_risk_reduction', 0),
                                'threats_covered': result.get('threats_covered', 0),
                                'selected_measures': self._format_selected_measures(result['selected_measures']),
                                'actif_obj': actif,
                                'attribut_obj': attribut,
                                'raw_result': result
                            })
            
            # Optimisation globale si un budget est spécifié
            if budget_max and optimization_results:
                global_optimization = self._optimize_global_with_budget(
                    optimization_results, budget_max, architecture.risque_tolere
                )
                
                return {
                    'architecture_id': str(architecture_id),
                    'architecture_nom': architecture.nom,
                    'optimization_type': 'global_with_budget',
                    'budget_max': float(budget_max),
                    'risk_tolerance': float(architecture.risque_tolere),
                    'solver_used': self.solver_name,
                    'total_actifs_processed': architecture.actifs.count(),
                    'total_attributs_processed': sum(a.attributs_securite.count() for a in architecture.actifs.all()),
                    'successful_optimizations': len(optimization_results),
                    'individual_results': optimization_results,
                    'global_optimization': global_optimization,
                    'summary': self._create_summary(optimization_results, global_optimization)
                }
            
            # Retourner les résultats individuels sans budget
            return {
                'architecture_id': str(architecture_id),
                'architecture_nom': architecture.nom,
                'optimization_type': 'individual_by_attribute',
                'solver_used': self.solver_name,
                'total_actifs_processed': architecture.actifs.count(),
                'total_attributs_processed': sum(a.attributs_securite.count() for a in architecture.actifs.all()),
                'successful_optimizations': len(optimization_results),
                'results': optimization_results,
                'recommended_measures': self._summarize_recommendations(optimization_results)
            }
            
        except Architecture.DoesNotExist:
            return {'error': f'Architecture {architecture_id} non trouvée'}
        except Exception as e:
            logger.error(f"Erreur d'optimisation pour l'architecture {architecture_id}: {str(e)}", exc_info=True)
            return {'error': f'Erreur d\'optimisation: {str(e)}'}
    
    def _format_selected_measures(self, selected_measures: List[Dict]) -> List[Dict]:
        """Formate les mesures sélectionnées avec tous les détails"""
        formatted = []
        
        for measure_data in selected_measures:
            measure = measure_data['measure_data']['measure']
            
            formatted.append({
                'measure_id': str(measure.id),
                'measure_code': measure.mesure_code,
                'measure_nom': measure.nom,
                'description': measure.description,
                'nature_mesure': measure.nature_mesure,
                'cout_mise_en_oeuvre': float(measure.cout_mise_en_oeuvre),
                'cout_maintenance_annuel': float(measure.cout_maintenance_annuel),
                'cout_total_3_ans': float(measure.cout_total_3_ans),
                'efficacite': float(measure.efficacite),
                'duree_implementation': measure.duree_implementation,
                'technique': {
                    'id': str(measure.technique.id),
                    'code': measure.technique.technique_code,
                    'nom': measure.technique.nom,
                    'type': measure.technique.type_technique,
                    'complexite': measure.technique.complexite
                },
                'controle_nist': {
                    'id': str(measure.technique.controle_nist.id),
                    'code': measure.technique.controle_nist.code,
                    'nom': measure.technique.controle_nist.nom,
                    'famille': measure.technique.controle_nist.famille,
                    'priorite': measure.technique.controle_nist.priorite
                },
                'menace_info': {
                    'menace_id': measure_data['measure_data']['menace_id'],
                    'efficacite_contre_menace': measure_data['measure_data']['menace_efficacity'],
                    'statut_conformite': measure_data['measure_data']['conformity_status']
                }
            })
        
        return formatted
    
    def _optimize_attribut_security(self, attribut_securite: AttributSecurite) -> Dict:
        """
        Optimise la sélection de mesures pour un attribut de sécurité spécifique
        VERSION SIMPLIFIÉE LINÉAIRE
        """
        if self.solver is None:
            return {
                'status': 'solver_unavailable',
                'error': 'Aucun solveur d\'optimisation disponible',
                'help': 'Pour installer : conda install -c conda-forge glpk'
            }
        
        try:
            available_measures = self._get_available_measures_for_attribut(attribut_securite)
            
            if not available_measures:
                return {
                    'status': 'no_measures',
                    'message': 'Aucune mesure disponible pour cet attribut'
                }
            
            model = pyo.ConcreteModel()
            
            measure_ids = [m['measure_id'] for m in available_measures]
            model.M = pyo.Set(initialize=measure_ids)
            model.x = pyo.Var(model.M, domain=pyo.Boolean)
            
            # Fonction objectif : minimiser le coût total
            model.objective = pyo.Objective(
                expr=sum(
                    measure['cost'] * model.x[measure['measure_id']] 
                    for measure in available_measures
                ),
                sense=pyo.minimize
            )
            
            model.constraints = pyo.ConstraintList()
            
            # Grouper les mesures par menace
            measures_by_threat = {}
            for measure in available_measures:
                threat_id = measure['menace_id']
                if threat_id not in measures_by_threat:
                    measures_by_threat[threat_id] = []
                measures_by_threat[threat_id].append(measure['measure_id'])
            
            # Contrainte : au moins UNE mesure par menace
            for threat_id, measure_list in measures_by_threat.items():
                model.constraints.add(
                    sum(model.x[mid] for mid in measure_list) >= 1
                )
            
            result = self._solve_model(model)
            
            if result.solver.termination_condition == pyo.TerminationCondition.optimal:
                selected_measures = [
                    {
                        'measure_id': measure_id,
                        'measure_data': next(m for m in available_measures if m['measure_id'] == measure_id),
                        'selected': pyo.value(model.x[measure_id]) > 0.5
                    }
                    for measure_id in model.M
                    if pyo.value(model.x[measure_id]) > 0.5
                ]
                
                total_cost = sum(m['measure_data']['cost'] for m in selected_measures)
                
                # Calculer la réduction de risque estimée
                total_risk_reduction = 0
                for m in selected_measures:
                    efficacity = m['measure_data']['efficacity'] / 100
                    menace_eff = m['measure_data']['menace_efficacity'] / 100
                    combined_eff = efficacity * menace_eff
                    total_risk_reduction += combined_eff
                
                return {
                    'status': 'optimal',
                    'selected_measures': selected_measures,
                    'total_cost': round(total_cost, 2),
                    'objective_value': pyo.value(model.objective),
                    'measures_count': len(selected_measures),
                    'estimated_risk_reduction': round(min(total_risk_reduction * 100, 100), 2),
                    'threats_covered': len(measures_by_threat)
                }
            else:
                return {
                    'status': 'no_solution',
                    'termination_condition': str(result.solver.termination_condition),
                    'message': f'Aucune solution optimale trouvée',
                    'available_measures_count': len(available_measures),
                    'threats_count': len(measures_by_threat)
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de l'attribut {attribut_securite.id}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _get_available_measures_for_attribut(self, attribut_securite: AttributSecurite) -> List[Dict]:
        """Récupère toutes les mesures disponibles pour un attribut de sécurité"""
        measures = []
        
        for attr_menace in attribut_securite.menaces.all():
            menace = attr_menace.menace
            
            for menace_controle in menace.controles_nist.all():
                controle = menace_controle.controle_nist
                
                for technique in controle.techniques.all():
                    for mesure in technique.mesures_controle.all():
                        measures.append({
                            'measure_id': str(mesure.id),
                            'measure': mesure,
                            'cost': float(mesure.cout_total_3_ans),
                            'efficacity': float(mesure.efficacite),
                            'nature': mesure.nature_mesure,
                            'menace_id': str(menace.id),
                            'menace_efficacity': float(menace_controle.efficacite),
                            'conformity_status': menace_controle.statut_conformite
                        })
        
        # Supprimer les doublons
        unique_measures = {}
        for measure in measures:
            measure_id = measure['measure_id']
            if measure_id not in unique_measures:
                unique_measures[measure_id] = measure
        
        return list(unique_measures.values())
    
    def _optimize_global_with_budget(self, optimization_results: List[Dict], 
                                     budget_max: float, risk_tolerance: Decimal) -> Dict:
        """Optimisation globale avec contrainte budgétaire"""
        try:
            # Collecter toutes les mesures uniques de tous les résultats  
            # IMPORTANT: Ne pas utiliser les mesures déjà formatées, elles contiennent des objets Django
            unique_measures = {}
            measures_with_context = {}
            
            for result in optimization_results:
                attribut_id = result['attribut_id']
                actif_id = result['actif_id']
                
                # Utiliser raw_result qui contient les données brutes
                raw_selected = result.get('raw_result', {}).get('selected_measures', [])
                
                for measure_raw in raw_selected:
                    measure_data = measure_raw['measure_data']
                    measure_id = measure_data['measure_id']
                    
                    if measure_id not in unique_measures:
                        # Stocker uniquement les données primitives nécessaires pour l'optimisation
                        unique_measures[measure_id] = {
                            'measure_id': measure_id,
                            'cost': measure_data['cost'],
                            'efficacity': measure_data['efficacity']
                        }
                        
                        # Contexte pour l'implémentation
                        measures_with_context[measure_id] = {
                            'measure_id': measure_id,
                            'attribut_id': attribut_id,
                            'actif_id': actif_id,
                            'menace_id': measure_data['menace_id'],
                            'measure_obj': measure_data['measure']  # Objet Django, pour plus tard
                        }
            
            if not unique_measures:
                return {'status': 'no_measures', 'message': 'Aucune mesure à optimiser'}
            
            model = pyo.ConcreteModel()
            
            measure_ids = list(unique_measures.keys())
            model.M = pyo.Set(initialize=measure_ids)
            model.x = pyo.Var(model.M, domain=pyo.Boolean)
            
            # Objectif : maximiser l'efficacité totale
            model.objective = pyo.Objective(
                expr=sum(
                    unique_measures[mid]['efficacity'] * model.x[mid]
                    for mid in measure_ids
                ),
                sense=pyo.maximize
            )
            
            # Contrainte budgétaire
            model.budget_constraint = pyo.Constraint(
                expr=sum(
                    unique_measures[mid]['cost'] * model.x[mid] 
                    for mid in measure_ids
                ) <= budget_max
            )
            
            result = self._solve_model(model)
            
            if result.solver.termination_condition == pyo.TerminationCondition.optimal:
                selected = [
                    mid for mid in measure_ids 
                    if pyo.value(model.x[mid]) > 0.5
                ]
                
                # Récupérer les détails complets UNIQUEMENT pour les mesures sélectionnées
                selected_measures_details = []
                for mid in selected:
                    context = measures_with_context[mid]
                    measure_obj = context['measure_obj']
                    
                    # Formater en dict avec UNIQUEMENT des types primitifs
                    selected_measures_details.append({
                        'measure_id': str(measure_obj.id),
                        'measure_code': measure_obj.mesure_code,
                        'measure_nom': measure_obj.nom,
                        'description': measure_obj.description,
                        'nature_mesure': measure_obj.nature_mesure,
                        'cout_mise_en_oeuvre': float(measure_obj.cout_mise_en_oeuvre),
                        'cout_maintenance_annuel': float(measure_obj.cout_maintenance_annuel),
                        'cout_total_3_ans': float(measure_obj.cout_total_3_ans),
                        'efficacite': float(measure_obj.efficacite),
                        'duree_implementation': measure_obj.duree_implementation,
                        'technique': {
                            'id': str(measure_obj.technique.id),
                            'code': measure_obj.technique.technique_code,
                            'nom': measure_obj.technique.nom,
                        },
                        'controle_nist': {
                            'id': str(measure_obj.technique.controle_nist.id),
                            'code': measure_obj.technique.controle_nist.code,
                            'nom': measure_obj.technique.controle_nist.nom,
                        }
                    })
                
                total_cost = sum(unique_measures[mid]['cost'] for mid in selected)
                total_efficacity = sum(unique_measures[mid]['efficacity'] for mid in selected)
                
                # Préparer les données d'implémentation avec UNIQUEMENT des IDs
                implementation_data = {}
                for mid in selected:
                    context = measures_with_context[mid]
                    attr_id = context['attribut_id']
                    
                    if attr_id not in implementation_data:
                        implementation_data[attr_id] = {
                            'attribut_id': attr_id,
                            'actif_id': context['actif_id'],
                            'selected_measures': []
                        }
                    
                    implementation_data[attr_id]['selected_measures'].append({
                        'measure_id': mid,
                        'menace_id': context['menace_id']
                    })
                
                return {
                    'status': 'optimal',
                    'selected_measures': selected_measures_details,  # Liste de dicts avec types primitifs
                    'selected_measure_ids': selected,
                    'total_cost': round(total_cost, 2),
                    'total_efficacity': round(total_efficacity, 2),
                    'budget_used_percentage': round((total_cost / budget_max) * 100, 2),
                    'measures_count': len(selected),
                    'total_measures_analyzed': len(unique_measures),
                    'budget_remaining': round(budget_max - total_cost, 2),
                    '_implementation_data': list(implementation_data.values())
                }
            else:
                return {
                    'status': 'no_solution',
                    'message': 'Budget insuffisant ou problème infaisable',
                    'budget_max': budget_max,
                    'total_measures_analyzed': len(unique_measures)
                }
                
        except Exception as e:
            logger.error(f"Erreur dans l'optimisation globale: {str(e)}", exc_info=True)
            return {'status': 'error', 'error': str(e)}

    def _create_summary(self, individual_results: List[Dict], global_result: Dict) -> Dict:
        """Crée un résumé complet de l'optimisation"""
        total_measures = len(individual_results)
        total_cost_individual = sum(r['total_cost'] for r in individual_results)
        
        summary = {
            'total_attributs_optimized': len(individual_results),
            'total_cost_without_budget': round(total_cost_individual, 2),
            'measures_by_nature': {},
            'measures_by_priority': {},
            'top_controles_nist': []
        }
        
        if global_result.get('status') == 'optimal':
            summary.update({
                'total_cost_with_budget': global_result['total_cost'],
                'budget_savings': round(total_cost_individual - global_result['total_cost'], 2),
                'measures_selected_with_budget': global_result['measures_count'],
                'measures_eliminated_by_budget': total_measures - global_result['measures_count']
            })
        
        # Analyser les mesures par nature
        for result in individual_results:
            for measure in result['selected_measures']:
                nature = measure['nature_mesure']
                summary['measures_by_nature'][nature] = summary['measures_by_nature'].get(nature, 0) + 1
        
        return summary
    
    def _summarize_recommendations(self, optimization_results: List[Dict]) -> Dict:
        """Résumé des recommandations d'optimisation"""
        if not optimization_results:
            return {
                'total_measures': 0, 
                'total_cost': 0, 
                'measures_by_nature': {},
                'recommendations': []
            }
        
        total_cost = sum(r['total_cost'] for r in optimization_results)
        all_measures = []
        
        for result in optimization_results:
            all_measures.extend(result['selected_measures'])
        
        measures_by_nature = {}
        for measure in all_measures:
            nature = measure['nature_mesure']
            measures_by_nature[nature] = measures_by_nature.get(nature, 0) + 1
        
        return {
            'total_measures': len(all_measures),
            'total_cost': round(total_cost, 2),
            'measures_by_nature': measures_by_nature,
            'recommendations': [
                {
                    'actif': r['actif_nom'],
                    'attribut': r['attribut_type'],
                    'measures_count': r['measures_count'],
                    'cost': r['total_cost'],
                    'risk_reduction': r.get('estimated_risk_reduction', 0)
                }
                for r in optimization_results
            ]
        }

    @transaction.atomic
    def create_implementation_plan(self, optimization_result: Dict, 
                                 responsable_id: Optional[str] = None) -> Dict:
        """Crée un plan d'implémentation basé sur les résultats d'optimisation"""
        try:
            implementations_created = []
            
            results_to_process = []
            
            # Déterminer quelle liste de résultats utiliser
            if optimization_result.get('optimization_type') == 'global_with_budget':
                results_to_process = optimization_result.get('individual_results', [])
            else:
                results_to_process = optimization_result.get('results', [])
            
            for result in results_to_process:
                actif = result.get('actif_obj')
                attribut = result.get('attribut_obj')
                
                if not actif or not attribut:
                    continue
                
                for measure_data in result.get('selected_measures', []):
                    measure_id = measure_data['measure_id']
                    measure = MesureDeControle.objects.get(id=measure_id)
                    
                    menace_id = measure_data.get('menace_info', {}).get('menace_id')
                    if menace_id:
                        attr_menace = attribut.menaces.filter(menace_id=menace_id).first()
                        
                        if attr_menace:
                            implementation = ImplementationMesure.objects.create(
                                attribut_menace=attr_menace,
                                mesure_controle=measure,
                                statut='PLANIFIE',
                                responsable_id=responsable_id,
                                commentaires=f'Mesure recommandée par optimisation automatique'
                            )
                            implementations_created.append(implementation)
            
            return {
                'status': 'success',
                'implementations_created': len(implementations_created),
                'implementation_ids': [str(impl.id) for impl in implementations_created]
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du plan d'implémentation: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }