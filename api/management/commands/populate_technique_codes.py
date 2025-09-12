
from django.core.management.base import BaseCommand
from api.models import Technique

class Command(BaseCommand):
    help = 'Génère automatiquement les codes techniques pour les enregistrements existants'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait fait sans sauvegarder',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODE DRY-RUN - Aucune modification ne sera sauvegardée'))
        
        techniques_updated = 0
        
        # Récupérer toutes les techniques sans code
        techniques_sans_code = Technique.objects.filter(
            technique_code__isnull=True
        ).select_related('controle_nist').order_by('controle_nist__code', 'created_at')
        
        if not techniques_sans_code.exists():
            self.stdout.write(self.style.SUCCESS('✅ Toutes les techniques ont déjà un code'))
            return
        
        self.stdout.write(f'📋 {techniques_sans_code.count()} techniques à traiter')
        
        # Grouper par contrôle NIST pour une numérotation cohérente
        controles_dict = {}
        
        for technique in techniques_sans_code:
            controle_code = technique.controle_nist.code
            if controle_code not in controles_dict:
                controles_dict[controle_code] = []
            controles_dict[controle_code].append(technique)
        
        for controle_code, techniques_list in controles_dict.items():
            self.stdout.write(f'\n📦 Traitement du contrôle {controle_code}:')
            
            # Trouver le prochain numéro disponible pour ce contrôle
            techniques_existantes = Technique.objects.filter(
                controle_nist__code=controle_code,
                technique_code__isnull=False
            ).count()
            
            next_number = techniques_existantes + 1
            
            for i, technique in enumerate(techniques_list):
                # Générer le code technique
                technique_code = f"{controle_code}.{next_number + i}"
                
                # Vérifier l'unicité (au cas où)
                while Technique.objects.filter(technique_code=technique_code).exists():
                    next_number += 1
                    technique_code = f"{controle_code}.{next_number + i}"
                
                self.stdout.write(f'  ├─ {technique.nom[:50]}... → {technique_code}')
                
                if not dry_run:
                    technique.technique_code = technique_code
                    technique.save()
                
                techniques_updated += 1
        
        if dry_run:
            self.stdout.write(f'\n🔍 {techniques_updated} techniques seraient mises à jour')
            self.stdout.write('💡 Exécutez sans --dry-run pour appliquer les changements')
        else:
            self.stdout.write(f'\n✅ {techniques_updated} techniques mises à jour avec succès')
        
        # Vérification finale
        if not dry_run:
            remaining = Technique.objects.filter(technique_code__isnull=True).count()
            if remaining == 0:
                self.stdout.write(self.style.SUCCESS('🎉 Toutes les techniques ont maintenant un code unique!'))



                