import streamlit as st
import pandas as pd
import io
import os
import json
import smtplib
from email.message import EmailMessage
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
        return gspread.authorize(creds)
    except Exception as e: 
        st.error(f"❌ ERROR DE AUTENTICACIÓN: Revisa los Secrets. Detalle: {e}")
        return None

# ==========================================
# 2. LÓGICA DE CORRELATIVOS Y BORRADORES
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
        except Exception: return "ERR"
    else: return "OFFLINE"

def guardar_borrador_nube():
    client = conectar_google_sheets()
    if not client: return
    try:
        sheet = client.open(NOMBRE_HOJA_GOOGLE)
        try: ws = sheet.worksheet("Borrador")
        except: ws = sheet.add_worksheet(title="Borrador", rows="2", cols="2")
        
        datos = {k: v for k, v in st.session_state.items() if k.endswith('_confirmado') or k == 'paso_actual' or k == 'items_manuales_parabrisas'}
        ws.update_acell('A1', json.dumps(datos))
    except Exception: pass

def cargar_borrador_nube():
    client = conectar_google_sheets()
    if not client: return None
    try:
        sheet = client.open(NOMBRE_HOJA_GOOGLE)
        ws = sheet.worksheet("Borrador")
        val = ws.acell('A1').value
        if val: return json.loads(val)
    except Exception: pass
    return None

def limpiar_borrador_nube():
    client = conectar_google_sheets()
    if not client: return
    try:
        sheet = client.open(NOMBRE_HOJA_GOOGLE)
        ws = sheet.worksheet("Borrador")
        ws.update_acell('A1', '')
    except Exception: pass

def enviar_cotizacion_correo(email_destino, pdf_bytes, correlativo, nombre_cliente):
    try:
        remitente = st.secrets.get("email_sender", "")
        password = st.secrets.get("email_password", "")
        if not remitente or not password:
            return False, "⚠️ Falta configurar el correo en los Secrets de Streamlit."
        
        msg = EmailMessage()
        msg['Subject'] = f"Presupuesto N° {correlativo} - Pascual Parabrisas"
        msg['From'] = remitente
        msg['To'] = email_destino
        msg.set_content(f"Estimado/a {nombre_cliente},\n\nJunto con saludar cordialmente, adjuntamos la propuesta técnica y comercial solicitada.\n\nQuedamos atentos a sus comentarios o dudas para proceder con la agendamiento del servicio.\n\nSaludos cordiales,\nEquipo Pascual Parabrisas\nCaupolicán 0320, Temuco.")
        
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f"Presupuesto_Pascual_{correlativo}.pdf")
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(remitente, password)
            smtp.send_message(msg)
        return True, "Enviado con éxito"
    except Exception as e:
        return False, f"Error del servidor: {str(e)}"

# ==========================================
# 3. DATOS DE LA EMPRESA Y ESTILOS
# ==========================================
EMPRESA_NOMBRE = "PASCUAL PARABRISAS"
EMPRESA_TITULAR = "Venta e Instalación de Cristales Automotrices"
RUT_EMPRESA = "8810453-6" 
DIRECCION = "Caupolicán 0320, Temuco" 

COLOR_HEX = "#ff6c15"
NARANJA_PASCUAL = (255, 108, 21) 

st.markdown(f"""
<style>
    .stContainer {{ border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 10px; margin-bottom: 5px; }}
    div[data-testid="stNumberInput"] input {{ max-width: 150px; text-align: center; }}
    input[type=number]::-webkit-inner-spin-button {{ -webkit-appearance: none; margin: 0; }}
    
    .stButton > button[kind="primary"] {{ background-color: {COLOR_HEX} !important; border-color: {COLOR_HEX} !important; color: white !important; font-weight: bold; }}
    .stButton > button[kind="primary"]:hover {{ background-color: #E65A0D !important; border-color: #E65A0D !important; }}
    .stTabs [aria-selected="true"] {{ background-color: {COLOR_HEX} !important; color: white !important; border-radius: 4px;}}
    div[data-testid="stRadio"] > label {{ font-weight: bold; color: {COLOR_HEX}; }}

    #MainMenu {{ visibility: hidden !important; }}
    footer {{ display: none !important; }}
    header {{ display: none !important; }}
    .stDeployButton {{ display: none !important; }}
    div[data-testid="stToolbar"] {{ display: none !important; }}
    div[data-testid="stDecoration"] {{ display: none !important; }}
    div[data-testid="stStatusWidget"] {{ display: none !important; }}
    div[class^="viewerBadge"] {{ display: none !important; }}
    #st-cloud-logo {{ display: none !important; }}
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
    limpiar_borrador_nube()
    st.query_params.clear()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

def encontrar_imagen(nombre_base):
    for ext in ['.jpg', '.png', '.jpeg', '.JPG', '.PNG']:
        if os.path.exists(nombre_base + ext): return nombre_base + ext
        if os.path.exists(nombre_base.capitalize() + ext): return nombre_base.capitalize() + ext
    return None

# ==========================================
# 4. PDF (MANTENIDO INTACTO)
# ==========================================
class PDF(FPDF):
    def __init__(self, logo_header=None, correlativo=""):
        super().__init__()
        self.logo_header = logo_header
        self.correlativo = correlativo

    def header(self):
        self.set_xy(130, 10); self.set_font('Arial', 'B', 14); self.set_text_color(0, 0, 0)
        self.set_draw_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
        titulo = "PRESUPUESTO"
        if self.correlativo and self.correlativo != "BORRADOR": titulo += f" N° {self.correlativo}"
        self.cell(70, 10, titulo, 1, 1, 'C')
        self.set_xy(130, 20); self.set_font('Arial', '', 10)
        self.cell(70, 8, f"Fecha Emisión: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C')
        self.set_draw_color(0, 0, 0) 

        logo_footer = encontrar_imagen("logo") 
        if logo_footer: self.image(logo_footer, x=10, y=8, w=40)

        self.set_xy(52, 10); self.set_font('Arial', 'B', 12) 
        self.cell(75, 5, EMPRESA_NOMBRE, 0, 1, 'L')
        self.set_font('Arial', '', 8)
        self.set_x(52); self.cell(75, 4, EMPRESA_TITULAR, 0, 1, 'L')
        self.set_x(52); self.cell(75, 4, f"RUT: {RUT_EMPRESA} | Dir: {DIRECCION}", 0, 1, 'L')
        self.set_x(52); self.cell(75, 4, "Contacto: Ana María Riquelme | +56 9 4491 8018", 0, 1, 'L')
        self.set_x(52); self.cell(75, 4, "Email: ejecutivapascual@gmail.com", 0, 1, 'L')
        self.set_x(52); self.cell(75, 4, "Dueño: Gonzalo Pascual J. | pascualparabrisas@hotmail.com", 0, 1, 'L')
        self.ln(8)

    def footer(self):
        self.set_y(-20); self.set_font('Arial', 'I', 8); self.set_text_color(150, 150, 150)
        self.line(10, 275, 200, 275)
        self.cell(0, 5, "Documento generado automáticamente - Pascual Parabrisas", 0, 1, 'C')

def generar_pdf_parabrisas(cliente_tipo, cliente_nombre, rut_empresa, contacto_nombre, contacto_fono, marca, modelo, ano, patente, tipo_servicio, dir_servicio, condicion_pago, descuento_pct, items, fotos_adjuntas):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=30) 
    pdf.set_font('Arial', 'I', 10); pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 5, "De nuestra consideración: Por medio de la presente, y en respuesta a su solicitud, presentamos la siguiente propuesta técnica y económica para la provisión e instalación de cristales automotrices y/o servicios asociados.")
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2]); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, " 1. IDENTIFICACIÓN DEL CLIENTE Y VEHÍCULO", 1, 1, 'L', 1)
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 9)
    
    pdf.cell(30, 6, "TIPO CLIENTE:", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(cliente_tipo).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "COMPAÑÍA:" if cliente_tipo == "Compañía de Seguros" else "CLIENTE:", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(cliente_nombre).upper(), 'R', 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "CONTACTO:", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(contacto_nombre).upper() if contacto_nombre else "N/A", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "TELÉFONO:", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(contacto_fono).upper() if contacto_fono else "N/A", 'R', 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "MARCA:", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(marca).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "MODELO:", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(modelo).upper(), 'R', 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "AÑO:", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(ano), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "PATENTE:", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(patente).upper() if patente else "S/P", 'R', 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "LUGAR SERV.:", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(60, 6, str(tipo_servicio).upper(), 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, "DIRECCIÓN:", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(dir_servicio).upper() if tipo_servicio == "En Terreno" else "TALLER PASCUAL", 'R', 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, "FORMA PAGO:", 'L,B', 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 6, str(condicion_pago).upper(), 'R,B', 1)

    pdf.ln(6)
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2]); pdf.set_text_color(255,255,255)
    pdf.cell(0, 7, " 2. DETALLE DE CRISTALES Y SERVICIOS", 1, 1, 'L', 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(110, 7, "DESCRIPCIÓN", 1, 0, 'C', 1); pdf.cell(20, 7, "CANT.", 1, 0, 'C', 1); pdf.cell(30, 7, "PRECIO UNIT.", 1, 0, 'C', 1); pdf.cell(30, 7, "TOTAL", 1, 1, 'C', 1)
    
    pdf.set_text_color(0,0,0); pdf.set_font('Arial', '', 9)
    total_neto = 0
    for item in items:
        x = pdf.get_x(); y = pdf.get_y()
        pdf.multi_cell(110, 6, item['Descripción'].upper(), 1, 'L')
        h = pdf.get_y() - y; pdf.set_xy(x+110, y)
        pdf.cell(20, h, str(item['Cantidad']), 1, 0, 'C'); pdf.cell(30, h, format_clp(item['Unitario']), 1, 0, 'R'); pdf.cell(30, h, format_clp(item['Total']), 1, 0, 'R')
        pdf.set_xy(x, y + h); total_neto += item['Total']

    monto_descuento = total_neto * (descuento_pct / 100.0); subtotal = total_neto - monto_descuento; iva = subtotal * 0.19; bruto = subtotal + iva

    pdf.ln(2); pdf.set_x(130); pdf.cell(40, 6, "Total Neto:", 1, 0, 'L'); pdf.cell(30, 6, format_clp(total_neto), 1, 1, 'R')
    if descuento_pct > 0:
        pdf.set_x(130); pdf.cell(40, 6, f"Descuento ({descuento_pct}%):", 1, 0, 'L'); pdf.cell(30, 6, f"- {format_clp(monto_descuento)}", 1, 1, 'R')
        pdf.set_x(130); pdf.cell(40, 6, "Subtotal Neto:", 1, 0, 'L'); pdf.cell(30, 6, format_clp(subtotal), 1, 1, 'R')
        
    pdf.set_x(130); pdf.cell(40, 6, "IVA (19%):", 1, 0, 'L'); pdf.cell(30, 6, format_clp(iva), 1, 1, 'R')
    pdf.set_font('Arial', 'B', 10); pdf.set_x(130); pdf.set_draw_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
    pdf.cell(40, 8, "TOTAL A PAGAR:", 1, 0, 'L'); pdf.cell(30, 8, format_clp(bruto), 1, 1, 'R'); pdf.set_draw_color(0, 0, 0) 

    pdf.ln(12); pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 7, " CONDICIONES COMERCIALES Y DE GARANTÍA", 1, 1, 'L', 1)
    pdf.set_font('Arial', '', 8)
    pdf.multi_cell(0, 5, "1. VALIDEZ: Cotización válida por 15 días hábiles, sujeta a stock.\n2. GARANTÍA: 6 meses de garantía por filtraciones de agua o ruidos de viento anómalos.\n3. EXCLUSIONES: La garantía no cubre trizaduras por impactos de piedras, vandalismo, ni daños por choques.\n4. SECADO: No lavar el vehículo con agua a presión ni someterlo a terrenos irregulares durante 48 horas.\n5. PAGOS: Pagos con Orden de Compra sujetos a verificación de crédito.", 1, 'L')

    pdf.ln(15); pdf.set_draw_color(150, 150, 150)
    pdf.line(30, pdf.get_y(), 80, pdf.get_y()); pdf.line(130, pdf.get_y(), 180, pdf.get_y())
    pdf.set_font('Arial', 'B', 9); pdf.cell(100, 5, "Firma / Recepción Conforme Cliente", 0, 0, 'C'); pdf.cell(90, 5, EMPRESA_NOMBRE, 0, 1, 'C')
    pdf.set_font('Arial', '', 8); pdf.cell(100, 5, "RUT:", 0, 0, 'C'); pdf.cell(90, 5, "Departamento Comercial", 0, 1, 'C')

    if fotos_adjuntas:
        pdf.add_page(); pdf.set_font('Arial', 'B', 14); pdf.set_text_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
        pdf.cell(0, 10, "REGISTRO FOTOGRÁFICO DE DAÑOS / VEHÍCULO", 0, 1, 'C'); pdf.ln(5)
        margin_x = 15; margin_y = 40; w_photo = 85; h_photo = 85; col_gap = 10; row_gap = 10
        for i, f in enumerate(fotos_adjuntas):
            if i > 0 and i % 4 == 0:
                pdf.add_page(); pdf.cell(0, 10, "REGISTRO FOTOGRÁFICO (Cont.)", 0, 1, 'C')
            row = (i % 4) // 2; col = (i % 4) % 2; x = margin_x + (col * (w_photo + col_gap)); y = margin_y + (row * (h_photo + row_gap))
            try:
                img = Image.open(f); img = ImageOps.exif_transpose(img); img = img.convert('RGB')
                img.thumbnail((600, 600)); tmp = f"temp_img_{i}.jpg"; img.save(tmp, quality=60, optimize=True)
                pdf.set_draw_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
                pdf.image(tmp, x=x, y=y, w=w_photo, h=h_photo); pdf.rect(x, y, w_photo, h_photo); os.remove(tmp); pdf.set_draw_color(0, 0, 0)
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

# --- VERIFICADOR DE BORRADORES AUTOMÁTICO ---
if 'check_borrador' not in st.session_state:
    st.session_state.check_borrador = True
    borrador_recuperado = cargar_borrador_nube()
    if borrador_recuperado and 'cliente_confirmado' in borrador_recuperado:
        st.session_state.borrador_pendiente = borrador_recuperado

if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 1

# --- PASO 1: DATOS DEL CLIENTE ---
if st.session_state.paso_actual == 1:
    col_centro = st.columns([1, 2, 1])
    with col_centro[1]:
        logo_main = encontrar_imagen("logo") 
        if logo_main: st.image(logo_main, width=250)
        
        # ALERTA DE BORRADOR
        if 'borrador_pendiente' in st.session_state:
            st.error(f"⚠️ ¡ATENCIÓN! Tienes una cotización en pausa para **{st.session_state.borrador_pendiente['cliente_confirmado']}**.")
            ca, cb = st.columns(2)
            if ca.button("✅ Recuperar Trabajo", use_container_width=True):
                for k, v in st.session_state.borrador_pendiente.items(): st.session_state[k] = v
                del st.session_state['borrador_pendiente']
                st.rerun()
            if cb.button("🗑️ Descartar y empezar de cero", use_container_width=True):
                limpiar_borrador_nube()
                del st.session_state['borrador_pendiente']
                st.rerun()
            st.markdown("---")

        st.title("Cotizador de Cristales")
        st.markdown("#### 1. Identificación de Cliente")
        
        cliente_tipo = st.radio("", ("Particular", "Empresa", "Compañía de Seguros"), horizontal=True, label_visibility="collapsed")
        cliente_final = ""; rut_empresa = ""
        if cliente_tipo == "Compañía de Seguros": cliente_final = st.selectbox("Compañía de Seguros", LISTA_ASEGURADORAS)
        elif cliente_tipo == "Empresa":
            c_e1, c_e2 = st.columns([3, 1])
            cliente_final = c_e1.text_input("Nombre Empresa", placeholder="Ej: Transportes Garmendia")
            rut_empresa = c_e2.text_input("RUT Empresa")
        else: cliente_final = st.text_input("Nombre del Cliente Particular")
            
        c_c1, c_c2 = st.columns(2)
        contacto_nombre = c_c1.text_input("Nombre del Contacto")
        contacto_fono = c_c2.text_input("Teléfono del Contacto")
        contacto_email = st.text_input("Email del Contacto (Para enviar la cotización)", placeholder="ejemplo@correo.cl")

        condicion_pago = st.selectbox("Condición de Pago Acordada", LISTA_PAGOS)

        st.markdown("---")
        st.markdown("**Datos del Vehículo y Servicio**")
        c_m1, c_m2 = st.columns(2)
        marca_input = c_m1.selectbox("Marca", LISTA_MARCAS)
        modelo_input = c_m2.text_input("Modelo", placeholder="Ej: Hilux")
        c_a1, c_a2 = st.columns(2)
        ano_input = c_a1.selectbox("Año", LISTA_ANOS, index=1)
        patente_input = c_a2.text_input("Patente (Opcional)")

        c_s1, c_s2 = st.columns(2)
        tipo_servicio = c_s1.radio("Lugar del Servicio", ("En Taller", "En Terreno"), horizontal=True)
        dir_servicio = c_s2.text_input("Dirección de visita") if tipo_servicio == "En Terreno" else ""
        descuento_input = st.number_input("Descuento a aplicar (%)", min_value=0, max_value=100, value=0)
        
        if st.button("🚀 PASO SIGUIENTE: AGREGAR CRISTALES", type="primary", use_container_width=True):
            if not cliente_final or cliente_final == "--- Seleccione Compañía ---" or condicion_pago == "--- Seleccione ---" or marca_input == "--- Seleccione Marca ---" or not modelo_input or (tipo_servicio == "En Terreno" and not dir_servicio):
                st.error("⛔ Faltan campos obligatorios por completar.")
            else:
                st.session_state.cliente_tipo_confirmado = cliente_tipo
                st.session_state.cliente_confirmado = cliente_final.upper()
                st.session_state.rut_empresa_confirmado = rut_empresa.upper()
                st.session_state.contacto_nombre_confirmado = contacto_nombre
                st.session_state.contacto_fono_confirmado = contacto_fono
                st.session_state.contacto_email_confirmado = contacto_email.lower()
                st.session_state.pago_confirmado = condicion_pago
                st.session_state.marca_confirmada = marca_input.upper()
                st.session_state.modelo_confirmado = modelo_input.upper()
                st.session_state.ano_confirmado = ano_input
                st.session_state.patente_confirmada = patente_input.upper()
                st.session_state.tipo_servicio_confirmado = tipo_servicio
                st.session_state.dir_servicio_confirmada = dir_servicio
                st.session_state.descuento_confirmado = descuento_input
                st.session_state.paso_actual = 2
                guardar_borrador_nube() # Guardado Silencioso
                st.rerun()

# --- PASO 2: COTIZADOR MANUAL ---
elif st.session_state.paso_actual == 2:
    c_cli = st.session_state.cliente_confirmado
    c_mar = st.session_state.marca_confirmada
    c_mod = st.session_state.modelo_confirmado
    desc_val = st.session_state.descuento_confirmado
    
    c1, c2 = st.columns([1, 5])
    with c1: 
        if st.button("⬅️ Volver"): st.session_state.paso_actual = 1; st.rerun()
    with c2: st.markdown(f"### 🪟 <span style='color:{COLOR_HEX};'>{c_mar} {c_mod}</span> | Cliente: {c_cli}", unsafe_allow_html=True)
    
    if 'items_manuales_parabrisas' not in st.session_state: st.session_state.items_manuales_parabrisas = []
    
    with st.container():
        d_m = st.text_input("Descripción", placeholder="Ej: Parabrisas Original...")
        col_m1, col_m2 = st.columns(2)
        q_m = col_m1.number_input("Cantidad", min_value=1, value=1)
        p_m = col_m2.number_input("Precio Unitario Neto ($)", min_value=0, value=None, step=5000)
        
        if st.button("Agregar a la cotización", type="secondary"):
            if d_m and p_m is not None:
                st.session_state.items_manuales_parabrisas.append({"Descripción": d_m.upper(), "Cantidad": q_m, "Unitario": p_m, "Total": p_m * q_m})
                guardar_borrador_nube() # Respalda al instante
                st.rerun()

    seleccion_final = st.session_state.items_manuales_parabrisas
    if seleccion_final:
        for item in seleccion_final: st.text(f"• {item['Cantidad']}x {item['Descripción']} | {format_clp(item['Total'])}")
        if st.button("🗑️ Borrar Lista"): 
            st.session_state.items_manuales_parabrisas = []
            guardar_borrador_nube()
            st.rerun()

        total_neto = sum(x['Total'] for x in seleccion_final)
        total_final = (total_neto - (total_neto * (desc_val / 100.0))) * 1.19
        st.subheader(f"📊 TOTAL A PAGAR: {format_clp(total_final)}")

        fotos_adjuntas = st.file_uploader("Adjuntar fotos", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])

        if 'presupuesto_generado' not in st.session_state:
            if st.button("💾 GENERAR PRESUPUESTO", type="primary", use_container_width=True):
                correlativo = obtener_y_registrar_correlativo(st.session_state.cliente_tipo_confirmado, c_cli, c_mar, c_mod, st.session_state.ano_confirmado, st.session_state.patente_confirmada, st.session_state.pago_confirmado, format_clp(total_final))
                st.session_state['correlativo_temp'] = correlativo
                pdf_bytes = generar_pdf_parabrisas(st.session_state.cliente_tipo_confirmado, c_cli, st.session_state.rut_empresa_confirmado, st.session_state.contacto_nombre_confirmado, st.session_state.contacto_fono_confirmado, c_mar, c_mod, st.session_state.ano_confirmado, st.session_state.patente_confirmada, st.session_state.tipo_servicio_confirmado, st.session_state.dir_servicio_confirmada, st.session_state.pago_confirmado, desc_val, seleccion_final, fotos_adjuntas)
                st.session_state['presupuesto_generado'] = {'pdf': pdf_bytes, 'nombre': f"Presupuesto {correlativo} - {c_mar} {c_mod}.pdf"}
                limpiar_borrador_nube() # Limpia la nube al terminar exitosamente
                st.rerun()
        else:
            data = st.session_state['presupuesto_generado']
            st.success(f"✅ Presupuesto N° {st.session_state['correlativo_temp']} generado.")
            st.download_button("📥 DESCARGAR PDF", data['pdf'], data['nombre'], "application/pdf", type="primary", use_container_width=True)
            
            # --- MÓDULO DE ENVÍO POR CORREO ---
            st.markdown("---")
            st.markdown("#### ✉️ Enviar Directamente por Correo")
            correo_destino = st.text_input("Correo del cliente:", value=st.session_state.get('contacto_email_confirmado', ''))
            if st.button("🚀 Enviar Cotización", type="primary", use_container_width=True):
                if correo_destino:
                    with st.spinner("Enviando correo..."):
                        exito, msg = enviar_cotizacion_correo(correo_destino, data['pdf'], st.session_state['correlativo_temp'], c_cli)
                        if exito: st.success("✅ ¡Cotización enviada exitosamente!")
                        else: st.error(msg)
                else: st.warning("⚠️ Escribe un correo de destino primero.")
