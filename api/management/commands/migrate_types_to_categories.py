# api/management/commands/migrate_types_to_categories.py

from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import CategorieActif, TypeActif
import re

class Command(BaseCommand):
    help = 'Migre les types d\'actifs existants vers la nouvelle structure avec catégories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule la migration sans appliquer les changements',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODE SIMULATION - Aucun changement ne sera appliqué'))
        
        try:
            with transaction.atomic():
                # ============================================================
                # ÉTAPE 1 : Créer les catégories par défaut
                # ============================================================
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('ÉTAPE 1 : Création des catégories'))
                self.stdout.write('='*60 + '\n')
                
                categories_default = [
                    {
                        'code': 'GENERAL',
                        'nom': 'Général',
                        'description': 'Catégorie générale pour les types non classifiés'
                    },
                    {
                        'code': 'INFRA',
                        'nom': 'Infrastructure',
                        'description': 'Infrastructure matérielle et réseau (serveurs, équipements réseau, stockage)'
                    },
                    {
                        'code': 'APP',
                        'nom': 'Applications',
                        'description': 'Applications et logiciels (web, mobile, desktop)'
                    },
                    {
                        'code': 'DATA',
                        'nom': 'Données',
                        'description': 'Bases de données et systèmes de stockage de données'
                    },
                    {
                        'code': 'SERVICE',
                        'nom': 'Services',
                        'description': 'Services métier et services cloud'
                    },
                    {
                        'code': 'RESEAU',
                        'nom': 'Réseau',
                        'description': 'Équipements et services réseau'
                    },
                ]
                
                categories = {}
                for cat_data in categories_default:
                    if not dry_run:
                        cat, created = CategorieActif.objects.get_or_create(
                            code=cat_data['code'],
                            defaults={
                                'nom': cat_data['nom'],
                                'description': cat_data['description']
                            }
                        )
                        categories[cat_data['code']] = cat
                        
                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Catégorie créée: {cat.nom} ({cat.code})')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'  • Catégorie existante: {cat.nom} ({cat.code})')
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  • [SIMULATION] Créerait: {cat_data["nom"]} ({cat_data["code"]})')
                        )
                
                # ============================================================
                # ÉTAPE 2 : Générer les codes et associer les catégories
                # ============================================================
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('ÉTAPE 2 : Migration des types d\'actifs'))
                self.stdout.write('='*60 + '\n')
                
                # Mapping pour déterminer la catégorie selon le nom du type
                category_keywords = {
                    'INFRA': ['serveur', 'server', 'srv', 'hardware', 'matériel', 'infrastructure'],
                    'APP': ['application', 'app', 'logiciel', 'software', 'programme'],
                    'DATA': ['base', 'database', 'bdd', 'stockage', 'storage', 'data', 'données'],
                    'RESEAU': ['réseau', 'network', 'routeur', 'router', 'switch', 'firewall', 'vpn'],
                    'SERVICE': ['service', 'cloud', 'saas', 'paas', 'iaas', 'api'],
                }
                
                types_actifs = TypeActif.objects.all()
                total_types = types_actifs.count()
                
                if total_types == 0:
                    self.stdout.write(
                        self.style.WARNING('  • Aucun type d\'actif existant à migrer')
                    )
                else:
                    migrated = 0
                    code_counter = {}  # Pour gérer les codes uniques
                    
                    for type_actif in types_actifs:
                        # Déterminer la catégorie
                        nom_lower = type_actif.nom.lower()
                        categorie_code = 'GENERAL'  # Par défaut
                        
                        for cat_code, keywords in category_keywords.items():
                            if any(keyword in nom_lower for keyword in keywords):
                                categorie_code = cat_code
                                break
                        
                        # Générer un code unique pour ce type
                        # Format: Premières lettres du nom en majuscules
                        base_code = self._generate_code(type_actif.nom)
                        
                        # Gérer l'unicité du code
                        if base_code not in code_counter:
                            code_counter[base_code] = 0
                        else:
                            code_counter[base_code] += 1
                        
                        if code_counter[base_code] > 0:
                            code = f"{base_code}-{code_counter[base_code]}"
                        else:
                            code = base_code
                        
                        if not dry_run:
                            type_actif.code = code
                            type_actif.categorie = categories[categorie_code]
                            type_actif.save()
                            
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ {type_actif.nom}\n'
                                    f'     Code: {code}\n'
                                    f'     Catégorie: {categories[categorie_code].nom}'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  • [SIMULATION] {type_actif.nom}\n'
                                    f'     Code: {code}\n'
                                    f'     Catégorie: {categorie_code}'
                                )
                            )
                        
                        migrated += 1
                    
                    self.stdout.write(
                        f'\n  {migrated}/{total_types} type(s) traité(s)'
                    )
                
                # ============================================================
                # ÉTAPE 3 : Résumé
                # ============================================================
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('RÉSUMÉ'))
                self.stdout.write('='*60 + '\n')
                
                if not dry_run:
                    for cat in CategorieActif.objects.all():
                        nb_types = cat.types_actifs.count()
                        self.stdout.write(f'  • {cat.nom} ({cat.code}): {nb_types} type(s)')
                    
                    self.stdout.write('\n' + self.style.SUCCESS('✓ Migration terminée avec succès!'))
                    
                    self.stdout.write('\n' + '='*60)
                    self.stdout.write(self.style.WARNING('PROCHAINES ÉTAPES'))
                    self.stdout.write('='*60)
                    self.stdout.write(
                        '\n1. Vérifiez les types dans l\'admin Django'
                        '\n2. Réorganisez manuellement si nécessaire'
                        '\n3. Appliquez la migration finale pour rendre les champs obligatoires\n'
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            '\n✓ Simulation terminée. Exécutez sans --dry-run pour appliquer les changements.'
                        )
                    )
                
                if dry_run:
                    raise Exception("Dry run - rollback de la transaction")
                    
        except Exception as e:
            if not dry_run or str(e) != "Dry run - rollback de la transaction":
                self.stdout.write(
                    self.style.ERROR(f'\n✗ Erreur lors de la migration: {str(e)}')
                )
                raise
    
    def _generate_code(self, nom):
        """Génère un code à partir du nom"""
        # Nettoyer le nom
        nom_clean = re.sub(r'[^a-zA-Z0-9\s-]', '', nom)
        
        # Prendre les premières lettres des mots
        words = nom_clean.split()
        if len(words) >= 2:
            # Si plusieurs mots, prendre les initiales
            code = ''.join([word[0].upper() for word in words[:3] if word])
        else:
            # Si un seul mot, prendre les 3-5 premières lettres
            code = nom_clean[:5].upper().replace(' ', '')
        
        # S'assurer que le code n'est pas vide
        if not code:
            code = 'TYPE'
        
        return code