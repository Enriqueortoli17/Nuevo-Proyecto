# Generated by Django 5.1.6 on 2025-05-03 00:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("servicios", "0019_motor_num_cabezas_motor_num_cilindros"),
    ]

    operations = [
        migrations.AddField(
            model_name="orden",
            name="fecha_inicio_real",
            field=models.DateTimeField(
                blank=True,
                help_text="Marca de tiempo cuando el PRIMER servicio pasa a 'En proceso'.",
                null=True,
                verbose_name="Fecha Inicio Real Trabajo",
            ),
        ),
    ]
