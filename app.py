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
st.set_page_config(page_title="Cotizador Pascual Parabrisas", layout="wide", page_icon="🪟")

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
def obtener_y_registrar_correlativo(cliente, marca, modelo, ano, patente, total):
    client = conectar_google_sheets()
    if client:
        try:
            spreadsheet = client.open(NOMBRE_HOJA_GOOGLE)
            try: worksheet_hist = spreadsheet.worksheet("Historial")
            except:
                worksheet_hist = spreadsheet.add_worksheet(title="Historial", rows="1000", cols="8")
                worksheet_hist.append_row(["Fecha", "Hora", "Correlativo", "Cliente", "Marca", "Modelo", "Año", "Patente", "Monto Total"])
            
            datos = worksheet_hist.get_all_values()
            numero_actual = len(datos) 
            correlativo_str = str(numero_actual)
            
            ahora = datetime.now()
            worksheet_hist.append_row([ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S"), correlativo_str, cliente, marca, modelo, ano, patente, total])
            return correlativo_str
        except Exception as e: 
            return "ERR"
    else: return "OFFLINE"

# ==========================================
# 3. DATOS DE LA EMPRESA (PASCUAL PARABRISAS)
# ==========================================
EMPRESA_NOMBRE = "PASCUAL PARABRISAS"
EMPRESA_TITULAR = "Venta e Instalación de Cristales Automotrices"
RUT_EMPRESA = "76.XXX.XXX-X" # Reemplazar cuando Ana María te lo dé
DIRECCION = "Dirección de Pascual" # Reemplazar
TELEFONO = "+56 9 XXXX XXXX" # Reemplazar
EMAIL = "contacto@pascualparabrisas.cl" # Reemplazar

LISTA_MARCAS = [
    "--- Seleccione Marca ---", "Audi", "BMW", "Chery", "Chevrolet", "Changan", "Citroën", 
    "Dodge", "Dongfeng", "Fiat", "Ford", "Foton", "Great Wall", "Honda", "Hyundai", 
    "JAC", "Jeep", "Kia", "Maxus", "Mazda", "Mercedes-Benz", "MG", "Mitsubishi", 
    "Nissan", "Peugeot", "Renault", "SsangYong", "Subaru", "Suzuki", "Toyota", 
    "Volkswagen", "Volvo", "Otra..."
]

def format_clp(value):
    try: return f"${float(value):,.0f}".replace(",", ".")
    except: return "$0"

def reset_session():
    st.query_params.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.markdown("""
<style>
    .stContainer { border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 10px; margin-bottom: 5px; }
    div[data-testid="stNumberInput"] input { max-width: 150px; text-align: center; }
    input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. PDF (ADAPTADO A PARABRISAS)
# ==========================================
class PDF(FPDF):
    def __init__(self, logo_header=None, correlativo=""):
        super().__init__()
        self.logo_header = logo_header
        self.correlativo = correlativo

    def header(self):
        self.set_xy(130, 10)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(20, 80, 150) # Tono azul cristal
        titulo = "PRESUPUESTO"
        if self.correlativo and self.correlativo != "BORRADOR": 
            titulo += f" N° {self.correlativo}"
        self.cell(70, 10, titulo, 1, 1, 'C')
        
        self.set_xy(130, 20)
        self.set_text_color(0, 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(70, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C')

        self.set_xy(10, 10)
        self.set_font('Arial', 'B', 14) 
        self.cell(115, 6, EMPRESA_NOMBRE, 0, 1, 'L')
        self.set_font('Arial', '', 9)
        self.cell(115, 5, EMPRESA_TITULAR, 0, 1, 'L')
        self.cell(115, 5, f"RUT: {RUT_EMPRESA}", 0, 1, 'L')
        self.cell(115, 5, f"Dirección: {DIRECCION}", 0, 1, 'L')
        self.cell(115, 5, f"Teléfono: {TELEFONO}", 0, 1, 'L')
        self.cell(115, 5, f"E-mail: {EMAIL}", 0, 1, 'L')
        self.ln(12)

    def footer(self):
        self.set_y(-30); self.set_font('Arial', 'I', 8); self.line(10, 265, 200, 265)
        self.multi_cell(0, 5, "Validez oferta: 15 días. Sujeto a disponibilidad de stock.", 0, 'C')

def generar_pdf_parabrisas(cliente, marca, modelo, ano, patente, items, total_neto, fotos_adjuntas):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30) 
    
    # Identificación
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(220, 235, 250) # Fondo celestito
    pdf.cell(0, 8, " IDENTIFICACIÓN DEL CLIENTE Y VEHÍCULO", 1, 1, 'L', 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(35, 7, "CLIENTE / CÍA:", 'L', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(cliente).upper(), 'R', 1)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(35, 7, "MARCA:", 'L', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(50, 7, str(marca).upper(), 0, 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 7, "MODELO:", 0, 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(modelo).upper(), 'R', 1)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(35, 7, "AÑO:", 'L,B', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(50, 7, str(ano), 'B', 0)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(25, 7, "PATENTE:", 'B', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(patente).upper() if patente else "S/P", 'R,B', 1)

    pdf.ln(8)
    
    # Tabla de Ítems
    pdf.set_font('Arial', 'B', 9); pdf.set_fill_color(30, 80, 140); pdf.set_text_color(255,255,255)
    pdf.cell(110, 8, "DESCRIPCIÓN DEL CRISTAL / SERVICIO", 1, 0, 'C', 1)
    pdf.cell(20, 8, "CANT.", 1, 0, 'C', 1)
    pdf.cell(30, 8, "PRECIO", 1, 0, 'C', 1)
    pdf.cell(30, 8, "TOTAL", 1, 1, 'C', 1)
    pdf.ln(0)
    pdf.set_text_color(0,0,0); pdf.set_font('Arial', '', 9)

    for item in items:
        x = pdf.get_x(); y = pdf.get_y()
        pdf.multi_cell(110, 6, item['Descripción'].upper(), 1, 'L')
        h = pdf.get_y() - y
        pdf.set_xy(x+110, y)
        pdf.cell(20, h, str(item['Cantidad']), 1, 0, 'C')
        pdf.cell(30, h, format_clp(item['Unitario']), 1, 0, 'R')
        pdf.cell(30, h, format_clp(item['Total']), 1, 0, 'R')
        pdf.set_xy(x, y + h)

    pdf.ln(5)
    iva = total_neto * 0.19; bruto = total_neto + iva
    pdf.set_x(120); pdf.cell(40, 7, "Valor Neto:", 1, 0, 'L'); pdf.cell(30, 7, format_clp(total_neto), 1, 1, 'R')
    pdf.set_x(120); pdf.cell(40, 7, "IVA (19%):", 1, 0, 'L'); pdf.cell(30, 7, format_clp(iva), 1, 1, 'R')
    pdf.set_font('Arial', 'B', 10); pdf.set_x(120)
    pdf.cell(40, 8, "TOTAL A PAGAR:", 1, 0, 'L'); pdf.cell(30, 8, format_clp(bruto), 1, 1, 'R')
    pdf.set_text_color(0,0,0)

    # --- PÁGINA DE FOTOS ---
    if fotos_adjuntas:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14); pdf.set_text_color(20, 80, 150)
        pdf.cell(0, 10, "REGISTRO FOTOGRÁFICO DE DAÑOS / VEHÍCULO", 0, 1, 'C')
        pdf.ln(5)
        
        margin_x = 15; margin_y = 40 
        w_photo = 85; h_photo = 85; col_gap = 10; row_gap = 10
        
        for i, foto_uploaded in enumerate(fotos_adjuntas):
            if i > 0 and i % 4 == 0:
                pdf.add_page()
                pdf.cell(0, 10, "REGISTRO FOTOGRÁFICO (Cont.)", 0, 1, 'C')
            
            pos_page = i % 4; row = pos_page // 2; col = pos_page % 2
            x = margin_x + (col * (w_photo + col_gap))
            y = margin_y + (row * (h_photo + row_gap))
            
            try:
                img = Image.open(foto_uploaded)
                img = ImageOps.exif_transpose(img) 
                img = img.convert('RGB')
                img.thumbnail((600, 600))
                temp_filename = f"temp_img_{i}.jpg"
                img.save(temp_filename, quality=60, optimize=True)
                pdf.image(temp_filename, x=x, y=y, w=w_photo, h=h_photo)
                os.remove(temp_filename)
            except: pass

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI PRINCIPAL (FLUJO PASO A PASO)
# ==========================================
with st.sidebar:
    st.markdown("## 🪟 Pascual Parabrisas")
    st.markdown("---")
    if st.button("🗑️ Reiniciar / Nueva Cotización", type="primary", use_container_width=True): reset_session()

if 'paso_actual' not in st.session_state:
    st.session_state.paso_actual = 1

# --- PASO 1: DATOS DEL CLIENTE Y VEHÍCULO ---
if st.session_state.paso_actual == 1:
    col_centro = st.columns([1, 2, 1])
    with col_centro[1]:
        st.title("Cotizador de Cristales")
        st.markdown("#### 1. Identificación del Vehículo")
        
        cliente_input = st.text_input("Cliente / Aseguradora", placeholder="Ej: Particular, BCI Seguros, Kaufmann...")
        
        c_m1, c_m2 = st.columns(2)
        marca_input = c_m1.selectbox("Marca del Vehículo", LISTA_MARCAS)
        modelo_input = c_m2.text_input("Modelo", placeholder="Ej: Hilux, Sprinter, Yaris...")
        
        c_a1, c_a2 = st.columns(2)
        ano_actual = datetime.now().year
        ano_input = c_a1.number_input("Año", min_value=1980, max_value=ano_actual+1, value=ano_actual, step=1)
        patente_input = c_a2.text_input("Patente (Opcional)", placeholder="Ej: AB-CD-12")
        
        if st.button("🚀 PASO SIGUIENTE: AGREGAR CRISTALES", type="primary", use_container_width=True):
            if not cliente_input or marca_input == "--- Seleccione Marca ---" or not modelo_input:
                st.error("⛔ Por favor, complete Cliente, Marca y Modelo.")
            else:
                st.session_state.cliente_confirmado = cliente_input.upper()
                st.session_state.marca_confirmada = marca_input.upper()
                st.session_state.modelo_confirmado = modelo_input.upper()
                st.session_state.ano_confirmado = ano_input
                st.session_state.patente_confirmada = patente_input.upper()
                st.session_state.paso_actual = 2
                st.rerun()

# --- PASO 2: COTIZADOR MANUAL ---
elif st.session_state.paso_actual == 2:
    c_cli = st.session_state.cliente_confirmado
    c_mar = st.session_state.marca_confirmada
    c_mod = st.session_state.modelo_confirmado
    c_ano = st.session_state.ano_confirmado
    
    c1, c2 = st.columns([1, 5])
    with c1: 
        if st.button("⬅️ Volver"): st.session_state.paso_actual = 1; st.rerun()
    with c2: st.markdown(f"### 🪟 {c_mar} {c_mod} ({c_ano}) | Cliente: {c_cli}")
    
    if 'items_manuales_parabrisas' not in st.session_state: st.session_state.items_manuales_parabrisas = []
    
    st.markdown("---")
    st.markdown("#### ➕ Ingreso de Cristales o Servicios")
    
    with st.container():
        d_m = st.text_input("Descripción (Ej: Parabrisas Original, Instalación, Pegamento...)", placeholder="¿Qué se va a instalar/cobrar?")
        col_m1, col_m2 = st.columns(2)
        q_m = col_m1.number_input("Cantidad", min_value=1, value=1)
        p_m = col_m2.number_input("Precio Unitario Neto ($)", min_value=0, value=None, step=5000, placeholder="Ej: 85000")
        
        if st.button("Agregar a la cotización", type="secondary"):
            if d_m and p_m is not None and p_m >= 0:
                st.session_state.items_manuales_parabrisas.append({"Descripción": d_m, "Cantidad": q_m, "Unitario": p_m, "Total": p_m * q_m})
                st.success("✅ Ítem agregado.")
                time.sleep(0.5)
                st.rerun()
            else: 
                st.warning("⚠️ Ingrese descripción y un precio válido.")

    seleccion_final = st.session_state.items_manuales_parabrisas

    if seleccion_final:
        st.markdown("---")
        st.markdown("###### Ítems Agregados:")
        for idx, item in enumerate(seleccion_final):
            st.text(f"• {item['Cantidad']}x {item['Descripción'][:50]} | {format_clp(item['Total'])}")
        if st.button("🗑️ Borrar Lista"): st.session_state.items_manuales_parabrisas = []; st.rerun()

        st.markdown("---")
        total_neto = sum(x['Total'] for x in seleccion_final)
        
        st.subheader("📊 Resumen Final")
        k1, k2, k3 = st.columns(3)
        k1.metric("Valor Neto", format_clp(total_neto))
        iva = total_neto * 0.19; k2.metric("IVA (19%)", format_clp(iva))
        total_final = total_neto + iva; k3.metric("TOTAL A PAGAR", format_clp(total_final))

        st.markdown("### 📸 Fotografías (Crucial para Seguros)")
        fotos_adjuntas = st.file_uploader("Adjuntar fotos de daños, padrón o vehículo", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])

        if 'presupuesto_generado' not in st.session_state:
            if st.button("💾 GENERAR PDF Y GUARDAR", type="primary", use_container_width=True):
                # Generar correlativo real en la nube
                correlativo = obtener_y_registrar_correlativo(c_cli, c_mar, c_mod, c_ano, st.session_state.patente_confirmada, format_clp(total_final))
                st.session_state['correlativo_temp'] = correlativo
                
                pdf_bytes = generar_pdf_parabrisas(c_cli, c_mar, c_mod, c_ano, st.session_state.patente_confirmada, seleccion_final, total_neto, fotos_adjuntas)
                st.session_state['presupuesto_generado'] = {'pdf': pdf_bytes, 'nombre': f"Presupuesto {correlativo} - {c_mar} {c_mod}.pdf"}
                st.rerun()
        else:
            data = st.session_state['presupuesto_generado']
            st.success(f"✅ Presupuesto N° {st.session_state['correlativo_temp']} generado.")
            st.download_button("📥 DESCARGAR PDF", data['pdf'], data['nombre'], "application/pdf", type="primary", use_container_width=True)