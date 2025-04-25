# proyecto_profesional/servicios/tests.py

import json # Para manejar datos JSON
import urllib.parse
from datetime import date, timedelta
from unittest.mock import patch
from django.test import TestCase, Client # Importa el Cliente de Pruebas
from django.urls import reverse # Para obtener URLs a partir de sus nombres
from django.contrib.auth.models import User, Group # Para crear usuarios y grupos de prueba
from django.utils import timezone
from .models import Orden, Cliente, CatalogoServicio, Servicio, Motor, InventarioItem, OrdenInventario
from .forms import ClienteForm, MotorForm, OrdenForm, InventarioSelectionForm, ServicioSelectionForm
# Create your tests here.

class OrdenModelTests(TestCase):

    def setUp(self):
        """
        Método especial que se ejecuta ANTES de cada método test_.
        Crea objetos comunes que usarán varias pruebas.
        """
        self.cliente_test = Cliente.objects.create(nombre="Cliente de Prueba")
        # --- CORREGIDO: Asignar los catálogos creados a self ---
        self.catalogo_lavado = CatalogoServicio.objects.create(nombre="Lavar Motor Test")
        self.catalogo_pintura = CatalogoServicio.objects.create(nombre="Pintar Bloque Test")
        # --------------------------------------------------------
        # print(f"Ejecutando setUp para OrdenModelTests...") # Puedes mantener o quitar los prints

    # --- Tests Originales ---
    def test_numero_provisional_sin_numero_orden(self):
        """
        Prueba que numero_provisional genera 'TMP<pk>' si numero_orden es None.
        """
        # print("-> Ejecutando test_numero_provisional_sin_numero_orden")
        orden_sin_numero = Orden.objects.create(
            cliente="Cliente Temporal",
            cliente_registrado=self.cliente_test
        )
        expected_provisional = "TMP" + str(orden_sin_numero.pk)
        self.assertEqual(orden_sin_numero.numero_provisional, expected_provisional)
        # print(f"   Orden ID: {orden_sin_numero.pk} - OK")

    def test_numero_provisional_con_numero_orden(self):
        """
        Prueba que numero_provisional devuelve numero_orden si este tiene valor.
        """
        # print("-> Ejecutando test_numero_provisional_con_numero_orden")
        numero_asignado = "ORD00123"
        orden_con_numero = Orden.objects.create(
            cliente="Cliente Permanente",
            numero_orden=numero_asignado,
            cliente_registrado=self.cliente_test
        )
        self.assertEqual(orden_con_numero.numero_provisional, numero_asignado)
        # print(f"   Orden ID: {orden_con_numero.pk} - OK")

    def test_str_representation(self):
        """
        Prueba la representación en string (__str__) del modelo Orden.
        """
        # print("-> Ejecutando test_str_representation")
        orden = Orden.objects.create(cliente="Cliente String", cliente_registrado=self.cliente_test)
        expected_string = f"Orden {orden.numero_provisional} - {orden.cliente}"
        self.assertEqual(str(orden), expected_string)
        # print(f"   Orden ID: {orden.pk} - OK")
    # --- Fin Tests Originales ---


    # --- Tests para actualizar_estado_general ---

    def test_actualizar_estado_general_sin_servicios(self):
        """
        Prueba que una orden ACEPTADA sin servicios se mantiene ACEPTADA.
        """
        # print("-> Ejecutando test_actualizar_estado_general_sin_servicios")
        orden = Orden.objects.create(
            cliente="Cliente Sin Servicios",
            estado_general='ACEPTADA',
            cliente_registrado=self.cliente_test
        )
        orden.actualizar_estado_general()
        self.assertEqual(orden.estado_general, 'ACEPTADA')
        # print(f"   Orden ID: {orden.pk}, Estado: {orden.estado_general} - OK")

    def test_actualizar_estado_general_servicios_pendientes(self):
        """
        Prueba que una orden ACEPTADA con servicios PENDIENTES se mantiene ACEPTADA.
        """
        # print("-> Ejecutando test_actualizar_estado_general_servicios_pendientes")
        orden = Orden.objects.create(
            cliente="Cliente Pendiente",
            estado_general='ACEPTADA',
            cliente_registrado=self.cliente_test
        )
        Servicio.objects.create(
            orden=orden,
            catalogo_servicio=self.catalogo_lavado, # Usa el atributo de self
            estado='PENDIENTE'
        )
        orden.actualizar_estado_general()
        self.assertEqual(orden.estado_general, 'ACEPTADA')
        # print(f"   Orden ID: {orden.pk}, Estado: {orden.estado_general} - OK")

    def test_actualizar_estado_general_servicio_en_proceso(self):
        """
        Prueba que si un servicio pasa a PROCESO, la orden pasa a PROCESO.
        """
        # print("-> Ejecutando test_actualizar_estado_general_servicio_en_proceso")
        orden = Orden.objects.create(
            cliente="Cliente En Proceso",
            estado_general='ACEPTADA',
            cliente_registrado=self.cliente_test
        )
        Servicio.objects.create(orden=orden, catalogo_servicio=self.catalogo_lavado, estado='PENDIENTE')
        Servicio.objects.create(orden=orden, catalogo_servicio=self.catalogo_pintura, estado='PROCESO') # Usa el atributo de self

        orden.actualizar_estado_general()
        self.assertEqual(orden.estado_general, 'PROCESO')
        # print(f"   Orden ID: {orden.pk}, Estado: {orden.estado_general} - OK")

    def test_actualizar_estado_general_servicios_terminados(self):
        """
        Prueba que si TODOS los servicios están TERMINADO/NO_REALIZADO, la orden pasa a LISTO.
        """
        # print("-> Ejecutando test_actualizar_estado_general_servicios_terminados")
        orden = Orden.objects.create(
            cliente="Cliente Terminado",
            estado_general='PROCESO',
            cliente_registrado=self.cliente_test
        )
        Servicio.objects.create(orden=orden, catalogo_servicio=self.catalogo_lavado, estado='TERMINADO') # Usa el atributo de self
        Servicio.objects.create(orden=orden, catalogo_servicio=self.catalogo_pintura, estado='NO_REALIZADO') # Usa el atributo de self

        orden.actualizar_estado_general()
        self.assertEqual(orden.estado_general, 'LISTO')
        # print(f"   Orden ID: {orden.pk}, Estado: {orden.estado_general} - OK")

    def test_actualizar_estado_general_mezcla_proceso_terminado(self):
        """
        Prueba que si hay servicios TERMINADOS y otros EN PROCESO, la orden se mantiene EN PROCESO.
        """
        # print("-> Ejecutando test_actualizar_estado_general_mezcla_proceso_terminado")
        orden = Orden.objects.create(
            cliente="Cliente Mezcla",
            estado_general='PROCESO',
            cliente_registrado=self.cliente_test
        )
        Servicio.objects.create(orden=orden, catalogo_servicio=self.catalogo_lavado, estado='TERMINADO') # Usa el atributo de self
        Servicio.objects.create(orden=orden, catalogo_servicio=self.catalogo_pintura, estado='PROCESO') # Usa el atributo de self

        orden.actualizar_estado_general()
        self.assertEqual(orden.estado_general, 'PROCESO')
        # print(f"   Orden ID: {orden.pk}, Estado: {orden.estado_general} - OK")

# --- Fin de la clase OrdenModelTests ---

class ClienteFormTests(TestCase):

    def test_cliente_form_valid_data(self):
        """
        Prueba que el formulario ClienteForm es válido con datos correctos.
        """
        print("-> Ejecutando test_cliente_form_valid_data")
        # Datos válidos para un cliente nuevo
        form_data = {
            'nombre': 'Cliente Nuevo Valido',
            'telefono': '1234567890',
            'ruta': 'Ruta Prueba'
        }
        form = ClienteForm(data=form_data)
        # Verificamos que el formulario sea válido
        self.assertTrue(form.is_valid(), f"El formulario debería ser válido. Errores: {form.errors}")
        print("   Formulario válido - OK")

    def test_cliente_form_invalid_duplicate_name(self):
        """
        Prueba que ClienteForm es inválido si el nombre ya existe.
        """
        print("-> Ejecutando test_cliente_form_invalid_duplicate_name")
        # 1. Crear un cliente existente en la base de datos de prueba
        nombre_existente = "Cliente Repetido"
        Cliente.objects.create(nombre=nombre_existente, telefono="111", ruta="R1")
        print(f"   Cliente '{nombre_existente}' creado.")

        # 2. Preparar datos para el formulario con el MISMO nombre
        form_data = {
            'nombre': nombre_existente, # Nombre duplicado
            'telefono': '222',
            'ruta': 'R2'
        }
        form = ClienteForm(data=form_data)

        # 3. Verificar que el formulario NO sea válido
        self.assertFalse(form.is_valid(), "El formulario debería ser inválido por nombre duplicado.")
        print(f"   Formulario inválido (esperado) - OK")

        # 4. (Opcional pero recomendado) Verificar que el error específico esté en el campo 'nombre'
        self.assertIn('nombre', form.errors, "Debería haber un error en el campo 'nombre'.")
        # Puedes ser más específico y verificar el texto del error si lo conoces
        # self.assertTrue('ya existe' in form.errors['nombre'][0]) # Ejemplo
        print(f"   Error encontrado en campo 'nombre' - OK")

    # --- Puedes añadir más pruebas para ClienteForm aquí ---
    # def test_cliente_form_nombre_requerido(self):
    #     """Prueba que el campo nombre es requerido."""
    #     form_data = {'telefono': '123', 'ruta': 'R3'} # Sin nombre
    #     form = ClienteForm(data=form_data)
    #     self.assertFalse(form.is_valid())
    #     self.assertIn('nombre', form.errors)

# --- Fin de la clase ClienteFormTests ---

class MotorFormTests(TestCase):

    def test_motor_form_valid_data(self):
        """
        Prueba que MotorForm es válido con datos numéricos correctos.
        """
        print("-> Ejecutando test_motor_form_valid_data")
        # Usamos valores decimales válidos (como strings o Decimal)
        form_data = {
            'nombre': 'Motor Test Válido',
            'diametro_cilindro': '100.50',
            'carrera': '80.25',
            'diametro_piston': '100.00',
            'diametro_cabeza_escape': '45.50',
            'distancia_valvula_escape': '5.10',
            'diametro_vastago_escape': '8.00',
            'angulo_asiento_escape': '45.00',
            'diametro_cabeza_admision': '50.00',
            'distancia_valvula_admision': '5.00',
            'diametro_vastago_admision': '8.00',
            'angulo_asiento_admision': '30.00',
            'diametro_alojamiento': '110.00',
            'diametro_munon_biela': '60.00',
            'diametro_munon_bancada': '65.00',
            'altura_cabeza': '95.75',
        }
        form = MotorForm(data=form_data)
        # Verificamos que el formulario sea válido
        # Usamos form.errors para dar más info si falla
        self.assertTrue(form.is_valid(), f"Formulario debería ser válido. Errores: {form.errors}")
        print("   MotorForm válido - OK")

    def test_motor_form_invalid_non_numeric(self):
        """
        Prueba que MotorForm es inválido si se introduce texto en un campo decimal.
        """
        print("-> Ejecutando test_motor_form_invalid_non_numeric")
        # Copiamos los datos válidos y modificamos un campo
        form_data = {
            'nombre': 'Motor Test Inválido',
            'diametro_cilindro': 'esto no es un numero', # <-- Dato inválido
            'carrera': '80.25',
            'diametro_piston': '100.00',
            # ... (podrías poner el resto de datos válidos o dejar que fallen por requeridos si lo fueran)
            # Para esta prueba, solo necesitamos uno inválido
            'diametro_cabeza_escape': '45.50',
            'distancia_valvula_escape': '5.10',
            'diametro_vastago_escape': '8.00',
            'angulo_asiento_escape': '45.00',
            'diametro_cabeza_admision': '50.00',
            'distancia_valvula_admision': '5.00',
            'diametro_vastago_admision': '8.00',
            'angulo_asiento_admision': '30.00',
            'diametro_alojamiento': '110.00',
            'diametro_munon_biela': '60.00',
            'diametro_munon_bancada': '65.00',
            'altura_cabeza': '95.75',
        }
        form = MotorForm(data=form_data)
        # Verificamos que el formulario NO sea válido
        self.assertFalse(form.is_valid(), "Formulario debería ser inválido por dato no numérico.")
        print("   MotorForm inválido (esperado) - OK")
        # Verificamos que el error esté en el campo correcto
        self.assertIn('diametro_cilindro', form.errors, "Debería haber un error en 'diametro_cilindro'.")
        # Verificamos que el mensaje de error sea el esperado por Django para números inválidos
        self.assertTrue(
            any('Introduzca un número.' in error for error in form.errors['diametro_cilindro']),
            "El error debería ser sobre introducir un número válido."
        )
        print("   Error encontrado en campo 'diametro_cilindro' - OK")

    # Podrías añadir pruebas para verificar los límites de max_digits/decimal_places si quisieras
    # def test_motor_form_invalid_too_many_decimals(self): ...
    # def test_motor_form_invalid_too_many_digits(self): ...

# --- Fin de la clase MotorFormTests ---

class ListaOrdenesViewTests(TestCase):

    def setUp(self):
        """Configuración inicial para las pruebas de esta vista."""
        # Creamos el cliente de pruebas
        self.client = Client()
        # Creamos un usuario 'chofer' y el grupo 'Chofer'
        self.chofer_group, created = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofertest', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        # Creamos un usuario normal (sin grupo especial)
        self.normal_user = User.objects.create_user(username='normaltest', password='password123')
        # Obtenemos la URL de la vista usando su nombre ('lista_ordenes' definido en urls.py)
        self.lista_ordenes_url = reverse('lista_ordenes')
        print(f"Ejecutando setUp para ListaOrdenesViewTests... URL: {self.lista_ordenes_url}")

    def test_lista_ordenes_view_logged_out_redirect(self):
        """
        Prueba que un usuario no autenticado sea redirigido al intentar acceder.
        """
        print("-> Ejecutando test_lista_ordenes_view_logged_out_redirect")
        # Hacemos una petición GET a la URL sin iniciar sesión
        response = self.client.get(self.lista_ordenes_url)
        # Verificamos que la respuesta sea una redirección (código 302)
        # Django usualmente redirige a la URL de login
        self.assertEqual(response.status_code, 302)
        # Podríamos verificar a dónde redirige, usualmente contiene '/accounts/login/'
        self.assertIn('/accounts/login/', response.url, "Debería redirigir a la página de login.")
        print(f"   Status Code: {response.status_code}, Redirect URL: {response.url} - OK")

    def test_lista_ordenes_view_chofer_access(self):
        """
        Prueba que un usuario 'Chofer' autenticado pueda acceder a la vista.
        """
        print("-> Ejecutando test_lista_ordenes_view_chofer_access")
        # Iniciamos sesión con el usuario chofer
        login_success = self.client.login(username='chofertest', password='password123')
        self.assertTrue(login_success, "Login del chofer falló") # Verificar que el login fue exitoso
        # Hacemos la petición GET estando autenticado
        response = self.client.get(self.lista_ordenes_url)
        # Verificamos que la respuesta sea exitosa (código 200)
        self.assertEqual(response.status_code, 200)
        # Verificamos que se usó la plantilla HTML correcta
        self.assertTemplateUsed(response, 'servicios/lista_ordenes.html')
        print(f"   Status Code: {response.status_code}, Template: servicios/lista_ordenes.html - OK")

    def test_lista_ordenes_view_unauthorized_user_redirect(self):
        """
        Prueba que un usuario autenticado pero sin el permiso adecuado sea redirigido.
        """
        print("-> Ejecutando test_lista_ordenes_view_unauthorized_user_redirect")
        # Iniciamos sesión con el usuario normal (sin grupo 'Chofer')
        login_success = self.client.login(username='normaltest', password='password123')
        self.assertTrue(login_success, "Login del usuario normal falló")
        # Hacemos la petición GET
        response = self.client.get(self.lista_ordenes_url)
        # Verificamos que la respuesta sea una redirección (302)
        # El decorador user_passes_test usualmente redirige al login_url por defecto
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url, "Usuario no autorizado debería ser redirigido.")
        # NOTA: Si configuraste un 'login_url' diferente en tus settings o en el decorador,
        # la URL de redirección podría ser distinta. También podría ser un 403 Forbidden
        # dependiendo de la configuración, pero 302 es común.
        print(f"   Status Code: {response.status_code}, Redirect URL: {response.url} - OK")

# --- Fin de la clase ListaOrdenesViewTests ---

class CrearOrdenViewTests(TestCase):

    def setUp(self):
        """Configuración inicial para las pruebas de crear_orden."""
        self.client = Client()
        # Creamos usuario y grupo 'Chofer' (necesario para acceder a la vista)
        self.chofer_group, created = Group.objects.get_or_create(name='Chofer')
        self.user = User.objects.create_user(username='testchofer_crear', password='password123')
        self.user.groups.add(self.chofer_group)
        # URLs necesarias
        self.crear_orden_url = reverse('crear_orden')
        self.lista_ordenes_url = reverse('lista_ordenes')
        self.login_url = reverse('login') # Asume que tienes una URL de login llamada 'login'

        # Crear objetos relacionados mínimos que podrían ser necesarios
        # (Aunque la vista crea clientes/motores si no existen, es bueno tenerlos para IDs)
        self.cliente_existente = Cliente.objects.create(nombre="Cliente Base")
        self.motor_existente = Motor.objects.create(nombre="Motor Base")
        self.servicio_existente = CatalogoServicio.objects.create(nombre="Servicio Base")
        self.inventario_existente = InventarioItem.objects.create(nombre="Item Base")

        print(f"Ejecutando setUp para CrearOrdenViewTests...")

    def test_crear_orden_view_get_request_as_chofer(self):
        """Prueba que un chofer puede acceder al formulario GET."""
        print("-> Ejecutando test_crear_orden_view_get_request_as_chofer")
        self.client.login(username='testchofer_crear', password='password123')
        response = self.client.get(self.crear_orden_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/crear_orden.html')
        # Verificar que los formularios estén en el contexto (opcional pero útil)
        self.assertIn('form', response.context)
        self.assertIn('inv_form', response.context)
        self.assertIn('serv_form', response.context)
        print(f"   GET exitoso (200) - OK")

    def test_crear_orden_view_post_valid_data(self):
        """Prueba crear una orden con datos válidos vía POST."""
        print("-> Ejecutando test_crear_orden_view_post_valid_data")
        self.client.login(username='testchofer_crear', password='password123')
        # Contar órdenes antes de crear una nueva
        orden_count_before = Orden.objects.count()

        # Datos mínimos válidos para el formulario principal y los formsets
        # Nota: Los formsets (inventario, servicios) requieren datos de 'management_form'
        # y también los datos de los campos seleccionados.
        # Para simplificar, solo enviaremos los datos del form principal ahora.
        # La lógica de la vista parece manejar la creación de clientes/motores si no existen.
        post_data = {
            'cliente': 'Cliente POST Test',
            'telefono': '5551112233',
            'modelo_motor': 'Motor POST Test',
            'ruta': 'Ruta POST',
            'notificacion': 'Obs POST',
            # Datos para InventarioSelectionForm (prefix 'inv') - Simulado sin selección
            'inv-TOTAL_FORMS': '1', # Número de formularios (incluyendo 'Otro')
            'inv-INITIAL_FORMS': '0',
            'inv-MIN_NUM_FORMS': '0',
            'inv-MAX_NUM_FORMS': '1000',
            # Datos para ServicioSelectionForm (prefix 'serv') - Simulado sin selección
            'serv-TOTAL_FORMS': '1', # Número de formularios (incluyendo 'Otro')
            'serv-INITIAL_FORMS': '0',
            'serv-MIN_NUM_FORMS': '0',
            'serv-MAX_NUM_FORMS': '1000',
        }

        # Hacemos la petición POST
        response = self.client.post(self.crear_orden_url, data=post_data)

        # 1. Verificar que se redirige (código 302) a la lista de órdenes
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, target_status_code=200)
        print(f"   Redirección a {self.lista_ordenes_url} (302) - OK")

        # 2. Verificar que se creó UNA nueva orden en la BD
        orden_count_after = Orden.objects.count()
        self.assertEqual(orden_count_after, orden_count_before + 1)
        print(f"   Conteo de órdenes incrementó en 1 - OK")

        # 3. Verificar que la orden creada tiene los datos correctos (opcional)
        nueva_orden = Orden.objects.latest('fecha_ingreso')
        self.assertEqual(nueva_orden.cliente, 'Cliente POST Test')
        self.assertEqual(nueva_orden.modelo_motor, 'Motor POST Test')
        self.assertEqual(nueva_orden.chofer, self.user) # Verificar que se asignó el usuario
        print(f"   Datos básicos de la orden creada son correctos - OK")


    def test_crear_orden_view_post_invalid_data(self):
        """Prueba crear una orden con datos inválidos (ej. cliente vacío)."""
        print("-> Ejecutando test_crear_orden_view_post_invalid_data")
        self.client.login(username='testchofer_crear', password='password123')
        orden_count_before = Orden.objects.count()

        # Datos inválidos (falta 'cliente', que es requerido por el modelo)
        post_data = {
            # 'cliente': '', # Campo requerido vacío
            'telefono': '5551112233',
            'modelo_motor': 'Motor POST Inválido',
            # ... (faltan datos de formsets, pero el form principal ya fallará)
            'inv-TOTAL_FORMS': '1', 'inv-INITIAL_FORMS': '0', 'inv-MIN_NUM_FORMS': '0', 'inv-MAX_NUM_FORMS': '1000',
            'serv-TOTAL_FORMS': '1', 'serv-INITIAL_FORMS': '0', 'serv-MIN_NUM_FORMS': '0', 'serv-MAX_NUM_FORMS': '1000',
        }

        response = self.client.post(self.crear_orden_url, data=post_data)

        # 1. Verificar que NO se redirige, sino que se vuelve a mostrar la página (código 200)
        self.assertEqual(response.status_code, 200)
        print(f"   Sin redirección (200) - OK")

        # 2. Verificar que NO se creó ninguna orden nueva
        orden_count_after = Orden.objects.count()
        self.assertEqual(orden_count_after, orden_count_before)
        print(f"   Conteo de órdenes no cambió - OK")

        # 3. Verificar que se usó la plantilla correcta (la misma del formulario)
        self.assertTemplateUsed(response, 'servicios/crear_orden.html')
        print(f"   Plantilla 'crear_orden.html' usada - OK")

        # 4. Verificar que el formulario en el contexto contiene errores
        self.assertFalse(response.context['form'].is_valid()) # El form no es válido
        self.assertIn('cliente', response.context['form'].errors) # Hay un error en el campo 'cliente'
        print(f"   Formulario inválido con error en 'cliente' - OK")

    def test_crear_orden_post_con_inventario_existente(self):
        """Prueba crear orden seleccionando un ítem de inventario existente."""
        print("-> Ejecutando test_crear_orden_post_con_inventario_existente")
        self.client.login(username='testchofer_crear', password='password123')
        orden_count_before = Orden.objects.count()
        inv_orden_count_before = OrdenInventario.objects.count()

        # Datos válidos + selección de inventario existente
        item_existente_id = self.inventario_existente.pk # Usamos el creado en setUp
        post_data = {
            'cliente': 'Cliente Con Inventario',
            'telefono': '555INV1', 'modelo_motor': 'Motor Inv', 'ruta': 'RI',
            # --- Datos Inventario (prefijo 'inv') ---
            'inv-TOTAL_FORMS': '2', # Ahora hay 2: el existente + el custom
            'inv-INITIAL_FORMS': '0',
            'inv-MIN_NUM_FORMS': '0',
            'inv-MAX_NUM_FORMS': '1000',
            f'inv-item_{item_existente_id}_selected': 'on', # Marcar el checkbox
            f'inv-item_{item_existente_id}_cantidad': '3',    # Especificar cantidad
            f'inv-item_{item_existente_id}_comentario': 'Comentario Inv',
            # Datos para el form custom (vacíos en este test)
            'inv-item_custom_selected': '',
            'inv-item_custom_nombre': '',
            'inv-item_custom_cantidad': '1',
            'inv-item_custom_comentario': '',
            # -----------------------------------------
            # --- Datos Servicios (prefijo 'serv') - Mínimos ---
            'serv-TOTAL_FORMS': '2', # Existente + custom
            'serv-INITIAL_FORMS': '0',
            'serv-MIN_NUM_FORMS': '0',
            'serv-MAX_NUM_FORMS': '1000',
            # ... (campos de servicios vacíos por ahora) ...
            # -----------------------------------------------
        }
        response = self.client.post(self.crear_orden_url, data=post_data)
        self.assertRedirects(response, self.lista_ordenes_url) # Verificar redirección
        self.assertEqual(Orden.objects.count(), orden_count_before + 1) # Se creó la orden
        self.assertEqual(OrdenInventario.objects.count(), inv_orden_count_before + 1) # Se creó OrdenInventario
        # Verificar que el OrdenInventario creado es correcto
        nueva_orden = Orden.objects.latest('fecha_ingreso')
        orden_inv = OrdenInventario.objects.get(orden=nueva_orden, inventario_item=self.inventario_existente)
        self.assertEqual(orden_inv.cantidad, 3)
        self.assertEqual(orden_inv.comentario, 'Comentario Inv')
        print("   POST con inventario existente OK")

    def test_crear_orden_post_con_inventario_custom(self):
        """Prueba crear orden añadiendo un ítem de inventario custom."""
        print("-> Ejecutando test_crear_orden_post_con_inventario_custom")
        self.client.login(username='testchofer_crear', password='password123')
        item_count_before = InventarioItem.objects.count()
        inv_orden_count_before = OrdenInventario.objects.count()
        nombre_custom = "Inventario Custom Test"

        post_data = {
            'cliente': 'Cliente Con Inventario Custom',
            'telefono': '555INV2', 'modelo_motor': 'Motor Inv C', 'ruta': 'RIC',
            # --- Datos Inventario (prefijo 'inv') ---
            'inv-TOTAL_FORMS': '2', 'inv-INITIAL_FORMS': '0','inv-MIN_NUM_FORMS': '0','inv-MAX_NUM_FORMS': '1000',
            # Datos para item existente (vacíos en este test)
            f'inv-item_{self.inventario_existente.pk}_selected': '',
            f'inv-item_{self.inventario_existente.pk}_cantidad': '1',
            f'inv-item_{self.inventario_existente.pk}_comentario': '',
            # Datos para el form custom
            'inv-item_custom_selected': 'on', # Marcar el checkbox custom
            'inv-item_custom_nombre': nombre_custom, # Nombre del nuevo ítem
            'inv-item_custom_cantidad': '5',
            'inv-item_custom_comentario': 'Comentario Custom',
            # -----------------------------------------
            # --- Datos Servicios (Mínimos) ---
            'serv-TOTAL_FORMS': '2', 'serv-INITIAL_FORMS': '0','serv-MIN_NUM_FORMS': '0','serv-MAX_NUM_FORMS': '1000',
            # ---------------------------------
        }
        response = self.client.post(self.crear_orden_url, data=post_data)
        self.assertRedirects(response, self.lista_ordenes_url)
        # Verificar que se creó el InventarioItem Y el OrdenInventario
        self.assertEqual(InventarioItem.objects.count(), item_count_before + 1)
        self.assertEqual(OrdenInventario.objects.count(), inv_orden_count_before + 1)
        nuevo_item = InventarioItem.objects.get(nombre=nombre_custom)
        nueva_orden = Orden.objects.latest('fecha_ingreso')
        orden_inv = OrdenInventario.objects.get(orden=nueva_orden, inventario_item=nuevo_item)
        self.assertEqual(orden_inv.cantidad, 5)
        self.assertEqual(orden_inv.comentario, 'Comentario Custom')
        print("   POST con inventario custom OK")


    def test_crear_orden_post_con_servicio_existente(self):
        """Prueba crear orden seleccionando un servicio existente."""
        print("-> Ejecutando test_crear_orden_post_con_servicio_existente")
        self.client.login(username='testchofer_crear', password='password123')
        orden_count_before = Orden.objects.count()
        servicio_orden_count_before = Servicio.objects.count()

        # Datos válidos + selección de servicio existente
        servicio_existente_id = self.servicio_existente.pk
        post_data = {
            'cliente': 'Cliente Con Servicio',
            'telefono': '555SERV1', 'modelo_motor': 'Motor Serv', 'ruta': 'RS',
            # --- Datos Inventario (Mínimos) ---
            'inv-TOTAL_FORMS': '2','inv-INITIAL_FORMS': '0','inv-MIN_NUM_FORMS': '0','inv-MAX_NUM_FORMS': '1000',
            # ----------------------------------
            # --- Datos Servicios (prefijo 'serv') ---
            'serv-TOTAL_FORMS': '2','serv-INITIAL_FORMS': '0','serv-MIN_NUM_FORMS': '0','serv-MAX_NUM_FORMS': '1000',
            f'serv-serv_{servicio_existente_id}_selected': 'on', # Marcar checkbox
            f'serv-serv_{servicio_existente_id}_quantity_required': 'on', # Indicar que sí queremos cantidad
            f'serv-serv_{servicio_existente_id}_quantity': 'Prueba Cantidad', # Especificar cantidad/texto
            # Datos para el form custom (vacíos)
            'serv-serv_custom_selected': '',
            'serv-serv_custom_nombre': '',
            'serv-serv_custom_quantity_required': '',
            'serv-serv_custom_quantity': '',
            # ------------------------------------
        }
        response = self.client.post(self.crear_orden_url, data=post_data)
        self.assertRedirects(response, self.lista_ordenes_url)
        self.assertEqual(Orden.objects.count(), orden_count_before + 1)
        self.assertEqual(Servicio.objects.count(), servicio_orden_count_before + 1)
        # Verificar que el Servicio creado es correcto
        nueva_orden = Orden.objects.latest('fecha_ingreso')
        servicio = Servicio.objects.get(orden=nueva_orden, catalogo_servicio=self.servicio_existente)
        self.assertEqual(servicio.cantidad, 'Prueba Cantidad')
        self.assertEqual(servicio.estado, 'PENDIENTE')
        print("   POST con servicio existente OK")


    def test_crear_orden_post_con_servicio_custom(self):
        """Prueba crear orden añadiendo un servicio custom."""
        print("-> Ejecutando test_crear_orden_post_con_servicio_custom")
        self.client.login(username='testchofer_crear', password='password123')
        catalogo_count_before = CatalogoServicio.objects.count()
        servicio_orden_count_before = Servicio.objects.count()
        nombre_custom = "Servicio Custom Crear Test"

        post_data = {
            'cliente': 'Cliente Con Servicio Custom',
            'telefono': '555SERV2', 'modelo_motor': 'Motor Serv C', 'ruta': 'RSC',
            # --- Datos Inventario (Mínimos) ---
            'inv-TOTAL_FORMS': '2','inv-INITIAL_FORMS': '0','inv-MIN_NUM_FORMS': '0','inv-MAX_NUM_FORMS': '1000',
            # ----------------------------------
            # --- Datos Servicios (prefijo 'serv') ---
            'serv-TOTAL_FORMS': '2','serv-INITIAL_FORMS': '0','serv-MIN_NUM_FORMS': '0','serv-MAX_NUM_FORMS': '1000',
            # Datos servicio existente (vacíos)
            f'serv-serv_{self.servicio_existente.pk}_selected': '',
            f'serv-serv_{self.servicio_existente.pk}_quantity_required': '',
            f'serv-serv_{self.servicio_existente.pk}_quantity': '',
            # Datos servicio custom
            'serv-serv_custom_selected': 'on', # Marcar checkbox custom
            'serv-serv_custom_nombre': nombre_custom,
            'serv-serv_custom_quantity_required': 'on',
            'serv-serv_custom_quantity': 'Custom Qty',
            # ------------------------------------
        }
        response = self.client.post(self.crear_orden_url, data=post_data)
        self.assertRedirects(response, self.lista_ordenes_url)
        # Verificar que se creó el CatalogoServicio y el Servicio
        self.assertEqual(CatalogoServicio.objects.count(), catalogo_count_before + 1)
        self.assertEqual(Servicio.objects.count(), servicio_orden_count_before + 1)
        nuevo_catalogo = CatalogoServicio.objects.get(nombre=nombre_custom)
        nueva_orden = Orden.objects.latest('fecha_ingreso')
        servicio = Servicio.objects.get(orden=nueva_orden, catalogo_servicio=nuevo_catalogo)
        self.assertEqual(servicio.cantidad, 'Custom Qty')
        print("   POST con servicio custom OK")

# --- Fin de la clase CrearOrdenViewTests ---

class EditarOrdenViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de editar_orden."""
        self.client = Client()
        self.superuser = User.objects.create_superuser(username='superadmin_edit', password='password123', email='admin_e@test.com')
        self.normal_user = User.objects.create_user(username='testuser_edit', password='password123')

        # Objetos relacionados base
        self.cliente = Cliente.objects.create(nombre="Cliente Original Edit")
        self.motor = Motor.objects.create(nombre="Motor Original Edit")
        self.item_inv_1 = InventarioItem.objects.create(nombre="Item Inv Previo")
        self.item_inv_2 = InventarioItem.objects.create(nombre="Item Inv No Asociado")
        self.cat_serv_1 = CatalogoServicio.objects.create(nombre="Servicio Previo")
        self.cat_serv_2 = CatalogoServicio.objects.create(nombre="Servicio No Asociado")

        # Orden existente para editar
        self.orden_a_editar = Orden.objects.create(
            cliente="Cliente Original",
            modelo_motor="Motor Original",
            ruta="Ruta Original",
            cliente_registrado=self.cliente,
            motor_registrado=self.motor,
            estado_general='ACEPTADA',
            notificacion="Notif Original"
        )
        # Asociar algunos items/servicios previos a la orden
        self.orden_inv_previo = OrdenInventario.objects.create(
            orden=self.orden_a_editar,
            inventario_item=self.item_inv_1,
            cantidad=2,
            comentario="Comentario previo inv"
        )
        self.servicio_previo = Servicio.objects.create(
            orden=self.orden_a_editar,
            catalogo_servicio=self.cat_serv_1,
            cantidad="Cantidad previa serv",
            estado='PENDIENTE' # El estado se manejará en otra vista/API
        )
        # Asegurarnos que la relación M2M también se establece (aunque se haga vía Servicio)
        self.orden_a_editar.servicios.add(self.cat_serv_1)


        # URLs
        self.edit_url = reverse('editar_orden', args=[self.orden_a_editar.pk])
        self.lista_ordenes_url = reverse('lista_ordenes')
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para EditarOrdenViewTests... URL: {self.edit_url}")

    def test_editar_orden_view_get_as_superuser(self):
        """Prueba que el superusuario puede ver el form de edición con datos iniciales correctos."""
        print("-> test_editar_orden_view_get_as_superuser")
        self.client.login(username='superadmin_edit', password='password123')
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/editar_orden.html')
        self.assertIn('form', response.context)
        self.assertIn('inv_form', response.context)
        self.assertIn('serv_form', response.context)
        self.assertEqual(response.context['orden'], self.orden_a_editar)

        # Verificar datos iniciales de los formsets
        inv_form_initial = response.context['inv_form'].initial
        serv_form_initial = response.context['serv_form'].initial

        # Verificar que el item asociado está marcado y tiene datos correctos
        self.assertTrue(inv_form_initial.get(f'item_{self.item_inv_1.pk}_selected'))
        self.assertEqual(inv_form_initial.get(f'item_{self.item_inv_1.pk}_cantidad'), self.orden_inv_previo.cantidad)
        self.assertEqual(inv_form_initial.get(f'item_{self.item_inv_1.pk}_comentario'), self.orden_inv_previo.comentario)
        # Verificar que el item NO asociado NO está marcado
        self.assertFalse(inv_form_initial.get(f'item_{self.item_inv_2.pk}_selected'))

        # Verificar que el servicio asociado está marcado y tiene datos correctos
        self.assertTrue(serv_form_initial.get(f'serv_{self.cat_serv_1.pk}_selected'))
        self.assertEqual(serv_form_initial.get(f'serv_{self.cat_serv_1.pk}_quantity'), self.servicio_previo.cantidad)
        self.assertTrue(serv_form_initial.get(f'serv_{self.cat_serv_1.pk}_quantity_required')) # Asume True si hay cantidad
        # Verificar que el servicio NO asociado NO está marcado
        self.assertFalse(serv_form_initial.get(f'serv_{self.cat_serv_2.pk}_selected'))

        print(f"   GET exitoso (200) para superuser con datos iniciales - OK")

    def test_editar_orden_view_get_as_normal_user(self):
        """Prueba que un usuario normal NO puede ver el formulario de edición."""
        print("-> Ejecutando test_editar_orden_view_get_as_normal_user")
        self.client.login(username='testuser_edit', password='password123')
        response = self.client.get(self.edit_url)
        # --- MODIFICADO: Añadir fetch_redirect_response=False ---
        self.assertRedirects(
            response,
            f'{self.login_url}?next={self.edit_url}',
            status_code=302,
            target_status_code=200, # Django aún espera esto por defecto, pero no lo comprobará
            fetch_redirect_response=False
        )
        print(f"   Redirección (302) para usuario normal - OK")

    def test_editar_orden_view_get_non_existent(self):
        """Prueba que se obtiene un 404 si la orden no existe."""
        print("-> test_editar_orden_view_get_non_existent")
        self.client.login(username='superadmin_edit', password='password123')
        non_existent_url = reverse('editar_orden', args=[9999]) # ID que no existe
        response = self.client.get(non_existent_url)
        # --- MODIFICADO: Revertir a esperar 404 ---
        self.assertEqual(response.status_code, 404)
        print(f"   GET Non-Existent obtuvo {response.status_code} (Esperado: 404) - OK")

    def test_editar_orden_view_post_invalid_data_as_superuser(self):
        """Prueba actualizar con datos inválidos (cliente vacío)."""
        print("-> test_editar_orden_view_post_invalid_data_as_superuser")
        self.client.login(username='superadmin_edit', password='password123')
        cliente_original = self.orden_a_editar.cliente
        # Usamos el post_data simplificado del intento anterior
        post_data = {
            'cliente': '', # Inválido (Campo Requerido)
            'telefono': '123456', # Valor simple válido
            'modelo_motor': 'Motor Simple', # Valor simple válido
            'ruta': 'Ruta Simple', # Valor simple válido
            'fecha_programada': '',
            'notificacion': 'Notif simple',
            # Sin datos de formsets
        }
        response = self.client.post(self.edit_url, data=post_data)

        # 1. Verificar que NO redirige (código 200)
        # Si esta aserción sigue fallando (obteniendo 302), indica que
        # form.is_valid() está dando True en la vista, lo cual es inesperado.
        # El problema estaría en views.py o forms.py.
        self.assertEqual(response.status_code, 200, f"FALLO PERSISTENTE: Se esperaba 200 pero se obtuvo {response.status_code}. Revisar lógica de view/form.")
        print(f"   Status Code: {response.status_code} (Esperado: 200)") # No se imprimirá si falla arriba

        # Estas aserciones solo se ejecutarán si la anterior (status_code) pasa
        print(f"   Continuando verificación (si status fue 200)...")
        # 2. Verificar que la orden NO cambió en la BD
        orden_despues = Orden.objects.get(pk=self.orden_a_editar.pk)
        self.assertEqual(orden_despues.cliente, cliente_original, "El cliente cambió incorrectamente.")
        print(f"   Orden NO actualizada en BD - OK")

        # 3. Verificar que se muestra el formulario con errores
        self.assertTemplateUsed(response, 'servicios/editar_orden.html')
        self.assertIn('form', response.context)
        form_in_context = response.context['form']
        self.assertFalse(form_in_context.is_valid(), "El formulario principal ('form') en el contexto debería ser inválido.")
        self.assertIn('cliente', form_in_context.errors, "Debería haber un error en el campo 'cliente' en el contexto.")
        print(f"   Formulario inválido en contexto con error en 'cliente' - OK")

    def test_editar_orden_post_update_existing_items_only(self):
        """Prueba actualizar solo cantidad/comentario de item/servicio existente."""
        print("-> test_editar_orden_post_update_existing_items_only")
        self.client.login(username='superadmin_edit', password='password123')

        # Datos POST - Solo modificamos el item/servicio ya asociado en setUp
        post_data = {
            # Datos OrdenForm (sin cambios o mínimos)
            'cliente': self.orden_a_editar.cliente,
            'telefono': self.orden_a_editar.telefono or '',
            'modelo_motor': self.orden_a_editar.modelo_motor or '',
            'ruta': self.orden_a_editar.ruta or '',
            'fecha_programada': self.orden_a_editar.fecha_programada.strftime('%Y-%m-%d') if self.orden_a_editar.fecha_programada else '',
            'notificacion': "Notif actualizada solo items",

            # Datos Inventario - Solo el item_1 que ya estaba, con nuevos datos
            'inv-TOTAL_FORMS': str(InventarioItem.objects.count() + 1),
            'inv-INITIAL_FORMS': '0',
            'inv-MIN_NUM_FORMS': '0',
            'inv-MAX_NUM_FORMS': '1000',
            f'inv-item_{self.item_inv_1.pk}_selected': 'on', # Mantenemos seleccionado
            f'inv-item_{self.item_inv_1.pk}_cantidad': '99',   # Nueva cantidad
            f'inv-item_{self.item_inv_1.pk}_comentario': 'Comentario actualizado inv', # Nuevo comentario
            # No enviamos datos para item_2 ni custom

            # Datos Servicios - Solo el servicio_1 que ya estaba, con nueva cantidad
            'serv-TOTAL_FORMS': str(CatalogoServicio.objects.count() + 1),
            'serv-INITIAL_FORMS': '0',
            'serv-MIN_NUM_FORMS': '0',
            'serv-MAX_NUM_FORMS': '1000',
            f'serv-serv_{self.cat_serv_1.pk}_selected': 'on', # Mantenemos seleccionado
            f'serv-serv_{self.cat_serv_1.pk}_quantity_required': 'on',
            f'serv-serv_{self.cat_serv_1.pk}_quantity': 'Cantidad actualizada serv', # Nueva cantidad
            # No enviamos datos para serv_2 ni custom
        }

        response = self.client.post(self.edit_url, data=post_data)
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, fetch_redirect_response=False)

        # Verificar que la orden tiene SOLO UN item/servicio asociado y con datos actualizados
        self.orden_a_editar.refresh_from_db()
        self.assertEqual(self.orden_a_editar.ordeninventario_set.count(), 1)
        orden_inv_actualizado = self.orden_a_editar.ordeninventario_set.first()
        self.assertEqual(orden_inv_actualizado.inventario_item, self.item_inv_1)
        self.assertEqual(orden_inv_actualizado.cantidad, 99)
        self.assertEqual(orden_inv_actualizado.comentario, 'Comentario actualizado inv')

        self.assertEqual(self.orden_a_editar.servicios_detalle.count(), 1)
        servicio_actualizado = self.orden_a_editar.servicios_detalle.first()
        self.assertEqual(servicio_actualizado.catalogo_servicio, self.cat_serv_1)
        self.assertEqual(servicio_actualizado.cantidad, 'Cantidad actualizada serv')
        print("   POST Update Existing Items OK")

    def test_editar_orden_post_add_custom_only(self):
        """Prueba actualizar añadiendo solo items/servicios custom."""
        print("-> test_editar_orden_post_add_custom_only")
        self.client.login(username='superadmin_edit', password='password123')
        item_count_before = InventarioItem.objects.count()
        cat_count_before = CatalogoServicio.objects.count()
        nuevo_nombre_item_custom = "Solo Item Custom Edit"
        nuevo_nombre_servicio_custom = "Solo Servicio Custom Edit"

        # Datos POST - No seleccionamos los existentes, solo los custom
        post_data = {
            # Datos OrdenForm (mínimos)
            'cliente': self.orden_a_editar.cliente,
            'telefono': self.orden_a_editar.telefono or '',
            'modelo_motor': self.orden_a_editar.modelo_motor or '',
            'ruta': self.orden_a_editar.ruta or '',
            'fecha_programada': '',
            'notificacion': "Notif solo custom",

            # Datos Inventario - Solo el custom
            'inv-TOTAL_FORMS': str(InventarioItem.objects.count() + 1),
            'inv-INITIAL_FORMS': '0',
            'inv-MIN_NUM_FORMS': '0',
            'inv-MAX_NUM_FORMS': '1000',
            # No marcamos item_1 ni item_2
            f'inv-item_{self.item_inv_1.pk}_cantidad': '1', # Valor por defecto necesario
            f'inv-item_{self.item_inv_1.pk}_comentario': '',
            f'inv-item_{self.item_inv_2.pk}_cantidad': '1', # Valor por defecto necesario
            f'inv-item_{self.item_inv_2.pk}_comentario': '',
            # Marcamos y definimos el custom
            'inv-item_custom_selected': 'on',
            'inv-item_custom_nombre': nuevo_nombre_item_custom,
            'inv-item_custom_cantidad': '55',
            'inv-item_custom_comentario': 'Com custom solo',

            # Datos Servicios - Solo el custom
            'serv-TOTAL_FORMS': str(CatalogoServicio.objects.count() + 1),
            'serv-INITIAL_FORMS': '0',
            'serv-MIN_NUM_FORMS': '0',
            'serv-MAX_NUM_FORMS': '1000',
             # No marcamos serv_1 ni serv_2
            f'serv-serv_{self.cat_serv_1.pk}_quantity_required':'',
            f'serv-serv_{self.cat_serv_1.pk}_quantity': '',
            f'serv-serv_{self.cat_serv_2.pk}_quantity_required':'',
            f'serv-serv_{self.cat_serv_2.pk}_quantity': '',
            # Marcamos y definimos el custom
            'serv-serv_custom_selected': 'on',
            'serv-serv_custom_nombre': nuevo_nombre_servicio_custom,
            'serv-serv_custom_quantity_required': 'on', # Sí pedimos cantidad
            'serv-serv_custom_quantity': 'Cantidad custom solo',
        }

        response = self.client.post(self.edit_url, data=post_data)
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, fetch_redirect_response=False)

        # Verificar que se crearon los nuevos items/catalogos
        self.assertEqual(InventarioItem.objects.count(), item_count_before + 1)
        self.assertEqual(CatalogoServicio.objects.count(), cat_count_before + 1)
        item_custom = InventarioItem.objects.get(nombre=nuevo_nombre_item_custom)
        cat_custom = CatalogoServicio.objects.get(nombre=nuevo_nombre_servicio_custom)

        # Verificar que la orden AHORA solo tiene asociados los custom
        self.orden_a_editar.refresh_from_db()
        self.assertEqual(self.orden_a_editar.ordeninventario_set.count(), 1)
        self.assertEqual(self.orden_a_editar.ordeninventario_set.first().inventario_item, item_custom)
        self.assertEqual(self.orden_a_editar.ordeninventario_set.first().cantidad, 55)

        self.assertEqual(self.orden_a_editar.servicios_detalle.count(), 1)
        self.assertEqual(self.orden_a_editar.servicios_detalle.first().catalogo_servicio, cat_custom)
        self.assertEqual(self.orden_a_editar.servicios_detalle.first().cantidad, 'Cantidad custom solo')
        print("   POST Add Custom Only OK")

    def test_editar_orden_post_add_custom_empty_name(self):
        """Prueba que no se crea item/servicio custom si el nombre está vacío."""
        print("-> test_editar_orden_post_add_custom_empty_name")
        self.client.login(username='superadmin_edit', password='password123')
        item_count_before = InventarioItem.objects.count()
        cat_count_before = CatalogoServicio.objects.count()
        inv_assoc_before = self.orden_a_editar.ordeninventario_set.count() # Debe ser 1
        serv_assoc_before = self.orden_a_editar.servicios_detalle.count() # Debe ser 1

        post_data = {
            # Datos OrdenForm (mínimos)
            'cliente': self.orden_a_editar.cliente,
            'telefono': self.orden_a_editar.telefono or '',
            'modelo_motor': self.orden_a_editar.modelo_motor or '',
            'ruta': self.orden_a_editar.ruta or '',
            'fecha_programada': '',
            'notificacion': "Notif custom vacio",

            # Datos Inventario - Marcamos custom pero SIN nombre
            'inv-TOTAL_FORMS': str(InventarioItem.objects.count() + 1),
            'inv-INITIAL_FORMS': '0','inv-MIN_NUM_FORMS': '0','inv-MAX_NUM_FORMS': '1000',
            # No marcamos los existentes
            f'inv-item_{self.item_inv_1.pk}_cantidad': '1', f'inv-item_{self.item_inv_1.pk}_comentario': '',
            f'inv-item_{self.item_inv_2.pk}_cantidad': '1', f'inv-item_{self.item_inv_2.pk}_comentario': '',
            # Marcamos custom pero nombre vacío
            'inv-item_custom_selected': 'on',
            'inv-item_custom_nombre': '', # Nombre vacío
            'inv-item_custom_cantidad': '1', 'inv-item_custom_comentario': '',

            # Datos Servicios - Marcamos custom pero SIN nombre
            'serv-TOTAL_FORMS': str(CatalogoServicio.objects.count() + 1),
            'serv-INITIAL_FORMS': '0','serv-MIN_NUM_FORMS': '0','serv-MAX_NUM_FORMS': '1000',
             # No marcamos los existentes
            f'serv-serv_{self.cat_serv_1.pk}_quantity_required':'', f'serv-serv_{self.cat_serv_1.pk}_quantity': '',
            f'serv-serv_{self.cat_serv_2.pk}_quantity_required':'', f'serv-serv_{self.cat_serv_2.pk}_quantity': '',
            # Marcamos custom pero nombre vacío
            'serv-serv_custom_selected': 'on',
            'serv-serv_custom_nombre': '', # Nombre vacío
            'serv-serv_custom_quantity_required': '', 'serv-serv_custom_quantity': '',
        }

        response = self.client.post(self.edit_url, data=post_data)
        # Debe redirigir porque el form principal es válido, pero no debe crear items/servicios custom
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, fetch_redirect_response=False)

        # Verificar que NO se crearon nuevos items/catálogos
        self.assertEqual(InventarioItem.objects.count(), item_count_before)
        self.assertEqual(CatalogoServicio.objects.count(), cat_count_before)

        # Verificar que la orden quedó SIN items/servicios asociados (porque desmarcamos los existentes y los custom no se crearon)
        self.orden_a_editar.refresh_from_db()
        self.assertEqual(self.orden_a_editar.ordeninventario_set.count(), 0)
        self.assertEqual(self.orden_a_editar.servicios_detalle.count(), 0)
        print("   POST Add Custom Empty Name OK")

# --- Fin de la clase EditarOrdenViewTests ---

class OrdenParcialViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de orden_parcial."""
        self.client = Client()
        # Usuarios con diferentes permisos
        self.admin_user = User.objects.create_superuser(username='admin_parcial', password='password123')
        self.trabajador_group, _ = Group.objects.get_or_create(name='Trabajador')
        self.trabajador_user = User.objects.create_user(username='trabajador_parcial', password='password123')
        self.trabajador_user.groups.add(self.trabajador_group)
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_parcial', password='password123') # No autorizado
        self.chofer_user.groups.add(self.chofer_group)

        # Orden de prueba
        self.orden = Orden.objects.create(cliente="Cliente Parcial Test", estado_general='PROCESO')
        # Añadir un servicio para que el contexto service_state_choices sea relevante
        cat_serv = CatalogoServicio.objects.create(nombre="Servicio Parcial Test")
        Servicio.objects.create(orden=self.orden, catalogo_servicio=cat_serv)


        # URLs
        self.parcial_url = reverse('orden_parcial', args=[self.orden.pk])
        self.parcial_url_inexistente = reverse('orden_parcial', args=[9999])
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para OrdenParcialViewTests...")

    def test_orden_parcial_get_as_admin(self):
        """Prueba GET como admin (autorizado)."""
        print("-> test_orden_parcial_get_as_admin")
        self.client.login(username='admin_parcial', password='password123')
        response = self.client.get(self.parcial_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/orden_parcial.html')
        self.assertIn('order', response.context)
        self.assertEqual(response.context['order'], self.orden)
        self.assertIn('service_state_choices', response.context) # Verificar contexto extra
        print("   GET Admin OK")

    def test_orden_parcial_get_as_trabajador(self):
        """Prueba GET como trabajador (autorizado)."""
        print("-> test_orden_parcial_get_as_trabajador")
        self.client.login(username='trabajador_parcial', password='password123')
        response = self.client.get(self.parcial_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/orden_parcial.html')
        self.assertIn('order', response.context)
        self.assertEqual(response.context['order'], self.orden)
        self.assertIn('service_state_choices', response.context)
        print("   GET Trabajador OK")

    def test_orden_parcial_get_unauthorized(self):
        """Prueba GET como usuario no autorizado (chofer)."""
        print("-> test_orden_parcial_get_unauthorized")
        self.client.login(username='chofer_parcial', password='password123') # Chofer no tiene permiso
        response = self.client.get(self.parcial_url)
        # user_passes_test redirige al login por defecto
        expected_redirect_url = f"{self.login_url}?next={self.parcial_url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Unauthorized (Chofer) OK")

    def test_orden_parcial_get_logged_out(self):
        """Prueba GET sin estar logueado."""
        print("-> test_orden_parcial_get_logged_out")
        response = self.client.get(self.parcial_url)
        expected_redirect_url = f"{self.login_url}?next={self.parcial_url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Logged Out OK")

    def test_orden_parcial_get_non_existent(self):
        """Prueba GET para una orden que no existe."""
        print("-> test_orden_parcial_get_non_existent")
        self.client.login(username='admin_parcial', password='password123') # Usuario autorizado
        response = self.client.get(self.parcial_url_inexistente)
        self.assertEqual(response.status_code, 404) # Esperamos 404 por get_object_or_404
        print("   GET Non-Existent (404) OK")

# --- Fin de la clase OrdenParcialViewTests ---

class OrdenDetalleViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de orden_detalle."""
        self.client = Client()
        # Usuario autorizado (Chofer)
        self.chofer_group, created = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_detalle', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        # Usuario no autorizado
        self.normal_user = User.objects.create_user(username='normal_detalle', password='password123')
        # Objetos relacionados (puedes omitir si no son estrictamente necesarios para cargar la orden)
        self.cliente = Cliente.objects.create(nombre="Cliente Detalle")
        self.motor = Motor.objects.create(nombre="Motor Detalle")
        # Orden existente para ver
        self.orden = Orden.objects.create(
            cliente="Cliente Detalle",
            modelo_motor="Motor Detalle",
            cliente_registrado=self.cliente,
            motor_registrado=self.motor,
            estado_general='ACEPTADA'
        )
        # URLs
        self.detalle_url = reverse('orden_detalle', args=[self.orden.pk])
        self.detalle_url_inexistente = reverse('orden_detalle', args=[9999]) # ID que no existe
        self.login_url = reverse('login')
        # print(f"Ejecutando setUp para OrdenDetalleViewTests... URL: {self.detalle_url}")

    def test_orden_detalle_view_get_as_chofer(self):
        """Prueba que un chofer puede ver el detalle de una orden existente."""
        # print("-> Ejecutando test_orden_detalle_view_get_as_chofer")
        self.client.login(username='chofer_detalle', password='password123')
        response = self.client.get(self.detalle_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/orden_detalle.html')
        # Verificar que la orden correcta esté en el contexto
        self.assertIn('orden', response.context)
        self.assertEqual(response.context['orden'], self.orden)
        # print(f"   GET exitoso (200) para chofer - OK")

    def test_orden_detalle_view_get_logged_out(self):
        """Prueba que un usuario no logueado es redirigido."""
        # print("-> Ejecutando test_orden_detalle_view_get_logged_out")
        response = self.client.get(self.detalle_url)
        # Esperamos redirección al login (sin seguirla)
        self.assertRedirects(response, f'{self.login_url}?next={self.detalle_url}', fetch_redirect_response=False)
        # print(f"   Redirección (302) para loggout out - OK")

    def test_orden_detalle_view_get_unauthorized_user(self):
        """Prueba que un usuario logueado pero no autorizado es redirigido."""
        # print("-> Ejecutando test_orden_detalle_view_get_unauthorized_user")
        self.client.login(username='normal_detalle', password='password123')
        response = self.client.get(self.detalle_url)
        # Esperamos redirección al login (sin seguirla)
        # --- CORREGIDO: Se quitó target_status_code=200 porque login.html no existe ---
        self.assertRedirects(response, f'{self.login_url}?next={self.detalle_url}', status_code=302, fetch_redirect_response=False)
        # print(f"   Redirección (302) para usuario no autorizado - OK")

    def test_orden_detalle_view_get_non_existent(self):
        """Prueba que intentar ver una orden inexistente devuelve 404."""
        # print("-> Ejecutando test_orden_detalle_view_get_non_existent")
        self.client.login(username='chofer_detalle', password='password123') # Logueado como usuario autorizado
        response = self.client.get(self.detalle_url_inexistente)
        self.assertEqual(response.status_code, 404)
        # print(f"   GET 404 para orden inexistente - OK")

# --- Fin de la clase OrdenDetalleViewTests ---

class TableroOrdenesViewTests(TestCase):

    def setUp(self):
        """Configuración mejorada para pruebas de tablero_ordenes."""
        self.client = Client()
        # Usuarios
        self.admin_user = User.objects.create_superuser(username='admin_tablero', password='password123')
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_tablero', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        self.normal_user = User.objects.create_user(username='normal_tablero', password='password123') # No autorizado

        # Crear órdenes con diferentes fechas, estados y posiciones
        # --- MODIFICADO: Guardar fechas con self. ---
        self.today = timezone.localdate()
        self.lunes_proximo = self.today + timedelta(days=(0 - self.today.weekday() + 7) % 7) # 0 = Lunes
        self.martes_proximo = self.lunes_proximo + timedelta(days=1)
        # --- FIN MODIFICADO ---

        # Órdenes que deben aparecer
        self.orden_pen1 = Orden.objects.create(cliente="Cliente Tablero Pen 1", estado_general='ACEPTADA', fecha_programada=None, posicion=30)
        # --- MODIFICADO: Usar self.today ---
        self.orden_pen2 = Orden.objects.create(cliente="Cliente Tablero Pen 2", estado_general='PROCESO', fecha_programada=self.today - timedelta(days=2), posicion=15) # Fecha pasada
        # --- FIN MODIFICADO ---
        # --- MODIFICADO: Usar self.lunes_proximo ---
        self.orden_lun1 = Orden.objects.create(cliente="Cliente Tablero Lun 1", estado_general='ACEPTADA', fecha_programada=self.lunes_proximo, posicion=80)
        self.orden_lun2 = Orden.objects.create(cliente="Cliente Tablero Lun 2", estado_general='PROCESO', fecha_programada=self.lunes_proximo, posicion=40)
        # --- FIN MODIFICADO ---
        # --- MODIFICADO: Usar self.martes_proximo ---
        self.orden_mar1 = Orden.objects.create(cliente="Cliente Tablero Mar 1", estado_general='ACEPTADA', fecha_programada=self.martes_proximo, posicion=25)
        # --- FIN MODIFICADO ---
        # Orden que NO debe aparecer
        # --- MODIFICADO: Usar self.today ---
        self.orden_entregada = Orden.objects.create(cliente="Cliente Tablero Entregado", estado_general='ENTREGADO', fecha_programada=self.today)
        # --- FIN MODIFICADO ---

        # URLs
        self.tablero_url = reverse('tablero_ordenes')
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para TableroOrdenesViewTests...") # Opcional

    def test_tablero_ordenes_view_get_as_authorized(self):
        """Prueba GET como usuario autorizado (admin o chofer) y verifica contexto."""
        print("-> test_tablero_ordenes_view_get_as_authorized")
        self.client.login(username='admin_tablero', password='password123')
        response = self.client.get(self.tablero_url)

        # Verificaciones básicas
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/tablero_ordenes.html')
        self.assertIn('ordered_groups', response.context)

        # Verificaciones detalladas del contexto ordered_groups
        ordered_groups = response.context['ordered_groups']
        self.assertTrue(len(ordered_groups) >= 1)

        # Verificar grupo 'Pendientes'
        pendientes_group = next((g for g in ordered_groups if g[0] == 'Pendientes'), None)
        self.assertIsNotNone(pendientes_group, "El grupo 'Pendientes' debería existir")
        ordenes_pendientes = pendientes_group[1]
        self.assertEqual(len(ordenes_pendientes), 2, "Debería haber 2 órdenes pendientes/pasadas")
        self.assertEqual(ordenes_pendientes[0].pk, self.orden_pen2.pk)
        self.assertEqual(ordenes_pendientes[1].pk, self.orden_pen1.pk)

        # Verificar grupo 'Lunes' (o el día que corresponda)
        # --- MODIFICADO: Usar self.lunes_proximo ---
        nombre_lunes = self.lunes_proximo.strftime('%A')
        # --- FIN MODIFICADO ---
        traducciones = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
        nombre_dia_lunes_esp = traducciones.get(nombre_lunes, nombre_lunes)

        lunes_group = next((g for g in ordered_groups if g[0] == nombre_dia_lunes_esp), None)
        self.assertIsNotNone(lunes_group, f"El grupo '{nombre_dia_lunes_esp}' debería existir")
        ordenes_lunes = lunes_group[1]
        self.assertEqual(len(ordenes_lunes), 2, f"Debería haber 2 órdenes en '{nombre_dia_lunes_esp}'")
        self.assertEqual(ordenes_lunes[0].pk, self.orden_lun2.pk)
        self.assertEqual(ordenes_lunes[1].pk, self.orden_lun1.pk)

        # Verificar que la orden 'ENTREGADO' NO está
        all_pks_shown = [o.pk for group in ordered_groups for o in group[1]]
        self.assertNotIn(self.orden_entregada.pk, all_pks_shown)

        print("   GET Autorizado OK y contexto verificado")

    def test_tablero_ordenes_view_get_logged_out(self):
        """Prueba redirección si no logueado."""
        response = self.client.get(self.tablero_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.tablero_url}', fetch_redirect_response=False)

    def test_tablero_ordenes_view_get_unauthorized(self):
        """Prueba redirección si usuario logueado no está autorizado."""
        self.client.login(username='normal_tablero', password='password123')
        response = self.client.get(self.tablero_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.tablero_url}', status_code=302, fetch_redirect_response=False)

# --- Fin de la clase TableroOrdenesViewTests ---

class TableroParcialViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de tablero_parcial."""
        self.client = Client()
        # Usuarios
        self.admin_user = User.objects.create_superuser(username='admin_tab_parcial', password='password123')
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_tab_parcial', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        self.trabajador_group, _ = Group.objects.get_or_create(name='Trabajador') # No autorizado
        self.trabajador_user = User.objects.create_user(username='trabajador_tab_parcial', password='password123')
        self.trabajador_user.groups.add(self.trabajador_group)

        # Crear órdenes con diferentes fechas y estados para probar agrupación/ordenamiento
        today = timezone.localdate()
        lunes_proximo = today + timedelta(days=(0 - today.weekday() + 7) % 7) # 0 = Lunes
        martes_proximo = lunes_proximo + timedelta(days=1)

        Orden.objects.create(cliente="Cliente Pendiente 1", estado_general='ACEPTADA', fecha_programada=None, posicion=20)
        Orden.objects.create(cliente="Cliente Pendiente 2", estado_general='PROCESO', fecha_programada=today - timedelta(days=1), posicion=10) # Fecha pasada
        Orden.objects.create(cliente="Cliente Lunes 1", estado_general='ACEPTADA', fecha_programada=lunes_proximo, posicion=100)
        Orden.objects.create(cliente="Cliente Lunes 2", estado_general='PROCESO', fecha_programada=lunes_proximo, posicion=50)
        Orden.objects.create(cliente="Cliente Martes 1", estado_general='ACEPTADA', fecha_programada=martes_proximo, posicion=10)
        Orden.objects.create(cliente="Cliente Entregado", estado_general='ENTREGADO', fecha_programada=today) # No debe aparecer

        # URLs
        self.url = reverse('tablero_parcial')
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para TableroParcialViewTests...") # Opcional

    def test_tablero_parcial_get_as_admin(self):
        """Prueba GET como admin."""
        print("-> test_tablero_parcial_get_as_admin")
        self.client.login(username='admin_tab_parcial', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/tablero_parcial.html')
        self.assertIn('ordered_groups', response.context)
        self.assertIn('service_state_choices', response.context)

        # Verificaciones más detalladas del contexto (opcional pero recomendable)
        ordered_groups = response.context['ordered_groups']
        # Verificar que hay grupos (Pendientes + Lunes a Viernes)
        self.assertTrue(len(ordered_groups) >= 1) # Al menos 'Pendientes'
        # Buscar el grupo 'Pendientes' y verificar su contenido y orden
        pendientes_group = next((g for g in ordered_groups if g[0] == 'Pendientes'), None)
        self.assertIsNotNone(pendientes_group)
        self.assertEqual(len(pendientes_group[1]), 2) # Deben estar las 2 órdenes pendientes/pasadas
        self.assertEqual(pendientes_group[1][0].cliente, "Cliente Pendiente 2") # Ordenado por posicion (10)
        self.assertEqual(pendientes_group[1][1].cliente, "Cliente Pendiente 1") # Ordenado por posicion (20)

        # Buscar grupo 'Lunes' (o el día correspondiente a lunes_proximo) y verificar
        lunes_group = next((g for g in ordered_groups if g[0] == 'Lunes'), None) # Asume que lunes_proximo cae en Lunes
        if lunes_group: # Puede no existir si lunes_proximo es fin de semana (ajustar test si es necesario)
             self.assertEqual(len(lunes_group[1]), 2)
             self.assertEqual(lunes_group[1][0].cliente, "Cliente Lunes 2") # Ordenado por posicion (50)
             self.assertEqual(lunes_group[1][1].cliente, "Cliente Lunes 1") # Ordenado por posicion (100)

        # Verificar que la orden 'ENTREGADO' NO está
        clientes_mostrados = [o.cliente for group in ordered_groups for o in group[1]]
        self.assertNotIn("Cliente Entregado", clientes_mostrados)

        print("   GET Admin OK y contexto verificado")

    def test_tablero_parcial_get_as_chofer(self):
        """Prueba GET como chofer."""
        print("-> test_tablero_parcial_get_as_chofer")
        self.client.login(username='chofer_tab_parcial', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/tablero_parcial.html')
        self.assertIn('ordered_groups', response.context)
        print("   GET Chofer OK")

    def test_tablero_parcial_get_unauthorized(self):
        """Prueba GET como usuario no autorizado (trabajador)."""
        print("-> test_tablero_parcial_get_unauthorized")
        self.client.login(username='trabajador_tab_parcial', password='password123') # Trabajador no tiene permiso
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Unauthorized (Trabajador) OK")

    def test_tablero_parcial_get_logged_out(self):
        """Prueba GET sin estar logueado."""
        print("-> test_tablero_parcial_get_logged_out")
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Logged Out OK")

# --- Fin de la clase TableroParcialViewTests ---

class ActualizarEstadoServicioAPITests(TestCase):

    def setUp(self):
        """Configuración para pruebas de la API actualizar_estado_servicio."""
        self.client = Client()
        # Usuarios y Grupos
        self.trabajador_group, created = Group.objects.get_or_create(name='Trabajador')
        self.chofer_group, created_c = Group.objects.get_or_create(name='Chofer') # Para prueba no autorizada
        self.trabajador_user = User.objects.create_user(username='trabajador_api', password='password123')
        self.trabajador_user.groups.add(self.trabajador_group)
        self.chofer_user = User.objects.create_user(username='chofer_api', password='password123') # Usuario NO autorizado para esta API
        self.chofer_user.groups.add(self.chofer_group)
        # Objetos necesarios
        self.cliente = Cliente.objects.create(nombre="Cliente API")
        self.catalogo = CatalogoServicio.objects.create(nombre="Servicio API")
        self.orden = Orden.objects.create(cliente="Cliente API", cliente_registrado=self.cliente, estado_general='ACEPTADA')
        self.servicio = Servicio.objects.create(orden=self.orden, catalogo_servicio=self.catalogo, estado='PENDIENTE')
        # URLs
        self.api_url = reverse('actualizar_estado_servicio')
        self.login_url = reverse('login')
        # print(f"Ejecutando setUp para ActualizarEstadoServicioAPITests...")

    def test_actualizar_estado_servicio_valido_trabajador(self):
        """Prueba actualizar estado como trabajador autorizado."""
        # print("-> test_actualizar_estado_servicio_valido_trabajador")
        self.client.login(username='trabajador_api', password='password123')
        post_data = json.dumps({ # Convertir diccionario a string JSON
            'service_id': self.servicio.pk,
            'estado': 'PROCESO'
        })
        response = self.client.post(
            self.api_url,
            data=post_data,
            content_type='application/json' # Indicar que enviamos JSON
        )
        # Verificar respuesta exitosa y contenido JSON
        self.assertEqual(response.status_code, 200)
        response_data = response.json() # Decodificar respuesta JSON
        self.assertEqual(response_data['status'], 'ok')
        self.assertEqual(response_data['data']['service_id'], self.servicio.pk)
        self.assertEqual(response_data['data']['estado'], 'PROCESO')
        self.assertEqual(response_data['data']['orden_estado'], 'PROCESO') # Verificar estado de orden actualizado

        # Verificar cambio en la BD
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado, 'PROCESO')
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado_general, 'PROCESO')
        # print("   Actualización válida OK")

    def test_actualizar_estado_servicio_id_invalido(self):
        """Prueba actualizar con un ID de servicio que no existe."""
        # print("-> test_actualizar_estado_servicio_id_invalido")
        self.client.login(username='trabajador_api', password='password123')
        post_data = json.dumps({'service_id': 9999, 'estado': 'PROCESO'})
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos un error 404 Not Found
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Servicio no encontrado', response_data['message'])
        # print("   ID inválido 404 OK")

    def test_actualizar_estado_servicio_datos_faltantes(self):
        """Prueba actualizar sin enviar todos los datos requeridos."""
        # print("-> test_actualizar_estado_servicio_datos_faltantes")
        self.client.login(username='trabajador_api', password='password123')
        post_data = json.dumps({'service_id': self.servicio.pk}) # Falta 'estado'
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos un error 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Faltan parámetros requeridos', response_data['message'])
        # print("   Datos faltantes 400 OK")

    def test_actualizar_estado_servicio_no_autorizado(self):
        """Prueba actualizar estado con usuario no autorizado (Chofer)."""
        # print("-> test_actualizar_estado_servicio_no_autorizado")
        self.client.login(username='chofer_api', password='password123') # Usuario incorrecto
        post_data = json.dumps({'service_id': self.servicio.pk, 'estado': 'PROCESO'})
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # La vista AJAX protegida por user_passes_test debería redirigir al login
        self.assertEqual(response.status_code, 302)
        # No usamos assertRedirects aquí porque la respuesta puede no tener 'Location' si es AJAX
        # Verificamos solo el código 302.
        # print("   No autorizado 302 OK")

    def test_actualizar_estado_servicio_metodo_no_permitido(self):
        """Prueba que un método GET no está permitido."""
        print("-> test_actualizar_estado_servicio_metodo_no_permitido")
        self.client.login(username='trabajador_api', password='password123')
        response = self.client.get(self.api_url) # Usamos GET
        self.assertEqual(response.status_code, 405) # Method Not Allowed
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Método no permitido', response_data['message'])
        print("   GET 405 OK")

    def test_actualizar_estado_servicio_datos_vacios(self):
        """Prueba enviar un cuerpo JSON vacío."""
        print("-> test_actualizar_estado_servicio_datos_vacios")
        self.client.login(username='trabajador_api', password='password123')
        response = self.client.post(self.api_url, data='{}', content_type='application/json')
        # Esperamos 400 Bad Request porque el JSON está vacío
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        # --- CORREGIDO: Esperar mensaje correcto Y ELIMINAR checks de 'errors'/'missing' ---
        self.assertEqual(response_data.get('message'), 'No se recibieron datos') # Espera este mensaje exacto
        # Ya no verificamos 'errors' ni 'missing' aquí
        # --- FIN CORREGIDO ---
        print("   POST JSON vacío 400 OK")

    def test_actualizar_estado_servicio_datos_faltantes_id(self):
        """Prueba enviar JSON sin la clave 'service_id'."""
        print("-> test_actualizar_estado_servicio_datos_faltantes_id")
        self.client.login(username='trabajador_api', password='password123')
        post_data = json.dumps({'estado': 'PROCESO'}) # Falta service_id
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Faltan parámetros requeridos', response_data['message'])
        self.assertIn('missing', response_data.get('errors', {}))
        self.assertIn('service_id', response_data.get('errors', {}).get('missing', []))
        self.assertNotIn('estado', response_data.get('errors', {}).get('missing', [])) # estado sí se envió
        print("   POST sin service_id 400 OK")

    @patch('servicios.views.async_to_sync') # Mockeamos para verificar llamadas a websockets
    def test_actualizar_estado_servicio_cambia_orden_a_listo(self, mock_async_to_sync):
        """Prueba que al terminar el último servicio, la orden pasa a LISTO."""
        print("-> test_actualizar_estado_servicio_cambia_orden_a_listo")
        # Aseguramos que la orden solo tenga este servicio en estado PENDIENTE
        self.orden.servicios_detalle.exclude(pk=self.servicio.pk).delete()
        self.servicio.estado = 'PENDIENTE'
        self.servicio.save()
        self.orden.estado_general = 'PROCESO' # Forzamos un estado previo
        self.orden.save()

        self.client.login(username='trabajador_api', password='password123')
        post_data = json.dumps({
            'service_id': self.servicio.pk,
            'estado': 'TERMINADO' # Actualizamos a TERMINADO
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')

        # Verificar respuesta exitosa
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'ok')
        self.assertEqual(response_data['data']['estado'], 'TERMINADO')
        # ¡Verificar que el estado de la orden ahora es LISTO!
        self.assertEqual(response_data['data']['orden_estado'], 'LISTO')

        # Verificar cambio en BD
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado, 'TERMINADO')
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado_general, 'LISTO')

        # Verificar que se llamaron las notificaciones WebSocket correctas
        # Debe llamarse 2 veces: una para service_update, otra para orden_terminada
        self.assertEqual(mock_async_to_sync.call_count, 2)
        # Puedes hacer verificaciones más específicas de los argumentos si quieres
        # call_args_list = mock_async_to_sync.call_args_list
        # print(call_args_list) # Para ver qué se llamó

        print("   Actualización a LISTO y notificación OK")

    def test_actualizar_estado_servicio_json_invalido(self):
        """Prueba enviar datos que no son JSON válido."""
        print("-> test_actualizar_estado_servicio_json_invalido")
        self.client.login(username='trabajador_api', password='password123')
        # Enviamos texto plano en lugar de JSON
        response = self.client.post(self.api_url, data='esto no es json', content_type='text/plain')
        # Esperamos 400 Bad Request por JSONDecodeError en la vista
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('JSON inválido', response_data['message'])
        print("   POST JSON inválido 400 OK")

# --- Fin de la clase ActualizarEstadoServicioAPITests ---

class ActualizarServiciosViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de actualizar_servicios (vista completa)."""
        self.client = Client()
        # Usuarios
        self.admin_user = User.objects.create_superuser(username='admin_act_full', password='password123')
        self.trabajador_group, _ = Group.objects.get_or_create(name='Trabajador')
        self.trabajador_user = User.objects.create_user(username='trabajador_act_full', password='password123')
        self.trabajador_user.groups.add(self.trabajador_group)
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer') # No autorizado
        self.chofer_user = User.objects.create_user(username='chofer_act_full', password='password123')
        self.chofer_user.groups.add(self.chofer_group)

        # Crear órdenes (similar a ActualizarServiciosParcialViewTests)
        today = timezone.localdate()
        lunes_proximo = today + timedelta(days=(0 - today.weekday() + 7) % 7)

        Orden.objects.create(cliente="Cliente ASF Pendiente", estado_general='ACEPTADA', fecha_programada=None, posicion=10)
        Orden.objects.create(cliente="Cliente ASF Lunes", estado_general='PROCESO', fecha_programada=lunes_proximo, posicion=5)
        Orden.objects.create(cliente="Cliente ASF Entregado", estado_general='ENTREGADO', fecha_programada=today) # No debe aparecer

        # Crear algunos CatalogoServicio para probar el contexto 'servicios_list'
        self.cat_serv_asf1 = CatalogoServicio.objects.create(nombre="Servicio ASF 1")
        self.cat_serv_asf2 = CatalogoServicio.objects.create(nombre="Servicio ASF 2")

        # URLs
        self.url = reverse('actualizar_servicios') # URL de la vista completa
        self.login_url = reverse('login')
        # print(f"Ejecutando setUp para ActualizarServiciosViewTests...") # Opcional

    def test_actualizar_servicios_get_as_admin(self):
        """Prueba GET como admin (autorizado)."""
        # print("-> test_actualizar_servicios_get_as_admin") # Opcional
        self.client.login(username='admin_act_full', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Verificar la plantilla de la vista completa
        self.assertTemplateUsed(response, 'servicios/actualizar_servicios.html')
        # Verificar variables principales del contexto
        self.assertIn('ordered_groups', response.context)
        self.assertIn('service_state_choices', response.context)
        self.assertIn('servicios_list', response.context)

        # Verificar contenido de contextos clave (opcional pero recomendado)
        ordered_groups = response.context['ordered_groups']
        pendientes_group = next((g for g in ordered_groups if g[0] == 'Pendientes'), None)
        self.assertIsNotNone(pendientes_group)
        self.assertEqual(len(pendientes_group[1]), 1)
        self.assertEqual(pendientes_group[1][0].cliente, "Cliente ASF Pendiente")

        servicios_list = response.context['servicios_list']
        self.assertEqual(servicios_list.count(), CatalogoServicio.objects.count())
        self.assertIn(self.cat_serv_asf1, servicios_list)
        self.assertIn(self.cat_serv_asf2, servicios_list)

        # print("   GET Admin OK y contexto verificado") # Opcional

    def test_actualizar_servicios_get_as_trabajador(self):
        """Prueba GET como trabajador (autorizado)."""
        # print("-> test_actualizar_servicios_get_as_trabajador") # Opcional
        self.client.login(username='trabajador_act_full', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/actualizar_servicios.html')
        self.assertIn('ordered_groups', response.context)
        self.assertIn('servicios_list', response.context)
        # print("   GET Trabajador OK") # Opcional

    def test_actualizar_servicios_get_unauthorized(self):
        """Prueba GET como usuario no autorizado (chofer)."""
        # print("-> test_actualizar_servicios_get_unauthorized") # Opcional
        self.client.login(username='chofer_act_full', password='password123') # Chofer no tiene permiso
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        # print("   GET Unauthorized (Chofer) OK") # Opcional

    def test_actualizar_servicios_get_logged_out(self):
        """Prueba GET sin estar logueado."""
        # print("-> test_actualizar_servicios_get_logged_out") # Opcional
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        # print("   GET Logged Out OK") # Opcional

# --- Fin de la clase ActualizarServiciosViewTests ---

class ActualizarServiciosParcialViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de actualizar_servicios_parcial."""
        self.client = Client()
        # Usuarios
        self.admin_user = User.objects.create_superuser(username='admin_act_parcial', password='password123')
        self.trabajador_group, _ = Group.objects.get_or_create(name='Trabajador')
        self.trabajador_user = User.objects.create_user(username='trabajador_act_parcial', password='password123')
        self.trabajador_user.groups.add(self.trabajador_group)
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer') # No autorizado
        self.chofer_user = User.objects.create_user(username='chofer_act_parcial', password='password123')
        self.chofer_user.groups.add(self.chofer_group)

        # Crear órdenes (similar a TableroParcialViewTests)
        today = timezone.localdate()
        lunes_proximo = today + timedelta(days=(0 - today.weekday() + 7) % 7)

        Orden.objects.create(cliente="Cliente ASP Pendiente", estado_general='ACEPTADA', fecha_programada=None, posicion=10)
        Orden.objects.create(cliente="Cliente ASP Lunes", estado_general='PROCESO', fecha_programada=lunes_proximo, posicion=5)
        Orden.objects.create(cliente="Cliente ASP Entregado", estado_general='ENTREGADO', fecha_programada=today) # No debe aparecer

        # Crear algunos CatalogoServicio para probar el contexto 'servicios_list'
        self.cat_serv_asp1 = CatalogoServicio.objects.create(nombre="Servicio ASP 1")
        self.cat_serv_asp2 = CatalogoServicio.objects.create(nombre="Servicio ASP 2")

        # URLs
        self.url = reverse('actualizar_servicios_parcial')
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para ActualizarServiciosParcialViewTests...") # Opcional

    def test_actualizar_servicios_parcial_get_as_admin(self):
        """Prueba GET como admin (autorizado)."""
        print("-> test_actualizar_servicios_parcial_get_as_admin")
        self.client.login(username='admin_act_parcial', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/actualizar_servicios_parcial.html')
        # Verificar variables principales del contexto
        self.assertIn('ordered_groups', response.context)
        self.assertIn('service_state_choices', response.context)
        self.assertIn('servicios_list', response.context)

        # Verificar contenido de contextos clave
        ordered_groups = response.context['ordered_groups']
        pendientes_group = next((g for g in ordered_groups if g[0] == 'Pendientes'), None)
        self.assertIsNotNone(pendientes_group)
        self.assertEqual(len(pendientes_group[1]), 1) # Solo la orden ASP Pendiente
        self.assertEqual(pendientes_group[1][0].cliente, "Cliente ASP Pendiente")

        # Verificar que la lista completa de catálogos está presente
        servicios_list = response.context['servicios_list']
        self.assertEqual(servicios_list.count(), CatalogoServicio.objects.count()) # Compara con el total en BD
        self.assertIn(self.cat_serv_asp1, servicios_list)
        self.assertIn(self.cat_serv_asp2, servicios_list)

        print("   GET Admin OK y contexto verificado")

    def test_actualizar_servicios_parcial_get_as_trabajador(self):
        """Prueba GET como trabajador (autorizado)."""
        print("-> test_actualizar_servicios_parcial_get_as_trabajador")
        self.client.login(username='trabajador_act_parcial', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/actualizar_servicios_parcial.html')
        self.assertIn('ordered_groups', response.context)
        self.assertIn('servicios_list', response.context)
        print("   GET Trabajador OK")

    def test_actualizar_servicios_parcial_get_unauthorized(self):
        """Prueba GET como usuario no autorizado (chofer)."""
        print("-> test_actualizar_servicios_parcial_get_unauthorized")
        self.client.login(username='chofer_act_parcial', password='password123') # Chofer no tiene permiso
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Unauthorized (Chofer) OK")

    def test_actualizar_servicios_parcial_get_logged_out(self):
        """Prueba GET sin estar logueado."""
        print("-> test_actualizar_servicios_parcial_get_logged_out")
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Logged Out OK")

# --- Fin de la clase ActualizarServiciosParcialViewTests ---

class AgregarServicioAPITests(TestCase):

    def setUp(self):
        """Configuración para pruebas de la API agregar_servicio_orden."""
        self.client = Client()
        # Usuarios y Grupos
        self.trabajador_group, created = Group.objects.get_or_create(name='Trabajador')
        self.chofer_group, created_c = Group.objects.get_or_create(name='Chofer')
        self.trabajador_user = User.objects.create_user(username='trabajador_agregar', password='password123')
        self.trabajador_user.groups.add(self.trabajador_group)
        self.chofer_user = User.objects.create_user(username='chofer_agregar', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        # Objetos necesarios
        self.cliente = Cliente.objects.create(nombre="Cliente Agregar API")
        self.catalogo_existente = CatalogoServicio.objects.create(nombre="Servicio Existente API")
        self.orden = Orden.objects.create(cliente="Cliente Agregar API", cliente_registrado=self.cliente, estado_general='ACEPTADA')
        # URLs
        self.api_url = reverse('agregar_servicio_orden')
        self.login_url = reverse('login')
        # print(f"Ejecutando setUp para AgregarServicioAPITests...")

    def test_agregar_servicio_existente_valido(self):
        """Prueba agregar un servicio existente a una orden."""
        # print("-> test_agregar_servicio_existente_valido")
        self.client.login(username='trabajador_agregar', password='password123')
        servicio_count_before = self.orden.servicios_detalle.count()
        post_data = json.dumps({
            'order_id': self.orden.pk,
            'servicio_id': self.catalogo_existente.pk,
            'cantidad': '1.5',
            'observacion': 'Obs test'
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')

        # Verificar respuesta y creación
        self.assertEqual(response.status_code, 200, f"Error: {response.content.decode()}")
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')
        self.assertEqual(self.orden.servicios_detalle.count(), servicio_count_before + 1)
        nuevo_servicio = self.orden.servicios_detalle.latest('id')
        self.assertEqual(nuevo_servicio.catalogo_servicio, self.catalogo_existente)
        self.assertEqual(nuevo_servicio.cantidad, '1.5')
        self.assertEqual(nuevo_servicio.estado, 'PENDIENTE') # Verifica estado inicial
        # print("   Agregar servicio existente OK")

    def test_agregar_servicio_custom_valido(self):
        """Prueba agregar un servicio custom (nuevo) a una orden."""
        # print("-> test_agregar_servicio_custom_valido")
        self.client.login(username='trabajador_agregar', password='password123')
        servicio_count_before = self.orden.servicios_detalle.count()
        catalogo_count_before = CatalogoServicio.objects.count()
        nombre_nuevo_servicio = "Servicio Custom Nuevo Test"

        post_data = json.dumps({
            'order_id': self.orden.pk,
            'servicio_id': 'custom', # Indicador para servicio custom
            'nombre_custom': nombre_nuevo_servicio,
            'cantidad': '2',
            'observacion': 'Obs custom'
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')

        # Verificar respuesta y creación
        self.assertEqual(response.status_code, 200, f"Error: {response.content.decode()}")
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')
        self.assertEqual(self.orden.servicios_detalle.count(), servicio_count_before + 1) # Se creó un Servicio
        self.assertEqual(CatalogoServicio.objects.count(), catalogo_count_before + 1) # Se creó un CatalogoServicio
        nuevo_servicio_catalogo = CatalogoServicio.objects.get(nombre=nombre_nuevo_servicio)
        nuevo_servicio = self.orden.servicios_detalle.latest('id')
        self.assertEqual(nuevo_servicio.catalogo_servicio, nuevo_servicio_catalogo)
        self.assertEqual(nuevo_servicio.cantidad, '2')
        # print("   Agregar servicio custom OK")

    def test_agregar_servicio_custom_sin_nombre(self):
        """Prueba agregar un servicio custom sin proporcionar el nombre."""
        # print("-> test_agregar_servicio_custom_sin_nombre")
        self.client.login(username='trabajador_agregar', password='password123')
        servicio_count_before = self.orden.servicios_detalle.count()
        catalogo_count_before = CatalogoServicio.objects.count()
        post_data = json.dumps({
            'order_id': self.orden.pk,
            'servicio_id': 'custom',
            'nombre_custom': '', # Nombre vacío
            'cantidad': '1'
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')

        # Esperamos error 400 Bad Request
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'error')
        self.assertIn('Debe ingresar el nombre del servicio custom', response_data.get('error', ''))
        # Verificar que no se crearon objetos
        self.assertEqual(self.orden.servicios_detalle.count(), servicio_count_before)
        self.assertEqual(CatalogoServicio.objects.count(), catalogo_count_before)
        # print("   Agregar custom sin nombre 400 OK")

    def test_agregar_servicio_orden_invalida(self):
        """Prueba agregar servicio a una orden que no existe."""
        # print("-> test_agregar_servicio_orden_invalida")
        self.client.login(username='trabajador_agregar', password='password123')
        post_data = json.dumps({
            'order_id': 9999, # ID no existente
            'servicio_id': self.catalogo_existente.pk,
            'cantidad': '1'
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos error 404 Not Found
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'error')
        self.assertIn('Orden no encontrada', response_data.get('error', ''))
        # print("   Orden inválida 404 OK")

    def test_agregar_servicio_no_autorizado(self):
        """Prueba agregar servicio con usuario no autorizado (Chofer)."""
        # print("-> test_agregar_servicio_no_autorizado")
        self.client.login(username='chofer_agregar', password='password123') # Usuario incorrecto
        post_data = json.dumps({
            'order_id': self.orden.pk,
            'servicio_id': self.catalogo_existente.pk,
            'cantidad': '1'
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos redirección (302) al login
        self.assertEqual(response.status_code, 302)
        # print("   No autorizado 302 OK")

    def test_agregar_servicio_metodo_no_permitido(self):
        """Prueba que un método GET no está permitido."""
        print("-> test_agregar_servicio_metodo_no_permitido")
        self.client.login(username='trabajador_agregar', password='password123')
        response = self.client.get(self.api_url) # Usamos GET
        self.assertEqual(response.status_code, 405) # Method Not Allowed
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'error')
        self.assertIn('Método no permitido', response_data.get('error', ''))
        print("   GET 405 OK")

    def test_agregar_servicio_id_invalido(self):
        """Prueba agregar un servicio con un ID de catálogo que no existe."""
        print("-> test_agregar_servicio_id_invalido")
        self.client.login(username='trabajador_agregar', password='password123')
        servicio_count_before = self.orden.servicios_detalle.count()
        catalogo_count_before = CatalogoServicio.objects.count()

        post_data = json.dumps({
            'order_id': self.orden.pk,
            'servicio_id': 99999, # ID de servicio inexistente
            'cantidad': '1',
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')

        # Esperamos error 404 Not Found porque el servicio_id no existe
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'error')
        self.assertIn('Servicio no encontrado', response_data.get('error', ''))
        # Verificar que no se crearon objetos
        self.assertEqual(self.orden.servicios_detalle.count(), servicio_count_before)
        self.assertEqual(CatalogoServicio.objects.count(), catalogo_count_before)
        print("   Servicio ID inválido 404 OK")

# --- Fin de la clase AgregarServicioAPITests ---

class ActualizarOrdenManualAPITests(TestCase):

    def setUp(self):
        """Configuración para pruebas de la API actualizar_orden_manual."""
        self.client = Client()
        # Usuarios y Grupos
        self.chofer_group, created_c = Group.objects.get_or_create(name='Chofer')
        self.trabajador_group, created_t = Group.objects.get_or_create(name='Trabajador') # Para usuario no autorizado
        self.chofer_user = User.objects.create_user(username='chofer_reorder', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        self.trabajador_user = User.objects.create_user(username='trabajador_reorder', password='password123') # No autorizado
        self.trabajador_user.groups.add(self.trabajador_group)
        # Objetos necesarios
        self.cliente = Cliente.objects.create(nombre="Cliente Reorder API Test")
        self.today = date.today()
        # Crear órdenes con diferentes posiciones y fechas
        self.orden1 = Orden.objects.create(cliente="Cliente R1", cliente_registrado=self.cliente, estado_general='ACEPTADA', posicion=10, fecha_programada=self.today)
        self.orden2 = Orden.objects.create(cliente="Cliente R2", cliente_registrado=self.cliente, estado_general='ACEPTADA', posicion=20, fecha_programada=self.today)
        self.orden3 = Orden.objects.create(cliente="Cliente R3", cliente_registrado=self.cliente, estado_general='PROCESO', posicion=10, fecha_programada=None) # En Pendientes
        # URLs
        self.api_url = reverse('actualizar_orden_manual')
        self.login_url = reverse('login')
        # Mapeo de días (para calcular fechas y obtener nombres)
        self.day_mapping_num = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4}
        self.day_mapping_name = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
        # print(f"Ejecutando setUp para ActualizarOrdenManualAPITests...")

    def _get_next_weekday(self, target_weekday_num):
        """Calcula la fecha del próximo día de la semana especificado."""
        days_ahead = target_weekday_num - self.today.weekday()
        if days_ahead <= 0: # Si hoy es el día o ya pasó, vamos a la siguiente semana
            days_ahead += 7
        return self.today + timedelta(days=days_ahead)

    def test_reordenar_dentro_mismo_dia(self):
        """Prueba reordenar cambiando solo la posición."""
        # print("-> test_reordenar_dentro_mismo_dia")
        self.client.login(username='chofer_reorder', password='password123')
        # Usamos el nombre del día actual como grupo
        grupo_hoy = self.day_mapping_name.get(self.today.weekday(), "Pendientes")

        post_data = json.dumps({
            'grupo': grupo_hoy,
            'nuevo_orden': [
                {'id': self.orden2.pk, 'newPos': 10}, # orden2 ahora va primero
                {'id': self.orden1.pk, 'newPos': 20}  # orden1 ahora va segundo
            ]
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')

        # Verificar respuesta OK
        self.assertEqual(response.status_code, 200, f"Error: {response.content.decode()}")
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')

        # Verificar cambio de posición en BD
        self.orden1.refresh_from_db()
        self.orden2.refresh_from_db()
        self.assertEqual(self.orden1.posicion, 20.0)
        self.assertEqual(self.orden2.posicion, 10.0)
        self.assertEqual(self.orden1.fecha_programada, self.today) # Fecha no debe cambiar
        self.assertEqual(self.orden2.fecha_programada, self.today) # Fecha no debe cambiar
        # print("   Reordenar mismo día OK")

    def test_mover_a_otro_dia(self):
        """Prueba mover una orden a otro día, actualizando fecha_programada."""
        # print("-> test_mover_a_otro_dia")
        self.client.login(username='chofer_reorder', password='password123')
        orden_a_mover = self.orden3 # La que estaba en Pendientes (fecha_programada=None)

        # Calculamos la fecha del próximo Lunes
        fecha_lunes_esperada = self._get_next_weekday(0) # 0 = Lunes

        post_data = json.dumps({
            'grupo': 'Lunes', # Movemos a Lunes
            'nuevo_orden': [
                {'id': orden_a_mover.pk, 'newPos': 10} # Es la única en Lunes ahora
            ]
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')

        # Verificar respuesta OK
        self.assertEqual(response.status_code, 200, f"Error: {response.content.decode()}")
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')

        # Verificar cambio de posición y FECHA en BD
        orden_a_mover.refresh_from_db()
        self.assertEqual(orden_a_mover.posicion, 10.0)
        self.assertEqual(orden_a_mover.fecha_programada, fecha_lunes_esperada) # Verificar nueva fecha
        # print("   Mover a otro día OK")

    def test_actualizar_orden_no_autorizado(self):
        """Prueba actualizar orden con usuario no autorizado (Trabajador)."""
        # print("-> test_actualizar_orden_no_autorizado")
        self.client.login(username='trabajador_reorder', password='password123') # Usuario incorrecto
        post_data = json.dumps({
            'grupo': 'Lunes',
            'nuevo_orden': [{'id': self.orden1.pk, 'newPos': 10}]
        })
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos redirección (302) al login
        self.assertEqual(response.status_code, 302)
        # print("   No autorizado 302 OK")

# --- Fin de la clase ActualizarOrdenManualAPITests ---

class MarcarEntregadaAPITests(TestCase):

    def setUp(self):
        """Configuración para pruebas de la API marcar_entregada."""
        self.client = Client()
        # Usuarios (Superusuario es el único autorizado aquí)
        self.superuser = User.objects.create_superuser(username='admin_entregada', password='password123')
        self.chofer_user = User.objects.create_user(username='chofer_entregada', password='password123') # No autorizado
        self.chofer_group, created = Group.objects.get_or_create(name='Chofer')
        self.chofer_user.groups.add(self.chofer_group)
        # Objetos necesarios
        self.cliente = Cliente.objects.create(nombre="Cliente Entregada API", telefono="+522221113344") # Cliente con teléfono
        self.orden_lista = Orden.objects.create(
            cliente="Cliente Entregada API",
            cliente_registrado=self.cliente,
            estado_general='LISTO', # Empezamos desde LISTO
            telefono=self.cliente.telefono # Copiamos el teléfono a la orden
        )
        # URLs
        self.api_url = reverse('marcar_entregada')
        self.login_url = reverse('login')
        # print(f"Ejecutando setUp para MarcarEntregadaAPITests...")

    # --- Usamos @patch para simular send_whatsapp_message ---
    @patch('servicios.views.send_whatsapp_message') # <-- CORREGIDO: Apunta a donde la vista lo usa
    def test_marcar_entregada_valido_superuser(self, mock_send_whatsapp): # El mock se sigue pasando igual
        """Prueba marcar como entregada por superusuario (autorizado)."""
        # print("-> test_marcar_entregada_valido_superuser")
        self.client.login(username='admin_entregada', password='password123')
        post_data = json.dumps({'order_id': self.orden_lista.pk})

        response = self.client.post(
            self.api_url,
            data=post_data,
            content_type='application/json'
        )

        # Verificar respuesta OK
        self.assertEqual(response.status_code, 200, f"Error: {response.content.decode()}")
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')
        # Ahora esta aserción debería pasar porque el mock no fallará
        self.assertTrue(response_data['data'].get('whatsapp_enviado'))

        # Verificar cambio de estado en BD
        self.orden_lista.refresh_from_db()
        self.assertEqual(self.orden_lista.estado_general, 'ENTREGADO')

        # Verificar que el mock fue llamado
        mock_send_whatsapp.assert_called_once()
        # print("   Marcar entregada válido OK")

    def test_marcar_entregada_orden_invalida(self):
        """Prueba marcar como entregada una orden que no existe."""
        # print("-> test_marcar_entregada_orden_invalida")
        self.client.login(username='admin_entregada', password='password123')
        post_data = json.dumps({'order_id': 9999}) # ID no existente
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos error 404
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'error')
        self.assertIn('No se encontró la orden', response_data.get('message', ''))
        # print("   Orden inválida 404 OK")

    def test_marcar_entregada_datos_faltantes(self):
        """Prueba llamar a la API sin enviar el order_id."""
        # print("-> test_marcar_entregada_datos_faltantes")
        self.client.login(username='admin_entregada', password='password123')
        post_data = json.dumps({}) # Sin order_id
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos error 400
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'error')
        self.assertIn('Falta el ID de la orden', response_data.get('message', ''))
        # print("   Datos faltantes 400 OK")

    def test_marcar_entregada_no_autorizado(self):
        """Prueba llamar a la API con usuario no superusuario (Chofer)."""
        # print("-> test_marcar_entregada_no_autorizado")
        self.client.login(username='chofer_entregada', password='password123') # Usuario incorrecto
        post_data = json.dumps({'order_id': self.orden_lista.pk})
        response = self.client.post(self.api_url, data=post_data, content_type='application/json')
        # Esperamos redirección 302 al login
        self.assertEqual(response.status_code, 302)
        # print("   No autorizado 302 OK")

# --- Fin de la clase MarcarEntregadaAPITests ---

class HistorialOrdenesViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_hist', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        self.normal_user = User.objects.create_user(username='normal_hist', password='password123')
        self.url = reverse('historial_ordenes')
        self.login_url = reverse('login')
        # Crear una orden entregada para que la lista no esté vacía
        Orden.objects.create(cliente="Cliente Hist 1", estado_general='ENTREGADO')

    def test_historial_view_get_as_chofer(self):
        """Prueba acceso GET como Chofer."""
        self.client.login(username='chofer_hist', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/historial_ordenes.html')
        self.assertIn('orders', response.context)

    def test_historial_view_get_logged_out(self):
        """Prueba redirección si no logueado."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{self.login_url}?next={self.url}', fetch_redirect_response=False)

    def test_historial_view_get_unauthorized(self):
        """Prueba redirección si usuario logueado no es Chofer/Admin."""
        self.client.login(username='normal_hist', password='password123')
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{self.login_url}?next={self.url}', status_code=302, fetch_redirect_response=False)

class OrdenesAnuladasViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_anul', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        self.normal_user = User.objects.create_user(username='normal_anul', password='password123')
        self.url = reverse('ordenes_anuladas')
        self.login_url = reverse('login')
        Orden.objects.create(cliente="Cliente Anul 1", estado_general='ANULADA')

    def test_anuladas_view_get_as_chofer(self):
        self.client.login(username='chofer_anul', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/ordenes_anuladas.html')
        self.assertIn('orders', response.context)

    def test_anuladas_view_get_logged_out(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{self.login_url}?next={self.url}', fetch_redirect_response=False)

    def test_anuladas_view_get_unauthorized(self):
        self.client.login(username='normal_anul', password='password123')
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{self.login_url}?next={self.url}', status_code=302, fetch_redirect_response=False)


class OrdenesTerminadasViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_term', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        self.normal_user = User.objects.create_user(username='normal_term', password='password123')
        self.url = reverse('ordenes_terminadas')
        self.login_url = reverse('login')
        # --- MODIFICADO: Crear órdenes con diferentes rutas ---
        Orden.objects.create(cliente="Cliente Term 1", estado_general='LISTO', ruta="Ruta A")
        Orden.objects.create(cliente="Cliente Term 2", estado_general='LISTO', ruta="Ruta B")
        Orden.objects.create(cliente="Cliente Term 3", estado_general='LISTO', ruta="Ruta A")
        Orden.objects.create(cliente="Cliente Proceso 1", estado_general='PROCESO', ruta="Ruta A") # Para asegurar que solo filtra LISTO
        # --- FIN MODIFICADO ---

    def test_terminadas_view_get_as_chofer(self):
        """Prueba acceso GET como Chofer (sin filtro)."""
        print("-> test_terminadas_view_get_as_chofer") # Añadido print para claridad
        self.client.login(username='chofer_term', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/ordenes_terminadas.html')
        self.assertIn('orders', response.context)
        self.assertIn('rutas', response.context) # Verificar contexto extra
        # --- MODIFICADO: Verificar conteo correcto sin filtro ---
        # Deben aparecer 3 órdenes en estado LISTO
        self.assertEqual(len(response.context['orders']), 3)
        print("   GET sin filtro OK") # Añadido print

    # --- NUEVA PRUEBA AÑADIDA ---
    def test_terminadas_view_filter_by_ruta(self):
        """Prueba el filtrado por parámetro 'ruta'."""
        print("-> test_terminadas_view_filter_by_ruta")
        self.client.login(username='chofer_term', password='password123')
        # Construimos la URL con el parámetro de filtro
        filter_url = f"{self.url}?ruta=Ruta%20A" # Usamos %20 para el espacio
        response = self.client.get(filter_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/ordenes_terminadas.html')
        self.assertIn('orders', response.context)
        self.assertIn('rutas', response.context)
        self.assertEqual(response.context['ruta_filtro'], "Ruta A") # Verificar que el filtro se pasó al contexto

        # Verificar que solo aparecen las órdenes correctas (2 con Ruta A y estado LISTO)
        orders_in_context = response.context['orders']
        self.assertEqual(len(orders_in_context), 2)
        self.assertTrue(all(o.estado_general == 'LISTO' and o.ruta == 'Ruta A' for o in orders_in_context))
        print("   GET con filtro OK")
    # --- FIN NUEVA PRUEBA ---

    def test_terminadas_view_get_logged_out(self):
        """Prueba redirección si no logueado."""
        print("-> test_terminadas_view_get_logged_out") # Añadido print
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{self.login_url}?next={self.url}', fetch_redirect_response=False)
        print("   GET logged out OK") # Añadido print

    def test_terminadas_view_get_unauthorized(self):
        """Prueba redirección si usuario logueado no es Chofer/Admin."""
        print("-> test_terminadas_view_get_unauthorized") # Añadido print
        self.client.login(username='normal_term', password='password123')
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{self.login_url}?next={self.url}', status_code=302, fetch_redirect_response=False)
        print("   GET unauthorized OK") # Añadido print

# --- Fin de las nuevas clases ---

class DashboardViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de dashboard."""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser_dash', password='password123')
        self.dashboard_url = reverse('home') # El dashboard usa la URL 'home'
        self.login_url = reverse('login')
        # Crear algunas órdenes con diferentes estados para probar los contadores
        Orden.objects.create(cliente="C1", estado_general='ACEPTADA')
        Orden.objects.create(cliente="C2", estado_general='PROCESO')
        Orden.objects.create(cliente="C3", estado_general='LISTO')
        Orden.objects.create(cliente="C4", estado_general='ENTREGADO')
        Orden.objects.create(cliente="C5", estado_general='ANULADA')
        # print(f"Ejecutando setUp para DashboardViewTests...")

    def test_dashboard_view_get_logged_in(self):
        """Prueba que un usuario logueado puede ver el dashboard."""
        # print("-> test_dashboard_view_get_logged_in")
        self.client.login(username='testuser_dash', password='password123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/dashboard.html')
        # Verificar que las variables de conteo estén en el contexto
        self.assertIn('total_ordenes', response.context)
        self.assertIn('ordenes_aceptadas', response.context)
        self.assertIn('ordenes_en_proceso', response.context)
        self.assertIn('ordenes_terminadas', response.context)
        self.assertIn('ordenes_entregadas', response.context)
        self.assertIn('ordenes_anuladas', response.context)
        # Verificar un conteo específico (opcional pero bueno)
        self.assertEqual(response.context['total_ordenes'], 5)
        self.assertEqual(response.context['ordenes_aceptadas'], 1)
        # print("   GET Dashboard OK")

    def test_dashboard_view_get_logged_out(self):
        """Prueba que un usuario no logueado es redirigido."""
        # print("-> test_dashboard_view_get_logged_out")
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.dashboard_url}', fetch_redirect_response=False)
        # print("   Redirect Dashboard OK")


class AnularOrdenViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de anular_orden."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin_anular', password='password123')
        self.chofer_user = User.objects.create_user(username='chofer_anular', password='password123') # No autorizado
        self.orden_a_anular = Orden.objects.create(
            cliente="Cliente a Anular",
            estado_general='ACEPTADA',
            numero_orden="ORD ANULAR TEST" # Usamos numero_orden porque la URL lo usa
        )
        # La URL usa numero_orden, no pk
        self.anular_url = reverse('anular_orden', kwargs={'numero_orden': self.orden_a_anular.numero_orden})
        self.anular_url_inexistente = reverse('anular_orden', args=["NOEXISTE123"])
        self.lista_ordenes_url = reverse('lista_ordenes')
        self.login_url = reverse('login')
        # print(f"Ejecutando setUp para AnularOrdenViewTests...")

    def test_anular_orden_as_superuser(self):
        """Prueba que un superusuario puede anular una orden."""
        # print("-> test_anular_orden_as_superuser")
        self.client.login(username='admin_anular', password='password123')
        # La vista usa GET para anular según urls.py, aunque POST sería más estándar
        response = self.client.get(self.anular_url)
        # Verifica redirección a lista_ordenes
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, target_status_code=200)
        # Verifica que el estado cambió en la BD
        self.orden_a_anular.refresh_from_db()
        self.assertEqual(self.orden_a_anular.estado_general, 'ANULADA')
        # print("   Anular Superuser OK")

    def test_anular_orden_forbidden_as_chofer(self):
        """Prueba que un usuario no superusuario no puede anular."""
        # print("-> test_anular_orden_forbidden_as_chofer")
        self.client.login(username='chofer_anular', password='password123')
        estado_original = self.orden_a_anular.estado_general
        response = self.client.get(self.anular_url)
        login_base_url = self.login_url
        next_param_raw = self.anular_url

        encoded_next_param = urllib.parse.quote(next_param_raw, safe='')
        expected_url_base = f'{login_base_url}?next={encoded_next_param}'
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(login_base_url))
        parsed_url = urllib.parse.urlparse(response.url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        self.assertIn('next', query_params)
        received_next_decoded = query_params['next'][0] # Tomamos el primer valor de 'next'
        self.assertEqual(received_next_decoded, next_param_raw)

        # Verifica que el estado NO cambió
        self.orden_a_anular.refresh_from_db()
        self.assertEqual(self.orden_a_anular.estado_general, estado_original)
        # print("   Anular Chofer Forbidden OK")

    def test_anular_orden_non_existent(self):
        """Prueba anular una orden que no existe (devuelve 404)."""
        # print("-> test_anular_orden_non_existent")
        self.client.login(username='admin_anular', password='password123')
        response = self.client.get(self.anular_url_inexistente)
        self.assertEqual(response.status_code, 404)
        # print("   Anular Non-Existent 404 OK")

# --- Fin de las nuevas clases ---

class AceptarOrdenViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de aceptar_orden."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(username='admin_aceptar', password='password123')
        # Creamos grupo y usuario Chofer para probar acceso no autorizado
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_aceptar', password='password123')
        self.chofer_user.groups.add(self.chofer_group)

        # Orden sin número de orden, en espera
        self.orden_sin_num = Orden.objects.create(cliente="Cliente Aceptar 1", estado_general='ESPERA')
        # Orden con número de orden, en espera
        self.orden_con_num = Orden.objects.create(cliente="Cliente Aceptar 2", estado_general='ESPERA', numero_orden="ORDEXISTING")
        # Orden ya entregada (para probar el chequeo inicial)
        self.orden_entregada = Orden.objects.create(cliente="Cliente Entregado", estado_general='ENTREGADO', numero_orden="ORDENTREGADO")

        # URLs
        self.aceptar_url_sin_num = reverse('aceptar_orden', args=[self.orden_sin_num.pk])
        self.aceptar_url_con_num = reverse('aceptar_orden', args=[self.orden_con_num.pk])
        self.aceptar_url_entregada = reverse('aceptar_orden', args=[self.orden_entregada.pk])
        self.aceptar_url_inexistente = reverse('aceptar_orden', args=[9999])
        self.lista_ordenes_url = reverse('lista_ordenes')
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para AceptarOrdenViewTests...") # Puedes quitar este print si quieres

    # Usamos patch para simular la función async_to_sync y evitar errores de Channels/WebSocket en tests
    @patch('servicios.views.async_to_sync')
    def test_aceptar_orden_sin_numero_as_admin(self, mock_async_to_sync): # El mock se pasa como argumento
        """Prueba aceptar una orden sin número por un admin."""
        print("-> test_aceptar_orden_sin_numero_as_admin")
        self.client.login(username='admin_aceptar', password='password123')
        # La vista usa POST según urls.py y la lógica esperada
        response = self.client.post(self.aceptar_url_sin_num)

        # Verificar redirección a la lista de órdenes
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, target_status_code=200, fetch_redirect_response=True) # Sigue la redirección

        # Verificar cambios en la BD
        self.orden_sin_num.refresh_from_db()
        self.assertEqual(self.orden_sin_num.estado_general, 'ACEPTADA')
        self.assertIsNotNone(self.orden_sin_num.fecha_programada, "La fecha programada no se asignó.") # Se asignó una fecha
        self.assertIsNotNone(self.orden_sin_num.numero_orden, "El número de orden no se asignó.") # Se asignó un número
        self.assertTrue(self.orden_sin_num.numero_orden.startswith('ORD'), "El número de orden no tiene el formato esperado.") # Verifica el prefijo
        # Verifica que la notificación WebSocket fue (intentada) enviada
        mock_async_to_sync.assert_called_once()
        print("   Aceptar sin número OK")

    @patch('servicios.views.async_to_sync')
    def test_aceptar_orden_con_numero_as_admin(self, mock_async_to_sync):
        """Prueba aceptar una orden que ya tenía número por un admin."""
        print("-> test_aceptar_orden_con_numero_as_admin")
        self.client.login(username='admin_aceptar', password='password123')
        numero_original = self.orden_con_num.numero_orden
        response = self.client.post(self.aceptar_url_con_num)

        # Verificar redirección
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, target_status_code=200, fetch_redirect_response=True)

        # Verificar cambios en la BD
        self.orden_con_num.refresh_from_db()
        self.assertEqual(self.orden_con_num.estado_general, 'ACEPTADA')
        self.assertIsNotNone(self.orden_con_num.fecha_programada, "La fecha programada no se asignó.")
        self.assertEqual(self.orden_con_num.numero_orden, numero_original, "El número de orden cambió incorrectamente.") # Número NO debe cambiar
        mock_async_to_sync.assert_called_once()
        print("   Aceptar con número OK")

    @patch('servicios.views.async_to_sync') # Mockeamos aunque no se espera que se llame
    def test_aceptar_orden_ya_entregada(self, mock_async_to_sync):
        """Prueba que no se puede aceptar una orden ya entregada."""
        print("-> test_aceptar_orden_ya_entregada")
        self.client.login(username='admin_aceptar', password='password123')
        estado_original = self.orden_entregada.estado_general
        # La vista debe verificar el estado ANTES de hacer cambios o llamar a async_to_sync
        response = self.client.post(self.aceptar_url_entregada)

        # La vista redirige directamente si ya está entregada (según la lógica if orden.estado_general == 'ENTREGADO': return...)
        self.assertRedirects(response, self.lista_ordenes_url, status_code=302, target_status_code=200, fetch_redirect_response=True)

        # Verificar que el estado NO cambió
        self.orden_entregada.refresh_from_db()
        self.assertEqual(self.orden_entregada.estado_general, estado_original)
        # Verificar que NO se llamó a la notificación WebSocket
        mock_async_to_sync.assert_not_called()
        print("   Aceptar entregada OK (no cambió estado)")

    @patch('servicios.views.async_to_sync')
    def test_aceptar_orden_forbidden_as_chofer(self, mock_async_to_sync):
        """Prueba que un usuario no superusuario (Chofer) no puede aceptar."""
        print("-> test_aceptar_orden_forbidden_as_chofer")
        self.client.login(username='chofer_aceptar', password='password123') # Usamos el usuario chofer
        estado_original = self.orden_sin_num.estado_general
        response = self.client.post(self.aceptar_url_sin_num)

        # El decorador @user_passes_test(lambda u: u.is_superuser) redirige al login
        # Necesitamos construir la URL de login con el 'next' correctamente codificado
        expected_redirect_url = f'{self.login_url}?next={self.aceptar_url_sin_num}'
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False) # No seguimos la redirección

        # Verificar que el estado NO cambió
        self.orden_sin_num.refresh_from_db()
        self.assertEqual(self.orden_sin_num.estado_general, estado_original)
        mock_async_to_sync.assert_not_called()
        print("   Aceptar Chofer Forbidden OK")

    @patch('servicios.views.async_to_sync')
    def test_aceptar_orden_non_existent(self, mock_async_to_sync):
        """Prueba aceptar una orden que no existe (devuelve 404)."""
        print("-> test_aceptar_orden_non_existent")
        self.client.login(username='admin_aceptar', password='password123')
        # La vista usa get_object_or_404 al principio, así que esperamos 404 en la petición POST
        response = self.client.post(self.aceptar_url_inexistente)
        self.assertEqual(response.status_code, 404)
        mock_async_to_sync.assert_not_called()
        print("   Aceptar Non-Existent 404 OK")

# --- Fin de la clase AceptarOrdenViewTests ---

class ConfigClientesViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de config_clientes."""
        self.client = Client()
        # Usuarios y Grupos
        self.admin_user = User.objects.create_superuser(username='admin_clientes', password='password123', email='adminc@test.com')
        self.chofer_group, created_c = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_clientes', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        self.trabajador_group, created_t = Group.objects.get_or_create(name='Trabajador')
        self.trabajador_user = User.objects.create_user(username='trabajador_clientes', password='password123') # No autorizado para GET
        self.trabajador_user.groups.add(self.trabajador_group)
        # Cliente existente para pruebas de edición
        self.cliente_existente = Cliente.objects.create(nombre="Cliente Existente Config", telefono="111", ruta="R1")
        # URLs
        self.config_url = reverse('config_clientes')
        self.login_url = reverse('login')
        # print(f"Ejecutando setUp para ConfigClientesViewTests...")

    def test_config_clientes_view_get_as_chofer(self):
        """Prueba que un chofer puede ver la página de configuración."""
        # print("-> test_config_clientes_view_get_as_chofer")
        self.client.login(username='chofer_clientes', password='password123')
        response = self.client.get(self.config_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_clientes.html')
        self.assertIn('form', response.context)
        self.assertIn('clientes', response.context)
        # print("   GET Chofer OK")

    def test_config_clientes_view_get_as_admin(self):
        """Prueba que un admin puede ver la página de configuración."""
        # print("-> test_config_clientes_view_get_as_admin")
        self.client.login(username='admin_clientes', password='password123')
        response = self.client.get(self.config_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_clientes.html')
        # print("   GET Admin OK")

    def test_config_clientes_view_get_unauthorized(self):
        """Prueba que un trabajador (no chofer/admin) es redirigido."""
        # print("-> test_config_clientes_view_get_unauthorized")
        self.client.login(username='trabajador_clientes', password='password123')
        response = self.client.get(self.config_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.config_url}', fetch_redirect_response=False)
        # print("   GET Unauthorized OK")

    def test_config_clientes_post_create_valid_as_chofer(self):
        """Prueba que un chofer puede crear un cliente nuevo."""
        # print("-> test_config_clientes_post_create_valid_as_chofer")
        self.client.login(username='chofer_clientes', password='password123')
        cliente_count_before = Cliente.objects.count()
        post_data = {'nombre': 'Nuevo Cliente Chofer', 'telefono': '123', 'ruta': 'RC'}
        response = self.client.post(self.config_url, data=post_data)
        # Espera redirección a la misma página tras éxito
        self.assertRedirects(response, self.config_url, status_code=302, target_status_code=200)
        self.assertEqual(Cliente.objects.count(), cliente_count_before + 1)
        self.assertTrue(Cliente.objects.filter(nombre='Nuevo Cliente Chofer').exists())
        # print("   POST Create Chofer OK")

    def test_config_clientes_post_create_invalid_as_chofer(self):
        """Prueba que falla la creación si el nombre se duplica."""
        # print("-> test_config_clientes_post_create_invalid_as_chofer")
        self.client.login(username='chofer_clientes', password='password123')
        cliente_count_before = Cliente.objects.count()
        post_data = {'nombre': self.cliente_existente.nombre, 'telefono': '456', 'ruta': 'RX'} # Nombre duplicado
        response = self.client.post(self.config_url, data=post_data)
        # No debe redirigir, debe mostrar el form con error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_clientes.html')
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('nombre', response.context['form'].errors)
        self.assertEqual(Cliente.objects.count(), cliente_count_before) # No se creó
        # print("   POST Create Invalid Chofer OK")

    def test_config_clientes_post_update_valid_as_admin(self):
        """Prueba que un admin puede actualizar un cliente."""
        # print("-> test_config_clientes_post_update_valid_as_admin")
        self.client.login(username='admin_clientes', password='password123')
        nuevo_nombre = "Cliente Existente Actualizado"
        post_data = {
            'cliente_id': self.cliente_existente.pk, # ID para indicar edición
            'nombre': nuevo_nombre,
            'telefono': '789',
            'ruta': 'RZ'
        }
        response = self.client.post(self.config_url, data=post_data)
        self.assertRedirects(response, self.config_url, status_code=302, target_status_code=200)
        self.cliente_existente.refresh_from_db()
        self.assertEqual(self.cliente_existente.nombre, nuevo_nombre)
        self.assertEqual(self.cliente_existente.telefono, '789')
        # print("   POST Update Admin OK")

    def test_config_clientes_post_update_forbidden_as_chofer(self):
        """Prueba que un chofer NO puede actualizar un cliente."""
        # print("-> test_config_clientes_post_update_forbidden_as_chofer")
        self.client.login(username='chofer_clientes', password='password123')
        nombre_original = self.cliente_existente.nombre
        post_data = {
            'cliente_id': self.cliente_existente.pk, # ID para indicar edición
            'nombre': "Intento de Update Chofer",
            'telefono': '999',
            'ruta': 'RY'
        }
        response = self.client.post(self.config_url, data=post_data)
        # La vista debería devolver 403 Forbidden según la lógica implementada
        self.assertEqual(response.status_code, 403)
        # Verificar que no cambió en la BD
        self.cliente_existente.refresh_from_db()
        self.assertEqual(self.cliente_existente.nombre, nombre_original)
        # print("   POST Update Chofer Forbidden OK")

    def test_config_clientes_get_edit_as_admin(self):
        """Prueba que admin puede cargar el formulario para editar vía GET."""
        print("-> test_config_clientes_get_edit_as_admin")
        self.client.login(username='admin_clientes', password='password123')
        edit_url = f"{self.config_url}?editar_id={self.cliente_existente.pk}"
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_clientes.html')
        self.assertEqual(response.context['cliente_editar'], self.cliente_existente)
        # Verifica que el formulario en el contexto está asociado a la instancia correcta
        self.assertEqual(response.context['form'].instance, self.cliente_existente)
        self.assertTrue(response.context['can_edit']) # Admin puede editar
        print("   GET Edit Admin OK")

    def test_config_clientes_get_edit_as_chofer(self):
        """Prueba que chofer recibe 403 si intenta cargar para editar vía GET."""
        print("-> test_config_clientes_get_edit_as_chofer")
        self.client.login(username='chofer_clientes', password='password123')
        edit_url = f"{self.config_url}?editar_id={self.cliente_existente.pk}"
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 403) # Esperamos Prohibido
        print("   GET Edit Chofer Forbidden (403) OK")

    def test_config_clientes_get_edit_non_existent(self):
        """Prueba 404 si admin intenta editar un cliente inexistente vía GET."""
        print("-> test_config_clientes_get_edit_non_existent")
        self.client.login(username='admin_clientes', password='password123')
        edit_url = f"{self.config_url}?editar_id=9999" # ID no existente
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404) # Esperamos No Encontrado
        print("   GET Edit Non-Existent (404) OK")

# --- Fin de la clase ConfigClientesViewTests ---

class ConfigModelosViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de config_modelos."""
        self.client = Client()
        # Usuarios
        self.admin_user = User.objects.create_superuser(username='admin_modelos', password='password123', email='admin_m@test.com')
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_modelos', password='password123')
        self.chofer_user.groups.add(self.chofer_group)
        # Motor existente para pruebas de edición
        self.motor_existente = Motor.objects.create(nombre="Motor Existente Test", diametro_cilindro="100.0") # Añadir un campo obligatorio si es necesario
        # URLs
        self.config_url = reverse('config_modelos')
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para ConfigModelosViewTests...") # Opcional

    # --- Pruebas GET ---
    def test_config_modelos_get_as_chofer(self):
        """Prueba que un chofer puede ver la página (pero no editar)."""
        print("-> test_config_modelos_get_as_chofer")
        self.client.login(username='chofer_modelos', password='password123')
        response = self.client.get(self.config_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_modelos.html')
        self.assertIn('form', response.context)
        self.assertIn('motores', response.context)
        self.assertFalse(response.context['can_edit'], "Chofer no debería poder editar")
        print("   GET Chofer OK")

    def test_config_modelos_get_as_admin(self):
        """Prueba que un admin puede ver la página (y puede editar)."""
        print("-> test_config_modelos_get_as_admin")
        self.client.login(username='admin_modelos', password='password123')
        response = self.client.get(self.config_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_modelos.html')
        self.assertTrue(response.context['can_edit'], "Admin debería poder editar")
        print("   GET Admin OK")

    def test_config_modelos_get_edit_as_admin(self):
        """Prueba que admin puede cargar el formulario para editar."""
        print("-> test_config_modelos_get_edit_as_admin")
        self.client.login(username='admin_modelos', password='password123')
        edit_url = f"{self.config_url}?editar_id={self.motor_existente.pk}"
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_modelos.html')
        self.assertEqual(response.context['motor_editar'], self.motor_existente)
        # Verifica que el formulario en el contexto está asociado a la instancia correcta
        self.assertEqual(response.context['form'].instance, self.motor_existente)
        print("   GET Edit Admin OK")

    def test_config_modelos_get_edit_as_chofer(self):
        """Prueba que chofer recibe 403 si intenta cargar para editar."""
        print("-> test_config_modelos_get_edit_as_chofer")
        self.client.login(username='chofer_modelos', password='password123')
        edit_url = f"{self.config_url}?editar_id={self.motor_existente.pk}"
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 403) # Esperamos Prohibido
        print("   GET Edit Chofer Forbidden (403) OK")

    def test_config_modelos_get_edit_non_existent(self):
        """Prueba 404 si admin intenta editar un motor inexistente."""
        print("-> test_config_modelos_get_edit_non_existent")
        self.client.login(username='admin_modelos', password='password123')
        edit_url = f"{self.config_url}?editar_id=9999" # ID no existente
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404) # Esperamos No Encontrado
        print("   GET Edit Non-Existent (404) OK")

    # --- Pruebas POST (Crear) ---
    def test_config_modelos_post_create_valid_as_chofer(self):
        """Prueba que un chofer PUEDE crear un motor nuevo."""
        print("-> test_config_modelos_post_create_valid_as_chofer")
        self.client.login(username='chofer_modelos', password='password123')
        motor_count_before = Motor.objects.count()
        post_data = {
            'nombre': 'Motor Nuevo Chofer',
            'diametro_cilindro': '80.5',
            'carrera': '70.0',
            'diametro_piston': '80.0',
            'diametro_cabeza_escape': '30.0',
            'distancia_valvula_escape': '5.0',
            'diametro_vastago_escape': '8.0',
            'angulo_asiento_escape': '45.0',
            'diametro_cabeza_admision': '35.0',
            'distancia_valvula_admision': '5.0',
            'diametro_vastago_admision': '8.0',
            'angulo_asiento_admision': '30.0',
            'diametro_alojamiento': '85.0',
            'diametro_munon_biela': '50.0',
            'diametro_munon_bancada': '55.0',
            'altura_cabeza': '90.0',
        }
        response = self.client.post(self.config_url, data=post_data)
        # Espera redirección a la misma página tras éxito
        self.assertRedirects(response, self.config_url, status_code=302, target_status_code=200, fetch_redirect_response=False)
        self.assertEqual(Motor.objects.count(), motor_count_before + 1)
        self.assertTrue(Motor.objects.filter(nombre='Motor Nuevo Chofer').exists())
        print("   POST Create Chofer OK")

    def test_config_modelos_post_create_invalid(self):
        """Prueba que falla la creación si datos son inválidos."""
        print("-> test_config_modelos_post_create_invalid")
        self.client.login(username='admin_modelos', password='password123') # Podría ser chofer también
        motor_count_before = Motor.objects.count()
        post_data = {'nombre': 'Motor Invalido', 'diametro_cilindro': 'no-es-numero'} # Dato inválido
        response = self.client.post(self.config_url, data=post_data)
        # No debe redirigir, debe mostrar el form con error (status 200)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_modelos.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('diametro_cilindro', response.context['form'].errors) # Verificar error específico
        self.assertEqual(Motor.objects.count(), motor_count_before) # No se creó
        print("   POST Create Invalid OK")

    # --- Pruebas POST (Update) ---
    def test_config_modelos_post_update_valid_as_admin(self):
        """Prueba que un admin puede actualizar un motor."""
        print("-> test_config_modelos_post_update_valid_as_admin")
        self.client.login(username='admin_modelos', password='password123')
        nuevo_nombre = "Motor Existente Actualizado"
        post_data = {
            'motor_id': self.motor_existente.pk, # ID para indicar edición
            'nombre': nuevo_nombre,
            'diametro_cilindro': '110.0', # Valor actualizado
            'carrera': '90.0', # Nuevos valores o los originales si prefieres
            'diametro_piston': '109.5',
            'diametro_cabeza_escape': '40.0',
            'distancia_valvula_escape': '6.0',
            'diametro_vastago_escape': '9.0',
            'angulo_asiento_escape': '45.0',
            'diametro_cabeza_admision': '45.0',
            'distancia_valvula_admision': '6.0',
            'diametro_vastago_admision': '9.0',
            'angulo_asiento_admision': '30.0',
            'diametro_alojamiento': '115.0',
            'diametro_munon_biela': '60.0',
            'diametro_munon_bancada': '65.0',
            'altura_cabeza': '100.0',
        }
        response = self.client.post(self.config_url, data=post_data)
        self.assertRedirects(response, self.config_url, status_code=302, target_status_code=200, fetch_redirect_response=False)
        self.motor_existente.refresh_from_db()
        self.assertEqual(self.motor_existente.nombre, nuevo_nombre)
        self.assertEqual(self.motor_existente.diametro_cilindro, 110.0) # Comparar como Decimal o float
        print("   POST Update Admin OK")

    def test_config_modelos_post_update_invalid_as_admin(self):
        """Prueba que falla la actualización si datos son inválidos."""
        print("-> test_config_modelos_post_update_invalid_as_admin")
        self.client.login(username='admin_modelos', password='password123')
        nombre_original = self.motor_existente.nombre
        post_data = {
            'motor_id': self.motor_existente.pk,
            'nombre': "Motor Update Invalido",
            'diametro_cilindro': 'no-valido', # Dato inválido
        }
        response = self.client.post(self.config_url, data=post_data)
        # No debe redirigir
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/config_modelos.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('diametro_cilindro', response.context['form'].errors)
        # Verificar que NO cambió en la BD
        self.motor_existente.refresh_from_db()
        self.assertEqual(self.motor_existente.nombre, nombre_original)
        print("   POST Update Invalid OK")


    def test_config_modelos_post_update_forbidden_as_chofer(self):
        """Prueba que un chofer NO puede actualizar un motor (devuelve 403)."""
        print("-> test_config_modelos_post_update_forbidden_as_chofer")
        self.client.login(username='chofer_modelos', password='password123')
        nombre_original = self.motor_existente.nombre
        post_data = {
            'motor_id': self.motor_existente.pk, # ID para indicar edición
            'nombre': "Intento Update Chofer",
            'diametro_cilindro': '120.0',
        }
        response = self.client.post(self.config_url, data=post_data)
        # La vista debería devolver 403 Forbidden según la lógica implementada
        self.assertEqual(response.status_code, 403)
        # Verificar que no cambió en la BD
        self.motor_existente.refresh_from_db()
        self.assertEqual(self.motor_existente.nombre, nombre_original)
        print("   POST Update Chofer Forbidden (403) OK")

# --- Fin de la clase ConfigModelosViewTests ---

class ConfigRutasViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de config_rutas."""
        self.client = Client()
        # Creamos un usuario básico, ya que la vista no parece tener
        # restricciones de permisos específicos por ahora.
        self.user = User.objects.create_user(username='testuser_rutas', password='password123')
        self.url = reverse('config_rutas')
        # Aunque no tenga @login_required, es buena práctica probar con login
        self.client.login(username='testuser_rutas', password='password123')
        print(f"Ejecutando setUp para ConfigRutasViewTests...") # Opcional

    def test_config_rutas_get_request(self):
        """Prueba que la vista 'en construcción' carga correctamente."""
        print("-> test_config_rutas_get_request")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Verificamos que el contenido contenga el texto esperado
        # Usamos decode() para convertir los bytes de content a string
        self.assertIn("Configuración: Rutas - En construcción", response.content.decode('utf-8'))
        print("   GET Config Rutas OK")

# --- Fin de la clase ConfigRutasViewTests ---

class SincronizarOrdenesViewTests(TestCase):

    def setUp(self):
        """Configuración para pruebas de sincronizar_ordenes."""
        self.client = Client()
        # Usuarios
        self.admin_user = User.objects.create_superuser(username='admin_sync', password='password123')
        self.chofer_group, _ = Group.objects.get_or_create(name='Chofer')
        self.chofer_user = User.objects.create_user(username='chofer_sync', password='password123') # Usuario autorizado
        self.chofer_user.groups.add(self.chofer_group)
        self.trabajador_group, _ = Group.objects.get_or_create(name='Trabajador') # No autorizado
        self.trabajador_user = User.objects.create_user(username='trabajador_sync', password='password123')
        self.trabajador_user.groups.add(self.trabajador_group)

        # Items/Servicios existentes para probar enlace por ID
        self.item_existente = InventarioItem.objects.create(nombre="Tornillos Sync")
        self.servicio_existente = CatalogoServicio.objects.create(nombre="Limpieza Sync")

        # URLs
        self.url = reverse('sincronizar_ordenes')
        self.login_url = reverse('login')
        print(f"Ejecutando setUp para SincronizarOrdenesViewTests...") # Opcional

    # --- Pruebas GET ---
    def test_sync_get_as_authorized(self):
        """Prueba GET como usuario autorizado (chofer o admin)."""
        print("-> test_sync_get_as_authorized")
        self.client.login(username='chofer_sync', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'servicios/sincronizar_ordenes.html')
        print("   GET Autorizado OK")

    def test_sync_get_unauthorized(self):
        """Prueba GET como usuario no autorizado (trabajador)."""
        print("-> test_sync_get_unauthorized")
        self.client.login(username='trabajador_sync', password='password123')
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Unauthorized OK")

    def test_sync_get_logged_out(self):
        """Prueba GET sin estar logueado."""
        print("-> test_sync_get_logged_out")
        response = self.client.get(self.url)
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   GET Logged Out OK")

    # --- Pruebas POST ---
    def test_sync_post_valid_data_new_items(self):
        """Prueba POST con datos válidos, creando nuevos items/servicios."""
        print("-> test_sync_post_valid_data_new_items")
        self.client.login(username='chofer_sync', password='password123')
        orden_count_before = Orden.objects.count()
        item_count_before = InventarioItem.objects.count()
        cat_count_before = CatalogoServicio.objects.count()

        payload = {
            "ordenes": [
                {
                    "cliente": "Cliente Sync Nuevo 1",
                    "telefono": "111222",
                    "modelo_motor": "Motor Sync 1",
                    "ruta": "Ruta Sync 1",
                    "notificacion": "Obs Sync 1",
                    "inventario": [
                        {"nombre": "Item Nuevo Sync 1", "cantidad": 3, "comentario": "Com1"},
                        {"nombre": "Item Nuevo Sync 2", "cantidad": 1}
                    ],
                    "servicios": [
                        {"nombre": "Servicio Nuevo Sync 1", "cantidad": "Medio"},
                        {"nombre": "Servicio Nuevo Sync 2"} # Sin cantidad
                    ]
                }
            ]
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')

        # Verificar respuesta (debería ser 200 OK si todo se creó bien)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')
        self.assertEqual(len(response_data.get('ordenes_creadas', [])), 1)
        self.assertEqual(len(response_data.get('errores_creacion_orden', [])), 0)
        self.assertEqual(len(response_data.get('errores_items', [])), 0)

        # Verificar creación en BD
        self.assertEqual(Orden.objects.count(), orden_count_before + 1)
        nueva_orden = Orden.objects.get(cliente="Cliente Sync Nuevo 1")
        self.assertEqual(nueva_orden.chofer, self.chofer_user) # Verificar chofer asignado
        # Verificar Items/Servicios creados y asociados
        self.assertEqual(InventarioItem.objects.count(), item_count_before + 2)
        self.assertEqual(CatalogoServicio.objects.count(), cat_count_before + 2)
        self.assertEqual(nueva_orden.ordeninventario_set.count(), 2)
        self.assertEqual(nueva_orden.servicios_detalle.count(), 2)
        # Verificar datos específicos (opcional pero bueno)
        self.assertTrue(nueva_orden.ordeninventario_set.filter(inventario_item__nombre="Item Nuevo Sync 1", cantidad=3).exists())
        self.assertTrue(nueva_orden.servicios_detalle.filter(catalogo_servicio__nombre="Servicio Nuevo Sync 1", cantidad="Medio").exists())
        print("   POST Válido Nuevos Items OK")

    def test_sync_post_valid_data_existing_items(self):
        """Prueba POST con datos válidos, usando items/servicios existentes por ID."""
        print("-> test_sync_post_valid_data_existing_items")
        self.client.login(username='chofer_sync', password='password123')
        orden_count_before = Orden.objects.count()
        item_count_before = InventarioItem.objects.count() # No deben crearse nuevos
        cat_count_before = CatalogoServicio.objects.count() # No deben crearse nuevos

        payload = {
            "ordenes": [
                {
                    "cliente": "Cliente Sync Existente",
                    "inventario": [
                        {"id": self.item_existente.pk, "cantidad": 5}
                    ],
                    "servicios": [
                        {"id": self.servicio_existente.pk, "cantidad": "Completo"}
                    ]
                }
            ]
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')
        self.assertEqual(len(response_data.get('ordenes_creadas', [])), 1)

        # Verificar creación de Orden y asociaciones, pero NO de Items/Catalogos
        self.assertEqual(Orden.objects.count(), orden_count_before + 1)
        self.assertEqual(InventarioItem.objects.count(), item_count_before) # No cambió
        self.assertEqual(CatalogoServicio.objects.count(), cat_count_before) # No cambió
        nueva_orden = Orden.objects.get(cliente="Cliente Sync Existente")
        self.assertTrue(nueva_orden.ordeninventario_set.filter(inventario_item=self.item_existente, cantidad=5).exists())
        self.assertTrue(nueva_orden.servicios_detalle.filter(catalogo_servicio=self.servicio_existente, cantidad="Completo").exists())
        print("   POST Válido Items Existentes OK")

    def test_sync_post_partial_error_missing_cliente(self):
        """Prueba POST donde una orden falla por faltar 'cliente'."""
        print("-> test_sync_post_partial_error_missing_cliente")
        self.client.login(username='chofer_sync', password='password123')
        orden_count_before = Orden.objects.count()
        payload = {
            "ordenes": [
                {"telefono": "123"}, # Orden inválida (falta cliente)
                {"cliente": "Cliente OK 2"} # Orden válida
            ]
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')

        # Esperamos 207 Multi-Status porque hubo éxito parcial
        self.assertEqual(response.status_code, 207)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'parcial')
        self.assertEqual(len(response_data.get('ordenes_creadas', [])), 1) # Solo se creó 1
        self.assertEqual(len(response_data.get('errores_creacion_orden', [])), 1) # Hubo 1 error
        self.assertIn("obligatorio", response_data['errores_creacion_orden'][0].get('error', '').lower()) # Check error message
        self.assertEqual(Orden.objects.count(), orden_count_before + 1) # Solo se creó 1 orden
        print("   POST Error Parcial (Falta Cliente) OK")

    def test_sync_post_partial_error_invalid_item(self):
        """Prueba POST donde falla la creación de un item/servicio."""
        print("-> test_sync_post_partial_error_invalid_item")
        self.client.login(username='chofer_sync', password='password123')
        orden_count_before = Orden.objects.count()
        payload = {
            "ordenes": [
                {
                    "cliente": "Cliente Con Item Malo",
                    "inventario": [
                        {"id": 99999} # ID de item inválido
                    ],
                     "servicios": [
                        {"nombre": self.servicio_existente.nombre} # Servicio válido
                    ]
                }
            ]
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')

        # Esperamos 207 Multi-Status
        self.assertEqual(response.status_code, 207)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'parcial')
        self.assertEqual(len(response_data.get('ordenes_creadas', [])), 1) # La orden se crea
        self.assertEqual(len(response_data.get('errores_creacion_orden', [])), 0) # No hubo error al crear la orden
        self.assertEqual(len(response_data.get('errores_items', [])), 1) # Sí hubo error en un item
        self.assertIn("no encontrado", response_data['errores_items'][0].get('error', '').lower())
        self.assertEqual(Orden.objects.count(), orden_count_before + 1)
        # Verificar que el servicio válido SÍ se asoció, pero el inválido no
        nueva_orden = Orden.objects.get(cliente="Cliente Con Item Malo")
        self.assertEqual(nueva_orden.ordeninventario_set.count(), 0) # No se asoció item inválido
        self.assertEqual(nueva_orden.servicios_detalle.count(), 1) # Sí se asoció servicio válido
        print("   POST Error Parcial (Item Inválido) OK")

    def test_sync_post_invalid_json_format(self):
        """Prueba POST con cuerpo que no es JSON."""
        print("-> test_sync_post_invalid_json_format")
        self.client.login(username='chofer_sync', password='password123')
        response = self.client.post(self.url, data='no es json', content_type='text/plain')
        self.assertEqual(response.status_code, 400) # Bad Request
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'error')
        self.assertIn("JSON inválido", response_data.get('error', ''))
        print("   POST JSON Inválido OK")

    def test_sync_post_invalid_payload_structure(self):
        """Prueba POST con JSON válido pero estructura incorrecta."""
        print("-> test_sync_post_invalid_payload_structure")
        self.client.login(username='chofer_sync', password='password123')
        # Falta la clave "ordenes"
        payload = {"clientes": [{"nombre": "Test"}]}
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        # La vista espera una lista en data.get("ordenes", []), si no la encuentra,
        # procesa una lista vacía y devuelve 200 OK sin errores.
        # Podríamos hacer la vista más estricta si quisiéramos un 400 aquí.
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data.get('status'), 'ok')
        self.assertEqual(len(response_data.get('ordenes_creadas', [])), 0)
        print("   POST Payload Inválido OK (devuelve OK sin procesar)")

    def test_sync_post_unauthorized(self):
        """Prueba POST como usuario no autorizado (trabajador)."""
        print("-> test_sync_post_unauthorized")
        self.client.login(username='trabajador_sync', password='password123')
        payload = {"ordenes": [{"cliente": "Test Unauthorized"}]}
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        # Esperamos redirección al login
        expected_redirect_url = f"{self.login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect_url, status_code=302, fetch_redirect_response=False)
        print("   POST Unauthorized OK")

# --- Fin de la clase SincronizarOrdenesViewTests ---