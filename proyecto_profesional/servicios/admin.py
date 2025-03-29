from django.contrib import admin
from .models import Orden, OrdenInventario, Servicio, CatalogoServicio, InventarioItem, Cliente, Motor 

class OrdenInventarioInline(admin.TabularInline):
    model = OrdenInventario
    extra = 0
    fields = ('inventario_item', 'cantidad')
    verbose_name = "Artículo de Inventario"
    verbose_name_plural = "Artículos de Inventario"

class ServicioInline(admin.TabularInline):
    model = Servicio
    extra = 0
    # Solo incluimos los campos que realmente existen en Servicio
    fields = ('catalogo_servicio', 'cantidad')
    verbose_name = "Servicio"
    verbose_name_plural = "Servicios"

class OrdenAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'cliente', 'estado_general', 'fecha_ingreso')
    inlines = [OrdenInventarioInline, ServicioInline]
    search_fields = ('numero_orden', 'cliente')
    list_filter = ('estado_general',)

admin.site.register(Orden, OrdenAdmin)
admin.site.register(CatalogoServicio)
admin.site.register(InventarioItem)
admin.site.register(Cliente)

class MotorAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': ('nombre',)
        }),
        ('Pistones', {
            'fields': ('diametro_cilindro', 'carrera', 'diametro_piston'),
        }),
        ('Válvulas de Escape', {
            'fields': ('diametro_cabeza_escape', 'distancia_valvula_escape', 'diametro_vastago_escape', 'angulo_asiento_escape'),
        }),
        ('Válvulas de Admisión', {
            'fields': ('diametro_cabeza_admision', 'distancia_valvula_admision', 'diametro_vastago_admision', 'angulo_asiento_admision'),
        }),
        ('Bancada', {
            'fields': ('diametro_alojamiento',),
        }),
        ('Cigüeñal', {
            'fields': ('diametro_munon_biela', 'diametro_munon_bancada'),
        }),
        ('Cabezas', {
            'fields': ('altura_cabeza',),
        }),
    )
    list_display = ('nombre',)

admin.site.register(Motor, MotorAdmin)
