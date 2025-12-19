# scripts/migrate_controle_nist_to_menace_mesure.py
"""
Script de migration pour transférer les données de ControleNIST/MenaceControle
vers le nouveau modèle MenaceMesure
"""

from django.db import transaction
from api.models import (
    Menace, MesureDeControle, Technique, 
    ControleNIST, MenaceControle, MenaceMesure
)

def migrate_data():
    """
    Migre les données de l'ancien modèle vers le nouveau
    """
    print("Début de la migration des données...")
    
    migrated_count = 0
    skipped_count = 0
    errors = []
    
    with transaction.atomic():
        # 1. Pour chaque association MenaceControle
        menace_controles = MenaceControle.objects.select_related(
            'menace', 'controle_nist'
        ).prefetch_related(
            'controle_nist__techniques__mesures_controle'
        ).all()
        
        print(f"Trouvé {menace_controles.count()} associations MenaceControle à migrer")
        
        for menace_controle in menace_controles:
            menace = menace_controle.menace
            controle_nist = menace_controle.controle_nist
            
            # 2. Pour chaque technique du contrôle NIST
            for technique in controle_nist.techniques.all():
                
                # 3. Pour chaque mesure de la technique
                for mesure in technique.mesures_controle.all():
                    
                    # 4. Créer MenaceMesure si elle n'existe pas déjà
                    menace_mesure, created = MenaceMesure.objects.get_or_create(
                        menace=menace,
                        mesure_controle=mesure,
                        defaults={
                            'efficacite': menace_controle.efficacite,
                            'statut_conformite': menace_controle.statut_conformite,
                            'commentaires': f"Migré de ControleNIST {controle_nist.code}: {menace_controle.commentaires or ''}"
                        }
                    )
                    
                    if created:
                        migrated_count += 1
                        print(f"✓ Créé: {menace.nom} → {mesure.mesure_code}")
                    else:
                        skipped_count += 1
                        print(f"- Existant: {menace.nom} → {mesure.mesure_code}")
        
        # 5. Migrer les informations des ControleNIST vers Technique
        print("\nMigration des informations ControleNIST vers Technique...")
        
        controles = ControleNIST.objects.prefetch_related('techniques').all()
        print(f"Trouvé {controles.count()} ControleNIST à migrer")
        
        for controle in controles:
            for technique in controle.techniques.all():
                # Mettre à jour famille et priorité de la technique
                if not technique.famille:
                    technique.famille = controle.famille
                if not technique.priorite:
                    technique.priorite = controle.priorite
                technique.save()
                print(f"✓ Mis à jour technique {technique.technique_code}: famille={controle.famille}, priorite={controle.priorite}")
    
    print("\n" + "="*50)
    print("RÉSUMÉ DE LA MIGRATION")
    print("="*50)
    print(f"Associations MenaceMesure créées: {migrated_count}")
    print(f"Associations existantes ignorées: {skipped_count}")
    print(f"Erreurs: {len(errors)}")
    
    if errors:
        print("\nERREURS:")
        for error in errors:
            print(f"  - {error}")
    
    return migrated_count, skipped_count, errors


def cleanup_old_data():
    """
    ATTENTION: Cette fonction supprime définitivement les anciennes données
    Exécutez ceci UNIQUEMENT après avoir vérifié que la migration est réussie
    """
    print("\n" + "="*50)
    print("NETTOYAGE DES ANCIENNES DONNÉES")
    print("="*50)
    
    response = input("Êtes-vous sûr de vouloir supprimer les anciennes données? (oui/NON): ")
    
    if response.lower() != 'oui':
        print("Nettoyage annulé.")
        return
    
    with transaction.atomic():
        # Compter avant suppression
        menace_controles_count = MenaceControle.objects.count()
        controles_nist_count = ControleNIST.objects.count()
        
        # Supprimer
        MenaceControle.objects.all().delete()
        print(f"✓ Supprimé {menace_controles_count} associations MenaceControle")
        
        ControleNIST.objects.all().delete()
        print(f"✓ Supprimé {controles_nist_count} ControleNIST")
    
    print("\nNettoyage terminé!")


def validate_migration():
    """
    Valide que la migration s'est bien passée
    """
    print("\n" + "="*50)
    print("VALIDATION DE LA MIGRATION")
    print("="*50)
    
    # Vérifier que toutes les menaces ont des mesures
    menaces_sans_mesures = []
    for menace in Menace.objects.all():
        mesures_count = menace.mesures_controle.count()
        if mesures_count == 0:
            menaces_sans_mesures.append(menace)
    
    if menaces_sans_mesures:
        print(f"\n⚠ ATTENTION: {len(menaces_sans_mesures)} menaces n'ont pas de mesures associées:")
        for menace in menaces_sans_mesures:
            print(f"  - {menace.nom} (ID: {menace.id})")
    else:
        print("\n✓ Toutes les menaces ont au moins une mesure associée")
    
    # Vérifier que toutes les techniques ont famille et priorité
    techniques_sans_info = Technique.objects.filter(
        Q(famille__isnull=True) | Q(famille='') |
        Q(priorite__isnull=True) | Q(priorite='')
    )
    
    if techniques_sans_info.exists():
        print(f"\n⚠ ATTENTION: {techniques_sans_info.count()} techniques n'ont pas de famille ou priorité:")
        for technique in techniques_sans_info[:10]:  # Afficher seulement les 10 premières
            print(f"  - {technique.technique_code}: famille={technique.famille}, priorite={technique.priorite}")
    else:
        print("✓ Toutes les techniques ont une famille et une priorité")
    
    # Statistiques générales
    print("\n" + "="*50)
    print("STATISTIQUES")
    print("="*50)
    print(f"Total Menaces: {Menace.objects.count()}")
    print(f"Total Techniques: {Technique.objects.count()}")
    print(f"Total Mesures: {MesureDeControle.objects.count()}")
    print(f"Total Associations MenaceMesure: {MenaceMesure.objects.count()}")
    print(f"Total ControleNIST restants: {ControleNIST.objects.count()}")
    print(f"Total MenaceControle restants: {MenaceControle.objects.count()}")


if __name__ == '__main__':
    print("="*50)
    print("MIGRATION CONTROLENIST → MENACEMESURE")
    print("="*50)
    
    # 1. Migration des données
    migrated, skipped, errors = migrate_data()
    
    # 2. Validation
    validate_migration()
    
    # 3. Proposer le nettoyage
    print("\n" + "="*50)
    print("La migration est terminée.")
    print("Vérifiez les résultats ci-dessus avant de nettoyer les anciennes données.")
    print("="*50)
    
    cleanup_response = input("\nVoulez-vous nettoyer les anciennes données maintenant? (oui/NON): ")
    if cleanup_response.lower() == 'oui':
        cleanup_old_data()
    else:
        print("\nVous pouvez exécuter cleanup_old_data() plus tard si nécessaire.")