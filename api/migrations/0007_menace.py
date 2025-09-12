
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0006_mesuredecontrole_mesure_code'),  # Remplacer par votre dernière migration
    ]

    operations = [
        migrations.AddField(
            model_name='menace',
            name='attribut_securite_principal',
            field=models.ForeignKey(
                blank=True, 
                help_text='Attribut de sécurité principal pour cette menace', 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='menaces_principales', 
                to='api.attributsecurite'
            ),
        ),
    ]