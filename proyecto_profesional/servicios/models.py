from django.db import models
from django.contrib.auth.models import User

# Opciones para el estado general de la orden
ESTADO_GENERAL_CHOICES = [
    ('ESPERA', 'En espera'),
    ('ACEPTADA', 'Aceptada'),
    ('PROCESO', 'En proceso'),
    ('LISTO', 'Listo para entrega'),
    ('ENTREGADO', 'Entregado'),
    ('ANULADA', 'Anulada'),
]

# Opciones para el estado de cada servicio
ESTADO_SERVICIO_CHOICES = [
    ('PENDIENTE', 'Pendiente'),
    ('PROCESO', 'En proceso'),
    ('TERMINADO', 'Terminado'),
    ('NO_REALIZADO', 'No realizado'),
]

# Modelo para cada ítem del inventario
class InventarioItem(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

# Catálogo de Servicios: define los servicios disponibles
class CatalogoServicio(models.Model):
    nombre = models.CharField(max_length=100, help_text="Nombre del servicio, ej. 'Lavar motor'")
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción o indicaciones del servicio")

    def __str__(self):
        return self.nombre

# Modelo Orden: representa cada orden de servicio
class Orden(models.Model):
    numero_orden = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Ingrese el número de orden. Si se deja vacío, se asignará automáticamente."
    )
    cliente = models.CharField(max_length=100, help_text="Nombre del cliente")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    modelo_motor = models.CharField(max_length=50, blank=True, null=True)
    ruta = models.CharField(max_length=50, blank=True, null=True)
    fecha_programada = models.DateField(blank=True, null=True, help_text="Fecha en la que se inicia la producción")
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    notificacion = models.TextField(blank=True, null=True, help_text="Mensaje de notificación, si aplica")
    estado_general = models.CharField(
        max_length=15,
        choices=ESTADO_GENERAL_CHOICES,
        default='ESPERA'
    )
    posicion = models.FloatField(default=0, blank=True)
    chofer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes",
        help_text="Usuario que capturó la orden",
        verbose_name="Usuario"
    )

    # Relación ManyToMany con InventarioItem usando un modelo intermedio para registrar cantidades
    inventario_items = models.ManyToManyField(
        InventarioItem,
        blank=True,
        related_name="ordenes",
        through='OrdenInventario'
    )
    # Relación ManyToMany con CatalogoServicio usando un modelo intermedio para registrar cantidades
    servicios = models.ManyToManyField(
        CatalogoServicio,
        blank=True,
        related_name="ordenes",
        through='Servicio'
    )

    cliente_registrado = models.ForeignKey(
        "Cliente", 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name="ordenes",
        help_text="Cliente registrado (opcional)"
    )
    motor_registrado = models.ForeignKey(
        "Motor", 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name="ordenes",
        help_text="Motor registrado (opcional)"
    )
    
    @property
    def numero_provisional(self):
        if self.numero_orden:
            return self.numero_orden
        elif self.pk:
            return "TMP" + str(self.pk)
        else:
            return "TMP-UNSAVED"

    def __str__(self):
        return f"Orden {self.numero_provisional} - {self.cliente}"

    from datetime import date

    def actualizar_estado_general(self):
        if self.estado_general == 'ENTREGADO':
            return
        servicios = self.servicios_detalle.all()
        if not servicios.exists():
            # Si la orden ya fue aceptada, mantenla como "ACEPTADA"
            if self.estado_general in ['ACEPTADA', 'PROCESO']:
                self.estado_general = 'ACEPTADA'
            else:
                self.estado_general = 'ESPERA'
        else:
            # Si todos los servicios están TERMINADO o NO_REALIZADO, la orden pasa a LISTO
            if all(s.estado in ['TERMINADO', 'NO_REALIZADO'] for s in servicios):
                self.estado_general = 'LISTO'
            # Si al menos un servicio está en PROCESO o (al menos uno terminado y la orden ya estaba aceptada)
            elif any(s.estado == 'PROCESO' for s in servicios) or (any(s.estado == 'TERMINADO' for s in servicios) and self.estado_general in ['ACEPTADA', 'PROCESO']):
                self.estado_general = 'PROCESO'
            # Si todos están pendientes y la orden ya estaba aceptada, mantenla como ACEPTADA; de lo contrario, en espera
            else:
                if self.estado_general in ['ACEPTADA', 'PROCESO']:
                    self.estado_general = 'ACEPTADA'
                else:
                    self.estado_general = 'ESPERA'
        self.save()

# Modelo Servicio: registra cada servicio aplicado a una orden
class Servicio(models.Model):
    orden = models.ForeignKey('Orden', on_delete=models.CASCADE, related_name='servicios_detalle')
    catalogo_servicio = models.ForeignKey(
        'CatalogoServicio',
        on_delete=models.CASCADE,
        default=1  # Se asignará este valor por defecto; asegúrate de que exista un CatalogoServicio con id=1
    )
    cantidad = models.CharField(max_length=50, default="")
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_SERVICIO_CHOICES,
        default='PENDIENTE'
    )
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.catalogo_servicio.nombre} ({self.get_estado_display()})"


# Modelo intermedio para la relación Orden - InventarioItem (con cantidad)
class OrdenInventario(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE)
    inventario_item = models.ForeignKey(InventarioItem, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    comentario = models.TextField(blank=True, null=True)  # Nuevo campo para comentarios

    def __str__(self):
        return f"{self.inventario_item} - {self.cantidad}"

# Nuevo modelo para Clientes
class Cliente(models.Model):
    nombre = models.CharField(max_length=100, unique=True, help_text="Nombre completo del cliente")
    telefono = models.CharField(max_length=20, blank=True, null=True, help_text="Teléfono del cliente")
    ruta = models.CharField(max_length=50, blank=True, null=True, help_text="Ruta o dirección del cliente")

    def __str__(self):
        return self.nombre

# Nuevo modelo para Motores
from django.db import models

class Motor(models.Model):
    nombre = models.CharField(max_length=100)
    
    # Especificaciones de Pistones
    diametro_cilindro = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro de cilindros", default=0.00)
    carrera = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Carrera", default=0.00)
    diametro_piston = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro del pistón", default=0.00)
    
    # Válvulas de Escape
    diametro_cabeza_escape = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro de cabeza (escape)", default=0.00)
    distancia_valvula_escape = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Distancia válvula (escape)", default=0.00)
    diametro_vastago_escape = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro vástago (escape)", default=0.00)
    angulo_asiento_escape = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Ángulo de asiento (escape)", default=0.00)
    
    # Válvulas de Admisión
    diametro_cabeza_admision = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro de cabeza (admisión)", default=0.00)
    distancia_valvula_admision = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Distancia válvula (admisión)", default=0.00)
    diametro_vastago_admision = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro vástago (admisión)", default=0.00)
    angulo_asiento_admision = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Ángulo de asiento (admisión)", default=0.00)
    
    # Bancada
    diametro_alojamiento = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro de alojamiento", default=0.00)
    
    # Cigüeñal
    diametro_munon_biela = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro de muñón de biela", default=0.00)
    diametro_munon_bancada = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Diámetro de muñón de bancada", default=0.00)
    
    # Cabezas
    altura_cabeza = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Altura de la cabeza", default=0.00)
    
    def __str__(self):
        return self.nombre
