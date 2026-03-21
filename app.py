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
# 2. BASE DE DATOS DE VEHÍCULOS (CSV DINÁMICO)
# ==========================================
@st.cache_data(ttl=3600)
def cargar_base_vehiculos():
    base_por_defecto = {
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
        "Ram": ["700", "1000", "1500", "2500", "ProMaster"]
    }
    
    try:
        if os.path.exists("vehiculos.csv"):
            df = pd.read_csv("vehiculos.csv", encoding='utf-8')
            if 'Marca' in df.columns and 'Modelo' in df.columns:
                base_csv = {"--- Seleccione Marca ---": ["---"]}
                marcas = sorted([str(m) for m in df['Marca'].dropna().unique()])
                for marca in marcas:
                    modelos = df[df['Marca'] == marca]['Modelo'].dropna().tolist()
                    base_csv[marca] = sorted(list(set([str(m) for m in modelos])))
                return base_csv
    except Exception as e:
        pass 
        
    return base_por_defecto

BASE_VEHICULOS = cargar_base_vehiculos()

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

def formato_patente_chilena(patente):
    # Elimina todo lo que no sea letra o número
    pat = re.sub(r'[^A-Z0-9]', '', str(patente).upper())
    if len(pat) == 6:
        # Si la tercera letra es una consonante, es formato nuevo (XXXX-11)
        if pat[2].isalpha():
            return f"{pat[:4]}-{pat[4:]}"
        # Si es un número, es formato antiguo (XX-1111)
        else:
            return f"{pat[:2]}-{pat[2:]}"
    return pat

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
        datos = {k: v for k, v in st.session_state.items() if k.endswith('_confirmado') or k.endswith('_confirmada') or k == 'paso_actual' or k == 'items_productos' or k == 'items_servicios' or k == 'cristales_sel' or k == 'servicio_desc'}
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

# --- HACK CSS PARA DESACTIVAR TECLADO EN SELECTBOX ---
st.markdown(f"""
<style>
    .stContainer {{ border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 8px; padding: 15px; margin-bottom: 10px; }}
    div[data-testid="stNumberInput"] input {{ max-width: 150px; text-align: center; font-weight: bold; }}
    input[type=number]::-webkit-inner-spin-button {{ -webkit-appearance: none; margin: 0; }}
    .stButton > button[kind="primary"] {{ background-color: {COLOR_HEX} !important; border-color: {COLOR_HEX} !important; color: white !important; font-weight: bold; padding: 10px; transition: 0.2s; }}
    .stButton > button[kind="primary"]:hover {{ background-color: #E65A0D !important; border-color: #E65A0D !important; }}
    footer {{ display: none !important; }} 
    
    /* Desactivar foco y teclado en las listas desplegables (Selectbox) para celular */
    div[data-baseweb="select"] input {{
        pointer-events: none !important;
    }}
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
# 5. LÓGICA DE MULTISELECCIÓN
# ==========================================
if 'cristales_sel' not in st.session_state:
    st.session_state.cristales_sel = []
if 'servicio_desc' not in st.session_state:
    st.session_state.servicio_desc = "INSTALACIÓN DE CRISTAL"

def toggle_cristal(cristal):
    if cristal in st.session_state.cristales_sel:
        st.session_state.cristales_sel.remove(cristal)
    else:
        st.session_state.cristales_sel.append(cristal)
        
def set_servicio(servicio):
    st.session_state.servicio_desc = servicio

def btn_type(cristal):
    return "primary" if cristal in st.session_state.cristales_sel else "secondary"

# ==========================================
# 6. CLASE PDF (DISEÑO TABULAR ORDENADO + DATOS DEL MÓVIL)
# ==========================================
class PDF(FPDF):
    def __init__(self, correlativo=""):
        super().__init__()
        self.correlativo = correlativo

    def header(self):
        logo_path = encontrar_imagen("logo") 
        if logo_path: self.image(logo_path, x=10, y=15, w=50) 
        
        self.set_xy(10, 40)
        self.set_font('Arial', 'B', 9); self.cell(100, 4, EMPRESA_NOMBRE, 0, 1, 'L')
        self.set_font('Arial', '', 8)
        self.cell(100, 4, EMPRESA_GIRO, 0, 1, 'L')
        self.cell(100, 4, f"C.M.: {DIRECCION}", 0, 1, 'L')
        self.set_font('Arial', 'B', 9); self.cell(100, 4, f"R.U.T.: {RUT_EMPRESA}", 0, 1, 'L')

        self.set_xy(140, 15)
        self.set_font('Arial', 'B', 16)
        
        self.multi_cell(60, 4, "COTIZACIÓN DE\nSERVICIO", 'LTR', 'C') 
        
        self.set_x(140)
        titulo = f"N° {self.correlativo}" if self.correlativo else "N° BORRADOR"
        self.cell(60, 8, titulo, 'LBR', 1, 'C')
        
        self.ln(15) 

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(150, 150, 150)
        self.cell(0, 5, "Documento generado por Sistema Pascual Parabrisas", 0, 1, 'L')

def generar_pdf_pascual(datos_cliente, datos_vehiculo, productos, servicios):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=20) 
    
    # --- 1. TABLA DATOS DEL CLIENTE ---
    pdf.set_y(70) 
    
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(190, 6, "  DATOS DEL CLIENTE", 1, 1, 'L', 1)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, " Señor(es)", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(85, 6, f": {str(datos_cliente.get('nombre', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Fecha Emisión", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(55, 6, f": {datetime.now().strftime('%d/%m/%Y')}", 'R', 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " RUT", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(85, 6, f": {str(datos_cliente.get('rut', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Teléfono", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(55, 6, f": {str(datos_cliente.get('fono', ''))}", 'R', 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Dirección", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(85, 6, f": {str(datos_cliente.get('direccion', '')).upper()}"[:45], 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(30, 6, " Forma de Pago", 0, 0); pdf.set_font('Arial', '', 8); pdf.cell(50, 6, f": {str(datos_cliente.get('pago', '')).upper()}", 'R', 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Ciudad", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(85, 6, f": {str(datos_cliente.get('ciudad', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Comuna", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(55, 6, f": {str(datos_cliente.get('comuna', '')).upper()}", 'R', 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Giro", 'L,B', 0); pdf.set_font('Arial', '', 9); pdf.cell(85, 6, f": {str(datos_cliente.get('giro', '')).upper()}"[:45], 'B', 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Vendedor", 'B', 0); pdf.set_font('Arial', '', 9); pdf.cell(55, 6, ": ANA MARIA RIQUELME", 'R,B', 1)
    
    pdf.ln(4)
    
    # --- 2. TABLA DATOS DEL VEHÍCULO ---
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(190, 6, "  DATOS DEL VEHÍCULO", 1, 1, 'L', 1)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(25, 6, " Marca", 'L', 0); pdf.set_font('Arial', '', 9); pdf.cell(70, 6, f": {str(datos_vehiculo.get('marca', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Modelo", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(70, 6, f": {str(datos_vehiculo.get('modelo', '')).upper()}", 'R', 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Año", 'L,B', 0); pdf.set_font('Arial', '', 9); pdf.cell(70, 6, f": {str(datos_vehiculo.get('anio', ''))}", 'B', 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 6, " Patente", 'B', 0); pdf.set_font('Arial', '', 9); pdf.cell(70, 6, f": {str(datos_vehiculo.get('patente', '')).upper()}", 'R,B', 1)

    pdf.ln(6)

    # --- 3. TABLA DETALLE DE COTIZACIÓN ---
    pdf.set_font('Arial', 'B', 9); pdf.set_fill_color(230, 230, 230)
    pdf.cell(130, 7, "Descripción", 1, 0, 'C', 1)
    pdf.cell(30, 7, "Descuento", 1, 0, 'C', 1)
    pdf.cell(30, 7, "Total", 1, 1, 'C', 1)
    
    total_general = 0

    def imprimir_fila(desc, total):
        x = pdf.get_x(); y = pdf.get_y()
        pdf.multi_cell(130, 6, desc, 1, 'L')
        h = pdf.get_y() - y 
        pdf.set_xy(x + 130, y)
        pdf.cell(30, h, "$0", 1, 0, 'C')
        pdf.cell(30, h, format_clp(total), 1, 1, 'R')
        pdf.set_xy(x, y + h)

    if productos:
        pdf.set_font('Arial', 'B', 8); pdf.set_fill_color(245, 245, 245)
        pdf.cell(190, 5, "  PRODUCTOS / REPUESTOS", 1, 1, 'L', 1)
        pdf.set_font('Arial', '', 9)
        for item in productos:
            imprimir_fila(item['Descripción'].upper(), item['Total'])
            total_general += item['Total']
            
    if servicios:
        pdf.set_font('Arial', 'B', 8); pdf.set_fill_color(245, 245, 245)
        pdf.cell(190, 5, "  MANO DE OBRA / SERVICIOS", 1, 1, 'L', 1)
        pdf.set_font('Arial', '', 9)
        for item in servicios:
            imprimir_fila(item['Descripción'].upper(), item['Total'])
            total_general += item['Total']

    neto = total_general / 1.19
    iva = total_general - neto
    
    pdf.ln(5)
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(35, 6, "SUB TOTAL", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(25, 6, format_clp(total_general), 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9); pdf.cell(35, 6, "DESCUENTO", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(25, 6, "$0", 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9); pdf.cell(35, 6, "NETO", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(25, 6, format_clp(neto), 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9); pdf.cell(35, 6, "I.V.A. (19%)", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(25, 6, format_clp(iva), 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(35, 8, "TOTAL", 1, 0, 'L', 1); pdf.cell(25, 8, format_clp(total_general), 1, 1, 'R', 1)

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 7. UI PRINCIPAL (FLUJO PASO A PASO)
# ==========================================
if 'check_borrador' not in st.session_state:
    st.session_state.check_borrador = True
    borrador_recuperado = cargar_borrador_nube()
    if borrador_recuperado and 'cliente_confirmado' in borrador_recuperado:
        st.session_state.borrador_pendiente = borrador_recuperado

if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 1

col_centro = st.columns([1, 2, 1])

# --- CABECERA PRINCIPAL ---
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
        
        opciones_pago = ["Transferencia Electrónica", "Efectivo / Contado", "Tarjeta (Débito/Crédito)", "Orden de Compra (O/C)", "Crédito Directo a 30 días"]
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
            st.markdown(f"**Cliente:** {st.session_state.get('cliente_confirmado', '')} | **RUT:** {st.session_state.get('rut_confirmado', '')}")
        st.markdown("---")
        
        # --- DATOS DEL VEHÍCULO GLOBAL CON OPCIÓN DE AGREGAR MANUALMENTE ---
        st.markdown("#### 🚗 Datos del Vehículo")
        c_v1, c_v2, c_v3, c_v4 = st.columns(4)
        
        lista_marcas = list(BASE_VEHICULOS.keys())
        if "--- AGREGAR OTRA MARCA ---" not in lista_marcas:
            lista_marcas.append("--- AGREGAR OTRA MARCA ---")
            
        marca_sel = c_v1.selectbox("Marca", lista_marcas, key="v_marca")
        
        if marca_sel == "--- AGREGAR OTRA MARCA ---":
            marca_final = c_v1.text_input("Escriba la Marca:", placeholder="Ej: Motorhome", key="v_marca_man").upper()
            modelos_lista = ["--- AGREGAR OTRO MODELO ---"]
        else:
            marca_final = marca_sel
            modelos_lista = BASE_VEHICULOS.get(marca_sel, ["---"]).copy()
            if "--- AGREGAR OTRO MODELO ---" not in modelos_lista:
                modelos_lista.append("--- AGREGAR OTRO MODELO ---")
                
        modelo_sel = c_v2.selectbox("Modelo", modelos_lista, key="v_modelo")
        
        if modelo_sel == "--- AGREGAR OTRO MODELO ---":
            modelo_final = c_v2.text_input("Escriba el Modelo:", placeholder="Ej: Ducato L3H2", key="v_modelo_man").upper()
        else:
            modelo_final = modelo_sel
            
        lista_anios = ["---"] + list(range(2027, 1979, -1)) + ["OTRO (MÁS ANTIGUO)"]
        anio_sel = c_v3.selectbox("Año (Opcional)", lista_anios, key="v_anio")
        
        if anio_sel == "OTRO (MÁS ANTIGUO)":
            anio_final = c_v3.text_input("Escriba el Año:", placeholder="Ej: 1975", key="v_anio_man")
        else:
            anio_final = anio_sel
            
        patente_sel = c_v4.text_input("Patente (Obligatoria)", placeholder="Ej: ABCD12", key="v_pat")
        st.markdown("---")

        tab1, tab2 = st.tabs(["📦 Productos", "🔧 Servicios"])
        
        with tab1:
            st.markdown("##### 1. Selector de Cristal Dinámico (Selección Múltiple)")
            
            tipo_carroceria = st.radio("Seleccione el Tipo de Vehículo:", 
                                       ["Automóvil / SUV", "Camioneta / Pick-up", "Furgón / Van", "Camión", "Micro / Bus"], 
                                       horizontal=True)
            st.markdown("---")
            
            if tipo_carroceria == "Automóvil / SUV":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL VEHÍCULO</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns([1, 2, 1])
                c_f2.button("🟩 PARABRISAS FRONTAL", type=btn_type("PARABRISAS FRONTAL"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS FRONTAL",))
                c_d1, c_d2, c_d3, c_d4 = st.columns(4)
                c_d1.button("Aleta D. Izq", type=btn_type("ALETA DEL. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("ALETA DEL. IZQ.",))
                c_d2.button("Puerta D. Izq", type=btn_type("PUERTA DEL. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. IZQ.",))
                c_d3.button("Puerta D. Der", type=btn_type("PUERTA DEL. DER."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. DER.",))
                c_d4.button("Aleta D. Der", type=btn_type("ALETA DEL. DER."), use_container_width=True, on_click=toggle_cristal, args=("ALETA DEL. DER.",))
                c_t1, c_t2, c_t3, c_t4 = st.columns(4)
                c_t1.button("Aleta T. Izq", type=btn_type("ALETA TRAS. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("ALETA TRAS. IZQ.",))
                c_t2.button("Puerta T. Izq", type=btn_type("PUERTA TRAS. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA TRAS. IZQ.",))
                c_t3.button("Puerta T. Der", type=btn_type("PUERTA TRAS. DER."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA TRAS. DER.",))
                c_t4.button("Aleta T. Der", type=btn_type("ALETA TRAS. DER."), use_container_width=True, on_click=toggle_cristal, args=("ALETA TRAS. DER.",))
                
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA", type=btn_type("LUNETA TRASERA"), use_container_width=True, on_click=toggle_cristal, args=("LUNETA TRASERA",))
                
                c_o1, c_o2, c_o3 = st.columns([1, 2, 1])
                c_o2.button("⬜ SUNROOF / TECHO PANORÁMICO", type=btn_type("SUNROOF / TECHO PANORÁMICO"), use_container_width=True, on_click=toggle_cristal, args=("SUNROOF / TECHO PANORÁMICO",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PARTE TRASERA</div>", unsafe_allow_html=True)
            
            elif tipo_carroceria == "Camioneta / Pick-up":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL VEHÍCULO</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns([1, 2, 1])
                c_f2.button("🟩 PARABRISAS FRONTAL", type=btn_type("PARABRISAS FRONTAL"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS FRONTAL",))
                c_d1, c_d2 = st.columns(2)
                c_d1.button("Puerta Del. Izq", type=btn_type("PUERTA DEL. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. IZQ.",))
                c_d2.button("Puerta Del. Der", type=btn_type("PUERTA DEL. DER."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. DER.",))
                c_t1, c_t2 = st.columns(2)
                c_t1.button("Puerta Tras. Izq", type=btn_type("PUERTA TRAS. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA TRAS. IZQ.",))
                c_t2.button("Puerta Tras. Der", type=btn_type("PUERTA TRAS. DER."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA TRAS. DER.",))
                c_a1, c_a2 = st.columns(2)
                c_a1.button("Aleta Izquierda", type=btn_type("ALETA IZQUIERDA"), use_container_width=True, on_click=toggle_cristal, args=("ALETA IZQUIERDA",))
                c_a2.button("Aleta Derecha", type=btn_type("ALETA DERECHA"), use_container_width=True, on_click=toggle_cristal, args=("ALETA DERECHA",))
                
                c_s1, c_s2, c_s3 = st.columns([1, 2, 1])
                c_s2.button("⬜ SUNROOF / TECHO PANORÁMICO", type=btn_type("SUNROOF / TECHO PANORÁMICO"), use_container_width=True, on_click=toggle_cristal, args=("SUNROOF / TECHO PANORÁMICO",))
                
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA CABINA", type=btn_type("LUNETA TRASERA"), use_container_width=True, on_click=toggle_cristal, args=("LUNETA TRASERA",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PICK-UP (CARGA)</div>", unsafe_allow_html=True)
                
            elif tipo_carroceria == "Furgón / Van":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL VEHÍCULO</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns([1, 2, 1])
                c_f2.button("🟩 PARABRISAS FRONTAL", type=btn_type("PARABRISAS FRONTAL"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS FRONTAL",))
                
                c_d1, c_d2, c_d3, c_d4 = st.columns(4)
                c_d1.button("Aleta D. Izq", type=btn_type("ALETA DEL. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("ALETA DEL. IZQ.",))
                c_d2.button("Puerta D. Izq", type=btn_type("PUERTA DEL. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. IZQ.",))
                c_d3.button("Puerta D. Der", type=btn_type("PUERTA DEL. DER."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. DER.",))
                c_d4.button("Aleta D. Der", type=btn_type("ALETA DEL. DER."), use_container_width=True, on_click=toggle_cristal, args=("ALETA DEL. DER.",))
                
                c_l1, c_l2, c_l3 = st.columns(3)
                c_l1.button("Lateral Fijo Izq", type=btn_type("LATERAL FIJO IZQ."), use_container_width=True, on_click=toggle_cristal, args=("LATERAL FIJO IZQ.",))
                c_l2.button("Lateral Corredera", type=btn_type("PUERTA LATERAL CORREDERA"), use_container_width=True, on_click=toggle_cristal, args=("PUERTA LATERAL CORREDERA",))
                c_l3.button("Lateral Fijo Der", type=btn_type("LATERAL FIJO DER."), use_container_width=True, on_click=toggle_cristal, args=("LATERAL FIJO DER.",))
                
                c_t1, c_t2 = st.columns(2)
                c_t1.button("Luneta Izquierda", type=btn_type("LUNETA TRASERA IZQ."), use_container_width=True, on_click=toggle_cristal, args=("LUNETA TRASERA IZQ.",))
                c_t2.button("Luneta Derecha", type=btn_type("LUNETA TRASERA DER."), use_container_width=True, on_click=toggle_cristal, args=("LUNETA TRASERA DER.",))
                
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PARTE TRASERA CARGA</div>", unsafe_allow_html=True)

            elif tipo_carroceria == "Camión":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DE CABINA</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns(3)
                c_f1.button("Parabrisas Izq", type=btn_type("PARABRISAS IZQUIERDO"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS IZQUIERDO",))
                c_f2.button("Parabrisas Entero", type=btn_type("PARABRISAS FRONTAL"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS FRONTAL",))
                c_f3.button("Parabrisas Der", type=btn_type("PARABRISAS DERECHO"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS DERECHO",))
                c_d1, c_d2 = st.columns(2)
                c_d1.button("Puerta Del. Izq", type=btn_type("PUERTA DEL. IZQ."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. IZQ.",))
                c_d2.button("Puerta Del. Der", type=btn_type("PUERTA DEL. DER."), use_container_width=True, on_click=toggle_cristal, args=("PUERTA DEL. DER.",))
                c_a1, c_a2 = st.columns(2)
                c_a1.button("Aleta Litera Izq", type=btn_type("ALETA LITERA IZQ."), use_container_width=True, on_click=toggle_cristal, args=("ALETA LITERA IZQ.",))
                c_a2.button("Aleta Litera Der", type=btn_type("ALETA LITERA DER."), use_container_width=True, on_click=toggle_cristal, args=("ALETA LITERA DER.",))
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA CABINA", type=btn_type("LUNETA TRASERA"), use_container_width=True, on_click=toggle_cristal, args=("LUNETA TRASERA",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>RESPALDO CABINA</div>", unsafe_allow_html=True)

            elif tipo_carroceria == "Micro / Bus":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL BUS</div>", unsafe_allow_html=True)
                c_f1, c_f2 = st.columns(2)
                c_f1.button("Parabrisas Superior", type=btn_type("PARABRISAS SUPERIOR"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS SUPERIOR",))
                c_f2.button("Parabrisas Inferior", type=btn_type("PARABRISAS INFERIOR"), use_container_width=True, on_click=toggle_cristal, args=("PARABRISAS INFERIOR",))
                c_d1, c_d2 = st.columns(2)
                c_d1.button("Puerta Chofer Izq", type=btn_type("PUERTA CHOFER"), use_container_width=True, on_click=toggle_cristal, args=("PUERTA CHOFER",))
                c_d2.button("Puerta Acceso Der", type=btn_type("PUERTA ACCESO PASAJEROS"), use_container_width=True, on_click=toggle_cristal, args=("PUERTA ACCESO PASAJEROS",))
                st.button("Vidrio Lateral Salón Pasajeros", type=btn_type("VIDRIO LATERAL SALÓN PASAJEROS"), use_container_width=True, on_click=toggle_cristal, args=("VIDRIO LATERAL SALÓN PASAJEROS",))
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA BUS", type=btn_type("LUNETA TRASERA"), use_container_width=True, on_click=toggle_cristal, args=("LUNETA TRASERA",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PARTE TRASERA BUS</div>", unsafe_allow_html=True)

            # LÓGICA DE VISIBILIDAD DE CÁMARA Y SENSOR
            camara_sel = "No"
            sensor_sel = "No"
            if any("PARABRISAS" in c for c in st.session_state.cristales_sel):
                c_v4, c_v5 = st.columns(2)
                camara_sel = c_v4.radio("¿Tiene Cámara?", ["No", "Sí"], horizontal=True, key="v_cam")
                sensor_sel = c_v5.radio("¿Sensor de Lluvia?", ["No", "Sí"], horizontal=True, key="v_sen")

            # --- CARRITO DE SELECCIÓN MÚLTIPLE EN FILAS SEPARADAS CON LLAVES ÚNICAS ---
            st.markdown("##### 🛒 2. Detalle de Productos a Agregar")
            
            cristales_a_procesar = st.session_state.cristales_sel if st.session_state.cristales_sel else ["CRISTAL / REPUESTO"]
            
            productos_temp = []
            with st.container():
                for i, cristal in enumerate(cristales_a_procesar):
                    desc_sugerida = cristal
                    
                    key_id = cristal.replace(" ", "_").replace("/", "_").replace(".", "")
                    
                    if marca_final and marca_final not in ["--- Seleccione Marca ---", "--- AGREGAR OTRA MARCA ---", "---"]:
                        desc_sugerida += f" {marca_final}"
                        if modelo_final and modelo_final not in ["---", "--- AGREGAR OTRO MODELO ---"]:
                            desc_sugerida += f" {modelo_final}"
                        if anio_final and anio_final not in ["---", "OTRO (MÁS ANTIGUO)"]:
                            desc_sugerida += f" {anio_final}"

                    if "PARABRISAS" in cristal:
                        if camara_sel == "Sí": 
                            desc_sugerida += " C/CÁMARA"
                            key_id += "_cam"
                        if sensor_sel == "Sí": 
                            desc_sugerida += " C/SENSOR"
                            key_id += "_sen"
                    
                    col_p1, col_p2 = st.columns([3, 1])
                    d_p = col_p1.text_input(f"Descripción Producto {i+1}", value=desc_sugerida, key=f"d_p_{key_id}")
                    p_p = col_p2.number_input("Valor c/IVA ($)", min_value=0, step=5000, key=f"p_p_{key_id}")
                    productos_temp.append({"desc": d_p, "precio": p_p})
                
                if st.button("➕ Agregar Producto(s) al Presupuesto", use_container_width=True):
                    agregados = 0
                    for p in productos_temp:
                        if p['desc'] and p['precio'] > 0:
                            st.session_state.items_productos.append({
                                "Descripción": p['desc'], 
                                "Cantidad": 1, 
                                "Unitario": p['precio'], 
                                "Total": p['precio']
                            })
                            agregados += 1
                    
                    if agregados > 0:
                        st.session_state.cristales_sel = [] 
                        guardar_borrador_nube()
                        st.rerun()
                    else:
                        st.warning("⚠️ Debes ingresar un valor mayor a $0 para agregar.")
            
            if st.session_state.items_productos:
                st.markdown("---")
                for item in st.session_state.items_productos: st.text(f"• {item['Descripción']} | {format_clp(item['Total'])}")
                if st.button("🗑️ Borrar Productos"): st.session_state.items_productos = []; guardar_borrador_nube(); st.rerun()

        with tab2:
            st.markdown("##### ⚡ Servicios Frecuentes")
            c_sf1, c_sf2, c_sf3, c_sf4 = st.columns(4)
            c_sf1.button("Instalación", use_container_width=True, on_click=set_servicio, args=("INSTALACIÓN DE CRISTAL",))
            c_sf2.button("Reparación Piquete", use_container_width=True, on_click=set_servicio, args=("REPARACIÓN DE PIQUETE",))
            c_sf3.button("Polarizado", use_container_width=True, on_click=set_servicio, args=("SERVICIO DE POLARIZADO",))
            c_sf4.button("Grabado Patentes", use_container_width=True, on_click=set_servicio, args=("GRABADO DE PATENTES",))
            
            st.markdown("##### 🔧 Detalle de Mano de Obra")
            with st.container():
                col_s1, col_s2 = st.columns([3, 1])
                d_s = col_s1.text_input("Descripción del Servicio", value=st.session_state.servicio_desc, placeholder="Seleccione un servicio rápido...")
                p_s = col_s2.number_input("Valor c/IVA ($)", min_value=0, step=5000, key="p_serv")
                
                if st.button("➕ Agregar Servicio", use_container_width=True):
                    if d_s and p_s > 0:
                        st.session_state.items_servicios.append({"Descripción": d_s, "Cantidad": 1, "Unitario": p_s, "Total": p_s})
                        st.session_state.servicio_desc = ""
                        guardar_borrador_nube(); st.rerun()
                        
            if st.session_state.items_servicios:
                st.markdown("---")
                for item in st.session_state.items_servicios: st.text(f"• {item['Descripción']} | {format_clp(item['Total'])}")
                if st.button("🗑️ Borrar Servicios"): st.session_state.items_servicios = []; guardar_borrador_nube(); st.rerun()

        total_prod = sum(x['Total'] for x in st.session_state.items_productos)
        total_serv = sum(x['Total'] for x in st.session_state.items_servicios)
        total_bruto = total_prod + total_serv

        if total_bruto > 0:
            st.markdown("---")
            st.subheader(f"📊 TOTAL COTIZACIÓN: {format_clp(total_bruto)}")

            if 'presupuesto_generado' not in st.session_state:
                if st.button("💾 GENERAR COTIZACIÓN", type="primary", use_container_width=True):
                    
                    if not patente_sel.strip():
                        st.error("⛔ La Patente del vehículo es obligatoria para generar la cotización.")
                    else:
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
                        
                        datos_vehiculo = {
                            "marca": marca_final if marca_final not in ["--- Seleccione Marca ---", "--- AGREGAR OTRA MARCA ---", "---"] else "",
                            "modelo": modelo_final if modelo_final not in ["---", "--- AGREGAR OTRO MODELO ---"] else "",
                            "anio": anio_final if anio_final not in ["---", "OTRO (MÁS ANTIGUO)"] else "",
                            "patente": formato_patente_chilena(patente_sel)
                        }
                        
                        pdf_bytes = generar_pdf_pascual(datos_cliente, datos_vehiculo, st.session_state.items_productos, st.session_state.items_servicios)
                        st.session_state['presupuesto_generado'] = {'pdf': pdf_bytes, 'nombre': f"Cotizacion_{correlativo}_{st.session_state.get('cliente_confirmado', 'CLIENTE')}.pdf"}
                        limpiar_borrador_nube() 
                        st.rerun()
            else:
                data = st.session_state['presupuesto_generado']
                st.success(f"✅ Cotización N° {st.session_state.get('correlativo_temp', '')} generada.")
                st.download_button("📥 DESCARGAR PDF", data['pdf'], data['nombre'], "application/pdf", type="primary", use_container_width=True)
