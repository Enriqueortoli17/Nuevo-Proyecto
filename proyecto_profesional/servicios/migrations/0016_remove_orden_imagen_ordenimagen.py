# Generated by Django 5.1.6 on 2025-04-28 22:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("servicios", "0015_orden_imagen"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="orden",
            name="imagen",
        ),
        migrations.CreateModel(
            name="OrdenImagen",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "imagen",
                    models.ImageField(
                        upload_to="orden_imagenes/", verbose_name="Imagen Adjunta"
                    ),
                ),
                ("fecha_subida", models.DateTimeField(auto_now_add=True)),
                (
                    "orden",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="imagenes",
                        to="servicios.orden",
                    ),
                ),
            ],
        ),
    ]
