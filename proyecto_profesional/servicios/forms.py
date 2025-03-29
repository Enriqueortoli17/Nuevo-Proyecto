from django import forms
from .models import Orden, Servicio, CatalogoServicio, InventarioItem, Cliente, Motor

class OrdenForm(forms.ModelForm):
    # Campo para seleccionar servicios del catálogo
    servicios = forms.ModelMultipleChoiceField(
        queryset=CatalogoServicio.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Servicios a aplicar"
    )
    # Campo para seleccionar ítems de inventario mediante checkboxes
    inventario_items = forms.ModelMultipleChoiceField(
        queryset=InventarioItem.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Inventario"
    )
    # Campo para seleccionar un cliente ya registrado
    cliente_existente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        required=False,
        label="Cliente Registrado"
    )
    # Campos para registrar un nuevo cliente (en caso de que no exista)
    nuevo_cliente_nombre = forms.CharField(max_length=100, required=False, label="Nuevo Cliente (Nombre)")
    nuevo_cliente_telefono = forms.CharField(max_length=20, required=False, label="Nuevo Cliente (Teléfono)")
    nuevo_cliente_ruta = forms.CharField(max_length=50, required=False, label="Nuevo Cliente (Ruta)")

    # Campo para seleccionar un motor ya registrado
    motor_existente = forms.ModelChoiceField(
        queryset=Motor.objects.all(),
        required=False,
        label="Motor Registrado"
    )
    # Campos para registrar un nuevo motor (en caso de que no exista)
    nuevo_motor_nombre = forms.CharField(max_length=100, required=False, label="Nuevo Motor (Nombre)")
    nuevo_motor_especificaciones = forms.CharField(widget=forms.Textarea, required=False, label="Nuevo Motor (Especificaciones)")

    class Meta:
        model = Orden
        fields = [
            'cliente',
            'telefono',
            'modelo_motor',
            'ruta',
            'inventario_items',
            'notificacion',
            # No incluimos estado_general porque se actualiza automáticamente.
            'servicios'  # Campo para seleccionar servicios.
        ]
        widgets = {
            'numero_orden': forms.TextInput(attrs={'class': 'form-control'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo_motor': forms.TextInput(attrs={'class': 'form-control'}),
            'ruta': forms.TextInput(attrs={'class': 'form-control'}),
            'notificacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super(OrdenForm, self).__init__(*args, **kwargs)
        # Aquí puedes inicializar valores o modificar atributos de los campos si lo deseas.

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['estado', 'observaciones', 'cantidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

from django import forms
from .models import InventarioItem, CatalogoServicio

class InventarioSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(InventarioSelectionForm, self).__init__(*args, **kwargs)
        self.item_list = []
        items = InventarioItem.objects.all()
        for item in items:
            checkbox_name = f'item_{item.id}_selected'
            quantity_name = f'item_{item.id}_cantidad'
            comment_name = f'item_{item.id}_comentario'
            self.fields[checkbox_name] = forms.BooleanField(required=False, label=item.nombre)
            self.fields[quantity_name] = forms.IntegerField(required=False, min_value=1, initial=1, label="Cantidad")
            self.fields[comment_name] = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows':2}), label="Comentario")
            self.item_list.append((checkbox_name, quantity_name, comment_name, item.nombre))
        # Agregar bloque para inventario custom
        custom_checkbox = "item_custom_selected"
        custom_name = "item_custom_nombre"
        custom_quantity = "item_custom_cantidad"
        custom_comment = "item_custom_comentario"
        self.fields[custom_checkbox] = forms.BooleanField(required=False, label="Otro ítem (no registrado)")
        self.fields[custom_name] = forms.CharField(required=False, label="Nombre del ítem")
        self.fields[custom_quantity] = forms.IntegerField(required=False, min_value=1, initial=1, label="Cantidad")
        self.fields[custom_comment] = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows':2}), label="Comentario")
        self.item_list.append((custom_checkbox, custom_name, custom_quantity, custom_comment, "Otro ítem"))

from django import forms
from .models import CatalogoServicio

class ServicioSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ServicioSelectionForm, self).__init__(*args, **kwargs)
        self.serv_list = []
        for servicio in CatalogoServicio.objects.all():
            selected_field = f'serv_{servicio.id}_selected'
            quantity_required_field = f'serv_{servicio.id}_quantity_required'
            quantity_field = f'serv_{servicio.id}_quantity'
            self.fields[selected_field] = forms.BooleanField(required=False, label=servicio.nombre)
            self.fields[quantity_required_field] = forms.BooleanField(required=False, initial=False)
            self.fields[quantity_field] = forms.CharField(required=False, initial="", label='Cantidad')
            self.serv_list.append((selected_field, quantity_required_field, quantity_field, servicio.nombre))
        # Agregar bloque para servicio custom:
        custom_selected = "serv_custom_selected"
        custom_name = "serv_custom_nombre"
        custom_quantity_required = "serv_custom_quantity_required"
        custom_quantity = "serv_custom_quantity"
        self.fields[custom_selected] = forms.BooleanField(required=False, label="Otro servicio (no registrado)")
        self.fields[custom_name] = forms.CharField(required=False, label="Nombre del servicio")
        self.fields[custom_quantity_required] = forms.BooleanField(required=False, initial=False)
        self.fields[custom_quantity] = forms.CharField(required=False, initial="", label="Cantidad")
        self.serv_list.append((custom_selected, custom_name, custom_quantity_required, custom_quantity, "Otro servicio"))

from .models import Cliente, Motor

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono', 'ruta']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'ruta': forms.TextInput(attrs={'class': 'form-control'}),
        }

class MotorForm(forms.ModelForm):
    class Meta:
        model = Motor
        fields = [
            'nombre',
            'diametro_cilindro',
            'carrera',
            'diametro_piston',
            # Válvulas de Escape:
            'diametro_cabeza_escape',
            'distancia_valvula_escape',
            'diametro_vastago_escape',
            'angulo_asiento_escape',
            # Válvulas de Admisión:
            'diametro_cabeza_admision',
            'distancia_valvula_admision',
            'diametro_vastago_admision',
            'angulo_asiento_admision',
            # Bancada:
            'diametro_alojamiento',
            # Cigüeñal:
            'diametro_munon_biela',
            'diametro_munon_bancada',
            # Cabezas:
            'altura_cabeza',
        ]

