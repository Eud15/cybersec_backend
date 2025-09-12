# 1. MIGRATION DJANGO NÉCESSAIRE
# Créer un nouveau fichier de migration : api/migrations/XXXX_simplify_attribut_securite_to_single_cost.py

from django.db import migrations, models
from decimal import Decimal
import django.core.validators

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_alter_attributmenace_impact_and_more'),  # Remplacer par votre dernière migration
    ]

    operations = [
        
        migrations.RemoveField(
            model_name='attributsecurite',
            name='valeur_cible',
        ),
        migrations.RemoveField(
            model_name='attributsecurite',
            name='valeur_actuelle',
        ),
        # Ajouter le nouveau champ unique
        migrations.AddField(
            model_name='attributsecurite',
            name='cout_compromission',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Coût financier en cas de compromission de cet attribut (en €)',
                max_digits=15,
                validators=[django.core.validators.MinValueValidator(0)]
            ),
        ),
    ]

