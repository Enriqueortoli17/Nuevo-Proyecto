from django.shortcuts import render, redirect, get_object_or_404
from .forms import OrdenForm, InventarioSelectionForm, ServicioSelectionForm, MotorForm, ClienteForm
from .models import Orden, OrdenInventario, Servicio, InventarioItem, CatalogoServicio, Cliente, Motor
from datetime import date, timedelta, datetime

def crear_orden(request):
    if request.method == 'POST':
        form = OrdenForm(request.POST, request.FILES)
        inv_form = InventarioSelectionForm(request.POST, prefix='inv')
        serv_form = ServicioSelectionForm(request.POST, prefix='serv')
        if form.is_valid() and inv_form.is_valid() and serv_form.is_valid():
            # Guarda la orden principal
            orden = form.save(commit=False)
            orden.chofer = request.user

            # Procesar el campo "cliente" (usando el datalist)
            client_input = form.cleaned_data.get('cliente')
            if client_input:
                try:
                    client_obj = Cliente.objects.get(nombre__iexact=client_input)
                except Cliente.DoesNotExist:
                    client_obj = Cliente.objects.create(
                        nombre=client_input,
                        telefono=form.cleaned_data.get('telefono'),
                        ruta=form.cleaned_data.get('ruta')
                    )
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
                    motor_obj = Motor.objects.create(nombre=motor_input)
                orden.motor_registrado = motor_obj
                orden.modelo_motor = motor_obj.nombre
            
            orden.save()

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
            for item in serv_form.serv_list:
                if len(item) == 4:
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
                        orden.servicios.add(serv)
                elif len(item) == 5:
                    custom_selected, custom_name, custom_quantity_required, custom_quantity, label = item
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


from django.shortcuts import get_object_or_404, redirect
from datetime import date, timedelta
from .models import Orden
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def aceptar_orden(request, orden_id):
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
    
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory, NumberInput
from .forms import OrdenForm, InventarioSelectionForm, ServicioSelectionForm
from .models import Orden, OrdenInventario, Servicio, InventarioItem, CatalogoServicio

def editar_orden(request, order_id):
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

def anular_orden(request, numero_orden):
    """
    Vista para anular una orden. Cambia el estado a "ANULADA".
    """
    orden = get_object_or_404(Orden, numero_orden=numero_orden)
    orden.estado_general = 'ANULADA'
    orden.save()
    return redirect('lista_ordenes')

from django.shortcuts import render
from collections import defaultdict
from .models import Orden
from django.contrib.auth.models import Group  # Asegúrate de importar esto

def lista_ordenes(request):
    if request.user.groups.filter(name="Chofer").exists():
        orders = Orden.objects.filter(chofer=request.user).order_by('fecha_ingreso')
    else:
        orders = Orden.objects.all().order_by('fecha_ingreso')
    context = {'orders': orders}
    return render(request, 'servicios/lista_ordenes.html', context)

from django.shortcuts import render, get_object_or_404
from .models import Orden

def orden_detalle(request, order_id):
    orden = get_object_or_404(Orden, id=order_id)
    inventario_items = orden.ordeninventario_set.all()
    servicios = orden.servicios_detalle.all()
    context = {
        'orden': orden,
        'inventario_items': inventario_items,
        'servicios': servicios,
    }
    return render(request, 'servicios/orden_detalle.html', context)

from datetime import date, timedelta, datetime
from django.shortcuts import render
from .models import Orden
from django.utils import timezone

def tablero_ordenes(request):
    # Filtra órdenes en estado ACEPTADA o EN PROCESO
    orders = Orden.objects.filter(estado_general__in=['ACEPTADA', 'PROCESO']).order_by('fecha_programada', 'posicion', 'fecha_ingreso')
    today = timezone.localdate()
    ayer = today - timedelta(days=1)

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

from datetime import date
from django.shortcuts import render
from .models import Orden, Servicio
from django.utils import timezone

def tablero_parcial(request):
    # Obtener las órdenes en estado ACEPTADA o EN PROCESO, ordenadas por fecha_programada, posicion y fecha_ingreso.
    orders = Orden.objects.filter(estado_general__in=['ACEPTADA', 'PROCESO']).order_by('fecha_programada', 'posicion', 'fecha_ingreso')
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


from django.shortcuts import render
from .models import Orden

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

from django.shortcuts import render
from .models import Orden, Servicio, CatalogoServicio
from django.db.models import Q
from datetime import date, timedelta, datetime

def actualizar_servicios(request):
    # Filtra las órdenes en estado ACEPTADA o EN PROCESO, ordenándolas por fecha_programada y fecha_ingreso
    orders = Orden.objects.filter(estado_general__in=['ACEPTADA', 'PROCESO']).order_by('fecha_programada', 'fecha_ingreso')
    today = date.today()
    ayer = today - timedelta(days=1)

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

    # Aquí se agrega la lista de servicios para el modal
    context = {
        'ordered_groups': ordered_groups,
        'service_state_choices': estado_choices,
        'servicios_list': CatalogoServicio.objects.all(),
    }
    return render(request, 'servicios/actualizar_servicios.html', context)

def actualizar_servicios_parcial(request):
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

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Servicio
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@csrf_exempt
def actualizar_estado_servicio(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not data:
                return JsonResponse({'status': 'error', 'error': 'No se recibieron datos'}, status=400)
            service_id = data.get('service_id')
            nuevo_estado = data.get('estado')
            if service_id is None or nuevo_estado is None:
                return JsonResponse({'status': 'error', 'error': 'Faltan parámetros'}, status=400)
            servicio = Servicio.objects.get(id=service_id)
            servicio.estado = nuevo_estado
            servicio.save()

            # Actualiza el estado general de la orden
            orden = servicio.orden
            orden.actualizar_estado_general()

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "servicios_updates",
                {
                    "type": "service_update",
                    "service_id": service_id,
                    "estado": nuevo_estado,
                }
            )

            if orden.estado_general == "LISTO":
                async_to_sync(channel_layer.group_send)(
                    "ordenes_updates",
                    {
                        "type": "orden_terminada",
                        "order_id": orden.id,
                    }
                )
            # NUEVO: Si la orden pasó a "PROCESO", enviar mensaje para que actualice la etiqueta
            elif orden.estado_general == "PROCESO":
                async_to_sync(channel_layer.group_send)(
                    "ordenes_updates",
                    {
                        "type": "orden_update",  # Nuevo tipo de mensaje
                        "order_id": orden.id,
                        "nuevo_estado": "EN Proceso",  # Puedes personalizar el texto aquí
                    }
                )

            return JsonResponse({'status': 'ok', 'service_id': service_id, 'estado': nuevo_estado})
        except Servicio.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': 'Servicio no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'error': 'Método no permitido'}, status=405)

import json
from datetime import date, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Orden
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@csrf_exempt  # Para pruebas; en producción maneja CSRF de forma segura.
def actualizar_orden_manual(request):
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

            # Enviar mensaje vía WebSocket para notificar al Tablero (opcional)
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
            return JsonResponse({'status': 'ok', 'mensaje': 'Orden actualizada'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'error': 'Método no permitido'}, status=405)

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # Para pruebas; en producción asegúrate de manejar CSRF de forma segura
def agregar_servicio_orden(request):
    """
    Vista que agrega un servicio a una orden específica.
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
            from .models import Orden, Servicio, CatalogoServicio
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
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
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

def orden_parcial(request, order_id):
    order = get_object_or_404(Orden, id=order_id)
    estado_choices = Servicio._meta.get_field('estado').choices
    return render(request, 'servicios/orden_parcial.html', {'order': order, 'service_state_choices': estado_choices})

def ordenes_terminadas(request):
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

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import send_whatsapp_message

@csrf_exempt
def marcar_entregada(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order_id = data.get("order_id")
            order = Orden.objects.filter(id=order_id).first()
            if not order:
                return JsonResponse({"status": "error", "error": "Orden no encontrada"}, status=404)
            # Actualiza el estado de la orden a "ENTREGADO"
            order.estado_general = "ENTREGADO"
            order.save()

             # Envía el mensaje de WhatsApp
            if order.telefono:
                # Puedes personalizar el mensaje a enviar
                send_whatsapp_message(order.telefono, "Su orden ha sido completada. Gracias por confiar en nosotros.")
            
            # Aquí puedes enviar también un mensaje vía WebSocket si deseas que se actualice en otras vistas
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "ordenes_updates",
                {
                    "type": "orden_entregada",  # Puedes definir este tipo para notificar
                    "order_id": order.id,
                }
            )
            return JsonResponse({"status": "ok", "mensaje": "Orden marcada como entregada"})
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=400)
    return JsonResponse({"status": "error", "error": "Método no permitido"}, status=405)

def historial_ordenes(request):
    # Filtra las órdenes cuyo estado general es "ENTREGADO"
    orders = Orden.objects.filter(estado_general='ENTREGADO').order_by('-fecha_programada')
    context = {'orders': orders}
    return render(request, 'servicios/historial_ordenes.html', context)

def ordenes_anuladas(request):
    # Filtrar las órdenes cuyo estado general es "ANULADA"
    orders = Orden.objects.filter(estado_general='ANULADA').order_by('fecha_ingreso')
    context = {'orders': orders}
    return render(request, 'servicios/ordenes_anuladas.html', context)

def config_modelos(request):
    return HttpResponse("<h1>Configuración: Modelos de Motor - En construcción</h1>")

def config_clientes(request):
    return HttpResponse("<h1>Configuración: Clientes - En construcción</h1>")

def config_rutas(request):
    return HttpResponse("<h1>Configuración: Rutas - En construcción</h1>")

def home(request):
    return render(request, 'servicios/partials/home_content.html')

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime

@csrf_exempt
def sincronizar_ordenes(request):
    """
    Vista para sincronizar las órdenes capturadas en ruta.
    Se espera recibir un JSON con una lista de órdenes offline.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ordenes_capturadas = data.get("ordenes", [])
            resultados = []
            for orden_data in ordenes_capturadas:
                # Crear la orden sin número, fecha_programada, ni estado general (se asignarán al aceptar)
                orden = Orden.objects.create(
                    cliente=orden_data.get("cliente"),
                    telefono=orden_data.get("telefono"),
                    modelo_motor=orden_data.get("modelo_motor"),
                    ruta=orden_data.get("ruta"),
                    notificacion=orden_data.get("notificacion", ""),
                    fecha_ingreso=datetime.now()
                )
                # Aquí puedes procesar los datos de inventario y servicios si vienen en orden_data
                resultados.append({"orden_id": orden.id})
            return JsonResponse({"status": "ok", "resultados": resultados})
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=400)
    return JsonResponse({"status": "error", "error": "Método no permitido"}, status=405)

def config_clientes(request):
    cliente_editar = None
    
    # Verificar si hay un ID para editar en los parámetros GET
    editar_id = request.GET.get('editar_id')
    if editar_id:
        cliente_editar = get_object_or_404(Cliente, id=editar_id)
        
    if request.method == 'POST':
        # Verificar si estamos editando un cliente existente
        cliente_id = request.POST.get('cliente_id')
        if cliente_id:
            # Editar cliente existente
            cliente = get_object_or_404(Cliente, id=cliente_id)
            form = ClienteForm(request.POST, instance=cliente)
        else:
            # Crear nuevo cliente
            form = ClienteForm(request.POST)
            
        if form.is_valid():
            form.save()
            return redirect('config_clientes')
    else:
        # Si hay un cliente para editar, inicializar el formulario con sus datos
        if cliente_editar:
            form = ClienteForm(instance=cliente_editar)
        else:
            form = ClienteForm()
            
    clientes = Cliente.objects.all()
    context = {
        'form': form,
        'clientes': clientes,
        'cliente_editar': cliente_editar,
    }
    return render(request, 'servicios/config_clientes.html', context)

def config_modelos(request):
    motor_editar = None
    
    # Verificar si hay un ID para editar en los parámetros GET
    editar_id = request.GET.get('editar_id')
    if editar_id:
        motor_editar = get_object_or_404(Motor, id=editar_id)
        
    if request.method == 'POST':
        # Verificar si estamos editando un motor existente
        motor_id = request.POST.get('motor_id')
        if motor_id:
            # Editar motor existente
            motor = get_object_or_404(Motor, id=motor_id)
            form = MotorForm(request.POST, instance=motor)
        else:
            # Crear nuevo motor
            form = MotorForm(request.POST)
            
        if form.is_valid():
            form.save()
            return redirect('config_modelos')
    else:
        # Si hay un motor para editar, inicializar el formulario con sus datos
        if motor_editar:
            form = MotorForm(instance=motor_editar)
        else:
            form = MotorForm()
            
    motores = Motor.objects.all()
    context = {
        'form': form,
        'motores': motores,
        'motor_editar': motor_editar,
    }
    return render(request, 'servicios/config_modelos.html', context)
