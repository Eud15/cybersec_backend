# ================================================================
# api/utils.py - Utilitaires et fonctions helper
# ================================================================

from django.contrib.auth.models import User
from .models import LogActivite

def get_client_ip(request):
    """Récupère l'adresse IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_activity(user, action, objet_type, objet_id, details=None, request=None):
    """Enregistre une activité dans les logs"""
    if details is None:
        details = {}
    
    ip = None
    if request:
        ip = get_client_ip(request)
    
    LogActivite.objects.create(
        utilisateur=user if isinstance(user, User) else None,
        action=action,
        objet_type=objet_type,
        objet_id=objet_id,
        details=details,
        adresse_ip=ip
    )

def calculer_risque_architecture(architecture):
    """Calcule le risque global d'une architecture selon la nouvelle hiérarchie"""
    risque_total = 0
    
    for actif in architecture.actifs.all():
        for attribut in actif.attributs_securite.all():
            for attr_menace in attribut.menaces.all():
                # Vérifier s'il y a des implémentations actives
                implementations_actives = attr_menace.implementations.filter(
                    statut__in=['IMPLEMENTE', 'VERIFIE']
                )
                
                if implementations_actives.exists():
                    # Prendre la meilleure implémentation (plus efficace)
                    meilleure_impl = max(implementations_actives, 
                                       key=lambda x: x.mesure_controle.efficacite)
                    risque_total += meilleure_impl.risque_residuel
                else:
                    # Pas d'implémentation, risque brut
                    risque_total += attr_menace.niveau_risque
    
    return round(risque_total, 2)

def calculer_taux_conformite_actif(actif):
    """Calcule le taux de conformité NIST pour un actif"""
    total_controles = 0
    controles_conformes = 0
    
    for attribut in actif.attributs_securite.all():
        for attr_menace in attribut.menaces.all():
            for menace_controle in attr_menace.menace.controles_nist.all():
                total_controles += 1
                if menace_controle.statut_conformite == 'CONFORME':
                    controles_conformes += 1
    
    if total_controles == 0:
        return 0
    
    return round((controles_conformes / total_controles) * 100, 2)

def generer_rapport_hierarchique_complet(architecture):
    """Génère un rapport hiérarchique complet pour une architecture"""
    rapport = {
        'architecture': {
            'nom': architecture.nom,
            'description': architecture.description,
            'risque_tolere': architecture.risque_tolere,
            'risque_reel': calculer_risque_architecture(architecture)
        },
        'actifs': []
    }
    
    for actif in architecture.actifs.all():
        actif_data = {
            'nom': actif.nom,
            'type': actif.type_actif.nom,
            'cout': actif.cout,
            'criticite': actif.criticite,
            'taux_conformite': calculer_taux_conformite_actif(actif),
            'attributs_securite': []
        }
        
        for attribut in actif.attributs_securite.all():
            attribut_data = {
                'type': attribut.type_attribut,
                'valeur_cible': attribut.valeur_cible,
                'valeur_actuelle': attribut.valeur_actuelle,
                'ecart': attribut.ecart_securite,
                'priorite': attribut.priorite,
                'menaces': []
            }
            
            for attr_menace in attribut.menaces.all():
                menace_data = {
                    'nom': attr_menace.menace.nom,
                    'type': attr_menace.menace.type_menace,
                    'severite': attr_menace.menace.severite,
                    'probabilite': attr_menace.probabilite,
                    'impact': attr_menace.impact,
                    'niveau_risque': attr_menace.niveau_risque,
                    'cout_impact': attr_menace.cout_impact,
                    'controles_nist': []
                }
                
                for menace_controle in attr_menace.menace.controles_nist.all():
                    controle_data = {
                        'code': menace_controle.controle_nist.code,
                        'nom': menace_controle.controle_nist.nom,
                        'famille': menace_controle.controle_nist.famille,
                        'priorite': menace_controle.controle_nist.priorite,
                        'efficacite': menace_controle.efficacite,
                        'statut_conformite': menace_controle.statut_conformite,
                        'techniques': []
                    }
                    
                    for technique in menace_controle.controle_nist.techniques.all():
                        technique_data = {
                            'nom': technique.nom,
                            'type': technique.type_technique,
                            'complexite': technique.complexite,
                            'mesures_controle': []
                        }
                        
                        for mesure in technique.mesures_controle.all():
                            mesure_data = {
                                'nom': mesure.nom,
                                'nature': mesure.nature_mesure,
                                'cout_mise_en_oeuvre': mesure.cout_mise_en_oeuvre,
                                'cout_maintenance_annuel': mesure.cout_maintenance_annuel,
                                'efficacite': mesure.efficacite,
                                'duree_implementation': mesure.duree_implementation,
                                'cout_total_3_ans': mesure.cout_total_3_ans
                            }
                            
                            # Vérifier s'il y a une implémentation pour ce risque spécifique
                            try:
                                implementation = mesure.implementations.get(
                                    attribut_menace=attr_menace
                                )
                                mesure_data['implementation'] = {
                                    'statut': implementation.statut,
                                    'pourcentage_avancement': implementation.pourcentage_avancement,
                                    'responsable': implementation.responsable.get_full_name() if implementation.responsable else None,
                                    'date_fin_prevue': implementation.date_fin_prevue,
                                    'risque_residuel': implementation.risque_residuel
                                }
                            except:
                                mesure_data['implementation'] = None
                            
                            technique_data['mesures_controle'].append(mesure_data)
                        
                        controle_data['techniques'].append(technique_data)
                    
                    menace_data['controles_nist'].append(controle_data)
                
                attribut_data['menaces'].append(menace_data)
            
            actif_data['attributs_securite'].append(attribut_data)
        
        rapport['actifs'].append(actif_data)
    
    return rapport

def calculer_roi_implementation(implementation):
    """Calcule le ROI d'une implémentation de mesure"""
    if implementation.statut not in ['IMPLEMENTE', 'VERIFIE']:
        return None
    
    risque_initial = implementation.attribut_menace.niveau_risque
    risque_residuel = implementation.risque_residuel
    reduction_risque = risque_initial - risque_residuel
    
    # Calcul financier
    risque_financier_initial = implementation.attribut_menace.risque_financier
    reduction_financiere = (reduction_risque / risque_initial) * risque_financier_initial if risque_initial > 0 else 0
    
    cout_total = implementation.mesure_controle.cout_total_3_ans
    
    if cout_total == 0:
        return float('inf') if reduction_financiere > 0 else 0
    
    roi = ((reduction_financiere - float(cout_total)) / float(cout_total)) * 100
    return round(roi, 2)

# Constantes pour les seuils de risque
SEUILS_RISQUE = {
    'FAIBLE': 25,
    'MOYEN': 50,
    'ELEVE': 75,
    'CRITIQUE': 100
}

def categoriser_risque(niveau_risque):
    """Catégorise un risque selon son niveau"""
    for categorie, seuil in SEUILS_RISQUE.items():
        if niveau_risque <= seuil:
            return categorie
    return 'CRITIQUE'

def generer_matrice_risques_architecture(architecture):
    """Génère une matrice des risques pour une architecture"""
    matrice = {}
    
    # Initialiser la matrice
    for prob in ['FAIBLE', 'MOYEN', 'ELEVE', 'CRITIQUE']:
        matrice[prob] = {}
        for impact in ['FAIBLE', 'MOYEN', 'ELEVE', 'CRITIQUE']:
            matrice[prob][impact] = []
    
    # Remplir la matrice
    for actif in architecture.actifs.all():
        for attribut in actif.attributs_securite.all():
            for attr_menace in attribut.menaces.all():
                prob_cat = categoriser_risque(attr_menace.probabilite)
                impact_cat = categoriser_risque(attr_menace.impact)
                
                risque_info = {
                    'actif': actif.nom,
                    'attribut': attribut.type_attribut,
                    'menace': attr_menace.menace.nom,
                    'niveau_risque': attr_menace.niveau_risque,
                    'cout_impact': attr_menace.cout_impact,
                    'implementations_actives': attr_menace.implementations.filter(
                        statut__in=['IMPLEMENTE', 'VERIFIE']
                    ).count()
                }
                
                matrice[prob_cat][impact_cat].append(risque_info)
    
    return matrice

