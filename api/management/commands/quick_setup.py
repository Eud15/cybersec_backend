# api/management/commands/load_realistic_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import random

from api.models import (
    TypeActif, Architecture, Actif, AttributSecurite, Menace, AttributMenace,
    ControleNIST, MenaceControle, Technique, MesureDeControle, ImplementationMesure
)

class Command(BaseCommand):
    help = 'Charge des données réalistes basées sur les vraies techniques et mesures NIST'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Supprime toutes les données existantes avant de charger les nouvelles',
        )

    def handle(self, *args, **options):
        if options['clean']:
            self.stdout.write('Suppression des données existantes...')
            self.clean_data()

        self.stdout.write('Chargement des données réalistes...')
        
        # Créer les utilisateurs
        users = self.create_users()
        
        # Créer les types d'actifs
        types_actifs = self.create_types_actifs()
        
        # Créer les menaces
        menaces = self.create_menaces()
        
        # Créer les contrôles NIST
        controles_nist = self.create_controles_nist()
        
        # Créer les techniques réalistes
        techniques = self.create_realistic_techniques(controles_nist)
        
        # Créer les mesures de contrôle réalistes
        mesures = self.create_realistic_mesures(techniques)
        
        # Créer les associations menace-contrôle
        self.create_menace_controle_associations(menaces, controles_nist)
        
        # Créer l'architecture et les actifs
        architecture = self.create_architecture_with_actifs(types_actifs, users)
        
        # Créer les attributs de sécurité
        self.create_attributs_securite(architecture)
        
        # Créer les associations attribut-menace
        self.create_attribut_menace_associations(architecture, menaces)
        
        # Créer les implémentations
        self.create_implementations(users)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nDonnées réalistes chargées avec succès!\n'
                f'Architecture: {architecture.nom}\n'
                f'Techniques: {len(techniques)}\n'
                f'Mesures: {len(mesures)}\n'
                'Utilisateur test: testuser/test123'
            )
        )

    def clean_data(self):
        """Supprime toutes les données existantes"""
        models_to_clean = [
            ImplementationMesure, MesureDeControle, Technique,
            MenaceControle, AttributMenace, AttributSecurite,
            Actif, Architecture, ControleNIST, Menace, TypeActif
        ]
        
        for model in models_to_clean:
            model.objects.all().delete()
        
        User.objects.filter(is_superuser=False).delete()

    def create_users(self):
        """Crée des utilisateurs de test"""
        users_data = [
            {'username': 'testuser', 'password': 'test123', 'first_name': 'Test', 'last_name': 'User'},
            {'username': 'rssi', 'password': 'rssi123', 'first_name': 'Marie', 'last_name': 'RSSI'},
            {'username': 'admin_it', 'password': 'admin123', 'first_name': 'Jean', 'last_name': 'Admin'},
        ]
        
        users = []
        for data in users_data:
            password = data.pop('password')
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={**data, 'email': f"{data['username']}@entreprise.com", 'is_staff': True}
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'Utilisateur créé: {user.username}/{password}')
            users.append(user)
        
        return users

    def create_types_actifs(self):
        """Crée les types d'actifs"""
        types_data = [
            'Serveur', 'Application', 'Base de Données', 'Réseau', 
            'Poste de Travail', 'Infrastructure Cloud'
        ]
        
        types = []
        for nom in types_data:
            type_actif, _ = TypeActif.objects.get_or_create(
                nom=nom,
                defaults={'description': f'Type {nom}'}
            )
            types.append(type_actif)
        
        return types

    def create_menaces(self):
        """Crée le catalogue des menaces"""
        menaces_data = [
            {'nom': 'Ransomware', 'type_menace': 'MALWARE', 'severite': 'CRITIQUE'},
            {'nom': 'Attaque DDoS', 'type_menace': 'INTRUSION', 'severite': 'ELEVE'},
            {'nom': 'Phishing', 'type_menace': 'HUMAIN', 'severite': 'ELEVE'},
            {'nom': 'Injection SQL', 'type_menace': 'INTRUSION', 'severite': 'ELEVE'},
            {'nom': 'Vol de données', 'type_menace': 'HUMAIN', 'severite': 'CRITIQUE'},
            {'nom': 'Panne matérielle', 'type_menace': 'PANNE', 'severite': 'MOYEN'},
        ]
        
        menaces = []
        for data in menaces_data:
            menace, _ = Menace.objects.get_or_create(
                nom=data['nom'],
                defaults={
                    **data,
                    'description': f"Description de {data['nom']}"
                }
            )
            menaces.append(menace)
        
        return menaces

    def create_controles_nist(self):
        """Crée les contrôles NIST"""
        controles_data = [
            {'code': 'AC-2', 'nom': 'Account Management', 'famille': 'Access Control', 'priorite': 'P1'},
            {'code': 'AC-3', 'nom': 'Access Enforcement', 'famille': 'Access Control', 'priorite': 'P1'},
            {'code': 'SC-7', 'nom': 'Boundary Protection', 'famille': 'System and Communications Protection', 'priorite': 'P1'},
            {'code': 'SI-3', 'nom': 'Malicious Code Protection', 'famille': 'System and Information Integrity', 'priorite': 'P1'},
            {'code': 'SI-4', 'nom': 'Information System Monitoring', 'famille': 'System and Information Integrity', 'priorite': 'P1'},
            {'code': 'CP-9', 'nom': 'Information System Backup', 'famille': 'Contingency Planning', 'priorite': 'P1'},
        ]
        
        controles = []
        for data in controles_data:
            controle, _ = ControleNIST.objects.get_or_create(
                code=data['code'],
                defaults={
                    **data,
                    'description': f"Description du contrôle {data['code']}"
                }
            )
            controles.append(controle)
        
        return controles

    def create_realistic_techniques(self, controles_nist):
        """Crée les techniques réalistes pour chaque contrôle NIST"""
        
        # Mapping des techniques par contrôle NIST (basé sur les vraies pratiques)
        techniques_mapping = {
            'AC-2': [
                {
                    'nom': 'Gestion centralisée des comptes utilisateurs',
                    'description': 'Mise en place d\'un annuaire centralisé (Active Directory) pour la gestion des comptes',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Processus de provisioning/deprovisioning automatisé',
                    'description': 'Automatisation de la création et suppression des comptes utilisateurs',
                    'type_technique': 'ADMINISTRATIF',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Révision périodique des comptes',
                    'description': 'Processus de révision trimestrielle des comptes actifs',
                    'type_technique': 'ADMINISTRATIF',
                    'complexite': 'MOYEN'
                }
            ],
            'AC-3': [
                {
                    'nom': 'Contrôle d\'accès basé sur les rôles (RBAC)',
                    'description': 'Implémentation d\'un système de rôles et permissions',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Contrôle d\'accès discrétionnaire (DAC)',
                    'description': 'Contrôle d\'accès basé sur la propriété des ressources',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'MOYEN'
                }
            ],
            'SC-7': [
                {
                    'nom': 'Pare-feu de périmètre',
                    'description': 'Déploiement de pare-feu pour protéger le périmètre réseau',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Segmentation réseau',
                    'description': 'Division du réseau en zones de sécurité',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Proxy web sécurisé',
                    'description': 'Filtrage et contrôle du trafic web sortant',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'MOYEN'
                }
            ],
            'SI-3': [
                {
                    'nom': 'Solution antivirus centralisée',
                    'description': 'Déploiement d\'une solution antivirus gérée centralement',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'MOYEN'
                },
                {
                    'nom': 'Protection anti-malware en temps réel',
                    'description': 'Détection et blocage en temps réel des malwares',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Sandboxing des fichiers suspects',
                    'description': 'Analyse des fichiers suspects dans un environnement isolé',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                }
            ],
            'SI-4': [
                {
                    'nom': 'SIEM (Security Information and Event Management)',
                    'description': 'Collecte et corrélation des événements de sécurité',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'IDS/IPS réseau',
                    'description': 'Système de détection/prévention d\'intrusion réseau',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Monitoring des logs système',
                    'description': 'Surveillance continue des journaux système',
                    'type_technique': 'DETECTIF',
                    'complexite': 'MOYEN'
                }
            ],
            'CP-9': [
                {
                    'nom': 'Sauvegarde automatisée quotidienne',
                    'description': 'Système de sauvegarde automatique des données critiques',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'MOYEN'
                },
                {
                    'nom': 'Sauvegarde vers site distant',
                    'description': 'Réplication des sauvegardes vers un site distant',
                    'type_technique': 'TECHNIQUE',
                    'complexite': 'ELEVE'
                },
                {
                    'nom': 'Tests de restauration périodiques',
                    'description': 'Vérification mensuelle de l\'intégrité des sauvegardes',
                    'type_technique': 'CORRECTIF',
                    'complexite': 'MOYEN'
                }
            ]
        }
        
        techniques = []
        for controle in controles_nist:
            techniques_list = techniques_mapping.get(controle.code, [])
            
            for technique_data in techniques_list:
                technique = Technique.objects.create(
                    controle_nist=controle,
                    nom=technique_data['nom'],
                    description=technique_data['description'],
                    type_technique=technique_data['type_technique'],
                    complexite=technique_data['complexite']
                )
                techniques.append(technique)
        
        self.stdout.write(f'{len(techniques)} techniques réalistes créées')
        return techniques

    def create_realistic_mesures(self, techniques):
        """Crée les mesures de contrôle réalistes pour chaque technique"""
        
        # Mapping des mesures par type de technique
        mesures_templates = {
            'gestion_comptes': [
                {
                    'nom': 'Microsoft Active Directory Premium',
                    'description': 'Solution de gestion d\'identité et d\'annuaire Active Directory avec fonctionnalités avancées',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 25000,
                    'cout_maintenance_annuel': 8000,
                    'efficacite': 92,
                    'duree_implementation': 45,
                    'ressources_necessaires': 'Administrateur système, consultant AD, 2 semaines de formation'
                },
                {
                    'nom': 'Solution IAM (Identity Access Management)',
                    'description': 'Plateforme complète de gestion des identités et des accès',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 45000,
                    'cout_maintenance_annuel': 12000,
                    'efficacite': 95,
                    'duree_implementation': 90,
                    'ressources_necessaires': 'Équipe sécurité 3 personnes, intégration SI'
                }
            ],
            'pare_feu': [
                {
                    'nom': 'Fortigate 600E Next Generation Firewall',
                    'description': 'Pare-feu nouvelle génération avec inspection profonde des paquets et prévention d\'intrusion',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 35000,
                    'cout_maintenance_annuel': 7000,
                    'efficacite': 90,
                    'duree_implementation': 30,
                    'ressources_necessaires': 'Ingénieur réseau certifié Fortinet, 1 semaine de configuration'
                },
                {
                    'nom': 'Palo Alto PA-5220 NGFW',
                    'description': 'Pare-feu avancé avec App-ID, User-ID et Content-ID',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 50000,
                    'cout_maintenance_annuel': 12000,
                    'efficacite': 95,
                    'duree_implementation': 35,
                    'ressources_necessaires': 'Expert Palo Alto, formation équipe réseau'
                }
            ],
            'antivirus': [
                {
                    'nom': 'CrowdStrike Falcon Endpoint Protection',
                    'description': 'Solution EDR cloud-native avec intelligence artificielle',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 20000,
                    'cout_maintenance_annuel': 15000,
                    'efficacite': 98,
                    'duree_implementation': 21,
                    'ressources_necessaires': 'Administrateur sécurité, déploiement sur 500 postes'
                },
                {
                    'nom': 'Microsoft Defender for Business',
                    'description': 'Solution de protection des terminaux intégrée à l\'écosystème Microsoft',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 12000,
                    'cout_maintenance_annuel': 8000,
                    'efficacite': 88,
                    'duree_implementation': 14,
                    'ressources_necessaires': 'Intégration avec environnement Office 365 existant'
                }
            ],
            'monitoring': [
                {
                    'nom': 'Splunk Enterprise Security',
                    'description': 'Plateforme SIEM complète avec analytics avancés et machine learning',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 80000,
                    'cout_maintenance_annuel': 25000,
                    'efficacite': 95,
                    'duree_implementation': 120,
                    'ressources_necessaires': 'Équipe SOC 4 personnes, consultant Splunk, formation 3 semaines'
                },
                {
                    'nom': 'QRadar SIEM d\'IBM',
                    'description': 'Solution SIEM avec corrélation automatique et détection des menaces',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 65000,
                    'cout_maintenance_annuel': 20000,
                    'efficacite': 92,
                    'duree_implementation': 90,
                    'ressources_necessaires': 'Analyste sécurité, intégration avec infrastructure existante'
                }
            ],
            'sauvegarde': [
                {
                    'nom': 'Veeam Backup & Replication Enterprise',
                    'description': 'Solution de sauvegarde et réplication pour environnements virtualisés',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 28000,
                    'cout_maintenance_annuel': 8000,
                    'efficacite': 96,
                    'duree_implementation': 30,
                    'ressources_necessaires': 'Administrateur virtualisation, stockage SAN 20TB'
                },
                {
                    'nom': 'Commvault Complete Data Protection',
                    'description': 'Plateforme unifiée de protection des données avec déduplication',
                    'nature_mesure': 'TECHNIQUE',
                    'cout_mise_en_oeuvre': 45000,
                    'cout_maintenance_annuel': 12000,
                    'efficacite': 94,
                    'duree_implementation': 45,
                    'ressources_necessaires': 'Spécialiste sauvegarde, infrastructure de stockage'
                }
            ],
            'formation': [
                {
                    'nom': 'Programme de sensibilisation KnowBe4',
                    'description': 'Formation continue de sensibilisation à la cybersécurité avec tests de phishing',
                    'nature_mesure': 'ORGANISATIONNEL',
                    'cout_mise_en_oeuvre': 8000,
                    'cout_maintenance_annuel': 6000,
                    'efficacite': 75,
                    'duree_implementation': 60,
                    'ressources_necessaires': 'Responsable formation, communication interne'
                },
                {
                    'nom': 'Certification sécurité du personnel IT',
                    'description': 'Formation et certification CISSP/CISM pour l\'équipe technique',
                    'nature_mesure': 'ORGANISATIONNEL',
                    'cout_mise_en_oeuvre': 15000,
                    'cout_maintenance_annuel': 5000,
                    'efficacite': 85,
                    'duree_implementation': 180,
                    'ressources_necessaires': 'Temps de formation 200h par personne, examens de certification'
                }
            ]
        }
        
        mesures = []
        for technique in techniques:
            # Déterminer le type de mesures selon la technique
            if 'compte' in technique.nom.lower() or 'utilisateur' in technique.nom.lower():
                mesures_type = mesures_templates['gestion_comptes']
            elif 'pare-feu' in technique.nom.lower() or 'firewall' in technique.nom.lower():
                mesures_type = mesures_templates['pare_feu']
            elif 'antivirus' in technique.nom.lower() or 'malware' in technique.nom.lower():
                mesures_type = mesures_templates['antivirus']
            elif 'monitoring' in technique.nom.lower() or 'siem' in technique.nom.lower():
                mesures_type = mesures_templates['monitoring']
            elif 'sauvegarde' in technique.nom.lower() or 'backup' in technique.nom.lower():
                mesures_type = mesures_templates['sauvegarde']
            elif technique.type_technique == 'ADMINISTRATIF':
                mesures_type = mesures_templates['formation']
            else:
                # Mesures génériques
                mesures_type = mesures_templates['antivirus']  # Par défaut
            
            # Prendre 1-2 mesures par technique
            nb_mesures = min(random.randint(1, 2), len(mesures_type))
            selected_mesures = random.sample(mesures_type, nb_mesures)
            
            for mesure_template in selected_mesures:
                # Variation de coût ±10%
                variation = random.uniform(0.9, 1.1)
                
                mesure = MesureDeControle.objects.create(
                    technique=technique,
                    nom=mesure_template['nom'],
                    description=mesure_template['description'],
                    nature_mesure=mesure_template['nature_mesure'],
                    cout_mise_en_oeuvre=Decimal(str(int(mesure_template['cout_mise_en_oeuvre'] * variation))),
                    cout_maintenance_annuel=Decimal(str(int(mesure_template['cout_maintenance_annuel'] * variation))),
                    efficacite=Decimal(str(mesure_template['efficacite'] + random.uniform(-3, 3))),
                    duree_implementation=mesure_template['duree_implementation'] + random.randint(-5, 10),
                    ressources_necessaires=mesure_template['ressources_necessaires']
                )
                mesures.append(mesure)
        
        self.stdout.write(f'{len(mesures)} mesures réalistes créées')
        return mesures

    def create_menace_controle_associations(self, menaces, controles_nist):
        """Crée les associations logiques menaces-contrôles"""
        associations = [
            ('Ransomware', ['SI-3', 'CP-9', 'AC-3']),
            ('Attaque DDoS', ['SC-7', 'SI-4']),
            ('Phishing', ['SI-3', 'AC-2', 'SI-4']),
            ('Injection SQL', ['SC-7', 'SI-4', 'AC-3']),
            ('Vol de données', ['AC-2', 'AC-3', 'SI-4']),
            ('Panne matérielle', ['CP-9', 'SI-4']),
        ]
        
        for menace_nom, controles_codes in associations:
            menace = next((m for m in menaces if m.nom == menace_nom), None)
            if not menace:
                continue
            
            for code in controles_codes:
                controle = next((c for c in controles_nist if c.code == code), None)
                if not controle:
                    continue
                
                MenaceControle.objects.get_or_create(
                    menace=menace,
                    controle_nist=controle,
                    defaults={
                        'efficacite': Decimal(str(random.uniform(75, 95))),
                        'statut_conformite': random.choice(['NON_CONFORME', 'PARTIELLEMENT', 'CONFORME']),
                        'commentaires': f'Association {menace.nom} - {controle.code}'
                    }
                )

    def create_architecture_with_actifs(self, types_actifs, users):
        """Crée l'architecture avec des actifs"""
        architecture = Architecture.objects.create(
            nom="Infrastructure SI Principal",
            description="Architecture principale du système d'information",
            risque_tolere=Decimal('15.0')
        )
        
        actifs_data = [
            {'nom': 'Serveur Web Production', 'type': 'Serveur', 'cout': 50000, 'criticite': 'CRITIQUE'},
            {'nom': 'Base de Données Clients', 'type': 'Base de Données', 'cout': 80000, 'criticite': 'CRITIQUE'},
            {'nom': 'Application ERP', 'type': 'Application', 'cout': 120000, 'criticite': 'CRITIQUE'},
            {'nom': 'Infrastructure AWS', 'type': 'Infrastructure Cloud', 'cout': 60000, 'criticite': 'ELEVE'},
            {'nom': 'Postes Utilisateurs', 'type': 'Poste de Travail', 'cout': 25000, 'criticite': 'MOYEN'},
        ]
        
        for data in actifs_data:
            type_actif = next(t for t in types_actifs if t.nom == data['type'])
            Actif.objects.create(
                nom=data['nom'],
                description=f"Description de {data['nom']}",
                cout=Decimal(str(data['cout'])),
                type_actif=type_actif,
                architecture=architecture,
                proprietaire=random.choice(users),
                criticite=data['criticite']
            )
        
        return architecture

    def create_attributs_securite(self, architecture):
        """Crée les attributs de sécurité"""
        for actif in architecture.actifs.all():
            for type_attribut in ['CONFIDENTIALITE', 'INTEGRITE', 'DISPONIBILITE']:
                if actif.criticite == 'CRITIQUE':
                    valeur_cible = random.uniform(95, 99)
                    valeur_actuelle = random.uniform(80, 94)
                    priorite = 'P1'
                elif actif.criticite == 'ELEVE':
                    valeur_cible = random.uniform(85, 95)
                    valeur_actuelle = random.uniform(70, 84)
                    priorite = 'P2'
                else:
                    valeur_cible = random.uniform(75, 90)
                    valeur_actuelle = random.uniform(60, 80)
                    priorite = 'P2'
                
                AttributSecurite.objects.create(
                    actif=actif,
                    type_attribut=type_attribut,
                    valeur_cible=Decimal(str(round(valeur_cible, 2))),
                    valeur_actuelle=Decimal(str(round(valeur_actuelle, 2))),
                    priorite=priorite
                )

    def create_attribut_menace_associations(self, architecture, menaces):
        """Crée les associations attribut-menace"""
        for actif in architecture.actifs.all():
            for attribut in actif.attributs_securite.all():
                # 2-3 menaces par attribut
                selected_menaces = random.sample(menaces, min(3, len(menaces)))
                
                for menace in selected_menaces:
                    if menace.severite == 'CRITIQUE':
                        probabilite = random.uniform(15, 40)
                        impact = random.uniform(80, 95)
                        cout_impact = random.uniform(100000, 300000)
                    elif menace.severite == 'ELEVE':
                        probabilite = random.uniform(25, 60)
                        impact = random.uniform(60, 85)
                        cout_impact = random.uniform(50000, 150000)
                    else:
                        probabilite = random.uniform(35, 70)
                        impact = random.uniform(40, 70)
                        cout_impact = random.uniform(10000, 60000)
                    
                    AttributMenace.objects.create(
                        attribut_securite=attribut,
                        menace=menace,
                        probabilite=Decimal(str(round(probabilite, 2))),
                        impact=Decimal(str(round(impact, 2))),
                        cout_impact=Decimal(str(round(cout_impact, 2)))
                    )

    def create_implementations(self, users):
        """Crée les implémentations"""
        attribut_menaces = list(AttributMenace.objects.all())
        mesures = list(MesureDeControle.objects.all())
        
        for i, attr_menace in enumerate(attribut_menaces[:10]):
            # Trouver une mesure appropriée
            mesures_appropriees = []
            for menace_controle in attr_menace.menace.controles_nist.all():
                for technique in menace_controle.controle_nist.techniques.all():
                    mesures_appropriees.extend(technique.mesures_controle.all())
            
            if not mesures_appropriees:
                mesures_appropriees = mesures
            
            mesure = random.choice(mesures_appropriees)
            
            ImplementationMesure.objects.create(
                attribut_menace=attr_menace,
                mesure_controle=mesure,
                statut=random.choice(['PLANIFIE', 'EN_COURS', 'IMPLEMENTE']),
                responsable=random.choice(users),
                pourcentage_avancement=Decimal(str(random.uniform(0, 100))),
                commentaires=f'Implémentation réaliste #{i+1}'
            )