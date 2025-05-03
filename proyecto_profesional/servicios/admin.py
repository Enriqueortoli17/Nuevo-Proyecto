# servicios/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Orden,
    OrdenInventario,
    Servicio,
    CatalogoServicio,
    InventarioItem,
    Cliente,
    Motor,
    OrdenImagen,
    # Ruta,        # Importa otros modelos si los usas
    # Operador     # Ejemplo
)

# --- ModelAdmin para modelos relacionados con autocomplete ---

@admin.register(InventarioItem) # Usar decorador
class InventarioItemAdmin(admin.ModelAdmin):
    search_fields = ['nombre'] # Campo a buscar para autocomplete

@admin.register(CatalogoServicio) # Usar decorador
class CatalogoServicioAdmin(admin.ModelAdmin):
    search_fields = ['nombre'] # Campo a buscar para autocomplete
    list_display = ('nombre', 'descripcion') # Opcional: mejorar la vista de lista

# --- Inlines ---

class OrdenInventarioInline(admin.TabularInline):
    model = OrdenInventario
    extra = 0
    fields = ("inventario_item", "cantidad", "comentario")
    verbose_name = "Artículo de Inventario"
    verbose_name_plural = "Artículos de Inventario"
    autocomplete_fields = ['inventario_item'] # Ahora funcionará

class ServicioInline(admin.TabularInline):
    model = Servicio
    extra = 0
    fields = ("catalogo_servicio", "cantidad", "estado", "observaciones")
    verbose_name = "Servicio"
    verbose_name_plural = "Servicios"
    autocomplete_fields = ['catalogo_servicio'] # Ahora funcionará

class OrdenImagenInline(admin.TabularInline):
    model = OrdenImagen
    extra = 1
    readonly_fields = ('imagen_thumbnail',)
    fields = ('imagen', 'imagen_thumbnail')
    verbose_name = "Imagen Adjunta"
    verbose_name_plural = "Imágenes Adjuntas"

    def imagen_thumbnail(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" width="150" />', obj.imagen.url)
        return "No hay imagen"
    imagen_thumbnail.short_description = 'Miniatura'

# --- ModelAdmin para Orden ---

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = (
        "numero_provisional",
        "cliente",
        "motor_registrado",
        "estado_general",
        "fecha_ingreso",
        'fecha_aceptacion',
        'fecha_programada',
        'fecha_terminacion',
        'fecha_entrega',
        "display_imagen",
    )
    list_filter = ('estado_general', 'fecha_ingreso', 'cliente_registrado', 'motor_registrado', 'posicion')
    search_fields = ('numero_orden', 'cliente', 'cliente_registrado__nombre', 'motor_registrado__nombre', 'telefono', 'modelo_motor')

    fieldsets = (
        (None, {
            'fields': ('numero_orden', ('cliente', 'telefono'), ('cliente_registrado', 'motor_registrado'), 'modelo_motor')
        }),
        ('Detalles y Programación', {
            'fields': ('ruta', 'fecha_programada', 'chofer', 'notificacion')
        }),
        ('Estado Interno', {
            'fields': ('estado_general', 'posicion')
        }),
        ('Fechas (Info)', {
            'classes': ('collapse',),
            'fields': ('fecha_ingreso',)
        }),
    )

    readonly_fields = ('fecha_ingreso',
            'fecha_aceptacion',
            'fecha_terminacion',
            'fecha_entrega',)

    inlines = [ServicioInline, OrdenInventarioInline, OrdenImagenInline]

    def display_imagen(self, obj):
        """Muestra la miniatura de la primera imagen en list_display."""
        primera_imagen = obj.imagenes.first()
        if primera_imagen and primera_imagen.imagen:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', primera_imagen.imagen.url)
        return "No hay imagen"
    display_imagen.short_description = 'Imagen'

# --- ModelAdmin para Motor ---
@admin.register(Motor)
class MotorAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("nombre",)}),
        ("Pistones", {"fields": ("diametro_cilindro", "carrera", "diametro_piston")}),
        ("Válvulas de Escape", {"fields": ("diametro_cabeza_escape", "distancia_valvula_escape", "diametro_vastago_escape", "angulo_asiento_escape")}),
        ("Válvulas de Admisión", {"fields": ("diametro_cabeza_admision", "distancia_valvula_admision", "diametro_vastago_admision", "angulo_asiento_admision")}),
        ("Bancada", {"fields": ("diametro_alojamiento",)}),
        ("Cigüeñal", {"fields": ("diametro_munon_biela", "diametro_munon_bancada")}),
        ("Cabezas", {"fields": ("altura_cabeza",)}),
    )
    list_display = ("nombre",)
    search_fields = ['nombre'] # Añadir search_fields también aquí es buena práctica

# --- ModelAdmin para Cliente ---
@admin.register(Cliente) # Usar decorador
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'ruta')
    search_fields = ['nombre', 'telefono'] # Campos para buscar clientes

# --- Registros Directos (Modelos restantes sin ModelAdmin complejo) ---
# Ya no registramos InventarioItem, CatalogoServicio, Cliente aquí porque usan decorador.
# admin.site.register(Ruta)    # Ejemplo si existe y no necesita admin complejo
# admin.site.register(Operador) # Ejemplo si existe y no necesita admin complejo
admin.site.register(OrdenImagen) # Opcional: permite gestionar imágenes fuera de la orden