from django.db import migrations, models
import django.core.validators
from decimal import Decimal

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'), 
    ]

    operations = [
        
        migrations.AlterField(
            model_name='architecture',
            name='risque_tolere',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('10000.00'),
                help_text='Coût maximal du risque toléré (en €)',
                max_digits=15,
                validators=[django.core.validators.MinValueValidator(0)]
            ),
        ),
        
        # Étape 2: Migration des données existantes
        # Conversion hypothétique : 1% de risque = 1000€ de budget risque
        # (À adapter selon votre contexte métier)
        migrations.RunSQL(
            # Conversion des pourcentages en coûts
            "UPDATE architecture SET risque_tolere = risque_tolere * 1000;",
            # Rollback : reconversion en pourcentages  
            "UPDATE architecture SET risque_tolere = risque_tolere / 1000;"
        ),
    ]