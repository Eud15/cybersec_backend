"""
Script de génération de données de test pour le système de gestion de cybersécurité
Basé sur les catégories et types ArchiMate
Montants en dollars américains (USD)

Usage: python manage.py shell < populate_database_archimate.py
"""

import random
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from api.models import (
    CategorieActif, TypeActif, Architecture, Actif, AttributSecurite,
    Menace, AttributMenace, Technique, MesureDeControle, MenaceMesure,
    ImplementationMesure
)

print("🚀 Début de la génération des données de test (ArchiMate + USD)...")

# ============================================================================
# 1. CRÉER DES UTILISATEURS
# ============================================================================
print("\n📝 Création des utilisateurs...")

users_data = [
    {'username': 'admine', 'email': 'admine@gmail.bj', 'first_name': 'Admine', 'last_name': 'System', 'is_staff': True},
    {'username': 'ciso', 'email': 'ciso@gmail.bj', 'first_name': 'Chief Information', 'last_name': 'Security Officer', 'is_staff': True},
    {'username': 'risk_manager', 'email': 'risk@gmail.bj', 'first_name': 'Risk', 'last_name': 'Manager', 'is_staff': True},
    {'username': 'security_analyst', 'email': 'analyst@gmail.bj', 'first_name': 'Security', 'last_name': 'Analyst'},
    {'username': 'it_manager', 'email': 'it@gmail.bj', 'first_name': 'IT', 'last_name': 'Manager'},
    {'username': 'network_admin', 'email': 'network@gmail.bj', 'first_name': 'Network', 'last_name': 'Administrator'},
]

users = []
for user_data in users_data:
    user, created = User.objects.get_or_create(
        username=user_data['username'],
        defaults={
            'email': user_data['email'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'is_staff': user_data.get('is_staff', False),
            'is_superuser': user_data.get('is_superuser', False)
        }
    )
    if created:
        user.set_password('Admin@2025')
        user.save()
        print(f"✅ Utilisateur créé: {user.username}")
    else:
        print(f"ℹ️  Utilisateur existant: {user.username}")
    users.append(user)

# ============================================================================
# 2. CRÉER DES CATÉGORIES D'ACTIFS (ArchiMate)
# ============================================================================
print("\n📁 Création des catégories d'actifs ArchiMate...")

categories_data = [
    {
        'code': 'STRATEGY',
        'nom': 'Stratégie',
        'description': 'Éléments stratégiques : capacités, ressources, flux de valeur et plans d\'action'
    },
    {
        'code': 'BUSINESS',
        'nom': 'Métier',
        'description': 'Couche métier : processus, fonctions, services, acteurs et objets métier'
    },
    {
        'code': 'APPLICATION',
        'nom': 'Application',
        'description': 'Couche applicative : composants, services, fonctions et objets de données'
    },
    {
        'code': 'TECHNOLOGY',
        'nom': 'Technologie',
        'description': 'Infrastructure technologique : nœuds, dispositifs, logiciels système et services'
    },
    {
        'code': 'PHYSICAL',
        'nom': 'Physique',
        'description': 'Éléments physiques : équipements, installations, réseaux et matériaux'
    },
    {
        'code': 'MOTIVATION',
        'nom': 'Motivation',
        'description': 'Motivations et exigences : objectifs, principes, contraintes et valeurs'
    },
    {
        'code': 'IMPLEMENTATION',
        'nom': 'Implémentation & migration',
        'description': 'Éléments d\'implémentation : lots de travaux, livrables, paliers et écarts'
    }
]

categories = {}
for cat_data in categories_data:
    categorie, created = CategorieActif.objects.get_or_create(
        code=cat_data['code'],
        defaults={
            'nom': cat_data['nom'],
            'description': cat_data['description']
        }
    )
    if created:
        print(f"✅ Catégorie créée: {categorie.nom}")
    else:
        print(f"ℹ️  Catégorie existante: {categorie.nom}")
    categories[cat_data['code']] = categorie

# ============================================================================
# 3. CRÉER DES TYPES D'ACTIFS (ArchiMate complet)
# ============================================================================
print("\n📋 Création des types d'actifs ArchiMate...")

types_actifs_data = [
    # STRATÉGIE
    {'code': 'CAPABILITY', 'nom': 'Capacité', 'categorie': 'STRATEGY'},
    {'code': 'RESOURCE', 'nom': 'Ressource', 'categorie': 'STRATEGY'},
    {'code': 'VALUESTREAM', 'nom': 'Flux de valeur', 'categorie': 'STRATEGY'},
    {'code': 'COURSEOFACTION', 'nom': 'Plan d\'action', 'categorie': 'STRATEGY'},
    
    # MÉTIER
    {'code': 'BUSINESSACTOR', 'nom': 'Acteur métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSROLE', 'nom': 'Rôle métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSCOLLABORATION', 'nom': 'Collaboration métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSINTERFACE', 'nom': 'Interface métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSPROCESS', 'nom': 'Processus métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSFUNCTION', 'nom': 'Fonction métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSINTERACTION', 'nom': 'Interaction métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSEVENT', 'nom': 'Événement métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSSERVICE', 'nom': 'Service métier', 'categorie': 'BUSINESS'},
    {'code': 'BUSINESSOBJECT', 'nom': 'Objet métier', 'categorie': 'BUSINESS'},
    {'code': 'CONTRACT', 'nom': 'Contrat', 'categorie': 'BUSINESS'},
    {'code': 'REPRESENTATION', 'nom': 'Représentation', 'categorie': 'BUSINESS'},
    {'code': 'PRODUCT', 'nom': 'Produit', 'categorie': 'BUSINESS'},
    
    # APPLICATION
    {'code': 'APPLICATIONCOMPONENT', 'nom': 'Composant applicatif', 'categorie': 'APPLICATION'},
    {'code': 'APPLICATIONCOLLABORATION', 'nom': 'Collaboration applicative', 'categorie': 'APPLICATION'},
    {'code': 'APPLICATIONINTERFACE', 'nom': 'Interface applicative', 'categorie': 'APPLICATION'},
    {'code': 'APPLICATIONFUNCTION', 'nom': 'Fonction applicative', 'categorie': 'APPLICATION'},
    {'code': 'APPLICATIONINTERACTION', 'nom': 'Interaction applicative', 'categorie': 'APPLICATION'},
    {'code': 'APPLICATIONPROCESS', 'nom': 'Processus applicatif', 'categorie': 'APPLICATION'},
    {'code': 'APPLICATIONEVENT', 'nom': 'Événement applicatif', 'categorie': 'APPLICATION'},
    {'code': 'APPLICATIONSERVICE', 'nom': 'Service applicatif', 'categorie': 'APPLICATION'},
    {'code': 'DATAOBJECT', 'nom': 'Objet de données', 'categorie': 'APPLICATION'},
    
    # TECHNOLOGIE
    {'code': 'NODE', 'nom': 'Nœud', 'categorie': 'TECHNOLOGY'},
    {'code': 'DEVICE', 'nom': 'Dispositif', 'categorie': 'TECHNOLOGY'},
    {'code': 'SYSTEMSOFTWARE', 'nom': 'Logiciel système', 'categorie': 'TECHNOLOGY'},
    {'code': 'TECHNOLOGYCOLLABORATION', 'nom': 'Collaboration technologique', 'categorie': 'TECHNOLOGY'},
    {'code': 'TECHNOLOGYINTERFACE', 'nom': 'Interface technologique', 'categorie': 'TECHNOLOGY'},
    {'code': 'TECHNOLOGYFUNCTION', 'nom': 'Fonction technologique', 'categorie': 'TECHNOLOGY'},
    {'code': 'TECHNOLOGYINTERACTION', 'nom': 'Interaction technologique', 'categorie': 'TECHNOLOGY'},
    {'code': 'TECHNOLOGYPROCESS', 'nom': 'Processus technologique', 'categorie': 'TECHNOLOGY'},
    {'code': 'TECHNOLOGYEVENT', 'nom': 'Événement technologique', 'categorie': 'TECHNOLOGY'},
    {'code': 'TECHNOLOGYSERVICE', 'nom': 'Service technologique', 'categorie': 'TECHNOLOGY'},
    {'code': 'PATH', 'nom': 'Chemin', 'categorie': 'TECHNOLOGY'},
    {'code': 'COMMUNICATIONPATH', 'nom': 'Chemin de communication', 'categorie': 'TECHNOLOGY'},
    {'code': 'ARTIFACT', 'nom': 'Artéfact', 'categorie': 'TECHNOLOGY'},
    
    # PHYSIQUE
    {'code': 'EQUIPMENT', 'nom': 'Équipement', 'categorie': 'PHYSICAL'},
    {'code': 'FACILITY', 'nom': 'Installation', 'categorie': 'PHYSICAL'},
    {'code': 'DISTRIBUTIONNETWORK', 'nom': 'Réseau de distribution', 'categorie': 'PHYSICAL'},
    {'code': 'MATERIAL', 'nom': 'Matériau', 'categorie': 'PHYSICAL'},
    
    # MOTIVATION
    {'code': 'STAKEHOLDER', 'nom': 'Partie prenante', 'categorie': 'MOTIVATION'},
    {'code': 'DRIVER', 'nom': 'Facteur moteur', 'categorie': 'MOTIVATION'},
    {'code': 'ASSESSMENT', 'nom': 'Évaluation', 'categorie': 'MOTIVATION'},
    {'code': 'GOAL', 'nom': 'Objectif', 'categorie': 'MOTIVATION'},
    {'code': 'OUTCOME', 'nom': 'Résultat', 'categorie': 'MOTIVATION'},
    {'code': 'PRINCIPLE', 'nom': 'Principe', 'categorie': 'MOTIVATION'},
    {'code': 'REQUIREMENT', 'nom': 'Exigence', 'categorie': 'MOTIVATION'},
    {'code': 'CONSTRAINT', 'nom': 'Contrainte', 'categorie': 'MOTIVATION'},
    {'code': 'MEANING', 'nom': 'Signification', 'categorie': 'MOTIVATION'},
    {'code': 'VALUE', 'nom': 'Valeur', 'categorie': 'MOTIVATION'},
    {'code': 'RISK', 'nom': 'Risque', 'categorie': 'MOTIVATION'},
    
    # IMPLÉMENTATION & MIGRATION
    {'code': 'WORKPACKAGE', 'nom': 'Lot de travaux', 'categorie': 'IMPLEMENTATION'},
    {'code': 'DELIVERABLE', 'nom': 'Livrable', 'categorie': 'IMPLEMENTATION'},
    {'code': 'PLATEAU', 'nom': 'Palier', 'categorie': 'IMPLEMENTATION'},
    {'code': 'GAP', 'nom': 'Écart', 'categorie': 'IMPLEMENTATION'},
]

types_actifs = {}
for type_data in types_actifs_data:
    categorie = categories[type_data['categorie']]
    type_actif, created = TypeActif.objects.get_or_create(
        code=type_data['code'],
        defaults={
            'nom': type_data['nom'],
            'categorie': categorie
        }
    )
    if created:
        print(f"✅ Type d'actif créé: {type_actif.nom}")
    else:
        print(f"ℹ️  Type d'actif existant: {type_actif.nom}")
    types_actifs[type_data['code']] = type_actif

# ============================================================================
# 4. CRÉER DES ARCHITECTURES
# ============================================================================
print("\n🏗️  Création des architectures...")

architectures_data = [
    {
        'nom': 'Infrastructure Production gmail',
        'description': 'Architecture de production pour les services critiques gmail Bénin',
        'risque_tolere': Decimal('750000.00')  # $750K budget risque
    },
    {
        'nom': 'Infrastructure Développement',
        'description': 'Environnement de développement, test et staging',
        'risque_tolere': Decimal('150000.00')  # $150K budget risque
    },
    {
        'nom': 'Plateforme Mobile Money',
        'description': 'Système de paiement mobile et services financiers',
        'risque_tolere': Decimal('1200000.00')  # $1.2M budget risque (critique)
    },
    {
        'nom': 'Réseau Télécommunications',
        'description': 'Infrastructure réseau national et équipements télécoms',
        'risque_tolere': Decimal('900000.00')  # $900K budget risque
    },
    {
        'nom': 'Système d\'Information Client',
        'description': 'CRM, portail client et applications métier',
        'risque_tolere': Decimal('500000.00')  # $500K budget risque
    },
]

architectures = []
for arch_data in architectures_data:
    architecture, created = Architecture.objects.get_or_create(
        nom=arch_data['nom'],
        defaults={
            'description': arch_data['description'],
            'risque_tolere': arch_data['risque_tolere']
        }
    )
    if created:
        print(f"✅ Architecture créée: {architecture.nom}")
    else:
        print(f"ℹ️  Architecture existante: {architecture.nom}")
    architectures.append(architecture)

# ============================================================================
# 5. CRÉER DES ACTIFS RÉALISTES (Montants en USD)
# ============================================================================
print("\n💻 Création des actifs avec montants en USD...")

actifs_templates = [
    # NŒUDS CRITIQUES (Serveurs Production)
    {'nom': 'Serveur Web Production', 'type': 'NODE', 'criticite': 'CRITIQUE', 'cout': 85000,
     'description': 'Serveur web principal pour les services en ligne'},
    {'nom': 'Serveur Base de Données Oracle', 'type': 'NODE', 'criticite': 'CRITIQUE', 'cout': 120000,
     'description': 'Serveur de base de données principale'},
    {'nom': 'Serveur Application Business', 'type': 'NODE', 'criticite': 'CRITIQUE', 'cout': 95000,
     'description': 'Serveur d\'applications métier critiques'},
    {'nom': 'Serveur Backup Principal', 'type': 'NODE', 'criticite': 'ELEVE', 'cout': 65000,
     'description': 'Infrastructure de sauvegarde'},
    {'nom': 'Serveur Active Directory', 'type': 'NODE', 'criticite': 'CRITIQUE', 'cout': 55000,
     'description': 'Contrôleur de domaine Active Directory'},
    
    # DISPOSITIFS RÉSEAU
    {'nom': 'Routeur Core Cisco', 'type': 'DEVICE', 'criticite': 'CRITIQUE', 'cout': 180000,
     'description': 'Routeur principal du réseau'},
    {'nom': 'Switch Datacenter', 'type': 'DEVICE', 'criticite': 'CRITIQUE', 'cout': 95000,
     'description': 'Switch principal du datacenter'},
    {'nom': 'Firewall Périmètre Palo Alto', 'type': 'DEVICE', 'criticite': 'CRITIQUE', 'cout': 145000,
     'description': 'Pare-feu périmétrique nouvelle génération'},
    {'nom': 'Load Balancer F5', 'type': 'DEVICE', 'criticite': 'ELEVE', 'cout': 110000,
     'description': 'Équilibreur de charge'},
    {'nom': 'IPS/IDS Fortinet', 'type': 'DEVICE', 'criticite': 'ELEVE', 'cout': 75000,
     'description': 'Système de prévention d\'intrusion'},
    
    # COMPOSANTS APPLICATIFS
    {'nom': 'Portail Web Client', 'type': 'APPLICATIONCOMPONENT', 'criticite': 'CRITIQUE', 'cout': 250000,
     'description': 'Application web pour les clients'},
    {'nom': 'Application Mobile Money', 'type': 'APPLICATIONCOMPONENT', 'criticite': 'CRITIQUE', 'cout': 350000,
     'description': 'Application de paiement mobile'},
    {'nom': 'API Gateway Enterprise', 'type': 'APPLICATIONCOMPONENT', 'criticite': 'ELEVE', 'cout': 125000,
     'description': 'Passerelle API pour les intégrations'},
    {'nom': 'Système CRM Salesforce', 'type': 'APPLICATIONCOMPONENT', 'criticite': 'ELEVE', 'cout': 180000,
     'description': 'Gestion de la relation client'},
    {'nom': 'ERP SAP', 'type': 'APPLICATIONCOMPONENT', 'criticite': 'CRITIQUE', 'cout': 850000,
     'description': 'Enterprise Resource Planning'},
    
    # SERVICES APPLICATIFS
    {'nom': 'Service d\'Authentification SSO', 'type': 'APPLICATIONSERVICE', 'criticite': 'CRITIQUE', 'cout': 95000,
     'description': 'Single Sign-On pour l\'entreprise'},
    {'nom': 'Service de Notification Push', 'type': 'APPLICATIONSERVICE', 'criticite': 'ELEVE', 'cout': 45000,
     'description': 'Notifications temps réel'},
    {'nom': 'Service de Géolocalisation', 'type': 'APPLICATIONSERVICE', 'criticite': 'MOYEN', 'cout': 35000,
     'description': 'Services de localisation'},
    
    # OBJETS DE DONNÉES
    {'nom': 'Base Clients', 'type': 'DATAOBJECT', 'criticite': 'CRITIQUE', 'cout': 200000,
     'description': 'Données clients sensibles'},
    {'nom': 'Base Transactions Financières', 'type': 'DATAOBJECT', 'criticite': 'CRITIQUE', 'cout': 280000,
     'description': 'Historique des transactions'},
    {'nom': 'Données de Localisation', 'type': 'DATAOBJECT', 'criticite': 'ELEVE', 'cout': 85000,
     'description': 'Données de géolocalisation'},
    {'nom': 'Logs Système', 'type': 'DATAOBJECT', 'criticite': 'MOYEN', 'cout': 45000,
     'description': 'Journaux d\'événements système'},
    
    # LOGICIELS SYSTÈME
    {'nom': 'Windows Server 2022', 'type': 'SYSTEMSOFTWARE', 'criticite': 'CRITIQUE', 'cout': 15000,
     'description': 'Système d\'exploitation serveur'},
    {'nom': 'Oracle Database 19c', 'type': 'SYSTEMSOFTWARE', 'criticite': 'CRITIQUE', 'cout': 95000,
     'description': 'Système de gestion de base de données'},
    {'nom': 'VMware vSphere', 'type': 'SYSTEMSOFTWARE', 'criticite': 'CRITIQUE', 'cout': 125000,
     'description': 'Plateforme de virtualisation'},
    {'nom': 'Red Hat Enterprise Linux', 'type': 'SYSTEMSOFTWARE', 'criticite': 'ELEVE', 'cout': 12000,
     'description': 'Système d\'exploitation Linux'},
    
    # ÉQUIPEMENTS PHYSIQUES
    {'nom': 'Onduleur APC 100kVA', 'type': 'EQUIPMENT', 'criticite': 'CRITIQUE', 'cout': 85000,
     'description': 'Alimentation sans interruption'},
    {'nom': 'Groupe Électrogène Caterpillar', 'type': 'EQUIPMENT', 'criticite': 'CRITIQUE', 'cout': 150000,
     'description': 'Générateur de secours'},
    {'nom': 'Système Climatisation Datacenter', 'type': 'EQUIPMENT', 'criticite': 'CRITIQUE', 'cout': 95000,
     'description': 'Système de refroidissement'},
    {'nom': 'Baie Serveur 42U', 'type': 'EQUIPMENT', 'criticite': 'ELEVE', 'cout': 12000,
     'description': 'Rack serveur'},
    
    # INSTALLATIONS
    {'nom': 'Datacenter Principal Cotonou', 'type': 'FACILITY', 'criticite': 'CRITIQUE', 'cout': 2500000,
     'description': 'Centre de données principal'},
    {'nom': 'Salle Serveurs Site Secondaire', 'type': 'FACILITY', 'criticite': 'ELEVE', 'cout': 450000,
     'description': 'Site de secours'},
    {'nom': 'Bureau Sécurité NOC/SOC', 'type': 'FACILITY', 'criticite': 'ELEVE', 'cout': 180000,
     'description': 'Centre de surveillance'},
    
    # ARTÉFACTS
    {'nom': 'Image Docker Application', 'type': 'ARTIFACT', 'criticite': 'ELEVE', 'cout': 25000,
     'description': 'Conteneur applicatif'},
    {'nom': 'Package Deployment Production', 'type': 'ARTIFACT', 'criticite': 'ELEVE', 'cout': 35000,
     'description': 'Package de déploiement'},
]

actifs = []
for actif_template in actifs_templates:
    # Choisir une architecture appropriée
    if 'Mobile Money' in actif_template['nom'] or 'Transaction' in actif_template['nom']:
        architecture = [a for a in architectures if 'Mobile Money' in a.nom][0]
    elif 'Développement' in actif_template['nom'] or 'Test' in actif_template['nom']:
        architecture = [a for a in architectures if 'Développement' in a.nom][0]
    elif 'Routeur' in actif_template['nom'] or 'Switch' in actif_template['nom'] or 'Firewall' in actif_template['nom']:
        architecture = [a for a in architectures if 'Réseau' in a.nom][0]
    elif 'CRM' in actif_template['nom'] or 'Portal' in actif_template['nom'] or 'Client' in actif_template['nom']:
        architecture = [a for a in architectures if 'Client' in a.nom][0]
    else:
        architecture = architectures[0]  # Infrastructure Production par défaut
    
    # Choisir un propriétaire
    proprietaire = random.choice(users)
    
    # Récupérer le type d'actif
    type_actif = types_actifs[actif_template['type']]
    
    actif, created = Actif.objects.get_or_create(
        nom=actif_template['nom'],
        architecture=architecture,
        defaults={
            'type_actif': type_actif,
            'description': actif_template['description'],
            'proprietaire': proprietaire,
            'criticite': actif_template['criticite'],
            'cout': Decimal(str(actif_template['cout']))
        }
    )
    if created:
        print(f"✅ Actif créé: {actif.nom} (${actif.cout:,.2f})")
    else:
        print(f"ℹ️  Actif existant: {actif.nom}")
    actifs.append(actif)

# ============================================================================
# 6. CRÉER DES ATTRIBUTS DE SÉCURITÉ
# ============================================================================
print("\n🔒 Création des attributs de sécurité...")

attributs_types = ['CONFIDENTIALITE', 'INTEGRITE', 'DISPONIBILITE', 'TRACABILITE']

attributs = []
for actif in actifs:
    # Créer 2-4 attributs par actif selon sa criticité
    if actif.criticite == 'CRITIQUE':
        nb_attributs = 4
        selected_types = attributs_types
    elif actif.criticite == 'ELEVE':
        nb_attributs = 3
        selected_types = random.sample(attributs_types, 3)
    else:
        nb_attributs = 2
        selected_types = random.sample(attributs_types, 2)
    
    for attr_type in selected_types:
        # Calculer le coût de compromission (en USD) basé sur la criticité
        cout_base = float(actif.cout)
        
        if actif.criticite == 'CRITIQUE':
            # Pour les actifs critiques, le coût de compromission est élevé
            multiplicateur = random.uniform(1.2, 2.5)
        elif actif.criticite == 'ELEVE':
            multiplicateur = random.uniform(0.8, 1.5)
        elif actif.criticite == 'MOYEN':
            multiplicateur = random.uniform(0.5, 1.0)
        else:
            multiplicateur = random.uniform(0.2, 0.6)
        
        cout_compromission = cout_base * multiplicateur
        
        # Priorité basée sur la criticité
        if actif.criticite == 'CRITIQUE':
            priorite = random.choice(['P0', 'P1'])
        elif actif.criticite == 'ELEVE':
            priorite = random.choice(['P1', 'P2'])
        else:
            priorite = random.choice(['P2', 'P3'])
        
        attribut, created = AttributSecurite.objects.get_or_create(
            actif=actif,
            type_attribut=attr_type,
            defaults={
                'cout_compromission': Decimal(str(round(cout_compromission, 2))),
                'priorite': priorite
            }
        )
        if created:
            attributs.append(attribut)

print(f"✅ {len(attributs)} attributs de sécurité créés")

# ============================================================================
# 7. CRÉER DES MENACES
# ============================================================================
print("\n⚠️  Création des menaces...")

menaces_data = [
    # Menaces STRIDE
    {'nom': 'Usurpation d\'identité (Spoofing)', 'type': 'Spoofing', 'severite': 'CRITIQUE', 
     'description': 'Tentative d\'usurpation de l\'identité d\'un utilisateur ou système légitime'},
    {'nom': 'Modification non autorisée (Tampering)', 'type': 'Tampering', 'severite': 'CRITIQUE',
     'description': 'Modification malveillante des données, code ou configurations'},
    {'nom': 'Répudiation des actions', 'type': 'Repudiation', 'severite': 'ELEVE',
     'description': 'Impossibilité de prouver qu\'une action a été effectuée'},
    {'nom': 'Divulgation d\'information sensible', 'type': 'Information_Disclosure', 'severite': 'CRITIQUE',
     'description': 'Exposition non autorisée de données confidentielles'},
    {'nom': 'Déni de service (DoS/DDoS)', 'type': 'Denial_of_Service', 'severite': 'ELEVE',
     'description': 'Interruption ou dégradation de la disponibilité des services'},
    {'nom': 'Élévation de privilèges', 'type': 'Elevation_of_Privilege', 'severite': 'CRITIQUE',
     'description': 'Obtention de droits d\'accès supérieurs non autorisés'},
    
    # Menaces applicatives
    {'nom': 'Injection SQL', 'type': 'Tampering', 'severite': 'CRITIQUE',
     'description': 'Injection de code SQL malveillant dans les requêtes'},
    {'nom': 'Cross-Site Scripting (XSS)', 'type': 'Tampering', 'severite': 'ELEVE',
     'description': 'Injection de scripts malveillants dans les pages web'},
    {'nom': 'Cross-Site Request Forgery (CSRF)', 'type': 'Tampering', 'severite': 'ELEVE',
     'description': 'Exécution d\'actions non autorisées au nom d\'un utilisateur'},
    {'nom': 'Faille d\'authentification', 'type': 'Spoofing', 'severite': 'CRITIQUE',
     'description': 'Contournement ou faiblesse des mécanismes d\'authentification'},
    {'nom': 'Gestion incorrecte des sessions', 'type': 'Spoofing', 'severite': 'ELEVE',
     'description': 'Vulnérabilités dans la gestion des sessions utilisateur'},
    
    # Menaces réseau
    {'nom': 'Attaque Man-in-the-Middle (MitM)', 'type': 'Information_Disclosure', 'severite': 'CRITIQUE',
     'description': 'Interception et modification des communications réseau'},
    {'nom': 'Attaque par force brute', 'type': 'Spoofing', 'severite': 'ELEVE',
     'description': 'Tentatives répétées de devinement de mots de passe'},
    {'nom': 'Scan de ports et reconnaissance', 'type': 'Information_Disclosure', 'severite': 'MOYEN',
     'description': 'Collecte d\'informations sur l\'infrastructure réseau'},
    {'nom': 'ARP Spoofing', 'type': 'Spoofing', 'severite': 'ELEVE',
     'description': 'Falsification des tables ARP pour rediriger le trafic'},
    
    # Malware et ransomware
    {'nom': 'Ransomware', 'type': 'Denial_of_Service', 'severite': 'CRITIQUE',
     'description': 'Chiffrement malveillant des données avec demande de rançon'},
    {'nom': 'Trojan / Cheval de Troie', 'type': 'Tampering', 'severite': 'ELEVE',
     'description': 'Logiciel malveillant déguisé en programme légitime'},
    {'nom': 'Rootkit', 'type': 'Elevation_of_Privilege', 'severite': 'CRITIQUE',
     'description': 'Logiciel malveillant furtif avec privilèges système'},
    {'nom': 'Spyware', 'type': 'Information_Disclosure', 'severite': 'ELEVE',
     'description': 'Logiciel espion collectant des informations sensibles'},
    {'nom': 'Virus / Worm', 'type': 'Tampering', 'severite': 'ELEVE',
     'description': 'Logiciel malveillant auto-réplicatif'},
    
    # Menaces d'ingénierie sociale
    {'nom': 'Phishing', 'type': 'Spoofing', 'severite': 'ELEVE',
     'description': 'Tentative de récupération d\'informations par tromperie'},
    {'nom': 'Spear Phishing', 'type': 'Spoofing', 'severite': 'CRITIQUE',
     'description': 'Attaque de phishing ciblée sur des individus spécifiques'},
    {'nom': 'Vishing (Voice Phishing)', 'type': 'Spoofing', 'severite': 'MOYEN',
     'description': 'Fraude par téléphone pour obtenir des informations'},
    {'nom': 'Smishing (SMS Phishing)', 'type': 'Spoofing', 'severite': 'MOYEN',
     'description': 'Phishing par SMS'},
    
    # Menaces physiques
    {'nom': 'Accès physique non autorisé', 'type': 'Elevation_of_Privilege', 'severite': 'ELEVE',
     'description': 'Intrusion physique dans les locaux ou salles serveurs'},
    {'nom': 'Vol de matériel', 'type': 'Information_Disclosure', 'severite': 'ELEVE',
     'description': 'Vol d\'équipements contenant des données sensibles'},
    {'nom': 'Destruction physique', 'type': 'Denial_of_Service', 'severite': 'CRITIQUE',
     'description': 'Sabotage ou destruction d\'infrastructure'},
    
    # Menaces internes
    {'nom': 'Menace interne malveillante', 'type': 'Information_Disclosure', 'severite': 'CRITIQUE',
     'description': 'Employé ou contractant agissant de manière malveillante'},
    {'nom': 'Erreur humaine', 'type': 'Tampering', 'severite': 'MOYEN',
     'description': 'Erreurs involontaires causant des incidents de sécurité'},
    {'nom': 'Fuite de données par négligence', 'type': 'Information_Disclosure', 'severite': 'ELEVE',
     'description': 'Exposition accidentelle de données sensibles'},
    
    # Menaces avancées
    {'nom': 'Advanced Persistent Threat (APT)', 'type': 'Information_Disclosure', 'severite': 'CRITIQUE',
     'description': 'Attaque sophistiquée et persistante par un acteur étatique'},
    {'nom': 'Zero-Day Exploit', 'type': 'Elevation_of_Privilege', 'severite': 'CRITIQUE',
     'description': 'Exploitation de vulnérabilité inconnue sans correctif'},
    {'nom': 'Supply Chain Attack', 'type': 'Tampering', 'severite': 'CRITIQUE',
     'description': 'Compromission via la chaîne d\'approvisionnement logicielle'},
]

menaces = []
for menace_data in menaces_data:
    menace, created = Menace.objects.get_or_create(
        nom=menace_data['nom'],
        defaults={
            'description': menace_data['description'],
            'type_menace': menace_data['type'],
            'severite': menace_data['severite']
        }
    )
    if created:
        print(f"✅ Menace créée: {menace.nom}")
    else:
        print(f"ℹ️  Menace existante: {menace.nom}")
    menaces.append(menace)

# ============================================================================
# 8. ASSOCIER MENACES AUX ATTRIBUTS (Probabilités réalistes)
# ============================================================================
print("\n🔗 Association menaces <-> attributs...")

associations_created = 0
for attribut in attributs:
    # Nombre de menaces selon la criticité de l'actif
    if attribut.actif.criticite == 'CRITIQUE':
        nb_menaces = random.randint(4, 6)
    elif attribut.actif.criticite == 'ELEVE':
        nb_menaces = random.randint(3, 5)
    else:
        nb_menaces = random.randint(2, 4)
    
    selected_menaces = random.sample(menaces, min(nb_menaces, len(menaces)))
    
    for menace in selected_menaces:
        # Probabilité basée sur la sévérité de la menace
        if menace.severite == 'CRITIQUE':
            probabilite = Decimal(str(random.randint(30, 70)))
        elif menace.severite == 'ELEVE':
            probabilite = Decimal(str(random.randint(20, 50)))
        else:
            probabilite = Decimal(str(random.randint(10, 30)))
        
        # Impact toujours 100% (max)
        impact = Decimal('100.0')
        cout_impact = attribut.cout_compromission
        
        # Créer l'association
        assoc, created = AttributMenace.objects.get_or_create(
            attribut_securite=attribut,
            menace=menace,
            defaults={
                'probabilite': probabilite,
                'impact': impact,
                'cout_impact': cout_impact
            }
        )
        if created:
            associations_created += 1

print(f"✅ {associations_created} associations attributs-menaces créées")

# ============================================================================
# 9. ASSOCIER MENACES ET MESURES
# ============================================================================
print("\n🔗 Association menaces <-> mesures...")

# Récupérer les techniques et mesures existantes
techniques = list(Technique.objects.all()[:100])
mesures = list(MesureDeControle.objects.all()[:200])

if techniques and mesures:
    menace_mesure_created = 0
    for menace in menaces:
        # Associer 4-8 mesures par menace
        nb_mesures = random.randint(4, min(8, len(mesures)))
        selected_mesures = random.sample(mesures, nb_mesures)
        
        for mesure in selected_mesures:
            # Efficacité réaliste basée sur la nature de la mesure
            if mesure.nature_mesure == 'TECHNIQUE':
                efficacite = Decimal(str(random.randint(70, 95)))
            elif mesure.nature_mesure == 'ORGANISATIONNEL':
                efficacite = Decimal(str(random.randint(60, 85)))
            else:
                efficacite = Decimal(str(random.randint(65, 90)))
            
            statut = random.choice(['NON_CONFORME', 'PARTIELLEMENT', 'CONFORME'])
            
            assoc, created = MenaceMesure.objects.get_or_create(
                menace=menace,
                mesure_controle=mesure,
                defaults={
                    'efficacite': efficacite,
                    'statut_conformite': statut,
                    'commentaires': f'Mesure {mesure.mesure_code} pour traiter {menace.nom}'
                }
            )
            if created:
                menace_mesure_created += 1
    
    print(f"✅ {menace_mesure_created} associations menaces-mesures créées")
else:
    print("⚠️  Pas de techniques ou mesures disponibles")
    print("    Veuillez importer les techniques et mesures avant de relancer")

# ============================================================================
# 10. CRÉER DES IMPLÉMENTATIONS
# ============================================================================
print("\n📅 Création des implémentations...")

if AttributMenace.objects.exists() and mesures:
    implementations_created = 0
    
    # Sélectionner les associations avec les risques les plus élevés
    attr_menaces = list(AttributMenace.objects.all().order_by('-probabilite')[:50])
    
    for attr_menace in attr_menaces:
        # Choisir 1-3 mesures à implémenter selon le risque
        if attr_menace.niveau_risque >= 70:
            nb_impl = random.randint(2, 3)
        elif attr_menace.niveau_risque >= 40:
            nb_impl = random.randint(1, 2)
        else:
            nb_impl = 1
        
        selected_mesures = random.sample(mesures, min(nb_impl, len(mesures)))
        
        for mesure in selected_mesures:
            statut = random.choice(['PLANIFIE', 'EN_COURS', 'IMPLEMENTE', 'VERIFIE'])
            responsable = random.choice(users)
            
            # Dates réalistes
            date_debut = timezone.now() - timedelta(days=random.randint(1, 90))
            duree = random.randint(30, 120)
            date_fin = date_debut + timedelta(days=duree)
            
            # Pourcentage selon le statut
            pourcentage_map = {
                'PLANIFIE': 0,
                'EN_COURS': random.randint(15, 75),
                'IMPLEMENTE': 100,
                'VERIFIE': 100
            }
            pourcentage = pourcentage_map[statut]
            
            impl, created = ImplementationMesure.objects.get_or_create(
                attribut_menace=attr_menace,
                mesure_controle=mesure,
                defaults={
                    'statut': statut,
                    'responsable': responsable,
                    'date_debut_prevue': date_debut.date(),
                    'date_fin_prevue': date_fin.date(),
                    'pourcentage_avancement': pourcentage,
                    'commentaires': f'Implémentation de {mesure.nom} pour {attr_menace.menace.nom}'
                }
            )
            if created:
                if statut in ['IMPLEMENTE', 'VERIFIE']:
                    impl.date_implementation = date_fin
                    impl.save()
                implementations_created += 1
    
    print(f"✅ {implementations_created} implémentations créées")
else:
    print("⚠️  Pas d'associations ou de mesures disponibles")

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
print("\n" + "="*80)
print("📊 RÉSUMÉ DE LA GÉNÉRATION (ArchiMate + USD)")
print("="*80)
print(f"👥 Utilisateurs: {User.objects.count()}")
print(f"📁 Catégories d'actifs ArchiMate: {CategorieActif.objects.count()}")
print(f"📋 Types d'actifs ArchiMate: {TypeActif.objects.count()}")
print(f"🏗️  Architectures: {Architecture.objects.count()}")
print(f"💻 Actifs: {Actif.objects.count()}")
print(f"🔒 Attributs de sécurité: {AttributSecurite.objects.count()}")
print(f"⚠️  Menaces: {Menace.objects.count()}")
print(f"🔗 Associations attributs-menaces: {AttributMenace.objects.count()}")
print(f"🛡️  Techniques: {Technique.objects.count()}")
print(f"🔧 Mesures de contrôle: {MesureDeControle.objects.count()}")
print(f"🔗 Associations menaces-mesures: {MenaceMesure.objects.count()}")
print(f"📅 Implémentations: {ImplementationMesure.objects.count()}")

# Calculs financiers
total_cout_actifs = sum(float(a.cout) for a in Actif.objects.all())
total_risque_architectures = sum(float(a.risque_tolere) for a in Architecture.objects.all())

print(f"\n💰 STATISTIQUES FINANCIÈRES (USD)")
print(f"   Valeur totale des actifs: ${total_cout_actifs:,.2f}")
print(f"   Budget risque total: ${total_risque_architectures:,.2f}")

print("="*80)
print("\n✅ GÉNÉRATION TERMINÉE AVEC SUCCÈS !")
print("\n🔐 Credentials pour se connecter:")
for user_data in users_data:
    print(f"   - Username: {user_data['username']} | Password: Admin@2025")
print("\n💡 Tous les montants sont en dollars américains (USD)")