from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

# Opciones para el estado general de la orden
ESTADO_GENERAL_CHOICES = [
    ("ESPERA", "En espera"),
    ("ACEPTADA", "Aceptada"),
    ("PROCESO", "En proceso"),
    ("LISTO", "Listo para entrega"),
    ("ENTREGADO", "Entregado"),
    ("ANULADA", "Anulada"),
]

# Opciones para el estado de cada servicio
ESTADO_SERVICIO_CHOICES = [
    ("PENDIENTE", "Pendiente"),
    ("PROCESO", "En proceso"),
    ("TERMINADO", "Terminado"),
    ("NO_REALIZADO", "No realizado"),
]

# Modelo para cada ítem del inventario
class InventarioItem(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

# Catálogo de Servicios: define los servicios disponibles
class CatalogoServicio(models.Model):
    nombre = models.CharField(
        max_length=100, help_text="Nombre del servicio, ej. 'Lavar motor'"
    )
    descripcion = models.TextField(
        blank=True, null=True, help_text="Descripción o indicaciones del servicio"
    )

    def __str__(self):
        return self.nombre

# Modelo Orden: representa cada orden de servicio
class Orden(models.Model):
    numero_orden = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Ingrese el número de orden. Si se deja vacío, se asignará automáticamente.",
    )
    cliente = models.CharField(max_length=100, help_text="Nombre del cliente")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    modelo_motor = models.CharField(max_length=50, blank=True, null=True)
    ruta = models.CharField(max_length=50, blank=True, null=True)
    fecha_programada = models.DateField(
        blank=True, null=True, help_text="Fecha en la que se inicia la producción"
    )
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    notificacion = models.TextField(
        blank=True, null=True, help_text="Mensaje de notificación, si aplica"
    )
    estado_general = models.CharField(
        max_length=15, choices=ESTADO_GENERAL_CHOICES, default="ESPERA"
    )
    posicion = models.FloatField(default=0, blank=True)
    chofer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes",
        help_text="Usuario que capturó la orden",
        verbose_name="Usuario",
    )
    fecha_aceptacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Aceptación",
        help_text="Fecha y hora en que la orden fue aceptada."
    )

    fecha_inicio_real = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Inicio Real Trabajo",
        help_text="Marca de tiempo cuando el PRIMER servicio pasa a 'En proceso'."
    )
    
    fecha_terminacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Terminación",
        help_text="Fecha y hora en que todos los servicios de la orden se completaron (estado LISTO)."
    )
    fecha_entrega = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Entrega",
        help_text="Fecha y hora en que la orden fue marcada como entregada."
    )

    # Relación ManyToMany con InventarioItem usando un modelo intermedio para registrar cantidades
    inventario_items = models.ManyToManyField(
        InventarioItem, blank=True, related_name="ordenes", through="OrdenInventario"
    )
    # Relación ManyToMany con CatalogoServicio usando un modelo intermedio para registrar cantidades
    servicios = models.ManyToManyField(
        CatalogoServicio, blank=True, related_name="ordenes", through="Servicio"
    )

    cliente_registrado = models.ForeignKey(
        "Cliente",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ordenes",
        help_text="Cliente registrado (opcional)",
    )
    motor_registrado = models.ForeignKey(
        "Motor",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ordenes",
        help_text="Motor registrado (opcional)",
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
        print(f"\n--- DEBUG: Ejecutando actualizar_estado_general para Orden ID {self.id} ---") # Añadido
        # Guarda el estado actual ANTES de cualquier cambio
        estado_actual = self.estado_general

        if estado_actual == "ENTREGADO":
            print(f"--- DEBUG: Orden {self.id} ya está ENTREGADO. Saliendo.") # Añadido
            return

        servicios = self.servicios_detalle.all()
        print(f"--- DEBUG: Orden {self.id} - Número de servicios encontrados: {servicios.count()}") # Añadido

        nuevo_estado = estado_actual # Por defecto, mantenemos el estado actual

        if not servicios.exists():
            print(f"--- DEBUG: Orden {self.id} - No tiene servicios.") # Añadido
            # Si no hay servicios, el estado debería ser ESPERA o ACEPTADA si ya lo estaba
            if estado_actual in ["ACEPTADA", "PROCESO"]:
                nuevo_estado = "ACEPTADA"
            else:
                nuevo_estado = "ESPERA"
        else:
            print(f"--- DEBUG: Orden {self.id} - Verificando estados de servicios:") # Añadido
            estados_servicios = [] # Lista para ver los estados
            for s in servicios:
                estados_servicios.append(s.estado)
                print(f"--- DEBUG:   - Servicio ID {s.id}: Estado '{s.estado}'") # Añadido

            # Determina si todos los servicios están terminados
            todos_terminados = all(s in ["TERMINADO", "NO_REALIZADO"] for s in estados_servicios)
            print(f"--- DEBUG: Orden {self.id} - Resultado de all(terminados): {todos_terminados}") # Añadido

            # Determina si alguno está en proceso
            alguno_en_proceso = any(s == "PROCESO" for s in estados_servicios)
            print(f"--- DEBUG: Orden {self.id} - Resultado de any(en_proceso): {alguno_en_proceso}") # Añadido

            # Determina si alguno está terminado (para la lógica de PROCESO)
            alguno_terminado = any(s == "TERMINADO" for s in estados_servicios)
            print(f"--- DEBUG: Orden {self.id} - Resultado de any(terminado): {alguno_terminado}") # Añadido


            # Lógica para decidir el nuevo estado general
            if todos_terminados:
                print(f"--- DEBUG: Orden {self.id} - ¡Todos terminados! Estableciendo estado a LISTO.") # Añadido
                nuevo_estado = "LISTO"
                if estado_actual not in ["LISTO", "ENTREGADO"]: # <-- Añadido chequeo
                    self.fecha_terminacion = timezone.now() # <--- AÑADIR ESTA LÍNEA
                    print(f"--- DEBUG: Orden {self.id} - Estableciendo fecha_terminacion: {self.fecha_terminacion}") # <-- Añadido debug
            elif alguno_en_proceso or (alguno_terminado and estado_actual in ["ACEPTADA", "PROCESO"]):
                # Si hay algo en proceso, O si algo está terminado y la orden ya había sido aceptada/estaba en proceso,
                # entonces el estado general es PROCESO.
                print(f"--- DEBUG: Orden {self.id} - Al menos uno en PROCESO o TERMINADO (y orden ya aceptada/proceso). Estableciendo estado a PROCESO.") # Añadido
                nuevo_estado = "PROCESO"
            else:
                # Si no aplica LISTO ni PROCESO, decidimos entre ACEPTADA o ESPERA
                if estado_actual in ["ACEPTADA", "PROCESO"]:
                     # Si todos estaban PENDIENTE pero la orden ya estaba aceptada, mantenla aceptada.
                    print(f"--- DEBUG: Orden {self.id} - No aplica LISTO/PROCESO, pero ya estaba ACEPTADA/PROCESO. Manteniendo/volviendo a ACEPTADA.") # Añadido
                    nuevo_estado = "ACEPTADA"
                else:
                    # Si estaba en ESPERA y todos los servicios están PENDIENTE
                    print(f"--- DEBUG: Orden {self.id} - No aplica LISTO/PROCESO y estaba en ESPERA. Manteniendo/volviendo a ESPERA.") # Añadido
                    nuevo_estado = "ESPERA"

        print(f"--- DEBUG: Orden {self.id} - Estado general final antes de guardar: {nuevo_estado}") # Añadido

        # Solo guarda si el estado realmente cambió
        campos_a_actualizar = [] # Lista para guardar solo lo que cambia
        if self.estado_general != nuevo_estado:
            print(f"--- DEBUG: Orden {self.id} - Guardando CAMBIO de estado: {self.estado_general} -> {nuevo_estado}")
            self.estado_general = nuevo_estado
            campos_a_actualizar.append('estado_general')

        # Si establecimos fecha_terminacion, añadirla a los campos a guardar
        if hasattr(self, 'fecha_terminacion') and self.fecha_terminacion and 'fecha_terminacion' not in campos_a_actualizar and nuevo_estado == "LISTO":
            if getattr(self, '_original_fecha_terminacion', None) != self.fecha_terminacion: # Evita guardar si no cambió (requiere _original_) o simplemente guarda siempre que el estado sea LISTO y el campo tenga valor
                campos_a_actualizar.append('fecha_terminacion')

        if campos_a_actualizar:
            print(f"--- DEBUG: Orden {self.id} - Campos a actualizar: {campos_a_actualizar}")
            self.save(update_fields=campos_a_actualizar) # Guarda solo los campos modificados
        else:
            print(f"--- DEBUG: Orden {self.id} - No hubo cambios detectados para guardar.")

        print(f"--- DEBUG: Fin actualizar_estado_general para Orden ID {self.id} ---\n") # Añadido

    @property
    def duracion_total_orden(self):
        """Calcula la duración total desde el inicio real del trabajo hasta la terminación."""
        if self.fecha_inicio_real and self.fecha_terminacion:
            # Asegurarse que fecha_terminacion es posterior a fecha_inicio_real
            if self.fecha_terminacion > self.fecha_inicio_real:
                delta = self.fecha_terminacion - self.fecha_inicio_real
            else:
                # Si las fechas son iguales o inicio es posterior, duración es 0 o mínima
                return "0m" # O puedes retornar '-' o lo que prefieras

            days = delta.days
            total_seconds = max(0, int(delta.total_seconds()))
            hours, remainder = divmod(total_seconds - (days * 86400), 3600)
            minutes, seconds = divmod(remainder, 60)

            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            # Mostrar minutos si es la única unidad > 0 o si no hay días
            if minutes > 0 and (days == 0 or hours == 0 or not parts):
                parts.append(f"{minutes}m")

            # Si el delta fue muy pequeño (menos de 1 minuto) y no se añadió nada, mostrar "0m"
            if not parts:
                parts.append("0m")

            return " ".join(parts)

        # Si falta alguna de las fechas necesarias, devuelve un guion
        return "-"

class OrdenImagen(models.Model):
    orden = models.ForeignKey(Orden, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='orden_imagenes/', verbose_name="Imagen Adjunta")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Extraer nombre de archivo de la ruta
        import os
        nombre_archivo = os.path.basename(self.imagen.name)
        return f"Imagen para Orden {self.orden.numero_provisional} ({nombre_archivo})"

    # Opcional: método para eliminar archivo físico al borrar el objeto
    def delete(self, *args, **kwargs):
        # Asegúrate de eliminar el archivo físico antes de borrar el registro
        self.imagen.delete(save=False) # save=False evita guardar el modelo vacío
        super().delete(*args, **kwargs)

# Modelo Servicio: registra cada servicio aplicado a una orden
class Servicio(models.Model):
    orden = models.ForeignKey(
        "Orden", on_delete=models.CASCADE, related_name="servicios_detalle"
    )
    catalogo_servicio = models.ForeignKey(
        "CatalogoServicio",
        on_delete=models.CASCADE,
        default=1,  # Se asignará este valor por defecto; asegúrate de que exista un CatalogoServicio con id=1
    )
    cantidad = models.CharField(max_length=50, default="")
    estado = models.CharField(
        max_length=15, choices=ESTADO_SERVICIO_CHOICES, default="PENDIENTE"
    )
    observaciones = models.TextField(blank=True, null=True)

    # --- NUEVOS CAMPOS ---
    fecha_inicio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Inicio Servicio",
        help_text="Marca de tiempo cuando el servicio pasa a 'En proceso'.",
    )
    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Fin Servicio",
        help_text="Marca de tiempo cuando el servicio pasa a 'Terminado'.",
    )
    # --- FIN NUEVOS CAMPOS ---

    def __str__(self):
        return f"{self.catalogo_servicio.nombre} ({self.get_estado_display()})"

    # --- NUEVA PROPIEDAD (OPCIONAL) ---
    @property
    def duracion(self):
        """Calcula la duración del servicio si tiene fecha de inicio y fin."""
        if self.fecha_inicio and self.fecha_fin:
            # Calcula la diferencia
            delta = self.fecha_fin - self.fecha_inicio
            # Formatea como HH:MM:SS (o como prefieras)
            total_seconds = int(delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            # Retorna en formato legible, por ejemplo "02h 15m 30s"
            # O puedes retornar solo el timedelta: delta
            return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
            # return delta # Retorna el objeto timedelta directamente
        return None # O retorna 'N/A', 0, etc., si no está completo
    # --- FIN NUEVA PROPIEDAD ---
    
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
    nombre = models.CharField(
        max_length=100, unique=True, help_text="Nombre completo del cliente"
    )
    telefono = models.CharField(
        max_length=20, blank=True, null=True, help_text="Teléfono del cliente"
    )
    ruta = models.CharField(
        max_length=50, blank=True, null=True, help_text="Ruta o dirección del cliente"
    )

    def __str__(self):
        return self.nombre

class Motor(models.Model):
    nombre = models.CharField(max_length=100)

    num_cilindros = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Número de Cilindros",
        help_text="Ej: 4, 6, 8"
    )
    num_cabezas = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Número de Cabezas",
        help_text="Ej: 1, 2"
    )

    # Especificaciones de Pistones
    diametro_cilindro = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro de cilindros",
        default=0.00,
    )
    carrera = models.DecimalField(
        max_digits=10, decimal_places=5, verbose_name="Carrera", default=0.00
    )
    diametro_piston = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro del pistón",
        default=0.00,
    )

    # Válvulas de Escape
    diametro_cabeza_escape = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro de cabeza (escape)",
        default=0.00,
    )
    distancia_valvula_escape = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Distancia válvula (escape)",
        default=0.00,
    )
    diametro_vastago_escape = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro vástago (escape)",
        default=0.00,
    )
    angulo_asiento_escape = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Ángulo de asiento (escape)",
        default=0.00,
    )

    # Válvulas de Admisión
    diametro_cabeza_admision = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro de cabeza (admisión)",
        default=0.00,
    )
    distancia_valvula_admision = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Distancia válvula (admisión)",
        default=0.00,
    )
    diametro_vastago_admision = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro vástago (admisión)",
        default=0.00,
    )
    angulo_asiento_admision = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Ángulo de asiento (admisión)",
        default=0.00,
    )

    # Bancada
    diametro_alojamiento = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro de alojamiento",
        default=0.00,
    )

    # Cigüeñal
    diametro_munon_biela = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro de muñón de biela",
        default=0.00,
    )
    diametro_munon_bancada = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Diámetro de muñón de bancada",
        default=0.00,
    )

    # Cabezas
    altura_cabeza = models.DecimalField(
        max_digits=10,
        decimal_places=5,
        verbose_name="Altura de la cabeza",
        default=0.00,
    )

    def __str__(self):
        return self.nombre
