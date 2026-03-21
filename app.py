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
# 2. RUT, CORRELATIVOS, CLIENTES Y BORRADORES
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
# 3. DATOS DE LA EMPRESA Y ESTILOS
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
    
    /* Restauramos el header y el MainMenu para poder cambiar a modo oscuro */
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
# 4. CLASE PDF (FORMATO OPEN TPV)
# ==========================================
class PDF(FPDF):
    def __init__(self, correlativo=""):
        super().__init__()
        self.correlativo = correlativo

    def header(self):
        logo_path = encontrar_imagen("logo") 
        if logo_path: self.image(logo_path, x=10, y=8, w=50)
        
        self.set_xy(10, 25)
        self.set_font('Arial', 'B', 9); self.cell(100, 4, EMPRESA_NOMBRE, 0, 1, 'L')
        self.set_font('Arial', '', 8)
        self.cell(100, 4, EMPRESA_GIRO, 0, 1, 'L')
        self.cell(100, 4, f"C.M.: {DIRECCION}", 0, 1, 'L')
        self.set_font('Arial', 'B', 9); self.cell(100, 4, f"R.U.T.: {RUT_EMPRESA}", 0, 1, 'L')

        self.set_xy(140, 15)
        self.set_font('Arial', 'B', 16)
        self.cell(60, 8, "COTIZACIÓN", 0, 1, 'C')
        self.set_x(140); self.set_font('Arial', 'B', 14)
        titulo = f"N° {self.correlativo}" if self.correlativo else "N° BORRADOR"
        self.cell(60, 8, titulo, 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(150, 150, 150)
        self.cell(0, 5, "Documento generado por Sistema Pascual Parabrisas", 0, 1, 'L')

def generar_pdf_pascual(datos_cliente, productos, servicios):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=20) 
    
    pdf.set_y(45)
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, "Señor(es)", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, f": {str(datos_cliente.get('nombre', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "Fecha Emision", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, f": {datetime.now().strftime('%d/%m/%Y')}", 0, 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, "Rut", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, f": {str(datos_cliente.get('rut', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "Teléfono", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, f": {str(datos_cliente.get('fono', ''))}", 0, 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, "Dirección", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, f": {str(datos_cliente.get('direccion', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "Forma de Pago", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, f": {str(datos_cliente.get('pago', '')).upper()}", 0, 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, "Ciudad", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, f": {str(datos_cliente.get('ciudad', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "Comuna", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, f": {str(datos_cliente.get('comuna', '')).upper()}", 0, 1)

    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, "Giro", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(90, 5, f": {str(datos_cliente.get('giro', '')).upper()}", 0, 0)
    pdf.set_font('Arial', 'B', 9); pdf.cell(25, 5, "O/C", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, ": ", 0, 1)
    
    pdf.set_font('Arial', 'B', 9); pdf.cell(20, 5, "Vendedor", 0, 0); pdf.set_font('Arial', '', 9); pdf.cell(0, 5, ": ANA MARIA RIQUELME", 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 9); pdf.set_fill_color(240, 240, 240)
    pdf.cell(100, 6, "Descripcion", 1, 0, 'L', 1)
    pdf.cell(30, 6, "Valor", 1, 0, 'R', 1)
    pdf.cell(15, 6, "Cant.", 1, 0, 'C', 1)
    pdf.cell(15, 6, "Desc.", 1, 0, 'C', 1)
    pdf.cell(30, 6, "Total", 1, 1, 'R', 1)
    
    pdf.set_font('Arial', '', 9)
    total_general = 0

    if productos:
        pdf.set_font('Arial', 'B', 8); pdf.cell(0, 6, "--- PRODUCTOS / REPUESTOS ---", 0, 1, 'L'); pdf.set_font('Arial', '', 9)
        for item in productos:
            pdf.cell(100, 6, item['Descripción'].upper(), 0, 0, 'L')
            pdf.cell(30, 6, format_clp(item['Unitario']), 0, 0, 'R')
            pdf.cell(15, 6, str(item['Cantidad']), 0, 0, 'C')
            pdf.cell(15, 6, "$0", 0, 0, 'C')
            pdf.cell(30, 6, format_clp(item['Total']), 0, 1, 'R')
            total_general += item['Total']
            
    if servicios:
        pdf.set_font('Arial', 'B', 8); pdf.cell(0, 6, "--- MANO DE OBRA / SERVICIOS ---", 0, 1, 'L'); pdf.set_font('Arial', '', 9)
        for item in servicios:
            pdf.cell(100, 6, item['Descripción'].upper(), 0, 0, 'L')
            pdf.cell(30, 6, format_clp(item['Unitario']), 0, 0, 'R')
            pdf.cell(15, 6, str(item['Cantidad']), 0, 0, 'C')
            pdf.cell(15, 6, "$0", 0, 0, 'C')
            pdf.cell(30, 6, format_clp(item['Total']), 0, 1, 'R')
            total_general += item['Total']

    neto = total_general / 1.19
    iva = total_general - neto
    
    pdf.ln(10)
    pdf.set_x(130); pdf.set_font('Arial', 'B', 9)
    pdf.cell(30, 5, "SUB TOTAL", 0, 0, 'L'); pdf.cell(5, 5, ":", 0, 0, 'C'); pdf.cell(25, 5, format_clp(total_general), 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', '', 9)
    pdf.cell(30, 5, "DESC. GRAL", 0, 0, 'L'); pdf.cell(5, 5, ":", 0, 0, 'C'); pdf.cell(25, 5, "0", 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 5, "NETO", 0, 0, 'L'); pdf.cell(5, 5, ":", 0, 0, 'C'); pdf.cell(25, 5, format_clp(neto), 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 5, "I.V.A. (19%)", 0, 0, 'L'); pdf.cell(5, 5, ":", 0, 0, 'C'); pdf.cell(25, 5, format_clp(iva), 0, 1, 'R')
    pdf.set_x(130)
    pdf.cell(30, 5, "EXENTO", 0, 0, 'L'); pdf.cell(5, 5, ":", 0, 0, 'C'); pdf.cell(25, 5, "0", 0, 1, 'R')
    pdf.set_x(130); pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 6, "TOTAL", 0, 0, 'L'); pdf.cell(5, 6, ":", 0, 0, 'C'); pdf.cell(25, 6, format_clp(total_general), 0, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL (FLUJO PASO A PASO)
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
        condicion_pago = c_f2.selectbox("Forma de Pago", ["CONTADO", "CREDITO DIRECTO", "TRANSFERENCIA", "TARJETA"])

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

        # --- MÓDULO DE ADMINISTRACIÓN DE CLIENTES ---
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
            with st.container():
                col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
                d_p = col_p1.text_input("Descripción del Producto", placeholder="Ej: Parabrisas...")
                q_p = col_p2.number_input("Cant.", min_value=1, value=1, key="q_prod")
                p_p = col_p3.number_input("Valor c/IVA ($)", min_value=0, step=5000, key="p_prod")
                
                if st.button("➕ Agregar Producto", use_container_width=True):
                    if d_p and p_p > 0:
                        st.session_state.items_productos.append({"Descripción": d_p, "Cantidad": q_p, "Unitario": p_p, "Total": p_p * q_p})
                        guardar_borrador_nube(); st.rerun()
            
            if st.session_state.items_productos:
                for item in st.session_state.items_productos: st.text(f"• {item['Cantidad']}x {item['Descripción']} | {format_clp(item['Total'])}")
                if st.button("🗑️ Borrar Productos"): st.session_state.items_productos = []; guardar_borrador_nube(); st.rerun()

        with tab2:
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
