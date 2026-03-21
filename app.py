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
    except:
        return rut_limpio

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
        datos = {k: v for k, v in st.session_state.items() if k.endswith('_confirmado') or k.endswith('_confirmada') or k == 'paso_actual' or k == 'items_productos' or k == 'items_servicios' or k == 'cristal_sel'}
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
# 5. LÓGICA DE TECLADO DE AUTO
# ==========================================
if 'cristal_sel' not in st.session_state:
    st.session_state.cristal_sel = "PARABRISAS"

def set_cristal(cristal):
    st.session_state.cristal_sel = cristal

# ==========================================
# 6. CLASE PDF (DISEÑO TABULAR ORDENADO)
# ==========================================
class PDF(FPDF):
    def __init__(self, correlativo=""):
        super().__init__()
        self.correlativo = correlativo

    def header(self):
        logo_path = encontrar_imagen("logo") 
        if logo_path: self.image(logo_path, x=10, y=8, w=50)
        
        self.set_xy(10, 40) 
        self.set_font('Arial', 'B', 9); self.cell(100, 4, EMPRESA_NOMBRE, 0, 1, 'L')
        self.set_font('Arial', '', 8)
        self.cell(100, 4, EMPRESA_GIRO, 0, 1, 'L')
        self.cell(100, 4, f"C.M.: {DIRECCION}", 0, 1, 'L')
        self.set_font('Arial', 'B', 9); self.cell(100, 4, f"R.U.T.: {RUT_EMPRESA}", 0, 1, 'L')

        self.set_xy(140, 15)
        self.set_font('Arial', 'B', 16)
        self.cell(60, 8, "COTIZACIÓN", 'LTR', 1, 'C')
        
        self.set_x(140)
        self.set_font('Arial', 'B', 14)
        titulo = f"N° {self.correlativo}" if self.correlativo else "N° BORRADOR"
        self.cell(60, 8, titulo, 'LBR', 1, 'C')
        self.ln(15)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(150, 150, 150)
        self.cell(0, 5, "Documento generado por Sistema Pascual Parabrisas", 0, 1, 'L')

def generar_pdf_pascual(datos_cliente, productos, servicios):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=20) 
    
    pdf.set_y(45)
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
    
    pdf.ln(6)

    pdf.set_font('Arial', 'B', 9); pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 7, "Descripción", 1, 0, 'C', 1)
    pdf.cell(30, 7, "Valor Unit.", 1, 0, 'C', 1)
    pdf.cell(15, 7, "Cant.", 1, 0, 'C', 1)
    pdf.cell(15, 7, "Desc.", 1, 0, 'C', 1)
    pdf.cell(30, 7, "Total", 1, 1, 'C', 1)
    
    total_general = 0

    def imprimir_fila(desc, unitario, cant, total):
        x = pdf.get_x(); y = pdf.get_y()
        pdf.multi_cell(100, 6, desc, 1, 'L')
        h = pdf.get_y() - y 
        pdf.set_xy(x + 100, y)
        pdf.cell(30, h, format_clp(unitario), 1, 0, 'R')
        pdf.cell(15, h, str(cant), 1, 0, 'C')
        pdf.cell(15, h, "$0", 1, 0, 'C')
        pdf.cell(30, h, format_clp(total), 1, 1, 'R')
        pdf.set_xy(x, y + h)

    if productos:
        pdf.set_font('Arial', 'B', 8); pdf.set_fill_color(245, 245, 245)
        pdf.cell(190, 5, "  PRODUCTOS / REPUESTOS", 1, 1, 'L', 1)
        pdf.set_font('Arial', '', 9)
        for item in productos:
            imprimir_fila(item['Descripción'].upper(), item['Unitario'], item['Cantidad'], item['Total'])
            total_general += item['Total']
            
    if servicios:
        pdf.set_font('Arial', 'B', 8); pdf.set_fill_color(245, 245, 245)
        pdf.cell(190, 5, "  MANO DE OBRA / SERVICIOS", 1, 1, 'L', 1)
        pdf.set_font('Arial', '', 9)
        for item in servicios:
            imprimir_fila(item['Descripción'].upper(), item['Unitario'], item['Cantidad'], item['Total'])
            total_general += item['Total']

    neto = total_general / 1.19
    iva = total_general - neto
    
    pdf.ln(5)
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(35, 6, "SUB TOTAL", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(35, 6, format_clp(total_general), 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9); pdf.cell(35, 6, "DESCUENTO", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(35, 6, "$0", 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9); pdf.cell(35, 6, "NETO", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(35, 6, format_clp(neto), 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 9); pdf.cell(35, 6, "I.V.A. (19%)", 1, 0, 'L'); pdf.set_font('Arial', '', 9); pdf.cell(35, 6, format_clp(iva), 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.set_font('Arial', 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(35, 8, "TOTAL", 1, 0, 'L', 1); pdf.cell(35, 8, format_clp(total_general), 1, 1, 'R', 1)

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
            st.markdown(f"**Cliente:** {st.session_state.get('cliente_confirmado', '')}")
            st.markdown(f"**RUT:** {st.session_state.get('rut_confirmado', '')}") 
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["📦 Productos", "🔧 Servicios"])
        
        with tab1:
            st.markdown("##### 🚗 1. Selector de Cristal Dinámico")
            
            # --- SELECTOR DE CARROCERÍA ---
            tipo_carroceria = st.radio("Seleccione el Tipo de Vehículo:", 
                                       ["Automóvil / SUV", "Camioneta / Pick-up", "Furgón / Van", "Camión", "Micro / Bus"], 
                                       horizontal=True)
            st.markdown("---")
            
            # --- BOTONERAS DINÁMICAS POR CARROCERÍA ---
            if tipo_carroceria == "Automóvil / SUV":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL VEHÍCULO</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns([1, 2, 1])
                c_f2.button("🟩 PARABRISAS FRONTAL", use_container_width=True, on_click=set_cristal, args=("PARABRISAS",))
                c_d1, c_d2, c_d3, c_d4 = st.columns(4)
                c_d1.button("Aleta D. Izq", use_container_width=True, on_click=set_cristal, args=("ALETA DEL. IZQ.",))
                c_d2.button("Puerta D. Izq", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. IZQ.",))
                c_d3.button("Puerta D. Der", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. DER.",))
                c_d4.button("Aleta D. Der", use_container_width=True, on_click=set_cristal, args=("ALETA DEL. DER.",))
                c_t1, c_t2, c_t3, c_t4 = st.columns(4)
                c_t1.button("Aleta T. Izq", use_container_width=True, on_click=set_cristal, args=("ALETA TRAS. IZQ.",))
                c_t2.button("Puerta T. Izq", use_container_width=True, on_click=set_cristal, args=("PUERTA TRAS. IZQ.",))
                c_t3.button("Puerta T. Der", use_container_width=True, on_click=set_cristal, args=("PUERTA TRAS. DER.",))
                c_t4.button("Aleta T. Der", use_container_width=True, on_click=set_cristal, args=("ALETA TRAS. DER.",))
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA", use_container_width=True, on_click=set_cristal, args=("LUNETA TRASERA",))
                c_o1, c_o2, c_o3 = st.columns([1, 2, 1])
                c_o2.button("⬜ ESCOTILLA / TECHO", use_container_width=True, on_click=set_cristal, args=("ESCOTILLA / TECHO",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PARTE TRASERA</div>", unsafe_allow_html=True)
            
            elif tipo_carroceria == "Camioneta / Pick-up":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL VEHÍCULO</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns([1, 2, 1])
                c_f2.button("🟩 PARABRISAS FRONTAL", use_container_width=True, on_click=set_cristal, args=("PARABRISAS",))
                c_d1, c_d2 = st.columns(2)
                c_d1.button("Puerta Del. Izq", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. IZQ.",))
                c_d2.button("Puerta Del. Der", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. DER.",))
                c_t1, c_t2 = st.columns(2)
                c_t1.button("Puerta Tras. Izq", use_container_width=True, on_click=set_cristal, args=("PUERTA TRAS. IZQ.",))
                c_t2.button("Puerta Tras. Der", use_container_width=True, on_click=set_cristal, args=("PUERTA TRAS. DER.",))
                c_a1, c_a2 = st.columns(2)
                c_a1.button("Aleta Izquierda", use_container_width=True, on_click=set_cristal, args=("ALETA IZQUIERDA",))
                c_a2.button("Aleta Derecha", use_container_width=True, on_click=set_cristal, args=("ALETA DERECHA",))
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA CABINA", use_container_width=True, on_click=set_cristal, args=("LUNETA TRASERA",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PICK-UP (CARGA)</div>", unsafe_allow_html=True)
                
            elif tipo_carroceria == "Furgón / Van":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL VEHÍCULO</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns([1, 2, 1])
                c_f2.button("🟩 PARABRISAS FRONTAL", use_container_width=True, on_click=set_cristal, args=("PARABRISAS",))
                
                # --- NUEVA BOTONERA PARA FURGÓN ---
                c_d1, c_d2, c_d3, c_d4 = st.columns(4)
                c_d1.button("Aleta D. Izq", use_container_width=True, on_click=set_cristal, args=("ALETA DEL. IZQ.",))
                c_d2.button("Puerta D. Izq", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. IZQ.",))
                c_d3.button("Puerta D. Der", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. DER.",))
                c_d4.button("Aleta D. Der", use_container_width=True, on_click=set_cristal, args=("ALETA DEL. DER.",))
                
                c_l1, c_l2, c_l3 = st.columns(3)
                c_l1.button("Lateral Fijo Izq", use_container_width=True, on_click=set_cristal, args=("LATERAL FIJO IZQ.",))
                c_l2.button("Lateral Corredera", use_container_width=True, on_click=set_cristal, args=("PUERTA LATERAL CORREDERA",))
                c_l3.button("Lateral Fijo Der", use_container_width=True, on_click=set_cristal, args=("LATERAL FIJO DER.",))
                
                c_t1, c_t2 = st.columns(2)
                c_t1.button("Luneta Izquierda", use_container_width=True, on_click=set_cristal, args=("LUNETA TRASERA IZQ.",))
                c_t2.button("Luneta Derecha", use_container_width=True, on_click=set_cristal, args=("LUNETA TRASERA DER.",))
                
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PARTE TRASERA CARGA</div>", unsafe_allow_html=True)

            elif tipo_carroceria == "Camión":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DE CABINA</div>", unsafe_allow_html=True)
                c_f1, c_f2, c_f3 = st.columns(3)
                c_f1.button("Parabrisas Izq", use_container_width=True, on_click=set_cristal, args=("PARABRISAS IZQUIERDO",))
                c_f2.button("Parabrisas Entero", use_container_width=True, on_click=set_cristal, args=("PARABRISAS",))
                c_f3.button("Parabrisas Der", use_container_width=True, on_click=set_cristal, args=("PARABRISAS DERECHO",))
                c_d1, c_d2 = st.columns(2)
                c_d1.button("Puerta Del. Izq", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. IZQ.",))
                c_d2.button("Puerta Del. Der", use_container_width=True, on_click=set_cristal, args=("PUERTA DEL. DER.",))
                c_a1, c_a2 = st.columns(2)
                c_a1.button("Aleta Litera Izq", use_container_width=True, on_click=set_cristal, args=("ALETA LITERA IZQ.",))
                c_a2.button("Aleta Litera Der", use_container_width=True, on_click=set_cristal, args=("ALETA LITERA DER.",))
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA CABINA", use_container_width=True, on_click=set_cristal, args=("LUNETA TRASERA",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>RESPALDO CABINA</div>", unsafe_allow_html=True)

            elif tipo_carroceria == "Micro / Bus":
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold;'>FRENTE DEL BUS</div>", unsafe_allow_html=True)
                c_f1, c_f2 = st.columns(2)
                c_f1.button("Parabrisas Superior", use_container_width=True, on_click=set_cristal, args=("PARABRISAS SUPERIOR",))
                c_f2.button("Parabrisas Inferior", use_container_width=True, on_click=set_cristal, args=("PARABRISAS INFERIOR",))
                c_d1, c_d2 = st.columns(2)
                c_d1.button("Puerta Chofer Izq", use_container_width=True, on_click=set_cristal, args=("PUERTA CHOFER",))
                c_d2.button("Puerta Acceso Der", use_container_width=True, on_click=set_cristal, args=("PUERTA ACCESO PASAJEROS",))
                st.button("Vidrio Lateral Salón Pasajeros", use_container_width=True, on_click=set_cristal, args=("VIDRIO LATERAL SALÓN PASAJEROS",))
                c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
                c_l2.button("🟦 LUNETA TRASERA BUS", use_container_width=True, on_click=set_cristal, args=("LUNETA TRASERA",))
                st.markdown("<div style='text-align: center; color: gray; font-size: 14px; font-weight: bold; margin-bottom: 15px;'>PARTE TRASERA BUS</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("##### 🚙 2. Especificaciones del Vehículo")
            with st.container():
                c_v1, c_v2, c_v3 = st.columns([2, 2, 1])
                marca_sel = c_v1.selectbox("Marca", list(BASE_VEHICULOS.keys()), key="v_marca")
                modelo_sel = c_v2.selectbox("Modelo", BASE_VEHICULOS.get(marca_sel, ["---"]), key="v_modelo")
                
                lista_anios = ["---"] + list(range(2027, 1979, -1))
                anio_sel = c_v3.selectbox("Año", lista_anios, key="v_anio")

                # LÓGICA DE VISIBILIDAD DE CÁMARA Y SENSOR (Solo si es parabrisas)
                camara_sel = "No"
                sensor_sel = "No"
                if "PARABRISAS" in st.session_state.cristal_sel:
                    c_v4, c_v5 = st.columns(2)
                    camara_sel = c_v4.radio("¿Tiene Cámara?", ["No", "Sí"], horizontal=True, key="v_cam")
                    sensor_sel = c_v5.radio("¿Sensor de Lluvia?", ["No", "Sí"], horizontal=True, key="v_sen")

            desc_sugerida = f"{st.session_state.cristal_sel}"
            if marca_sel != "--- Seleccione Marca ---":
                desc_sugerida += f" {marca_sel}"
                if modelo_sel != "---": desc_sugerida += f" {modelo_sel}"
                if anio_sel != "---": desc_sugerida += f" {anio_sel}"
                if camara_sel == "Sí": desc_sugerida += " C/CÁMARA"
                if sensor_sel == "Sí": desc_sugerida += " C/SENSOR"

            st.markdown("##### 🛒 3. Detalle del Producto")
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
