import streamlit as st
import pandas as pd
import io
import os
import json
import re
from fpdf import FPDF
from datetime import datetime
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image, ImageOps

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN A LA NUBE
# ==========================================
st.set_page_config(page_title="Pascual Parabrisas", layout="wide", page_icon="🪟")

NOMBRE_HOJA_GOOGLE = "DB_Cotizador_Pascual"

def conectar_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
        return None
    except Exception as e: 
        return None

# ==========================================
# 2. BASE DE DATOS DE VEHÍCULOS (CHILE)
# ==========================================
BASE_VEHICULOS = {
    "--- Seleccione Marca ---": ["---"],
    "Chevrolet": ["Sail", "Spark", "Tracker", "Colorado", "Silverado", "D-Max", "Captiva", "Onix", "Groove", "Spin", "N300", "Optra"],
    "Toyota": ["Yaris", "Hilux", "RAV4", "Corolla", "Auris", "4Runner", "Fortuner", "Land Cruiser", "Prius", "Rush", "Urban Cruiser"],
    "Hyundai": ["Accent", "Tucson", "Santa Fe", "Elantra", "Creta", "Grand i10", "H-1", "Porter", "Venue", "Kona", "Ioniq"],
    "Kia": ["Morning", "Rio", "Cerato", "Sportage", "Sorento", "Frontier", "Soluto", "Sonet", "Niro", "Carnival", "Carens"],
    "Nissan": ["Versa", "Sentra", "Qashqai", "X-Trail", "NP300", "Navara", "Kicks", "March", "Pathfinder", "Terrano", "Tiida"],
    "Suzuki": ["Swift", "Baleno", "Vitara", "Grand Nomade", "Jimny", "Dzire", "S-Presso", "Ertiga", "Celerio", "Alto", "S-Cross"],
    "Peugeot": ["208", "2008", "308", "3008", "5008", "Partner", "Boxer", "Expert", "Rifter"],
    "Ford": ["Ranger", "F-150", "Territory", "Escape", "Explorer", "Edge", "Transit", "Ecosport", "Puma"],
    "Mazda": ["Mazda 2", "Mazda 3", "Mazda 6", "CX-3", "CX-30", "CX-5", "CX-9", "BT-50"],
    "MG": ["ZS", "ZX", "HS", "RX5", "MG3", "MG5", "MG6", "Marvel R"],
    "Chery": ["Tiggo 2", "Tiggo 3", "Tiggo 4", "Tiggo 7", "Tiggo 8", "Arrizo 5", "IQ"],
    "Changan": ["CS15", "CS35", "CS55", "CX70", "Hunter", "Alsvin", "UNI-T", "UNI-K"],
    "Jac": ["S2", "S3", "JS2", "JS3", "JS4", "JS8", "T8", "T6", "Sunray", "Refine"],
    "Renault": ["Clio", "Symbol", "Captur", "Duster", "Koleos", "Kangoo", "Oroch", "Alaskan", "Megane"],
    "Mitsubishi": ["L200", "Outlander", "Eclipse Cross", "Montero", "ASX", "Mirage", "Katana"],
    "Subaru": ["XV", "Forester", "Outback", "Crosstrek", "Impreza", "WRX", "Legacy"],
    "Honda": ["Civic", "CR-V", "HR-V", "Pilot", "City", "Accord", "WR-V", "Fit"],
    "Volkswagen": ["Gol", "Polo", "Virtus", "Nivus", "T-Cross", "Taos", "Tiguan", "Amarok", "Saveiro", "Vento"],
    "Fiat": ["Mobi", "Argo", "Cronos", "Pulse", "Fiorino", "Strada", "Ducato", "Uno"],
    "BMW": ["Serie 1", "Serie 2", "Serie 3", "X1", "X2", "X3", "X4", "X5"],
    "Mercedes-Benz": ["Clase A", "Clase C", "GLA", "GLC", "GLE", "Sprinter", "Vito", "Citan"],
    "Audi": ["A1", "A3", "A4", "Q2", "Q3", "Q5", "Q7"],
    "Volvo": ["XC40", "XC60", "XC90", "V40", "S60"],
    "SsangYong": ["Tivoli", "Korando", "Rexton", "Musso", "Actyon", "Grand Musso"],
    "Great Wall": ["Poer", "Wingle 5", "Wingle 7", "Haval H6", "Haval Jolion", "Voleex"],
    "Maxus": ["T60", "T90", "G10", "D60", "Deliver 9"],
    "Geely": ["Coolray", "Azkarra", "GX3", "Emgrand"],
    "Citroën": ["C3", "C4", "C5 Aircross", "Berlingo", "Jumper", "Spacetourer"],
    "Jeep": ["Renegade", "Compass", "Cherokee", "Grand Cherokee", "Wrangler", "Gladiator"],
    "Mahindra": ["L200", "Pik Up", "Scorpio", "XUV500", "KUV100"],
    "Ram": ["700", "1000", "1500", "2500", "ProMaster"],
    "Otra Marca": ["Otro Modelo (Escribir Manualmente)"]
}

# ==========================================
# 3. RUT, CORRELATIVOS, CLIENTES Y BORRADORES
# ==========================================
def formato_rut_chileno(rut):
    rut_limpio = re.sub(r'[^0-9Kk]', '', str(rut).upper())
    if len(rut_limpio) <= 1: return rut_limpio
    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1]
    try:
        cuerpo_fmt = f"{int(cuerpo):,}".replace(",", ".")
        return f"{cuerpo_fmt}-{dv}"
    except: return rut_limpio

def obtener_y_registrar_correlativo(cliente, total):
    client = conectar_google_sheets()
    if client:
        try:
            spreadsheet = client.open(NOMBRE_HOJA_GOOGLE)
            try: worksheet_hist = spreadsheet.worksheet("Historial")
            except:
                worksheet_hist = spreadsheet.add_worksheet(title="Historial", rows="1000", cols="4")
                worksheet_hist.append_row(["Fecha", "Correlativo", "Cliente", "Total"])
            
            datos = worksheet_hist.get_all_values()
            numero_actual = len(datos) 
            correlativo_str = str(1650 + numero_actual)
            
            ahora = datetime.now()
            worksheet_hist.append_row([ahora.strftime("%d/%m/%Y %H:%M"), correlativo_str, cliente.upper(), total])
            return correlativo_str
        except Exception: return "ERR"
    else: return "OFFLINE"

@st.cache_data(ttl=60)
def obtener_clientes():
    client = conectar_google_sheets()
    if client:
        try:
            sheet = client.open(NOMBRE_HOJA_GOOGLE)
            try: ws = sheet.worksheet("Clientes")
            except:
                ws = sheet.add_worksheet(title="Clientes", rows="100", cols="7")
                ws.append_row(["RUT", "Nombre", "Direccion", "Ciudad", "Comuna", "Giro", "Fono"])
            return ws.get_all_records()
        except Exception: pass
    return []

def guardar_cliente_nuevo(rut, nombre, direccion, ciudad, comuna, giro, fono):
    client = conectar_google_sheets()
    if client:
        try:
            sheet = client.open(NOMBRE_HOJA_GOOGLE)
            ws = sheet.worksheet("Clientes")
            records = ws.get_all_records()
            if not any(str(r['RUT']).upper() == str(rut).upper() for r in records):
                ws.append_row([rut, nombre, direccion, ciudad, comuna, giro, fono])
                st.cache_data.clear() 
        except Exception: pass

def actualizar_cliente(rut_original, nuevos_datos):
    client = conectar_google_sheets()
    if client:
        try:
            sheet = client.open(NOMBRE_HOJA_GOOGLE)
            ws = sheet.worksheet("Clientes")
            cell = ws.find(rut_original, in_column=1)
            if cell:
                row = cell.row
                cell_list = ws.range(f'A{row}:G{row}')
                for i, c in enumerate(cell_list): c.value = nuevos_datos[i]
                ws.update_cells(cell_list)
                st.cache_data.clear()
        except Exception: pass

def eliminar_cliente(rut_original):
    client = conectar_google_sheets()
    if client:
        try:
            sheet = client.open(NOMBRE_HOJA_GOOGLE)
            ws = sheet.worksheet("Clientes")
            cell = ws.find(rut_original, in_column=1)
            if cell:
                ws.delete_rows(cell.row)
                st.cache_data.clear()
        except Exception: pass

def guardar_borrador_nube():
    client = conectar_google_sheets()
    if not client: return
    try:
        sheet = client.open(NOMBRE_HOJA_GOOGLE)
        try: ws = sheet.worksheet("Borrador")
        except: ws = sheet.add_worksheet(title="Borrador", rows="2", cols="2")
        datos = {k: v for k, v in st.session_state.items() if k.endswith('_confirmado') or k.endswith('_confirmada') or k == 'paso_actual' or k == 'items_productos' or k == 'items_servicios'}
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

# ==========================================
# 4. DATOS DE LA EMPRESA Y ESTILOS
# ==========================================
EMPRESA_NOMBRE = "LILY ISABEL UNDA CONTRERAS"
EMPRESA_GIRO = "VTA, FABRIC Y REPARAC. DE PARABRISAS Y SUS ACCESORIOS"
RUT_EMPRESA = "8.810.453-6" 
DIRECCION = "Caupolicán 0320 - Temuco" 
COLOR_HEX = "#ff6c15"
COLOR_RGB = (255, 108, 21) # Naranja Pascual

st.markdown(f"""
<style>
    .stContainer {{ border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 8px; padding: 15px; margin-bottom: 10px; }}
    div[data-testid="stNumberInput"] input {{ max-width: 150px; text-align: center; font-weight: bold; }}
    input[type=number]::-webkit-inner-spin-button {{ -webkit-appearance: none; margin: 0; }}
    .stButton > button[kind="primary"] {{ background-color: {COLOR_HEX} !important; border-color: {COLOR_HEX} !important; color: white !important; font-weight: bold; padding: 10px; }}
    .stButton > button[kind="primary"]:hover {{ background-color: #E65A0D !important; border-color: #E65A0D !important; }}
    footer {{ display: none !important; }} 
</style>
""", unsafe_allow_html=True)

def format_clp(value):
    try: return f"${float(value):,.0f}".replace(",", ".")
    except: return "$0"

def reset_session():
    limpiar_borrador_nube()
    st.query_params.clear()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

def encontrar_imagen(nombre_base):
    for ext in ['.jpg', '.png', '.jpeg']:
        if os.path.exists(nombre_base + ext): return nombre_base + ext
        if os.path.exists(nombre_base.capitalize() + ext): return nombre_base.capitalize() + ext
    return None

# ==========================================
# 5. CLASE PDF (DISEÑO MODERNO MINIMALISTA)
# ==========================================
class PDF(FPDF):
    def __init__(self, correlativo=""):
        super().__init__()
        self.correlativo = correlativo

    def header(self):
        # 1. Logo
        logo_path = encontrar_imagen("logo") 
        if logo_path: self.image(logo_path, x=10, y=10, w=45)
        
        # 2. Cotización y Número (Derecha)
        self.set_xy(110, 15)
        self.set_font('Arial', 'B', 24)
        self.set_text_color(*COLOR_RGB) # Naranja Pascual
        self.cell(90, 10, "COTIZACIÓN", 0, 1, 'R')
        
        self.set_x(110)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(50, 50, 50) # Gris oscuro
        titulo = f"N° {self.correlativo}" if self.correlativo else "N° BORRADOR"
        self.cell(90, 8, titulo, 0, 1, 'R')
        
        self.set_x(110)
        self.set_font('Arial', '', 10)
        self.cell(90, 6, f"Fecha Emisión: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')

    def footer(self):
        # Línea de color abajo
        self.set_y(-20)
        self.set_fill_color(*COLOR_RGB)
        self.rect(10, 275, 190, 2, 'F')
        
        self.set_y(-15)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(80, 80, 80)
        self.cell(70, 5, EMPRESA_NOMBRE, 0, 0, 'L')
        self.set_font('Arial', '', 8)
        self.cell(50, 5, f"RUT: {RUT_EMPRESA}", 0, 0, 'C')
        self.cell(70, 5, DIRECCION, 0, 1, 'R')

def generar_pdf_pascual(datos_cliente, productos, servicios):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=25) 
    
    # --- 1. BLOQUE DE CLIENTE ESTILO MODERNO ---
    pdf.set_y(45)
    pdf.set_fill_color(248, 248, 248) # Fondo gris super claro
    pdf.rect(10, 45, 190, 32, 'F')
    pdf.set_fill_color(*COLOR_RGB) 
    pdf.rect(10, 45, 2, 32, 'F') # Franja naranja decorativa
    
    pdf.set_xy(15, 48)
    
    # Fila 1 (Encabezados)
    pdf.set_font('Arial', 'B', 8); pdf.set_text_color(*COLOR_RGB)
    pdf.cell(95, 4, "NOMBRE / RAZÓN SOCIAL:", 0, 0, 'L')
    pdf.cell(90, 4, "RUT:", 0, 1, 'L')
    # Fila 1 (Valores)
    pdf.set_font('Arial', 'B', 10); pdf.set_text_color(40, 40, 40)
    pdf.set_x(15); pdf.cell(95, 5, f"{str(datos_cliente.get('nombre', '')).upper()}", 0, 0, 'L')
    pdf.cell(90, 5, f"{str(datos_cliente.get('rut', '')).upper()}", 0, 1, 'L')
    pdf.ln(2)
    
    # Fila 2 (Encabezados)
    pdf.set_x(15); pdf.set_font('Arial', 'B', 8); pdf.set_text_color(*COLOR_RGB)
    pdf.cell(95, 4, "DIRECCIÓN:", 0, 0, 'L')
    pdf.cell(90, 4, "FORMA DE PAGO:", 0, 1, 'L')
    # Fila 2 (Valores)
    pdf.set_font('Arial', '', 9); pdf.set_text_color(50, 50, 50)
    dir_full = f"{str(datos_cliente.get('direccion', ''))}, {str(datos_cliente.get('comuna', ''))}, {str(datos_cliente.get('ciudad', ''))}".upper()
    pdf.set_x(15); pdf.cell(95, 5, dir_full[:55], 0, 0, 'L')
    pdf.cell(90, 5, f"{str(datos_cliente.get('pago', '')).upper()}", 0, 1, 'L')
    pdf.ln(2)
    
    # Fila 3 (Encabezados)
    pdf.set_x(15); pdf.set_font('Arial', 'B', 8); pdf.set_text_color(*COLOR_RGB)
    pdf.cell(95, 4, "GIRO:", 0, 0, 'L')
    pdf.cell(90, 4, "TELÉFONO:", 0, 1, 'L')
    # Fila 3 (Valores)
    pdf.set_font('Arial', '', 9); pdf.set_text_color(50, 50, 50)
    pdf.set_x(15); pdf.cell(95, 5, f"{str(datos_cliente.get('giro', '')).upper()}"[:55], 0, 0, 'L')
    pdf.cell(90, 5, f"{str(datos_cliente.get('fono', ''))}", 0, 1, 'L')
    
    pdf.ln(10)

    # --- 2. TABLA PRINCIPAL MODERNA ---
    pdf.set_fill_color(*COLOR_RGB) # Fondo Naranja
    pdf.set_text_color(255, 255, 255) # Letra Blanca
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(15, 8, "CANT.", 0, 0, 'C', 1)
    pdf.cell(115, 8, "DESCRIPCIÓN", 0, 0, 'L', 1)
    pdf.cell(30, 8, "P. UNIT.", 0, 0, 'R', 1)
    pdf.cell(30, 8, "TOTAL", 0, 1, 'R', 1)
    
    total_general = 0
    pdf.set_text_color(50, 50, 50)
    pdf.set_font('Arial', '', 9)
    
    fill = False # Alternar colores de fila

    def imprimir_fila(cant, desc, unit, total, is_title=False):
        nonlocal fill
        if is_title:
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color(*COLOR_RGB)
            pdf.cell(190, 6, desc, 0, 1, 'L')
            pdf.set_font('Arial', '', 9)
            pdf.set_text_color(50, 50, 50)
            return
            
        pdf.set_fill_color(248, 248, 248) # Gris muy sutil para fila alterna
        x = pdf.get_x(); y = pdf.get_y()
        
        pdf.cell(15, 6, str(cant), 0, 0, 'C', fill=fill)
        pdf.cell(115, 6, desc, 0, 0, 'L', fill=fill)
        pdf.cell(30, 6, format_clp(unit), 0, 0, 'R', fill=fill)
        pdf.cell(30, 6, format_clp(total), 0, 1, 'R', fill=fill)
        fill = not fill

    if productos:
        imprimir_fila("", "  --- PRODUCTOS / REPUESTOS ---", "", "", True)
        for item in productos:
            imprimir_fila(item['Cantidad'], item['Descripción'].upper(), item['Unitario'], item['Total'])
            total_general += item['Total']
            
    if servicios:
        imprimir_fila("", "  --- MANO DE OBRA / SERVICIOS ---", "", "", True)
        for item in servicios:
            imprimir_fila(item['Cantidad'], item['Descripción'].upper(), item['Unitario'], item['Total'])
            total_general += item['Total']

    # Línea divisoria suave
    pdf.ln(2)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # --- 3. SECCIÓN DE TOTALES ---
    neto = total_general / 1.19
    iva = total_general - neto
    
    y_totales = pdf.get_y()
    
    # Texto Legal a la izquierda
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(120, 120, 120)
    notas = "Condiciones comerciales:\n- Validez de la oferta: 15 días corridos.\n- Los trabajos de instalación cuentan con 3 meses de\n  garantía por filtraciones o desprendimientos.\n- Documento generado por Pascual Parabrisas."
    pdf.multi_cell(100, 4, notas)
    
    # Caja de Totales a la derecha
    pdf.set_xy(120, y_totales)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(50, 50, 50)
    
    pdf.cell(40, 7, "SUB TOTAL:", 0, 0, 'L'); pdf.set_font('Arial', '', 10); pdf.cell(30, 7, format_clp(neto), 0, 1, 'R')
    pdf.set_x(120)
    pdf.set_font('Arial', 'B', 10); pdf.cell(40, 7, "I.V.A. (19%):", 0, 0, 'L'); pdf.set_font('Arial', '', 10); pdf.cell(30, 7, format_clp(iva), 0, 1, 'R')
    
    # Total a Pagar en Caja Naranja
    pdf.set_x(120)
    pdf.set_fill_color(*COLOR_RGB)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(40, 10, " TOTAL A PAGAR:", 0, 0, 'L', 1)
    pdf.cell(30, 10, format_clp(total_general) + " ", 0, 1, 'R', 1)

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 6. UI PRINCIPAL (FLUJO PASO A PASO)
# ==========================================
if 'check_borrador' not in st.session_state:
    st.session_state.check_borrador = True
    borrador_recuperado = cargar_borrador_nube()
    if borrador_recuperado and 'cliente_confirmado' in borrador_recuperado:
        st.session_state.borrador_pendiente = borrador_recuperado

if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 1

col_centro = st.columns([1, 2, 1])

with col_centro[1]:
    c_logo, c_btn = st.columns([3, 1], vertical_alignment="center")
    with c_logo:
        logo_app = encontrar_imagen("logo") 
        if logo_app: st.image(logo_app, width=200)
        else: st.title("🪟 Pascual Parabrisas")
    with c_btn:
        if st.button("🗑️ Nueva Cotización", type="primary", use_container_width=True): reset_session()
    st.markdown("---")

    # --- PASO 1: DATOS DEL CLIENTE Y CRM ---
    if st.session_state.paso_actual == 1:
        if 'borrador_pendiente' in st.session_state:
            st.error(f"⚠️ ¡ATENCIÓN! Tienes una cotización en pausa para **{st.session_state.borrador_pendiente.get('cliente_confirmado', 'Cliente')}**.")
            ca, cb = st.columns(2)
            if ca.button("✅ Recuperar Trabajo", use_container_width=True):
                for k, v in st.session_state.borrador_pendiente.items(): st.session_state[k] = v
                del st.session_state['borrador_pendiente']; st.rerun()
            if cb.button("🗑️ Descartar", use_container_width=True):
                limpiar_borrador_nube(); del st.session_state['borrador_pendiente']; st.rerun()
            st.markdown("---")

        st.markdown("#### Búsqueda Rápida de Clientes")
        clientes_db = obtener_clientes()
        opciones_cli = ["--- Nuevo Cliente ---"] + [f"{c['RUT']} | {c['Nombre']}" for c in clientes_db]
        sel_cli = st.selectbox("Seleccione un cliente guardado (opcional):", opciones_cli)
        
        def_nombre = ""; def_rut = ""; def_dir = ""; def_ciu = "Temuco"
        def_com = "Temuco"; def_giro = ""; def_fono = ""

        if sel_cli != "--- Nuevo Cliente ---":
            rut_buscado = sel_cli.split(" | ")[0]
            cli_data = next((c for c in clientes_db if str(c['RUT']) == rut_buscado), None)
            if cli_data:
                def_nombre = str(cli_data['Nombre']); def_rut = str(cli_data['RUT'])
                def_dir = str(cli_data['Direccion']); def_ciu = str(cli_data['Ciudad'])
                def_com = str(cli_data['Comuna']); def_giro = str(cli_data['Giro'])
                def_fono = str(cli_data['Fono'])
                st.success("✅ Datos del cliente cargados exitosamente.")

        st.markdown("---")
        st.markdown("#### Datos de Facturación")
        c_e1, c_e2 = st.columns([3, 1])
        cliente_final = c_e1.text_input("Señor(es) / Razón Social", value=def_nombre, placeholder="Ej: Transportes Garmendia S.A.")
        rut_empresa = c_e2.text_input("RUT", value=def_rut, placeholder="Ej: 76543210-K")
        
        direccion = st.text_input("Dirección", value=def_dir, placeholder="Ej: Av. Las Industrias 123")
        c_c1, c_c2 = st.columns(2)
        ciudad = c_c1.text_input("Ciudad", value=def_ciu, placeholder="Ej: Temuco")
        comuna = c_c2.text_input("Comuna", value=def_com, placeholder="Ej: Padre Las Casas")
        
        giro = st.text_input("Giro Comercial", value=def_giro, placeholder="Ej: Transporte de Carga")
        
        c_f1, c_f2 = st.columns(2)
        contacto_fono = c_f1.text_input("Teléfono", value=def_fono)
        
        opciones_pago = ["Transferencia Electrónica", "Efectivo / Contado", "Tarjeta (Débito/Crédito)", "Orden de Compra (O/C) - 30 días", "Orden de Compra (O/C) - 45 días", "Orden de Compra (O/C) - 60 días", "Crédito Directo a 30 días"]
        condicion_pago = c_f2.selectbox("Forma de Pago", opciones_pago)

        if st.button("🚀 CONTINUAR A DETALLE", type="primary", use_container_width=True):
            if not cliente_final: st.error("⛔ Falta el nombre del cliente.")
            else:
                rut_formateado = formato_rut_chileno(rut_empresa)
                st.session_state.cliente_confirmado = cliente_final.upper()
                st.session_state.rut_confirmado = rut_formateado.upper()
                st.session_state.dir_confirmada = direccion.upper()
                st.session_state.ciudad_confirmada = ciudad.upper()
                st.session_state.comuna_confirmada = comuna.upper()
                st.session_state.giro_confirmado = giro.upper()
                st.session_state.fono_confirmado = contacto_fono
                st.session_state.pago_confirmado = condicion_pago
                st.session_state.paso_actual = 2
                guardar_borrador_nube() 
                st.rerun()

        st.markdown("---")
        with st.expander("⚙️ Administrar Base de Datos de Clientes"):
            st.caption("Modifica o elimina clientes guardados.")
            if clientes_db:
                cliente_sel_admin = st.selectbox("Seleccionar Cliente a Editar:", opciones_cli[1:], key="admin_cli")
                rut_sel_admin = cliente_sel_admin.split(" | ")[0]
                datos_cli_admin = next((c for c in clientes_db if str(c['RUT']) == rut_sel_admin), None)
                
                if datos_cli_admin:
                    n_rut = st.text_input("RUT", value=str(datos_cli_admin['RUT']), key="e_rut")
                    n_nom = st.text_input("Razón Social", value=str(datos_cli_admin['Nombre']), key="e_nom")
                    n_dir = st.text_input("Dirección", value=str(datos_cli_admin['Direccion']), key="e_dir")
                    n_ciu = st.text_input("Ciudad", value=str(datos_cli_admin['Ciudad']), key="e_ciu")
                    n_com = st.text_input("Comuna", value=str(datos_cli_admin['Comuna']), key="e_com")
                    n_gir = st.text_input("Giro", value=str(datos_cli_admin['Giro']), key="e_gir")
                    n_fon = st.text_input("Teléfono", value=str(datos_cli_admin['Fono']), key="e_fon")
                    
                    col_ed1, col_ed2 = st.columns(2)
                    if col_ed1.button("💾 Guardar Cambios", use_container_width=True):
                        rut_fmt = formato_rut_chileno(n_rut)
                        actualizar_cliente(rut_sel_admin, [rut_fmt, n_nom.upper(), n_dir.upper(), n_ciu.upper(), n_com.upper(), n_gir.upper(), n_fon])
                        st.success("✅ Cliente actualizado.")
                        time.sleep(1); st.rerun()
                    if col_ed2.button("🗑️ Eliminar Cliente", use_container_width=True):
                        eliminar_cliente(rut_sel_admin)
                        st.success("✅ Cliente eliminado.")
                        time.sleep(1); st.rerun()
            else:
                st.info("Aún no hay clientes en la base de datos.")

    # --- PASO 2: PRODUCTOS Y MANO DE OBRA ---
    elif st.session_state.paso_actual == 2:
        if 'items_productos' not in st.session_state: st.session_state.items_productos = []
        if 'items_servicios' not in st.session_state: st.session_state.items_servicios = []
        
        c1, c2 = st.columns([1, 4])
        with c1: 
            if st.button("⬅️ Volver", use_container_width=True): st.session_state.paso_actual = 1; st.rerun()
        with c2: 
            st.markdown(f"**Cliente:** {st.session_state.get('cliente_confirmado', '')}")
            st.markdown(f"**RUT:** {st.session_state.get('rut_confirmado', '')}") 
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["📦 Productos", "🔧 Servicios"])
        
        with tab1:
            st.markdown("##### 🚗 Especificaciones del Vehículo (Opcional)")
            with st.container():
                c_v1, c_v2, c_v3 = st.columns([2, 2, 1])
                marca_sel = c_v1.selectbox("Marca", list(BASE_VEHICULOS.keys()), key="v_marca")
                modelo_sel = c_v2.selectbox("Modelo", BASE_VEHICULOS.get(marca_sel, ["---"]), key="v_modelo")
                
                lista_anios = ["---"] + list(range(2027, 1979, -1))
                anio_sel = c_v3.selectbox("Año", lista_anios, key="v_anio")

                c_v4, c_v5 = st.columns(2)
                camara_sel = c_v4.radio("¿Tiene Cámara?", ["No", "Sí"], horizontal=True, key="v_cam")
                sensor_sel = c_v5.radio("¿Sensor de Lluvia?", ["No", "Sí"], horizontal=True, key="v_sen")

            desc_sugerida = ""
            if marca_sel != "--- Seleccione Marca ---":
                desc_sugerida = f"Parabrisas {marca_sel}"
                if modelo_sel != "---": desc_sugerida += f" {modelo_sel}"
                if anio_sel != "---": desc_sugerida += f" {anio_sel}"
                if camara_sel == "Sí": desc_sugerida += " C/Cámara"
                if sensor_sel == "Sí": desc_sugerida += " C/Sensor"

            st.markdown("##### 🛒 Detalle del Producto")
            with st.container():
                col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
                d_p = col_p1.text_input("Descripción del Producto", value=desc_sugerida, placeholder="Ej: Parabrisas...")
                q_p = col_p2.number_input("Cant.", min_value=1, value=1, key="q_prod")
                p_p = col_p3.number_input("Valor c/IVA ($)", min_value=0, step=5000, key="p_prod")
                
                if st.button("➕ Agregar Producto al Presupuesto", use_container_width=True):
                    if d_p and p_p > 0:
                        st.session_state.items_productos.append({"Descripción": d_p, "Cantidad": q_p, "Unitario": p_p, "Total": p_p * q_p})
                        guardar_borrador_nube(); st.rerun()
            
            if st.session_state.items_productos:
                st.markdown("---")
                for item in st.session_state.items_productos: st.text(f"• {item['Cantidad']}x {item['Descripción']} | {format_clp(item['Total'])}")
                if st.button("🗑️ Borrar Productos"): st.session_state.items_productos = []; guardar_borrador_nube(); st.rerun()

        with tab2:
            st.markdown("##### 🔧 Detalle de Mano de Obra")
            with st.container():
                col_s1, col_s2, col_s3 = st.columns([3, 1, 1])
                d_s = col_s1.text_input("Descripción del Servicio", placeholder="Ej: Instalación...")
                q_s = col_s2.number_input("Cant.", min_value=1, value=1, key="q_serv")
                p_s = col_s3.number_input("Valor c/IVA ($)", min_value=0, step=5000, key="p_serv")
                
                if st.button("➕ Agregar Servicio", use_container_width=True):
                    if d_s and p_s > 0:
                        st.session_state.items_servicios.append({"Descripción": d_s, "Cantidad": q_s, "Unitario": p_s, "Total": p_s * q_s})
                        guardar_borrador_nube(); st.rerun()
                        
            if st.session_state.items_servicios:
                st.markdown("---")
                for item in st.session_state.items_servicios: st.text(f"• {item['Cantidad']}x {item['Descripción']} | {format_clp(item['Total'])}")
                if st.button("🗑️ Borrar Servicios"): st.session_state.items_servicios = []; guardar_borrador_nube(); st.rerun()

        total_prod = sum(x['Total'] for x in st.session_state.items_productos)
        total_serv = sum(x['Total'] for x in st.session_state.items_servicios)
        total_bruto = total_prod + total_serv

        if total_bruto > 0:
            st.markdown("---")
            st.subheader(f"📊 TOTAL COTIZACIÓN: {format_clp(total_bruto)}")

            if 'presupuesto_generado' not in st.session_state:
                if st.button("💾 GENERAR COTIZACIÓN", type="primary", use_container_width=True):
                    
                    guardar_cliente_nuevo(
                        st.session_state.get('rut_confirmado', ''), st.session_state.get('cliente_confirmado', ''), 
                        st.session_state.get('dir_confirmada', ''), st.session_state.get('ciudad_confirmada', ''), 
                        st.session_state.get('comuna_confirmada', ''), st.session_state.get('giro_confirmado', ''), 
                        st.session_state.get('fono_confirmado', '')
                    )
                    
                    correlativo = obtener_y_registrar_correlativo(st.session_state.get('cliente_confirmado', 'CLIENTE'), format_clp(total_bruto))
                    st.session_state['correlativo_temp'] = correlativo
                    
                    datos_cliente = {
                        "nombre": st.session_state.get('cliente_confirmado', ''), "rut": st.session_state.get('rut_confirmado', ''),
                        "direccion": st.session_state.get('dir_confirmada', ''), "ciudad": st.session_state.get('ciudad_confirmada', ''),
                        "comuna": st.session_state.get('comuna_confirmada', ''), "giro": st.session_state.get('giro_confirmado', ''),
                        "fono": st.session_state.get('fono_confirmado', ''), "pago": st.session_state.get('pago_confirmado', '')
                    }
                    
                    pdf_bytes = generar_pdf_pascual(datos_cliente, st.session_state.items_productos, st.session_state.items_servicios)
                    st.session_state['presupuesto_generado'] = {'pdf': pdf_bytes, 'nombre': f"Cotizacion_{correlativo}_{st.session_state.get('cliente_confirmado', 'CLIENTE')}.pdf"}
                    limpiar_borrador_nube() 
                    st.rerun()
            else:
                data = st.session_state['presupuesto_generado']
                st.success(f"✅ Cotización N° {st.session_state.get('correlativo_temp', '')} generada.")
                st.download_button("📥 DESCARGAR PDF", data['pdf'], data['nombre'], "application/pdf", type="primary", use_container_width=True)
