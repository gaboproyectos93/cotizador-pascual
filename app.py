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
                # Agregamos la columna Forma Pago al historial
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
RUT_EMPRESA = "76.XXX.XXX-X" 
DIRECCION = "Dirección de Pascual" 
TELEFONO = "+56 9 XXXX XXXX" 
EMAIL = "contacto@pascualparabrisas.cl" 

# Tono Naranja Corporativo basado en su Instagram
NARANJA_PASCUAL = (225, 100, 25) 
COLOR_HEX = "#E16419"

# Inyectamos CSS para pintar la App de Naranjo
st.markdown(f"""
<style>
    /* Bordes de contenedores */
    .stContainer {{ border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 10px; margin-bottom: 5px; }}
    div[data-testid="stNumberInput"] input {{ max-width: 150px; text-align: center; }}
    input[type=number]::-webkit-inner-spin-button {{ -webkit-appearance: none; margin: 0; }}
    
    /* Botones primarios Naranjos */
    .stButton > button[kind="primary"] {{
        background-color: {COLOR_HEX} !important;
        border-color: {COLOR_HEX} !important;
        color: white !important;
        font-weight: bold;
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: #C05010 !important;
        border-color: #C05010 !important;
    }}
    
    /* Pestañas */
    .stTabs [aria-selected="true"] {{ background-color: {COLOR_HEX} !important; color: white !important; border-radius: 4px;}}
    
    /* Radio buttons */
    div[data-testid="stRadio"] > label {{ font-weight: bold; color: {COLOR_HEX}; }}
</style>
""", unsafe_allow_html=True)

LISTA_ASEGURADORAS = ["--- Seleccione Compañía ---", "BCI Seguros", "Liberty Seguros", "Mapfre", "HDI Seguros", "Consorcio", "Chilena Consolidada", "Reale Seguros", "Sura", "Zenit", "Unnio", "Otra..."]
LISTA_MARCAS = ["--- Seleccione Marca ---", "Audi", "BMW", "Chery", "Chevrolet", "Changan", "Citroën", "Dodge", "Dongfeng", "Fiat", "Ford", "Foton", "Great Wall", "Honda", "Hyundai", "JAC", "Jeep", "Kia", "Maxus", "Mazda", "Mercedes-Benz", "MG", "Mitsubishi", "Nissan", "Peugeot", "Renault", "SsangYong", "Subaru", "Suzuki", "Toyota", "Volkswagen", "Volvo", "Otra..."]
# Generar años desde el próximo hasta 1990
LISTA_ANOS = list(range(datetime.now().year + 1, 1989, -1))
LISTA_PAGOS = ["--- Seleccione ---", "Orden de Compra (Empresas/Kaufmann)", "Transferencia Electrónica", "Contado / Efectivo", "Tarjeta Crédito / Débito", "Pago de Deducible (Seguros)"]

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
# 4. PDF (DISEÑO CORPORATIVO ALINEADO)
# ==========================================
class PDF(FPDF):
    def __init__(self, logo_header=None, correlativo=""):
        super().__init__()
        self.logo_header = logo_header
        self.correlativo = correlativo

    def header(self):
        self.set_xy(130, 10)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
        titulo = "PRESUPUESTO"
        if self.correlativo and self.correlativo != "BORRADOR": titulo += f" N° {self.correlativo}"
        self.cell(70, 10, titulo, 1, 1, 'C')
        
        self.set_xy(130, 20)
        self.set_text_color(0, 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(70, 8, f"Fecha Emisión: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'C')

        logo_footer = encontrar_imagen("logo") 
        if logo_footer: self.image(logo_footer, x=10, y=8, w=35)

        self.set_xy(48, 10)
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
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.line(10, 275, 200, 275)
        self.cell(0, 5, "Documento generado automáticamente - Pascual Parabrisas", 0, 1, 'C')

def generar_pdf_parabrisas(cliente_tipo, cliente_nombre, rut_empresa, marca, modelo, ano, patente, condicion_pago, items, total_neto, fotos_adjuntas):
    pdf = PDF(correlativo=st.session_state.get('correlativo_temp', 'BORRADOR'))
    pdf.add_page(); pdf.set_auto_page_break(auto=True, margin=30) 
    
    pdf.set_font('Arial', 'I', 10); pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 5, "De nuestra consideración: Por medio de la presente, y en respuesta a su solicitud, presentamos la siguiente propuesta técnica y económica para la provisión e instalación de cristales automotrices y/o servicios asociados.")
    pdf.ln(5)

    # Identificación
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, " 1. IDENTIFICACIÓN DEL CLIENTE Y VEHÍCULO", 1, 1, 'L', 1)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', 'B', 10)
    pdf.cell(35, 7, "TIPO CLIENTE:", 'L', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(cliente_tipo).upper(), 'R', 1)

    pdf.set_font('Arial', 'B', 10)
    label_cliente = "COMPAÑÍA:" if cliente_tipo == "Compañía de Seguros" else "CLIENTE:"
    pdf.cell(35, 7, label_cliente, 'L', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(cliente_nombre).upper(), 'R', 1)
    
    if cliente_tipo == "Empresa" and rut_empresa:
        pdf.set_font('Arial', 'B', 10); pdf.cell(35, 7, "RUT EMPRESA:", 'L', 0)
        pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(rut_empresa).upper(), 'R', 1)

    pdf.set_font('Arial', 'B', 10); pdf.cell(35, 7, "MARCA:", 'L', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(50, 7, str(marca).upper(), 0, 0)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(25, 7, "MODELO:", 0, 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(modelo).upper(), 'R', 1)

    # Quitamos borde inferior a Año y Patente para agregar la forma de pago abajo
    pdf.set_font('Arial', 'B', 10); pdf.cell(35, 7, "AÑO:", 'L', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(50, 7, str(ano), 0, 0)
    
    pdf.set_font('Arial', 'B', 10); pdf.cell(25, 7, "PATENTE:", 0, 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(patente).upper() if patente else "S/P", 'R', 1)

    # Nueva Fila: Forma de Pago
    pdf.set_font('Arial', 'B', 10); pdf.cell(35, 7, "FORMA PAGO:", 'L,B', 0)
    pdf.set_font('Arial', '', 10); pdf.cell(0, 7, str(condicion_pago).upper(), 'R,B', 1)

    pdf.ln(8)
    
    # Tabla de Ítems
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
    pdf.set_text_color(255,255,255)
    pdf.cell(0, 8, " 2. DETALLE DE CRISTALES Y SERVICIOS", 1, 1, 'L', 1)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(110, 8, "DESCRIPCIÓN", 1, 0, 'C', 1)
    pdf.cell(20, 8, "CANT.", 1, 0, 'C', 1)
    pdf.cell(30, 8, "PRECIO UNIT.", 1, 0, 'C', 1)
    pdf.cell(30, 8, "TOTAL", 1, 1, 'C', 1)
    
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

    # --- ALINEACIÓN PERFECTA DEL TOTAL ---
    # La tabla mide 190mm de ancho. Empezamos en X=10. Termina en 200.
    # Los cuadros de Total medirán 40 + 30 = 70.
    # Si seteamos X=130, terminan exactamente en 200, alineándose con el borde derecho.
    pdf.ln(2)
    iva = total_neto * 0.19; bruto = total_neto + iva
    pdf.set_x(130); pdf.cell(40, 7, "Valor Neto:", 1, 0, 'L'); pdf.cell(30, 7, format_clp(total_neto), 1, 1, 'R')
    pdf.set_x(130); pdf.cell(40, 7, "IVA (19%):", 1, 0, 'L'); pdf.cell(30, 7, format_clp(iva), 1, 1, 'R')
    pdf.set_font('Arial', 'B', 10); pdf.set_x(130)
    pdf.set_text_color(NARANJA_PASCUAL[0], NARANJA_PASCUAL[1], NARANJA_PASCUAL[2])
    pdf.cell(40, 8, "TOTAL A PAGAR:", 1, 0, 'L'); pdf.cell(30, 8, format_clp(bruto), 1, 1, 'R')
    pdf.set_text_color(0,0,0)

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
    pdf.ln(20)
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
        # Mostrar logo en grande arriba del título si existe
        logo_main = encontrar_imagen("logo") 
        if logo_main: st.image(logo_main, width=250)
        
        st.title("Cotizador de Cristales")
        st.markdown("#### 1. Identificación de Cliente y Vehículo")
        
        st.markdown("**Tipo de Cliente**")
        cliente_tipo = st.radio("", ("Particular", "Empresa", "Compañía de Seguros"), horizontal=True, label_visibility="collapsed")
        
        cliente_final = ""; rut_empresa = ""
        
        if cliente_tipo == "Compañía de Seguros":
            cliente_final = st.selectbox("Compañía de Seguros", LISTA_ASEGURADORAS)
        elif cliente_tipo == "Empresa":
            c_e1, c_e2 = st.columns([3, 1])
            cliente_final = c_e1.text_input("Nombre de la Empresa", placeholder="Ej: Transportes Garmendia, Kaufmann...")
            rut_empresa = c_e2.text_input("RUT Empresa", placeholder="Ej: 77.123.456-7")
        else:
            cliente_final = st.text_input("Nombre del Cliente Particular", placeholder="Ej: Juan Pérez")
            
        # --- MEJORA: Condición de Pago ---
        condicion_pago = st.selectbox("Condición de Pago Acordada", LISTA_PAGOS)

        st.markdown("---")
        st.markdown("**Datos del Vehículo**")
        c_m1, c_m2 = st.columns(2)
        marca_input = c_m1.selectbox("Marca", LISTA_MARCAS)
        modelo_input = c_m2.text_input("Modelo", placeholder="Ej: Hilux, Sprinter, Yaris...")
        
        c_a1, c_a2 = st.columns(2)
        # --- MEJORA: Lista desplegable de años (por defecto el año actual que es index 1) ---
        ano_input = c_a1.selectbox("Año", LISTA_ANOS, index=1)
        patente_input = c_a2.text_input("Patente (Opcional)", placeholder="Ej: AB-CD-12")
        
        if st.button("🚀 PASO SIGUIENTE: AGREGAR CRISTALES", type="primary", use_container_width=True):
            error = False
            if cliente_tipo == "Compañía de Seguros" and cliente_final == "--- Seleccione Compañía ---":
                st.error("⛔ Por favor, seleccione una Compañía de Seguros."); error = True
            elif not cliente_final and cliente_tipo != "Compañía de Seguros":
                st.error("⛔ Por favor, ingrese el nombre del Cliente."); error = True
            elif condicion_pago == "--- Seleccione ---":
                st.error("⛔ Por favor, seleccione una Condición de Pago."); error = True
            elif marca_input == "--- Seleccione Marca ---":
                st.error("⛔ Por favor, seleccione la Marca del vehículo."); error = True
            elif not modelo_input:
                st.error("⛔ Por favor, ingrese el Modelo."); error = True
                
            if not error:
                st.session_state.cliente_tipo_confirmado = cliente_tipo
                st.session_state.cliente_confirmado = cliente_final.upper()
                st.session_state.rut_empresa_confirmado = rut_empresa.upper()
                st.session_state.pago_confirmado = condicion_pago
                st.session_state.marca_confirmada = marca_input.upper()
                st.session_state.modelo_confirmado = modelo_input.upper()
                st.session_state.ano_confirmado = ano_input
                st.session_state.patente_confirmada = patente_input.upper()
                st.session_state.paso_actual = 2
                st.rerun()

# --- PASO 2: COTIZADOR MANUAL ---
elif st.session_state.paso_actual == 2:
    c_tip = st.session_state.cliente_tipo_confirmado
    c_cli = st.session_state.cliente_confirmado
    c_mar = st.session_state.marca_confirmada
    c_mod = st.session_state.modelo_confirmado
    c_ano = st.session_state.ano_confirmado
    c_pag = st.session_state.pago_confirmado
    
    c1, c2 = st.columns([1, 5])
    with c1: 
        if st.button("⬅️ Volver"): st.session_state.paso_actual = 1; st.rerun()
    with c2: st.markdown(f"### 🪟 <span style='color:{COLOR_HEX};'>{c_mar} {c_mod} ({c_ano})</span> | {c_tip}: {c_cli}", unsafe_allow_html=True)
    
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
        
        st.subheader("📊 Resumen Final")
        k1, k2, k3 = st.columns(3)
        k1.metric("Valor Neto", format_clp(total_neto))
        iva = total_neto * 0.19; k2.metric("IVA (19%)", format_clp(iva))
        total_final = total_neto + iva; k3.metric("TOTAL A PAGAR", format_clp(total_final))

        st.markdown("### 📸 Fotografías (Crucial para Seguros)")
        fotos_adjuntas = st.file_uploader("Adjuntar fotos de daños, padrón o vehículo", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])

        if 'presupuesto_generado' not in st.session_state:
            if st.button("💾 GENERAR PDF Y GUARDAR", type="primary", use_container_width=True):
                correlativo = obtener_y_registrar_correlativo(c_tip, c_cli, c_mar, c_mod, c_ano, st.session_state.patente_confirmada, c_pag, format_clp(total_final))
                st.session_state['correlativo_temp'] = correlativo
                
                pdf_bytes = generar_pdf_parabrisas(c_tip, c_cli, st.session_state.rut_empresa_confirmado, c_mar, c_mod, c_ano, st.session_state.patente_confirmada, c_pag, seleccion_final, total_neto, fotos_adjuntas)
                st.session_state['presupuesto_generado'] = {'pdf': pdf_bytes, 'nombre': f"Presupuesto {correlativo} - {c_mar} {c_mod}.pdf"}
                st.rerun()
        else:
            data = st.session_state['presupuesto_generado']
            st.success(f"✅ Presupuesto N° {st.session_state['correlativo_temp']} generado.")
            st.download_button("📥 DESCARGAR PDF", data['pdf'], data['nombre'], "application/pdf", type="primary", use_container_width=True)
            if st.button("🔄 Nueva Cotización", use_container_width=True): reset_session()
