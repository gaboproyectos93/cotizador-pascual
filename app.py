import streamlit as st
import pandas as pd
import io
import os
import streamlit.components.v1 as components
from fpdf import FPDF
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image, ImageOps

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Pascual Parabrisas Cotizador", layout="wide", page_icon="🪟")

NOMBRE_HOJA_GOOGLE = "DB_Cotizador_Pascual"

def conectar_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else: return None
        client = gspread.authorize(creds)
        return client 
    except Exception as e: 
        st.error(f"❌ ERROR DE AUTENTICACIÓN: Revisa los Secrets. Detalle: {e}")
        return None

# ==========================================
# 2. LÓGICA DE CORRELATIVOS
# ==========================================
def obtener_y_registrar_correlativo(cliente_tipo, cliente_nombre, marca, modelo, ano, patente, condicion_pago, total):
    client = conectar_google_sheets()
    if client:
        try:
            spreadsheet = client.open(NOMBRE_HOJA_GOOGLE)
            try: worksheet_hist = spreadsheet.worksheet("Historial")
            except:
                worksheet_hist = spreadsheet.add_worksheet(title="Historial", rows="1000", cols="10")
                worksheet_hist.append_row(["Fecha", "Hora", "Correlativo", "Tipo Cliente", "Nombre Cliente", "Marca", "Modelo", "Año", "Patente", "Forma Pago", "Monto Total"])
            
            datos = worksheet_hist.get_all_values()
            numero_actual = len(datos) 
            correlativo_str = str(numero_actual)
            
            ahora = datetime.now()
            worksheet_hist.append_row([ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), correlativo_str, cliente_tipo.upper(), cliente_nombre.upper(), marca.upper(), modelo.upper(), ano, patente.upper(), condicion_pago.upper(), total])
            return correlativo_str
        except Exception as e: 
            return "ERR"
    else: return "OFFLINE"

# ==========================================
# 3. DATOS DE LA EMPRESA Y ESTILOS
# ==========================================
EMPRESA_NOMBRE = "PASCUAL PARABRISAS"
EMPRESA_TITULAR = "Venta e Instalación de Cristales Automotrices"
RUT_EMPRESA = "8810453-6" 
DIRECCION = "Caupolicán 0320, Temuco" 

# Tono Naranja Intenso
COLOR_HEX = "#FF5200"
NARANJA_PASCUAL = (255, 82, 0) 

# Inyectamos CSS para pintar la App de Naranjo
st.markdown(f"""
<style>
    .stContainer {{ border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 10px; margin-bottom: 5px; }}
    div[data-testid="stNumberInput"] input {{ max-width: 150px; text-align: center; }}
    input[type=number]::-webkit-inner-spin-button {{ -webkit-appearance: none; margin: 0; }}
    
    .stButton > button[kind="primary"] {{
        background-color: {COLOR_HEX} !important;
        border-color: {COLOR_HEX} !important;
        color: white !important;
        font-weight: bold;
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: #E04800 !important;
        border-color: #E04800 !important;
    }}
    
    .stTabs [aria-selected="true"] {{ background-color: {COLOR_HEX} !important; color: white !important; border-radius: 4px;}}
    div[data-testid="stRadio"] > label {{ font-weight: bold; color: {COLOR_HEX}; }}
</style>
""", unsafe_allow_html=True)

LISTA_ASEGURADORAS = ["--- Seleccione Compañía ---", "BCI Seguros", "Liberty Seguros", "Mapfre", "HDI Seguros", "Consorcio", "Chilena Consolidada", "Reale Seguros", "Sura", "Zenit", "Unnio", "Otra..."]
LISTA_MARCAS = ["--- Seleccione Marca ---", "Audi", "BMW", "Chery", "Chevrolet", "Changan", "Citroën", "Dodge", "Dongfeng", "Fiat", "Ford", "Foton", "Great Wall", "Honda", "Hyundai", "JAC", "Jeep", "Kia", "Maxus", "Mazda", "Mercedes-Benz", "MG", "Mitsubishi", "Nissan", "Peugeot", "Renault", "SsangYong", "Subaru", "Suzuki", "Toyota", "Volkswagen", "Volvo", "Otra..."]
LISTA_ANOS = list(range(datetime.now().year + 1, 1989, -1))
LISTA_PAGOS = ["--- Seleccione ---", "Orden de Compra (Empresas)", "Transferencia Electrónica", "Contado / Efectivo", "Tarjeta Crédito / Débito", "Pago de Deducible (Seguros)"]

def format_clp(value):
    try: return f"${float(value):,.0f}".replace(",", ".")
    except: return "$0"

def reset_session():
    st.query_params.clear()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

def encontrar_imagen(nombre_base):
    extensiones = ['.jpg', '.png', '.jpeg', '.JPG', '.PNG']
    for ext in extensiones:
        if os.path.exists(nombre_base + ext): return nombre_base + ext
        if os.path.exists(nombre_base.capitalize() + ext): return nombre_base.capitalize() + ext
    return None

# ==========================================
# 4. PDF (DISEÑO CORPORATIVO ALINEADO Y CORREGIDO)
# ==========================================
class PDF(FPDF):
    def __init__(self, logo_header=None, correlativo=""):
        super().__init__()
        self.logo_header = logo_header
        self.correlativo = correlativo

    def header(self):
        # Cuadro Presupuesto a la derecha (x=130)
        self.set_xy(130, 10)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 0, 0) # Texto Negro
        self.set_draw_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
        titulo = "PRESUPUESTO"
        if self.correlativo and self.correlativo != "BORRADOR": titulo += f" N° {self.correlativo}"
        self.cell(70, 10, titulo, 1, 1, 'C')
        
        self.set_xy(130, 20)
        self.set_font('Arial', '', 10)
        # La fecha se dibuja, el borde sigue siendo NARANJO
        self.cell(70, 8, f"Fecha Emisión: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C')
        
        # AHORA SI, reseteamos el borde a negro después de haber dibujado ambos cuadros
        self.set_draw_color(0, 0, 0)

        # Logo a la izquierda
        logo_footer = encontrar_imagen("logo") 
        if logo_footer: 
            self.image(logo_footer, x=10, y=8, w=40)

        self.set_xy(52, 10)
        self.set_font('Arial', 'B', 12) 
        self.cell(75, 5, EMPRESA_NOMBRE, 0, 1, 'L')
        
        self.set_font('Arial', '', 8)
        self.set_x(52); self.cell(75, 4, EMPRESA_TITULAR, 0, 1, 'L')
        self.set_x(52); self.cell(75, 4, f"RUT: {RUT_EMPRESA} | Dir: {DIRECCION}", 0, 1, 'L')
        
        self.set_x(52); self.cell(75, 4, "Contacto: Ana María Riquelme | +56 9 4491 8018", 0, 1, 'L')
        self.set_x(52); self.cell(75, 4, "Email: ejecutivapascual@gmail.com", 0, 1, 'L')
        self.set_x(52); self.cell(75, 4, "Dueño: Gonzalo Pascual J. | pascualparabrisas@hotmail.com", 0, 1, 'L')
        self.ln(8)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.line(10, 275, 200, 275)
        self.cell(0, 5, "Documento generado automáticamente - Pascual Parabrisas", 0, 1, 'C')

def generar_pdf_parabrisas(cliente_tipo, cliente_nombre, rut_empresa, contacto_nombre, contacto_fono, marca, modelo, ano, patente, tipo_servicio, dir_servicio, condicion_pago, descuento_pct, items, fotos_adjuntas):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=30) 
    
    pdf.set_font('Arial', 'I', 10); pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 5, "De nuestra consideración: Por medio de la presente, y en respuesta a su solicitud, presentamos la siguiente propuesta técnica y económica para la provisión e instalación de cristales automotrices y/o servicios asociados.")
    pdf.ln(5)

    # Bloque 1: Identificación
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, " 1. IDENTIFICACIÓN DEL CLIENTE Y VEHÍCULO", 1, 1, 'L', 1)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 9)
    
    # Fila 1
    pdf.cell(30, 6, "TIPO CLIENTE:", 'L', 0)
    pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(cliente_tipo).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9)
    label_cliente = "COMPAÑÍA:" if cliente_tipo == "Compañía de Seguros" else "CLIENTE:"
    pdf.cell(25, 6, label_cliente, 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(cliente_nombre).upper(), 'R', 1)

    # Fila 2
    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "CONTACTO:", 'L', 0)
    pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(contacto_nombre).upper() if contacto_nombre else "N/A", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "TELÉFONO:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(contacto_fono).upper() if contacto_fono else "N/A", 'R', 1)

    # Fila 3
    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "MARCA:", 'L', 0)
    pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(marca).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "MODELO:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(modelo).upper(), 'R', 1)

    # Fila 4
    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "AÑO:", 'L', 0)
    pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(ano), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "PATENTE:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(patente).upper() if patente else "S/P", 'R', 1)

    # Fila 5
    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "LUGAR SERV.:", 'L', 0)
    pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(tipo_servicio).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "DIRECCIÓN:", 0, 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(dir_servicio).upper() if tipo_servicio == "En Terreno" else "TALLER PASCUAL", 'R', 1)

    # Fila 6
    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "FORMA PAGO:", 'L,B', 0)
    pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(condicion_pago).upper(), 'R,B', 1)

    pdf.ln(6)
    
    # Bloque 2: Tabla de Ítems
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 7, " 2. DETALLE DE CRISTALES Y SERVICIOS", 1, 1, 'L', 1)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(110, 7, "DESCRIPCIÓN", 1, 0, 'C', 1)
    pdf.cell(20, 7, "CANT.", 1, 0, 'C', 1)
    pdf.cell(30, 7, "PRECIO UNIT.", 1, 0, 'C', 1)
    pdf.cell(30, 7, "TOTAL", 1, 1, 'C', 1)
    
    pdf.set_text_color(0,0,0); pdf.set_font('Arial', '', 9)

    total_neto = 0
    for item in items:
        x = pdf.get_x(); y = pdf.get_y()
        pdf.multi_cell(110, 6, item['Descripción'].upper(), 1, 'L')
        h = pdf.get_y() - y
        pdf.set_xy(x+110, y)
        pdf.cell(20, h, str(item['Cantidad']), 1, 0, 'C')
        pdf.cell(30, h, format_clp(item['Unitario']), 1, 0, 'R')
        pdf.cell(30, h, format_clp(item['Total']), 1, 0, 'R')
        pdf.set_xy(x, y + h)
        total_neto += item['Total']

    # Cálculos Totales
    monto_descuento = total_neto * (descuento_pct / 100.0)
    subtotal = total_neto - monto_descuento
    iva = subtotal * 0.19
    bruto = subtotal + iva

    pdf.ln(2)
    # Totales alineados a X=130
    pdf.set_x(130); pdf.cell(40, 6, "Total Neto:", 1, 0, 'L'); pdf.cell(30, 6, format_clp(total_neto), 1, 1, 'R')
    
    if descuento_pct > 0:
        pdf.set_x(130); pdf.cell(40, 6, f"Descuento ({descuento_pct}%):", 1, 0, 'L'); pdf.cell(30, 6, f"- {format_clp(monto_descuento)}", 1, 1, 'R')
        pdf.set_x(130); pdf.cell(40, 6, "Subtotal Neto:", 1, 0, 'L'); pdf.cell(30, 6, format_clp(subtotal), 1, 1, 'R')
        
    pdf.set_x(130); pdf.cell(40, 6, "IVA (19%):", 1, 0, 'L'); pdf.cell(30, 6, format_clp(iva), 1, 1, 'R')
    
    pdf.set_font('Arial', 'B', 10); pdf.set_x(130)
    pdf.set_text_color(0, 0, 0) # TEXTO NEGRO
    pdf.set_draw_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
    # Borde naranja, texto negro
    pdf.cell(40, 8, "TOTAL A PAGAR:", 1, 0, 'L'); pdf.cell(30, 8, format_clp(bruto), 1, 1, 'R')
    pdf.set_draw_color(0, 0, 0) # reset

    # Condiciones Comerciales
    pdf.ln(12)
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 7, " CONDICIONES COMERCIALES Y DE GARANTÍA", 1, 1, 'L', 1)
    pdf.set_font('Arial', '', 8)
    condiciones = """1. VALIDEZ: La presente cotización tiene una validez de 15 días hábiles, sujeta a disponibilidad de stock en bodega.
2. GARANTÍA: Nuestros trabajos de instalación cuentan con 6 meses de garantía por filtraciones de agua o ruidos de viento anómalos.
3. EXCLUSIONES: La garantía no cubre trizaduras por impactos de piedras, vandalismo, ni daños por choques o torsiones del chasis.
4. TIEMPO DE SECADO: Se recomienda no lavar el vehículo con agua a presión ni someterlo a terrenos irregulares durante 48 horas post-instalación para el correcto curado del adhesivo.
5. PAGOS: Los pagos mediante Orden de Compra están sujetos a la verificación de crédito de la empresa emisora."""
    pdf.multi_cell(0, 5, condiciones, 1, 'L')

    # Firmas
    pdf.ln(15)
    pdf.set_draw_color(150, 150, 150)
    pdf.line(30, pdf.get_y(), 80, pdf.get_y()); pdf.line(130, pdf.get_y(), 180, pdf.get_y())
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(100, 5, "Firma / Recepción Conforme Cliente", 0, 0, 'C'); pdf.cell(90, 5, EMPRESA_NOMBRE, 0, 1, 'C')
    pdf.set_font('Arial', '', 8)
    pdf.cell(100, 5, "RUT:", 0, 0, 'C'); pdf.cell(90, 5, "Departamento Comercial", 0, 1, 'C')

    # Fotos
    if fotos_adjuntas:
        pdf.add_page(); pdf.set_font('Arial', 'B', 14); pdf.set_text_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
        pdf.cell(0, 10, "REGISTRO FOTOGRÁFICO DE DAÑOS / VEHÍCULO", 0, 1, 'C'); pdf.ln(5)
        margin_x = 15; margin_y = 40; w_photo = 85; h_photo = 85; col_gap = 10; row_gap = 10
        for i, foto_uploaded in enumerate(fotos_adjuntas):
            if i > 0 and i % 4 == 0:
                pdf.add_page(); pdf.cell(0, 10, "REGISTRO FOTOGRÁFICO (Cont.)", 0, 1, 'C')
            pos_page = i % 4; row = pos_page // 2; col = pos_page % 2
            x = margin_x + (col * (w_photo + col_gap)); y = margin_y + (row * (h_photo + row_gap))
            try:
                img = Image.open(foto_uploaded); img = ImageOps.exif_transpose(img); img = img.convert('RGB')
                img.thumbnail((600, 600)); temp_filename = f"temp_img_{i}.jpg"; img.save(temp_filename, quality=60, optimize=True)
                pdf.set_draw_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
                pdf.image(temp_filename, x=x, y=y, w=w_photo, h=h_photo); pdf.rect(x, y, w_photo, h_photo)
                os.remove(temp_filename); pdf.set_draw_color(0, 0, 0)
            except: pass

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL (FLUJO PASO A PASO)
# ==========================================
with st.sidebar:
    logo_app = encontrar_imagen("logo") 
    if logo_app: st.image(logo_app, use_container_width=True)
    st.markdown("## 🪟 Pascual Parabrisas")
    st.markdown("---")
    if st.button("🗑️ Nueva Cotización", type="primary", use_container_width=True): reset_session()

if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 1

# --- PASO 1: DATOS DEL CLIENTE Y VEHÍCULO ---
if st.session_state.paso_actual == 1:
    col_centro = st.columns([1, 2, 1])
    with col_centro[1]:
        logo_main = encontrar_imagen("logo") 
        if logo_main: st.image(logo_main, width=250)
        
        st.title("Cotizador de Cristales")
        st.markdown("#### 1. Identificación de Cliente y Servicio")
        
        st.markdown("**Empresa o Cliente a Facturar**")
        cliente_tipo = st.radio("", ("Particular", "Empresa", "Compañía de Seguros"), horizontal=True, label_visibility="collapsed")
        
        cliente_final = ""; rut_empresa = ""
        
        if cliente_tipo == "Compañía de Seguros":
            cliente_final = st.selectbox("Compañía de Seguros", LISTA_ASEGURADORAS)
        elif cliente_tipo == "Empresa":
            c_e1, c_e2 = st.columns([3, 1])
            cliente_final = c_e1.text_input("Nombre de la Empresa", placeholder="Ej: Transportes Garmendia, MOP...")
            rut_empresa = c_e2.text_input("RUT Empresa", placeholder="Ej: 77.123.456-7")
        else:
            cliente_final = st.text_input("Nombre del Cliente Particular", placeholder="Ej: Juan Pérez")
            
        c_c1, c_c2 = st.columns(2)
        contacto_nombre = c_c1.text_input("Nombre y Apellido del Contacto", placeholder="Persona a cargo")
        contacto_fono = c_c2.text_input("Teléfono del Contacto", placeholder="Ej: +56 9 1234 5678")

        condicion_pago = st.selectbox("Condición de Pago Acordada", LISTA_PAGOS)

        st.markdown("---")
        st.markdown("**Datos del Vehículo**")
        c_m1, c_m2 = st.columns(2)
        marca_input = c_m1.selectbox("Marca", LISTA_MARCAS)
        modelo_input = c_m2.text_input("Modelo", placeholder="Ej: Hilux, Sprinter, Yaris...")
        
        c_a1, c_a2 = st.columns(2)
        ano_input = c_a1.selectbox("Año", LISTA_ANOS, index=1)
        patente_input = c_a2.text_input("Patente (Opcional)", placeholder="Ej: AB-CD-12")

        st.markdown("---")
        st.markdown("**Detalles del Servicio**")
        c_s1, c_s2 = st.columns(2)
        tipo_servicio = c_s1.radio("Lugar del Servicio", ("En Taller", "En Terreno"), horizontal=True)
        dir_servicio = ""
        if tipo_servicio == "En Terreno":
            dir_servicio = c_s2.text_input("Dirección de visita", placeholder="Ej: Las Encinas 123, Temuco")
        
        descuento_input = st.number_input("Descuento a aplicar (%)", min_value=0, max_value=100, value=0, step=1, help="Dejar en 0 si no aplica")
        
        if st.button("🚀 PASO SIGUIENTE: AGREGAR CRISTALES", type="primary", use_container_width=True):
            error = False
            if cliente_tipo == "Compañía de Seguros" and cliente_final == "--- Seleccione Compañía ---":
                st.error("⛔ Seleccione una Compañía de Seguros."); error = True
            elif not cliente_final and cliente_tipo != "Compañía de Seguros":
                st.error("⛔ Ingrese el nombre del Cliente."); error = True
            elif condicion_pago == "--- Seleccione ---":
                st.error("⛔ Seleccione una Condición de Pago."); error = True
            elif marca_input == "--- Seleccione Marca ---":
                st.error("⛔ Seleccione la Marca del vehículo."); error = True
            elif not modelo_input:
                st.error("⛔ Ingrese el Modelo."); error = True
            elif tipo_servicio == "En Terreno" and not dir_servicio:
                st.error("⛔ Ingrese la dirección para el servicio en terreno."); error = True
                
            if not error:
                st.session_state.cliente_tipo_confirmado = cliente_tipo
                st.session_state.cliente_confirmado = cliente_final.upper()
                st.session_state.rut_empresa_confirmado = rut_empresa.upper()
                st.session_state.contacto_nombre_confirmado = contacto_nombre
                st.session_state.contacto_fono_confirmado = contacto_fono
                st.session_state.pago_confirmado = condicion_pago
                st.session_state.marca_confirmada = marca_input.upper()
                st.session_state.modelo_confirmado = modelo_input.upper()
                st.session_state.ano_confirmado = ano_input
                st.session_state.patente_confirmada = patente_input.upper()
                st.session_state.tipo_servicio_confirmado = tipo_servicio
                st.session_state.dir_servicio_confirmada = dir_servicio
                st.session_state.descuento_confirmado = descuento_input
                st.session_state.paso_actual = 2
                st.rerun()

# --- PASO 2: COTIZADOR MANUAL ---
elif st.session_state.paso_actual == 2:
    c_tip = st.session_state.cliente_tipo_confirmado
    c_cli = st.session_state.cliente_confirmado
    c_mar = st.session_state.marca_confirmada
    c_mod = st.session_state.modelo_confirmado
    c_ano = st.session_state.ano_confirmado
    desc_val = st.session_state.descuento_confirmado
    
    c1, c2 = st.columns([1, 5])
    with c1: 
        if st.button("⬅️ Volver"): st.session_state.paso_actual = 1; st.rerun()
    with c2: 
        st.markdown(f"### 🪟 <span style='color:{COLOR_HEX};'>{c_mar} {c_mod} ({c_ano})</span> | {c_tip}: {c_cli}", unsafe_allow_html=True)
        if desc_val > 0:
            st.success(f"🏷️ Cotización aplicando un {desc_val}% de descuento.")
    
    if 'items_manuales_parabrisas' not in st.session_state: st.session_state.items_manuales_parabrisas = []
    
    st.markdown("---")
    st.markdown("#### ➕ Ingreso de Cristales o Servicios")
    
    with st.container():
        d_m = st.text_input("Descripción", placeholder="Ej: Parabrisas Original, Instalación, Poliuretano...")
        col_m1, col_m2 = st.columns(2)
        q_m = col_m1.number_input("Cantidad", min_value=1, value=1)
        p_m = col_m2.number_input("Precio Unitario Neto ($)", min_value=0, value=None, step=5000, placeholder="Ej: 85000")
        
        if st.button("Agregar a la cotización", type="secondary"):
            if d_m and p_m is not None and p_m >= 0:
                st.session_state.items_manuales_parabrisas.append({"Descripción": d_m.upper(), "Cantidad": q_m, "Unitario": p_m, "Total": p_m * q_m})
                st.success("✅ Ítem agregado.")
                time.sleep(0.5)
                st.rerun()
            else: st.warning("⚠️ Ingrese descripción y un precio válido.")

    seleccion_final = st.session_state.items_manuales_parabrisas

    if seleccion_final:
        st.markdown("---")
        st.markdown("###### Ítems Agregados:")
        for idx, item in enumerate(seleccion_final):
            st.text(f"• {item['Cantidad']}x {item['Descripción'][:50]} | {format_clp(item['Total'])}")
        if st.button("🗑️ Borrar Lista"): st.session_state.items_manuales_parabrisas = []; st.rerun()

        st.markdown("---")
        total_neto = sum(x['Total'] for x in seleccion_final)
        monto_descuento = total_neto * (desc_val / 100.0)
        subtotal = total_neto - monto_descuento
        iva = subtotal * 0.19
        total_final = subtotal + iva
        
        st.subheader("📊 Resumen Final")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Valor Neto Bruto", format_clp(total_neto))
        k2.metric(f"Descuento ({desc_val}%)", f"- {format_clp(monto_descuento)}")
        k3.metric("IVA (19%)", format_clp(iva))
        k4.metric("TOTAL A PAGAR", format_clp(total_final))

        st.markdown("### 📸 Fotografías (Crucial para Seguros)")
        fotos_adjuntas = st.file_uploader("Adjuntar fotos de daños, padrón o vehículo", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])

        if 'presupuesto_generado' not in st.session_state:
            if st.button("💾 GENERAR PDF Y GUARDAR", type="primary", use_container_width=True):
                correlativo = obtener_y_registrar_correlativo(st.session_state.cliente_tipo_confirmado, c_cli, c_mar, c_mod, c_ano, st.session_state.patente_confirmada, st.session_state.pago_confirmado, format_clp(total_final))
                st.session_state['correlativo_temp'] = correlativo
                
                pdf_bytes = generar_pdf_parabrisas(
                    st.session_state.cliente_tipo_confirmado, c_cli, st.session_state.rut_empresa_confirmado,
                    st.session_state.contacto_nombre_confirmado, st.session_state.contacto_fono_confirmado,
                    c_mar, c_mod, c_ano, st.session_state.patente_confirmada,
                    st.session_state.tipo_servicio_confirmado, st.session_state.dir_servicio_confirmada,
                    st.session_state.pago_confirmado, desc_val, seleccion_final, fotos_adjuntas
                )
                st.session_state['presupuesto_generado'] = {'pdf': pdf_bytes, 'nombre': f"Presupuesto {correlativo} - {c_mar} {c_mod}.pdf"}
                st.rerun()
        else:
            data = st.session_state['presupuesto_generado']
            st.success(f"✅ Presupuesto N° {st.session_state['correlativo_temp']} generado.")
            st.download_button("📥 DESCARGAR PDF", data['pdf'], data['nombre'], "application/pdf", type="primary", use_container_width=True)
            if st.button("🔄 Nueva Cotización", use_container_width=True): reset_session()
