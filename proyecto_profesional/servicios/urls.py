from django.urls import path
from . import views

app_name = 'servicios'

urlpatterns = [
    # Dashboard y Vistas Principales
    path("", views.dashboard, name="home"),
    # Gestión de Órdenes
    path("crear/", views.crear_orden, name="crear_orden"),
    path("lista/", views.lista_ordenes, name="lista_ordenes"),
    path("tablero/", views.tablero_ordenes, name="tablero_ordenes"),
    path("tablero-parcial/", views.tablero_parcial, name="tablero_parcial"),
    path("actualizar/", views.actualizar_servicios, name="actualizar_servicios"),
    path("ordenes-terminadas/", views.ordenes_terminadas, name="ordenes_terminadas"),
    path("historial/", views.historial_ordenes, name="historial_ordenes"),
    path("aceptar/<int:orden_id>/", views.aceptar_orden, name="aceptar_orden"),
    path('anular/<int:orden_id>/', views.anular_orden, name='anular_orden'),
    path("anuladas/", views.ordenes_anuladas, name="ordenes_anuladas"),
    path('orden/imagen/<int:imagen_id>/eliminar/', views.eliminar_orden_imagen, name='eliminar_orden_imagen'),
    # API AJAX
    path(
        "ajax/actualizar_estado_servicio/",
        views.actualizar_estado_servicio,
        name="actualizar_estado_servicio",
    ),
    path(
        "actualizar-orden-manual/",
        views.actualizar_orden_manual,
        name="actualizar_orden_manual",
    ),
    path("orden_parcial/<int:order_id>/", views.orden_parcial, name="orden_parcial"),
    path(
        "ajax/agregar_servicio/",
        views.agregar_servicio_orden,
        name="agregar_servicio_orden",
    ),
    path(
        "actualizar_servicios_parcial/",
        views.actualizar_servicios_parcial,
        name="actualizar_servicios_parcial",
    ),
    path("marcar_entregada/", views.marcar_entregada, name="marcar_entregada"),
    # Configuración
    path("config/modelos/", views.config_modelos, name="config_modelos"),
    path("config/clientes/", views.config_clientes, name="config_clientes"),
    path("config/rutas/", views.config_rutas, name="config_rutas"),
    path('logout/', views.custom_logout_view, name='logout'),
    # Sincronización
    path("sincronizar_ordenes/", views.sincronizar_ordenes, name="sincronizar_ordenes"),
    # Detalles y Edición
    path("editar/<int:order_id>/", views.editar_orden, name="editar_orden"),
    path("<int:order_id>/", views.orden_detalle, name="orden_detalle"),
    # Reportes
    path("reportes/duracion-por-orden/", views.reporte_duracion_orden, name="reporte_duracion_orden"),
    path("reportes/productividad-por-servicio/", views.reporte_productividad_servicio, name="reporte_productividad_servicio"),
]
