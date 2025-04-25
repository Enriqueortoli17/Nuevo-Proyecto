import json
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.forms import inlineformset_factory, NumberInput
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.contrib.auth.models import Group
from .forms import OrdenForm, InventarioSelectionForm, ServicioSelectionForm, MotorForm, ClienteForm
from .models import (
    Orden, OrdenInventario, Servicio, InventarioItem, 
    CatalogoServicio, Cliente, Motor, ESTADO_SERVICIO_CHOICES
)
from .utils import send_whatsapp_message

# --- FUNCIONES AUXILIARES PARA PERMISOS ---
def es_chofer(user):
    """Verifica si el usuario pertenece al grupo 'Chofer'."""
    return user.is_authenticated and user.groups.filter(name='Chofer').exists()

def es_trabajador(user):
    """Verifica si el usuario pertenece al grupo 'Trabajador'."""
    return user.is_authenticated and user.groups.filter(name='Trabajador').exists()

def es_admin_o_chofer(user):
    """Verifica si el usuario es administrador o chofer."""
    return user.is_authenticated and (user.is_superuser or es_chofer(user))

def es_admin_o_trabajador(user):
    """Verifica si el usuario es administrador o trabajador."""
    return user.is_authenticated and (user.is_superuser or es_trabajador(user))
# --- FIN FUNCIONES AUXILIARES ---

# --- FUNCIONES AUXILIARES PARA APIs ---
def api_response(status="ok", data=None, message=None, errors=None, status_code=200):
    """
    Función auxiliar para generar respuestas JSON estandarizadas.
    
    Args:
        status: Estado de la respuesta ("ok", "error", "parcial")
        data: Datos a devolver (opcional)
        message: Mensaje descriptivo (opcional)
        errors: Lista o diccionario de errores (opcional)
        status_code: Código HTTP de respuesta
        
    Returns:
        JsonResponse con estructura estandarizada
    """
    response = {"status": status}
    
    if data is not None:
        response["data"] = data
        
    if message is not None:
        response["message"] = message
        
    if errors is not None:
        response["errors"] = errors
        
    return JsonResponse(response, status=status_code)
# --- FIN FUNCIONES AUXILIARES PARA APIs ---

# --- VISTAS DE PANEL DE CONTROL ---
@login_required
def dashboard(request):
    """
    Vista principal que muestra un resumen general con contadores de órdenes y
    un panel lateral de opciones. Los contadores se calculan a partir de las órdenes.
    """
    # Calcula los contadores basados en el estado general de la orden
    total_ordenes = Orden.objects.count()
    ordenes_aceptadas = Orden.objects.filter(estado_general='ACEPTADA').count()
    ordenes_en_proceso = Orden.objects.filter(estado_general='PROCESO').count()
    ordenes_terminadas = Orden.objects.filter(estado_general='LISTO').count()
    ordenes_entregadas = Orden.objects.filter(estado_general='ENTREGADO').count()
    ordenes_anuladas = Orden.objects.filter(estado_general='ANULADA').count()
    
    context = {
        'total_ordenes': total_ordenes,
        'ordenes_aceptadas': ordenes_aceptadas,
        'ordenes_en_proceso': ordenes_en_proceso,
        'ordenes_terminadas': ordenes_terminadas,
        'ordenes_entregadas': ordenes_entregadas,
        'ordenes_anuladas': ordenes_anuladas,
    }
    return render(request, 'servicios/dashboard.html', context)

# --- VISTAS DE GESTIÓN DE ÓRDENES ---
@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def crear_orden(request):
    """
    Vista para crear una nueva orden de servicio.
    Permite seleccionar cliente, motor, inventario y servicios.
    Incluye gestión de errores mejorada.
    """
    if request.method == 'POST':
        form = OrdenForm(request.POST, request.FILES)
        inv_form = InventarioSelectionForm(request.POST, prefix='inv')
        serv_form = ServicioSelectionForm(request.POST, prefix='serv')
        
        if form.is_valid() and inv_form.is_valid() and serv_form.is_valid():
            try:
                # Guarda la orden principal
                orden = form.save(commit=False)
                orden.chofer = request.user

                # Procesar el campo "cliente" (usando el datalist)
                client_input = form.cleaned_data.get('cliente')
                if client_input:
                    try:
                        client_obj = Cliente.objects.get(nombre__iexact=client_input)
                    except Cliente.DoesNotExist:
                        # Crear nuevo cliente
                        try:
                            client_obj = Cliente.objects.create(
                                nombre=client_input,
                                telefono=form.cleaned_data.get('telefono'),
                                ruta=form.cleaned_data.get('ruta')
                            )
                            messages.success(request, f"Se ha creado un nuevo cliente: {client_input}")
                        except Exception as e:
                            messages.error(request, f"Error al crear el cliente: {str(e)}")
                            raise
                            
                    orden.cliente_registrado = client_obj
                    # Rellena los campos de la orden con los datos del cliente
                    orden.cliente = client_obj.nombre
                    orden.telefono = client_obj.telefono
                    orden.ruta = client_obj.ruta

                # Procesar el campo "modelo_motor" (usando el datalist)
                motor_input = form.cleaned_data.get('modelo_motor')
                if motor_input:
                    try:
                        motor_obj = Motor.objects.get(nombre__iexact=motor_input)
                    except Motor.DoesNotExist:
                        try:
                            motor_obj = Motor.objects.create(nombre=motor_input)
                            messages.success(request, f"Se ha creado un nuevo modelo de motor: {motor_input}")
                        except Exception as e:
                            messages.error(request, f"Error al crear el modelo de motor: {str(e)}")
                            raise
                            
                    orden.motor_registrado = motor_obj
                    orden.modelo_motor = motor_obj.nombre
                
                orden.save()
                messages.success(request, f"Orden {orden.numero_provisional} creada correctamente")

                # Procesa el formulario de Inventario
                inventario_items_creados = 0
                for item in inv_form.item_list:
                    if len(item) == 4:
                        checkbox_name, quantity_name, comment_name, label = item
                        if inv_form.cleaned_data.get(checkbox_name):
                            try:
                                cantidad = inv_form.cleaned_data.get(quantity_name) or 1
                                comentario = inv_form.cleaned_data.get(comment_name) or ""
                                item_id = checkbox_name.split('_')[1]
                                inv_item = InventarioItem.objects.get(id=item_id)
                                OrdenInventario.objects.create(
                                    orden=orden,
                                    inventario_item=inv_item,
                                    cantidad=cantidad,
                                    comentario=comentario
                                )
                                inventario_items_creados += 1
                            except Exception as e:
                                messages.warning(request, f"Error al asociar ítem de inventario '{label}': {str(e)}")
                    elif len(item) == 5:
                        custom_checkbox, custom_name, custom_quantity, custom_comment, label = item
                        if inv_form.cleaned_data.get(custom_checkbox):
                            try:
                                nombre_custom = inv_form.cleaned_data.get(custom_name) or ""
                                if nombre_custom:
                                    cantidad = inv_form.cleaned_data.get(custom_quantity) or 1
                                    comentario = inv_form.cleaned_data.get(custom_comment) or ""
                                    inv_item, created = InventarioItem.objects.get_or_create(nombre=nombre_custom)
                                    if created:
                                        messages.info(request, f"Se ha creado un nuevo ítem de inventario: {nombre_custom}")
                                    OrdenInventario.objects.create(
                                        orden=orden,
                                        inventario_item=inv_item,
                                        cantidad=cantidad,
                                        comentario=comentario
                                    )
                                    inventario_items_creados += 1
                            except Exception as e:
                                messages.warning(request, f"Error al crear ítem de inventario personalizado: {str(e)}")

                if inventario_items_creados > 0:
                    messages.success(request, f"Se agregaron {inventario_items_creados} ítem(s) de inventario")

                # Procesa el formulario de Servicios
                servicios_creados = 0
                for item in serv_form.serv_list:
                    if len(item) == 4:
                        try:
                            selected_field, quantity_required_field, quantity_field, label = item
                            if serv_form.cleaned_data.get(selected_field):
                                if serv_form.cleaned_data.get(quantity_required_field):
                                    cantidad = serv_form.cleaned_data.get(quantity_field) or ""
                                else:
                                    cantidad = ""
                                serv_id = selected_field.split('_')[1]
                                serv = CatalogoServicio.objects.get(id=serv_id)
                                Servicio.objects.create(
                                    orden=orden,
                                    catalogo_servicio=serv,
                                    cantidad=cantidad
                                )
                                servicios_creados += 1
                        except Exception as e:
                            messages.warning(request, f"Error al asociar servicio '{label}': {str(e)}")
                    elif len(item) == 5:
                        try:
                            custom_selected, custom_name, custom_quantity_required, custom_quantity, label = item
                            if serv_form.cleaned_data.get(custom_selected):
                                nombre_custom = serv_form.cleaned_data.get(custom_name) or ""
                                if nombre_custom:
                                    if serv_form.cleaned_data.get(custom_quantity_required):
                                        cantidad = serv_form.cleaned_data.get(custom_quantity) or ""
                                    else:
                                        cantidad = ""
                                    serv_custom, created = CatalogoServicio.objects.get_or_create(nombre=nombre_custom)
                                    if created:
                                        messages.info(request, f"Se ha creado un nuevo servicio: {nombre_custom}")
                                    Servicio.objects.create(
                                        orden=orden,
                                        catalogo_servicio=serv_custom,
                                        cantidad=cantidad
                                    )
                                    servicios_creados += 1
                        except Exception as e:
                            messages.warning(request, f"Error al crear servicio personalizado: {str(e)}")
                
                if servicios_creados > 0:
                    messages.success(request, f"Se agregaron {servicios_creados} servicio(s)")

                return redirect('lista_ordenes')
            except Exception as e:
                messages.error(request, f"Error al crear la orden: {str(e)}")
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
    else:
        form = OrdenForm()
        inv_form = InventarioSelectionForm(prefix='inv')
        serv_form = ServicioSelectionForm(prefix='serv')
    
    context = {
        'form': form,
        'inv_form': inv_form,
        'serv_form': serv_form,
        'clientes': Cliente.objects.all(),
        'motores': Motor.objects.all(),
    }
    return render(request, 'servicios/crear_orden.html', context)

# --- VISTAS DE PROCESAMIENTO DE ÓRDENES ---
@login_required
@user_passes_test(lambda u: u.is_superuser)  # SOLO Admin
def aceptar_orden(request, orden_id):
    """
    Vista para aceptar una orden. Actualiza su estado y asigna número de orden definitivo.
    """
    orden = get_object_or_404(Orden, id=orden_id)
    if orden.estado_general == 'ENTREGADO':
        return redirect('lista_ordenes')
    
    production_date = date.today()
    while production_date.weekday() >= 5:
        production_date += timedelta(days=1)
    
    while Orden.objects.filter(
            fecha_programada=production_date, 
            estado_general__in=['ACEPTADA', 'PROCESO']
          ).count() >= 9:
        production_date += timedelta(days=1)
        while production_date.weekday() >= 5:
            production_date += timedelta(days=1)
    
    orden.fecha_programada = production_date
    orden.estado_general = 'ACEPTADA'
    
    if not orden.numero_orden:
        last_order = Orden.objects.filter(numero_orden__startswith="ORD").order_by("numero_orden").last()
        if last_order and last_order.numero_orden:
            try:
                last_number = int(last_order.numero_orden.replace("ORD", ""))
            except ValueError:
                last_number = 0
            new_number = last_number + 1
        else:
            new_number = 1
        orden.numero_orden = "ORD" + str(new_number).zfill(5)
    
    orden.save()
    
    # Enviar mensaje vía WebSocket para notificar que se ha aceptado la orden
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "ordenes_updates",  # Asegúrate de que este es el grupo al que se suscriben los clientes del tablero
        {
            "type": "orden_aceptada",  # Nuevo tipo de mensaje
            "order_id": orden.id,
            # Puedes incluir datos adicionales que necesites para actualizar la UI
            "order_data": {
                "numero_orden": orden.numero_orden,
                "cliente": orden.cliente,
                "estado_general": orden.estado_general,
                # Puedes agregar otros campos que consideres necesarios
            }
        }
    )
    
    return redirect('lista_ordenes')

# --- VISTAS DE EDICIÓN DE ÓRDENES ---
@login_required
@user_passes_test(lambda u: u.is_superuser)  # SOLO Admin
def editar_orden(request, order_id):
    """
    Vista para editar una orden existente.
    Permite modificar todos los datos, inventario y servicios.
    """
    orden = get_object_or_404(Orden, id=order_id)
    
    # Construir datos iniciales para el formulario de inventario
    initial_inv = {}
    for item in InventarioItem.objects.all():
        try:
            ord_inv = orden.ordeninventario_set.get(inventario_item=item)
            initial_inv[f'item_{item.id}_selected'] = True
            initial_inv[f'item_{item.id}_cantidad'] = ord_inv.cantidad
            initial_inv[f'item_{item.id}_comentario'] = ord_inv.comentario
        except OrdenInventario.DoesNotExist:
            initial_inv[f'item_{item.id}_selected'] = False
            initial_inv[f'item_{item.id}_cantidad'] = 1
            initial_inv[f'item_{item.id}_comentario'] = ""
    # Campo custom para inventario:
    initial_inv['item_custom_selected'] = False
    initial_inv['item_custom_nombre'] = ""
    initial_inv['item_custom_cantidad'] = 1
    initial_inv['item_custom_comentario'] = ""
    
    # Construir datos iniciales para el formulario de servicios
    initial_serv = {}
    for serv in CatalogoServicio.objects.all():
        qs = orden.servicios_detalle.filter(catalogo_servicio=serv)
        if qs.exists():
            ord_serv = qs.first()
            initial_serv[f'serv_{serv.id}_selected'] = True
            initial_serv[f'serv_{serv.id}_quantity'] = ord_serv.cantidad
            initial_serv[f'serv_{serv.id}_quantity_required'] = True
        else:
            initial_serv[f'serv_{serv.id}_selected'] = False
            initial_serv[f'serv_{serv.id}_quantity'] = ""
            initial_serv[f'serv_{serv.id}_quantity_required'] = False
    # Campo custom para servicios:
    initial_serv['serv_custom_selected'] = False
    initial_serv['serv_custom_nombre'] = ""
    initial_serv['serv_custom_quantity_required'] = False
    initial_serv['serv_custom_quantity'] = ""
    
    if request.method == 'POST':
        # Instanciamos los formularios con los datos del POST sin fusionarlos con los iniciales
        form = OrdenForm(request.POST, request.FILES, instance=orden)
        inv_form = InventarioSelectionForm(request.POST, prefix='inv')
        serv_form = ServicioSelectionForm(request.POST, prefix='serv')
        
        if form.is_valid() and inv_form.is_valid() and serv_form.is_valid():
            orden = form.save()
            # Eliminamos las relaciones previas para recrearlas
            orden.ordeninventario_set.all().delete()
            orden.servicios_detalle.all().delete()

            # Procesa el formulario de Inventario
            for item in inv_form.item_list:
                if len(item) == 4:
                    checkbox_name, quantity_name, comment_name, label = item
                    if inv_form.cleaned_data.get(checkbox_name):
                        cantidad = inv_form.cleaned_data.get(quantity_name) or 1
                        comentario = inv_form.cleaned_data.get(comment_name) or ""
                        item_id = checkbox_name.split('_')[1]
                        inv_item = InventarioItem.objects.get(id=item_id)
                        OrdenInventario.objects.create(
                            orden=orden,
                            inventario_item=inv_item,
                            cantidad=cantidad,
                            comentario=comentario
                        )
                elif len(item) == 5:
                    custom_checkbox, custom_name, custom_quantity, custom_comment, label = item
                    if inv_form.cleaned_data.get(custom_checkbox):
                        nombre_custom = inv_form.cleaned_data.get(custom_name) or ""
                        if nombre_custom:
                            cantidad = inv_form.cleaned_data.get(custom_quantity) or 1
                            comentario = inv_form.cleaned_data.get(custom_comment) or ""
                            inv_item, created = InventarioItem.objects.get_or_create(nombre=nombre_custom)
                            OrdenInventario.objects.create(
                                orden=orden,
                                inventario_item=inv_item,
                                cantidad=cantidad,
                                comentario=comentario
                            )

            # Procesa el formulario de Servicios
            for data_tuple in serv_form.serv_list:
                if len(data_tuple) == 4:
                    selected_field, quantity_required_field, quantity_field, label = data_tuple
                    if serv_form.cleaned_data.get(selected_field):
                        if serv_form.cleaned_data.get(quantity_required_field):
                            cantidad = serv_form.cleaned_data.get(quantity_field) or ""
                        else:
                            cantidad = ""
                        serv_id = selected_field.split('_')[1]
                        serv = CatalogoServicio.objects.get(id=serv_id)
                        Servicio.objects.create(
                            orden=orden,
                            catalogo_servicio=serv,
                            cantidad=cantidad
                        )
                        orden.servicios.add(serv)
                elif len(data_tuple) == 5:
                    custom_selected, custom_name, custom_quantity_required, custom_quantity, label = data_tuple
                    if serv_form.cleaned_data.get(custom_selected):
                        nombre_custom = serv_form.cleaned_data.get(custom_name) or ""
                        if nombre_custom:
                            if serv_form.cleaned_data.get(custom_quantity_required):
                                cantidad = serv_form.cleaned_data.get(custom_quantity) or ""
                            else:
                                cantidad = ""
                            serv_custom, created = CatalogoServicio.objects.get_or_create(nombre=nombre_custom)
                            Servicio.objects.create(
                                orden=orden,
                                catalogo_servicio=serv_custom,
                                cantidad=cantidad
                            )
                            orden.servicios.add(serv_custom)

            return redirect('lista_ordenes')
    else:
        form = OrdenForm(instance=orden)
        inv_form = InventarioSelectionForm(initial=initial_inv, prefix='inv')
        serv_form = ServicioSelectionForm(initial=initial_serv, prefix='serv')
    
    context = {
        'form': form,
        'inv_form': inv_form,
        'serv_form': serv_form,
        'orden': orden,
    }
    return render(request, 'servicios/editar_orden.html', context)

# --- VISTAS DE CAMBIO DE ESTADO DE ÓRDENES ---
@login_required
@user_passes_test(lambda u: u.is_superuser)  # SOLO Admin
def anular_orden(request, numero_orden):
    """
    Vista para anular una orden. Cambia el estado a "ANULADA".
    """
    orden = get_object_or_404(Orden, numero_orden=numero_orden)
    orden.estado_general = 'ANULADA'
    orden.save()
    return redirect('lista_ordenes')

# --- VISTAS DE LISTADO Y VISUALIZACIÓN ---
@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def lista_ordenes(request):
    """
    Vista que muestra una lista de todas las órdenes.
    Filtra las órdenes según el rol del usuario.
    """
    # Modificación necesaria aquí para filtrar por chofer
    if not request.user.is_superuser and es_chofer(request.user):
        orders = Orden.objects.filter(chofer=request.user).order_by('fecha_ingreso')
    else:  # Superusuario ve todo
        orders = Orden.objects.all().order_by('fecha_ingreso')
    context = {'orders': orders}
    return render(request, 'servicios/lista_ordenes.html', context)

@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def historial_ordenes(request):
    """
    Vista que muestra el historial de órdenes entregadas.
    """
    # Filtra las órdenes cuyo estado general es "ENTREGADO"
    orders = Orden.objects.filter(estado_general='ENTREGADO').order_by('-fecha_programada')
    context = {'orders': orders}
    return render(request, 'servicios/historial_ordenes.html', context)

@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def ordenes_anuladas(request):
    """
    Vista que muestra las órdenes anuladas.
    """
    # Filtrar las órdenes cuyo estado general es "ANULADA"
    orders = Orden.objects.filter(estado_general='ANULADA').order_by('fecha_ingreso')
    context = {'orders': orders}
    return render(request, 'servicios/ordenes_anuladas.html', context)

@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def ordenes_terminadas(request):
    """
    Vista que muestra las órdenes terminadas (listas para entrega).
    """
    # Obtén el filtro de ruta del query string, si existe
    ruta_filtro = request.GET.get('ruta', None)
    
    # Filtra las órdenes cuyo estado general es "LISTO"
    if ruta_filtro:
        orders = Orden.objects.filter(estado_general='LISTO', ruta=ruta_filtro).order_by('fecha_ingreso')
    else:
        orders = Orden.objects.filter(estado_general='LISTO').order_by('fecha_ingreso')
    
    # Obtener todas las rutas distintas para poblar el filtro (puedes ajustar el campo si se llama de otra forma)
    rutas = Orden.objects.values_list('ruta', flat=True).distinct()
    
    context = {
        'orders': orders,
        'ruta_filtro': ruta_filtro,
        'rutas': rutas,
    }
    return render(request, 'servicios/ordenes_terminadas.html', context)

@login_required
def home(request):
    """
    Vista de inicio.
    """
    return render(request, 'servicios/partials/home_content.html')

# --- VISTAS DE DETALLE ---
@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def orden_detalle(request, order_id):
    """
    Vista para ver el detalle de una orden específica.
    """
    orden = get_object_or_404(Orden, id=order_id)
    inventario_items = orden.ordeninventario_set.all()
    servicios = orden.servicios_detalle.all()
    context = {
        'orden': orden,
        'inventario_items': inventario_items,
        'servicios': servicios,
    }
    return render(request, 'servicios/orden_detalle.html', context)

@user_passes_test(es_admin_o_trabajador)
def orden_parcial(request, order_id):
    """
    Vista que devuelve el HTML parcial de una orden para actualizaciones AJAX.
    """
    order = get_object_or_404(Orden, id=order_id)
    estado_choices = Servicio._meta.get_field('estado').choices
    return render(request, 'servicios/orden_parcial.html', {'order': order, 'service_state_choices': estado_choices})

# --- VISTAS DE TABLERO ---
@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def tablero_ordenes(request):
    """
    Vista que muestra el tablero Kanban de órdenes.
    Usa prefetch_related para optimizar consultas a servicios.
    """
    # Filtra órdenes en estado ACEPTADA o EN PROCESO con prefetch_related para servicios
    orders = Orden.objects.filter(
        estado_general__in=['ACEPTADA', 'PROCESO']
    ).prefetch_related(
        'servicios_detalle__catalogo_servicio'  # Precarga servicios y catálogos
    ).order_by('fecha_programada', 'posicion', 'fecha_ingreso')
    
    today = timezone.localdate()

    # Definir grupos fijos: Pendientes y días de lunes a viernes
    grupos = {
        'Pendientes': [],
        'Lunes': [],
        'Martes': [],
        'Miércoles': [],
        'Jueves': [],
        'Viernes': [],
    }
    # Diccionario para traducir el día en inglés a español
    traducciones = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo',
    }

    # Agrupar cada orden
    for order in orders:
        if not order.fecha_programada or order.fecha_programada < today:
            grupos['Pendientes'].append(order)
        else:
            weekday = order.fecha_programada.strftime('%A')
            dia = traducciones.get(weekday)
            if dia and dia in grupos:
                grupos[dia].append(order)
            else:
                grupos['Pendientes'].append(order)

    # Ordenar cada grupo por el campo 'posicion'
    for key in grupos:
        grupos[key].sort(key=lambda o: o.posicion)

    # Lista de días fijos
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    # Obtener el día actual en español
    current_day = traducciones.get(today.strftime('%A'))
    # Reordenar la lista para que el día actual aparezca primero (si se encuentra en la lista)
    if current_day in days:
        index = days.index(current_day)
        ordered_days = days[index:] + days[:index]
    else:
        ordered_days = days

    # Construir la lista final de grupos (si algún grupo no tiene órdenes, seguirá apareciendo vacío)
    ordered_groups = []
    ordered_groups.append(('Pendientes', grupos.get('Pendientes', [])))
    for d in ordered_days:
        ordered_groups.append((d, grupos.get(d, [])))
    
    context = {
        'ordered_groups': ordered_groups,
    }
    return render(request, 'servicios/tablero_ordenes.html', context)

@user_passes_test(es_admin_o_chofer)
def tablero_parcial(request):
    """
    Vista que devuelve el HTML parcial del tablero para actualizaciones AJAX.
    Con optimización de consultas mediante prefetch_related.
    """
    # Obtener las órdenes en estado ACEPTADA o EN PROCESO con prefetch_related
    orders = Orden.objects.filter(
        estado_general__in=['ACEPTADA', 'PROCESO']
    ).prefetch_related(
        'servicios_detalle__catalogo_servicio'  # Precarga servicios y catálogos
    ).order_by('fecha_programada', 'posicion', 'fecha_ingreso')
    
    today = timezone.localdate()

    # Inicializar los grupos: "Pendientes" y días de la semana (de lunes a viernes)
    grupos = {
        'Pendientes': [],
        'Lunes': [],
        'Martes': [],
        'Miércoles': [],
        'Jueves': [],
        'Viernes': [],
    }
    traducciones = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo',
    }

    # Agrupar las órdenes según su fecha_programada
    for order in orders:
        if not order.fecha_programada or order.fecha_programada < today:
            grupos['Pendientes'].append(order)
        else:
            weekday = order.fecha_programada.strftime('%A')
            dia = traducciones.get(weekday, weekday)
            if dia in grupos:
                grupos[dia].append(order)
            else:
                grupos['Pendientes'].append(order)

    # Ordenar cada grupo por el campo 'posicion'
    for key in grupos:
        grupos[key].sort(key=lambda o: o.posicion)

    # Reordenar los días para que el día actual aparezca primero
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    current_day = traducciones.get(today.strftime('%A'))
    if current_day in days:
        index = days.index(current_day)
        ordered_days = days[index:] + days[:index]
    else:
        ordered_days = days

    # Construir la lista final de grupos ordenados: primero "Pendientes", luego los días en orden
    ordered_groups = []
    ordered_groups.append(('Pendientes', grupos['Pendientes']))
    for d in ordered_days:
        ordered_groups.append((d, grupos[d]))

    # Obtener las opciones de estado del modelo Servicio
    estado_choices = Servicio._meta.get_field('estado').choices

    context = {
        'ordered_groups': ordered_groups,
        'service_state_choices': estado_choices,
    }
    # Renderiza la plantilla parcial que contiene solo el contenido dinámico del Tablero.
    return render(request, 'servicios/tablero_parcial.html', context)

# --- VISTAS DE ACTUALIZACIÓN DE SERVICIOS ---
@login_required
@user_passes_test(es_admin_o_trabajador)  # Permite Admin Y Trabajador
def actualizar_servicios(request):
    """
    Vista que muestra la página para actualizar el estado de los servicios.
    
    Esta función obtiene todas las órdenes en estado ACEPTADA o EN PROCESO,
    precargando los servicios relacionados para reducir el número de consultas,
    y los agrupa por día de la semana para su visualización y actualización.
    """
    # Filtra las órdenes en estado ACEPTADA o EN PROCESO, con precarga de servicios
    orders = Orden.objects.filter(
        estado_general__in=['ACEPTADA', 'PROCESO']
    ).prefetch_related(
        'servicios_detalle__catalogo_servicio'  # Precarga servicios y catálogos
    ).order_by('fecha_programada', 'fecha_ingreso')
    
    today = date.today()

    # Inicializar grupos
    grupos = {
        'Pendientes': [],
        'Lunes': [],
        'Martes': [],
        'Miércoles': [],
        'Jueves': [],
        'Viernes': [],
    }
    # Traducción de días en inglés a español
    traducciones = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo',
    }

    # Agrupar órdenes: si no tienen fecha_programada o la fecha es menor que hoy, se agrupan en "Pendientes"
    for order in orders:
        if not order.fecha_programada or order.fecha_programada < today:
            grupos['Pendientes'].append(order)
        else:
            weekday = order.fecha_programada.strftime('%A')
            dia = traducciones.get(weekday, weekday)
            if dia in grupos:
                grupos[dia].append(order)
            else:
                grupos['Pendientes'].append(order)

    for key in grupos:
        grupos[key].sort(key=lambda o: o.posicion)

    # Ordenar los días: obtener la lista de días y reordenarla para que el día actual aparezca primero
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    current_day = traducciones.get(today.strftime('%A'))
    if current_day in days:
        index = days.index(current_day)
        ordered_days = days[index:] + days[:index]
    else:
        ordered_days = days

    # Construir la lista de grupos ordenados: primero "Pendientes", luego los días en el orden determinado
    ordered_groups = []
    ordered_groups.append(('Pendientes', grupos['Pendientes']))
    for d in ordered_days:
        ordered_groups.append((d, grupos[d]))

    # Obtener las opciones de estado para el select
    estado_choices = Servicio._meta.get_field('estado').choices

    # Aquí se agrega la lista de servicios para el modal, también con prefetch para optimizar
    context = {
        'ordered_groups': ordered_groups,
        'service_state_choices': estado_choices,
        'servicios_list': CatalogoServicio.objects.all(),
    }
    return render(request, 'servicios/actualizar_servicios.html', context)

@login_required
@user_passes_test(es_admin_o_trabajador)  # Permite Admin Y Trabajador
def actualizar_servicios_parcial(request):
    """
    Vista que devuelve el HTML parcial de la página de actualización de servicios.
    """
    # Misma lógica que la vista actualizar_servicios original
    orders = Orden.objects.filter(estado_general__in=['ACEPTADA', 'PROCESO']).order_by('fecha_programada', 'fecha_ingreso')
    today = date.today()

    grupos = {
        'Pendientes': [],
        'Lunes': [],
        'Martes': [],
        'Miércoles': [],
        'Jueves': [],
        'Viernes': [],
    }

    traducciones = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes',
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo',
    }

    for order in orders:
        if not order.fecha_programada or order.fecha_programada < today:
            grupos['Pendientes'].append(order)
        else:
            weekday = order.fecha_programada.strftime('%A')
            dia = traducciones.get(weekday, weekday)
            if dia in grupos:
                grupos[dia].append(order)
            else:
                grupos['Pendientes'].append(order)

    for key in grupos:
        grupos[key].sort(key=lambda o: o.posicion)

    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    current_day = traducciones.get(today.strftime('%A'))
    if current_day in days:
        index = days.index(current_day)
        ordered_days = days[index:] + days[:index]
    else:
        ordered_days = days

    ordered_groups = [('Pendientes', grupos['Pendientes'])]
    ordered_groups += [(d, grupos[d]) for d in ordered_days]

    estado_choices = Servicio._meta.get_field('estado').choices

    context = {
        'ordered_groups': ordered_groups,
        'service_state_choices': estado_choices,
        'servicios_list': CatalogoServicio.objects.all(),
    }
    return render(request, 'servicios/actualizar_servicios_parcial.html', context)

# --- API ENDPOINTS ---
@csrf_exempt
@login_required
@user_passes_test(es_admin_o_trabajador)  # Permite Admin Y Trabajador
def actualizar_estado_servicio(request):
    """
    API para actualizar el estado de un servicio vía AJAX.
    """
    if request.method != 'POST':
        return api_response(status="error", message="Método no permitido", status_code=405)
        
    try:
        data = json.loads(request.body)
        if not data:
            return api_response(
                status="error", 
                message="No se recibieron datos", 
                status_code=400
            )
            
        service_id = data.get('service_id')
        nuevo_estado = data.get('estado')
        
        if service_id is None or nuevo_estado is None:
            return api_response(
                status="error", 
                message="Faltan parámetros requeridos", 
                errors={"missing": ["service_id", "estado"] if service_id is None and nuevo_estado is None 
                                  else ["service_id"] if service_id is None else ["estado"]},
                status_code=400
            )
        
        try:
            servicio = Servicio.objects.get(id=service_id)
        except Servicio.DoesNotExist:
            return api_response(
                status="error", 
                message="Servicio no encontrado", 
                errors={"service_id": f"No existe servicio con ID {service_id}"},
                status_code=404
            )
            
        servicio.estado = nuevo_estado
        servicio.save()

        # Actualiza el estado general de la orden
        orden = servicio.orden
        orden.actualizar_estado_general()

        # Notificar vía WebSockets
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "servicios_updates",
            {
                "type": "service_update",
                "service_id": service_id,
                "estado": nuevo_estado,
            }
        )

        # Manejar notificaciones adicionales según el cambio de estado
        if orden.estado_general == "LISTO":
            async_to_sync(channel_layer.group_send)(
                "ordenes_updates",
                {
                    "type": "orden_terminada",
                    "order_id": orden.id,
                }
            )
        elif orden.estado_general == "PROCESO":
            async_to_sync(channel_layer.group_send)(
                "ordenes_updates",
                {
                    "type": "orden_update",
                    "order_id": orden.id,
                    "nuevo_estado": "EN Proceso",
                }
            )

        return api_response(
            data={
                "service_id": service_id, 
                "estado": nuevo_estado,
                "orden_estado": orden.estado_general
            },
            message="Estado de servicio actualizado correctamente"
        )
        
    except json.JSONDecodeError:
        return api_response(
            status="error", 
            message="JSON inválido", 
            status_code=400
        )
    except Exception as e:
        return api_response(
            status="error", 
            message=f"Error en el servidor: {str(e)}", 
            status_code=500
        )

@csrf_exempt
@user_passes_test(es_admin_o_trabajador)
def agregar_servicio_orden(request):
    """
    API para agregar un servicio a una orden específica vía AJAX.
    
    Se espera recibir un JSON con:
      - order_id: el id (o número de orden) de la orden a actualizar.
      - servicio_id: el id del servicio a agregar (o, si es custom, un valor especial, p.ej. "custom").
      - nombre_custom (opcional): si es un servicio custom, el nombre ingresado.
      - cantidad: el valor (texto) de la cantidad.
      - observacion (opcional): alguna observación.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order_id = data.get("order_id")
            servicio_id = data.get("servicio_id")
            cantidad = data.get("cantidad", "")
            observacion = data.get("observacion", "")
            nombre_custom = data.get("nombre_custom", "").strip()

            # Buscar la orden; suponemos que order_id corresponde al id o numero_orden
            order = Orden.objects.filter(id=order_id).first()
            if not order:
                return JsonResponse({"status": "error", "error": "Orden no encontrada."}, status=404)

            # Si el servicio_id es "custom" o similar, se toma el nombre custom
            if servicio_id == "custom":
                if not nombre_custom:
                    return JsonResponse({"status": "error", "error": "Debe ingresar el nombre del servicio custom."}, status=400)
                serv_obj, created = CatalogoServicio.objects.get_or_create(nombre=nombre_custom)
            else:
                serv_obj = CatalogoServicio.objects.filter(id=servicio_id).first()
                if not serv_obj:
                    return JsonResponse({"status": "error", "error": "Servicio no encontrado."}, status=404)

            # Crear el servicio asociado a la orden.
            new_service = Servicio.objects.create(
                orden=order,
                catalogo_servicio=serv_obj,
                cantidad=cantidad,
                observaciones=observacion
            )
            order.servicios.add(serv_obj)

            # Enviar notificación vía WebSocket para actualizar la tarjeta de la orden
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "ordenes_updates",
                {
                    "type": "servicio_agregado",  # Nuevo tipo de mensaje
                    "order_id": order.id,
                    "servicio": {
                        "id": new_service.id,
                        "nombre": serv_obj.nombre,
                        "cantidad": new_service.cantidad,
                        "estado": new_service.estado,
                    }
                }
            )
            return JsonResponse({"status": "ok", "mensaje": "Servicio agregado."})
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=400)
    else:
        return JsonResponse({"status": "error", "error": "Método no permitido."}, status=405)

# --- ENDPOINTS PARA ACTUALIZACIÓN DE ÓRDENES ---
@csrf_exempt
@user_passes_test(es_admin_o_chofer)
def actualizar_orden_manual(request):
    """
    API para actualizar el orden y la fecha programada de las órdenes vía AJAX.
    
    Esta función permite reasignar órdenes a diferentes días de la semana y 
    cambiar su posición en el tablero Kanban. Las órdenes movidas a un día específico
    tendrán su fecha_programada actualizada al próximo día correspondiente.
    
    Args:
        request: La solicitud HTTP con un JSON que debe contener:
            - grupo: Nombre del grupo/día ("Pendientes", "Lunes", etc.)
            - nuevo_orden: Lista de objetos con {id, newPos} para cada orden
            
    Returns:
        JsonResponse con el resultado de la operación
        
    Raises:
        JSONDecodeError: Si el cuerpo de la solicitud no es un JSON válido
        Exception: Si ocurre algún error durante el procesamiento
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            grupo = data.get('grupo')
            nuevo_orden = data.get('nuevo_orden')  # Lista de objetos: {id: ..., newPos: ...}
            
            # Si el grupo no es "Pendientes", actualizamos también la fecha_programada según el día
            if grupo != "Pendientes":
                day_mapping = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4}
                if grupo in day_mapping:
                    target_day = day_mapping[grupo]
                    today = date.today()
                    days_ahead = target_day - today.weekday()
                    if days_ahead < 0:  # Solo si es negativo se suma 7
                        days_ahead += 7
                    new_date = today + timedelta(days=days_ahead)
                else:
                    new_date = None
            else:
                new_date = None

            # Actualizar cada orden con el nuevo valor de posicion
            for item in nuevo_orden:
                order_id = item.get('id')
                new_pos = item.get('newPos')
                order = Orden.objects.filter(id=order_id).first()
                if order:
                    order.posicion = new_pos
                    if new_date is not None:
                        order.fecha_programada = new_date
                    else:
                        order.fecha_programada = None
                    order.save()

            # Enviar mensaje vía WebSocket para notificar al Tablero
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "ordenes_updates",
                {
                    "type": "orden_reorder",
                    "grupo": grupo,
                    "nuevo_orden": nuevo_orden,
                    "orden_completa": True,  # Indica que es una actualización completa
                    "timestamp": datetime.now().isoformat()  # Añadir timestamp para forzar actualización
                }
            )
            return api_response(
                message="Orden actualizada correctamente",
                data={"grupo": grupo, "ordenes_actualizadas": len(nuevo_orden)}
            )
        except json.JSONDecodeError:
            return api_response(
                status="error", 
                message="JSON inválido en la solicitud", 
                status_code=400
            )
        except Exception as e:
            return api_response(
                status="error", 
                message=f"Error al actualizar el orden: {str(e)}", 
                status_code=500
            )
    return api_response(
        status="error", 
        message="Método no permitido", 
        status_code=405
    )

@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser)  # SOLO Admin
def marcar_entregada(request):
    """
    API para marcar una orden como entregada vía AJAX.
    
    Esta función actualiza el estado de una orden a 'ENTREGADO', 
    envía una notificación por WhatsApp si el cliente tiene teléfono configurado,
    y notifica a través de WebSockets para actualizar la interfaz en tiempo real.
    """
    if request.method != "POST":
        return api_response(status="error", message="Método no permitido", status_code=405)
        
    try:
        data = json.loads(request.body)
        order_id = data.get("order_id")
        
        if not order_id:
            return api_response(
                status="error", 
                message="Falta el ID de la orden", 
                status_code=400
            )
            
        try:
            order = Orden.objects.get(id=order_id)
        except Orden.DoesNotExist:
            return api_response(
                status="error", 
                message=f"No se encontró la orden con ID {order_id}", 
                status_code=404
            )
            
        # Actualiza el estado de la orden a "ENTREGADO"
        old_estado = order.estado_general
        order.estado_general = "ENTREGADO"
        order.save()

        # Envía el mensaje de WhatsApp
        whatsapp_enviado = False
        if order.telefono:
            try:
                send_whatsapp_message(
                    order.telefono, 
                    f"¡Tu orden {order.numero_orden} ha sido entregada! Gracias por confiar en nosotros."
                )
                whatsapp_enviado = True
            except Exception as e:
                # Log error pero no fallar completamente si WhatsApp falla
                print(f"Error al enviar WhatsApp: {e}")
        
        # Enviar mensaje vía WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "ordenes_updates",
            {
                "type": "orden_entregada",
                "order_id": order.id,
            }
        )
        
        return api_response(
            message="Orden marcada como entregada correctamente",
            data={
                "order_id": order.id,
                "numero_orden": order.numero_orden,
                "cliente": order.cliente,
                "estado_anterior": old_estado,
                "estado_nuevo": "ENTREGADO",
                "whatsapp_enviado": whatsapp_enviado
            }
        )
    except json.JSONDecodeError:
        return api_response(
            status="error", 
            message="JSON inválido en la solicitud", 
            status_code=400
        )
    except Exception as e:
        return api_response(
            status="error", 
            message=f"Error en el servidor: {str(e)}", 
            status_code=500
        )

# --- VISTAS DE CONFIGURACIÓN ---
@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer ver/crear
def config_modelos(request):
    """
    Vista para configurar los modelos de motor.
    Los choferes pueden ver, solo los admins pueden editar.
    """
    motor_editar = None
    editar_id = request.GET.get('editar_id')
    if editar_id:
        if request.user.is_superuser:
            motor_editar = get_object_or_404(Motor, id=editar_id)
        else:
            return HttpResponse("Acceso denegado para editar.", status=403)

    if request.method == 'POST':
        motor_id = request.POST.get('motor_id')
        if motor_id:
            if not request.user.is_superuser:
                return HttpResponse("Acción no permitida.", status=403)
            motor = get_object_or_404(Motor, id=motor_id)
            form = MotorForm(request.POST, instance=motor)
        else:
            form = MotorForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, f"Motor {'actualizado' if motor_id else 'guardado'} correctamente.")
            return redirect('config_modelos')
        else:
             messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        if motor_editar:
            form = MotorForm(instance=motor_editar)
        else:
            form = MotorForm()

    motores = Motor.objects.all()
    can_edit = request.user.is_superuser
    context = {
        'form': form,
        'motores': motores,
        'motor_editar': motor_editar if can_edit else None,
        'can_edit': can_edit
    }
    return render(request, 'servicios/config_modelos.html', context)

@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer ver/crear
def config_clientes(request):
    """
    Vista para configurar los clientes.
    Los choferes pueden ver, solo los admins pueden editar.
    """
    cliente_editar = None
    editar_id = request.GET.get('editar_id')
    if editar_id:
        # SOLO el superusuario puede obtener el objeto para editar
        if request.user.is_superuser:
            cliente_editar = get_object_or_404(Cliente, id=editar_id)
        else:
            # Si un chofer intenta editar, niega el acceso o redirige
            return HttpResponse("Acceso denegado para editar.", status=403)  # O redirect

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        if cliente_id:
            # SOLO el superusuario puede procesar una edición
            if not request.user.is_superuser:
                 return HttpResponse("Acción no permitida.", status=403)  # O redirect
            cliente = get_object_or_404(Cliente, id=cliente_id)
            form = ClienteForm(request.POST, instance=cliente)
        else:
            # Crear es permitido para Admin y Chofer
            form = ClienteForm(request.POST)

        if form.is_valid():
            form.save()
            # Añadir mensaje de éxito
            messages.success(request, f"Cliente {'actualizado' if cliente_id else 'guardado'} correctamente.")
            return redirect('config_clientes')
        else:
            # Añadir mensaje de error si el formulario no es válido
             messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        # Si hay cliente_editar (y el user es admin), usa esa instancia
        if cliente_editar:
            form = ClienteForm(instance=cliente_editar)
        else:
            form = ClienteForm()

    clientes = Cliente.objects.all()
    # Pasamos explícitamente si se permite editar para usar en la plantilla
    can_edit = request.user.is_superuser
    context = {
        'form': form,
        'clientes': clientes,
        'cliente_editar': cliente_editar if can_edit else None,  # Solo pasa si puede editar
        'can_edit': can_edit
    }
    return render(request, 'servicios/config_clientes.html', context)

def config_rutas(request):
    """
    Vista para configurar rutas (en construcción).
    """
    return HttpResponse("<h1>Configuración: Rutas - En construcción</h1>")

# --- VISTAS DE SINCRONIZACIÓN ---
@csrf_exempt
@login_required
@user_passes_test(es_admin_o_chofer)  # Permite Admin Y Chofer
def sincronizar_ordenes(request):
    """
    Vista para sincronizar las órdenes capturadas offline.
    Recibe un JSON con una lista de órdenes, cada una puede contener
    listas de 'inventario' y 'servicios'.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ordenes_capturadas = data.get("ordenes", [])
            if not isinstance(ordenes_capturadas, list):
                raise ValueError("El formato de 'ordenes' debe ser una lista.")

            resultados_ok = []
            resultados_error = []
            errores_items = []  # Para errores específicos de inventario/servicio

            for orden_data in ordenes_capturadas:
                if not isinstance(orden_data, dict):
                    resultados_error.append({"error": "Formato de orden inválido (no es diccionario)", "data_recibida": orden_data})
                    continue

                orden = None  # Inicializa orden como None para el manejo de errores
                try:
                    # Crear la orden principal
                    # Asegurarse de que los campos obligatorios existan o manejar el error
                    cliente_nombre = orden_data.get("cliente")
                    if not cliente_nombre:
                         raise ValueError("El campo 'cliente' es obligatorio.")

                    orden = Orden.objects.create(
                        cliente=cliente_nombre,
                        telefono=orden_data.get("telefono"),
                        modelo_motor=orden_data.get("modelo_motor"),
                        ruta=orden_data.get("ruta"),
                        notificacion=orden_data.get("notificacion", ""),
                        fecha_ingreso=datetime.now(),  # Fecha del servidor
                        estado_general='ESPERA',  # Estado inicial
                        chofer=request.user  # Asigna el usuario que está sincronizando
                    )

                    # Procesar Inventario (si existe en los datos)
                    inventario_data = orden_data.get("inventario", [])
                    if isinstance(inventario_data, list):
                        for item_data in inventario_data:
                            try:
                                if not isinstance(item_data, dict):
                                    raise ValueError("Formato de ítem de inventario inválido.")

                                cantidad = item_data.get('cantidad', 1)
                                comentario = item_data.get('comentario', '')
                                inv_item = None

                                if 'id' in item_data:
                                    inv_item = InventarioItem.objects.filter(id=item_data['id']).first()
                                    if not inv_item:
                                        raise ValueError(f"Ítem de inventario con ID {item_data['id']} no encontrado.")
                                elif 'nombre' in item_data and item_data['nombre']:
                                    inv_item, created = InventarioItem.objects.get_or_create(
                                        nombre=item_data['nombre'].strip()
                                    )
                                else:
                                     raise ValueError("Ítem de inventario debe tener 'id' o 'nombre'.")

                                OrdenInventario.objects.create(
                                    orden=orden,
                                    inventario_item=inv_item,
                                    cantidad=cantidad,
                                    comentario=comentario
                                )
                            except Exception as item_error:
                                errores_items.append({
                                    "orden_cliente": orden_data.get("cliente", "N/A"),
                                    "tipo": "inventario",
                                    "item_data": item_data,
                                    "error": str(item_error)
                                })
                    else:
                         errores_items.append({ "orden_cliente": orden_data.get("cliente", "N/A"), "tipo": "inventario", "error": "La clave 'inventario' no es una lista."})

                    # Procesar Servicios (si existe en los datos)
                    servicios_data = orden_data.get("servicios", [])
                    if isinstance(servicios_data, list):
                        for serv_data in servicios_data:
                             try:
                                if not isinstance(serv_data, dict):
                                    raise ValueError("Formato de servicio inválido.")

                                cantidad = serv_data.get('cantidad', '')  # Cantidad es CharField, puede ser vacío
                                serv_obj = None

                                if 'id' in serv_data:
                                    serv_obj = CatalogoServicio.objects.filter(id=serv_data['id']).first()
                                    if not serv_obj:
                                         raise ValueError(f"Servicio con ID {serv_data['id']} no encontrado.")
                                elif 'nombre' in serv_data and serv_data['nombre']:
                                     serv_obj, created = CatalogoServicio.objects.get_or_create(
                                         nombre=serv_data['nombre'].strip()
                                     )
                                else:
                                    raise ValueError("Servicio debe tener 'id' o 'nombre'.")

                                # Crear la instancia de Servicio (que actúa como 'through' model)
                                Servicio.objects.create(
                                    orden=orden,
                                    catalogo_servicio=serv_obj,
                                    cantidad=cantidad,
                                    estado='PENDIENTE'  # Estado inicial para servicios sincronizados
                                    # 'observaciones' podrías añadirlo si lo capturas offline
                                )
                                # No necesitas 'orden.servicios.add(serv_obj)' porque Servicio ya lo relaciona
                             except Exception as serv_error:
                                 errores_items.append({
                                     "orden_cliente": orden_data.get("cliente", "N/A"),
                                     "tipo": "servicio",
                                     "item_data": serv_data,
                                     "error": str(serv_error)
                                 })
                    else:
                         errores_items.append({ "orden_cliente": orden_data.get("cliente", "N/A"), "tipo": "servicio", "error": "La clave 'servicios' no es una lista."})

                    # Si llegamos aquí sin error fatal para la orden, la añadimos a OK
                    resultados_ok.append({
                        "orden_provisional": orden.numero_provisional,  # Usamos el provisional por si acaso
                        "id_servidor": orden.id,
                        "cliente": orden.cliente
                    })

                except Exception as e:
                    # Captura error al crear la orden principal
                    resultados_error.append({
                        "error": f"Error al crear orden para cliente '{orden_data.get('cliente', 'N/A')}': {str(e)}",
                        "data_recibida": orden_data
                    })

            # Construir respuesta final
            response_data = {
                "status": "ok" if not resultados_error and not errores_items else "parcial",
                "ordenes_creadas": resultados_ok,
                "errores_creacion_orden": resultados_error,
                "errores_items": errores_items,
                "mensaje": f"{len(resultados_ok)} órdenes sincronizadas. {len(resultados_error)} errores al crear órdenes. {len(errores_items)} errores en ítems/servicios."
            }
            status_code = 200 if not resultados_error and not errores_items else 207  # 207 Multi-Status si hubo errores parciales

            return JsonResponse(response_data, status=status_code)

        except json.JSONDecodeError:
             return JsonResponse({"status": "error", "error": "JSON inválido recibido."}, status=400)
        except Exception as e:
             # Captura cualquier otro error inesperado
             return JsonResponse({"status": "error", "error": f"Error general en el servidor: {str(e)}"}, status=500)

    # Si es GET, muestra la plantilla (o redirige)
    return render(request, 'servicios/sincronizar_ordenes.html')