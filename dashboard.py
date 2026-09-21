import pandas as pd
import streamlit as st
import re
from datetime import time

# 1. Configuración de la página
st.set_page_config(page_title="Dashboard ZKTeco - Automático", layout="wide")
st.title("📊 Generador Automático de Reporte de Asistencia")

# ==========================================
# REGLAS DE NEGOCIO Y COLORES
# ==========================================
def clasificar_asistencia(hora_entrada):
    """Clasifica la hora de entrada según las reglas de la empresa."""
    if pd.isna(hora_entrada):
        return "Falta Registro"
    
    # ¡AQUÍ AJUSTAS TUS HORARIOS! (Hora, Minuto)
    limite_puntual = time(8, 50)       # Antes de 8:50 AM
    limite_ras = time(9, 0)          # Hasta las 9:00 AM
    limite_retardo = time(9, 15)       # Hasta las 9:15 AM
    
    if hora_entrada <= limite_puntual:
        return "Puntual"
    elif hora_entrada <= limite_ras:
        return "Puntualidad al ras"
    elif hora_entrada <= limite_retardo:
        return "Retardo"
    else:
        return "Falta"

def colorear_estatus(val):
    """Asigna colores estilo semáforo a la celda dependiendo del texto."""
    colores = {
        'Puntual': 'background-color: #A9DFBF; color: black;',       # Verde claro
        'Puntualidad al ras': 'background-color: #F9E79F; color: black;', # Amarillo claro
        'Retardo': 'background-color: #F5B041; color: black;',       # Naranja
        'Falta': 'background-color: #F1948A; color: black;',         # Rojo
        'Falta Registro': 'background-color: #D2B4DE; color: black;' # Morado
    }
    return colores.get(val, '')

# ==========================================
# MOTOR DEL DASHBOARD
# ==========================================
st.sidebar.header("⚙️ Panel de Control")
archivo_subido = st.sidebar.file_uploader("Sube el reporte ZKTeco (Excel)", type=["xls", "xlsx"])

if archivo_subido is not None:
    st.sidebar.success("¡Archivo cargado! Procesando datos...")
    
    with st.spinner('Aplicando reglas lógicas y colores...'):
        # 1. Extracción de datos en crudo (Tu código ETL)
        df_raw = pd.read_excel(archivo_subido, sheet_name='Reporte de Asistencia', header=None)
        periodo_str = str(df_raw.iloc[2, 2])
        año_mes = periodo_str[0:7] 
        
        registros = []
        for i in range(4, len(df_raw), 2):
            fila_datos = df_raw.iloc[i]
            
            # --- INICIO DEL FRENO DE SEGURIDAD ---
            if (i + 1) < len(df_raw):
                fila_checadas = df_raw.iloc[i+1]
            else:
                break # Si ya no hay fila de abajo, terminamos de leer
            # --- FIN DEL FRENO DE SEGURIDAD ---
            
            if str(fila_datos[0]).strip() != "ID:": continue
            nombre_emp = fila_datos[10]
            departamento = fila_datos[20]
            
            for col_dia in range(2, df_raw.shape[1]):
                dia = df_raw.iloc[3, col_dia]
                if pd.isna(dia): continue 
                    
                fecha = f"{año_mes}-{int(dia):02d}"
                checadas = str(fila_checadas[col_dia])
                
                if checadas != 'nan' and checadas.strip() != '':
                    lista_horas = re.findall(r'.{5}', checadas.strip())
                    for hora in lista_horas:
                        registros.append({
                            'Nombre': nombre_emp,
                            'Departamento': departamento,
                            'Fecha': fecha,
                            'Hora': hora
                        })
                        
        df_limpio = pd.DataFrame(registros)
        df_limpio['Hora'] = pd.to_datetime(df_limpio['Hora'], format='%H:%M').dt.time
        
        # 2. Agrupación para sacar Entrada y Salida
        df_resumen = df_limpio.groupby(['Fecha', 'Departamento', 'Nombre'])['Hora'].agg(['min', 'max']).reset_index()
        df_resumen.columns = ['Fecha', 'Departamento', 'Nombre', 'Hora Entrada', 'Hora Salida']
        df_resumen.loc[df_resumen['Hora Entrada'] == df_resumen['Hora Salida'], 'Hora Salida'] = None
        #########3
        # 3. Aplicar Lógica de Negocio (Clasificación)
        df_resumen['Estatus'] = df_resumen['Hora Entrada'].apply(clasificar_asistencia)
        
        # 4. Generar Observaciones Automáticas
        # 4. Generar Observaciones Automáticas
        def generar_observacion(estatus):
            if estatus == 'Puntual' or estatus == 'Puntualidad al ras':
                return "Excelente puntualidad"
            elif estatus == 'Retardo':
                return "Cuidar horarios de llegada"
            elif estatus == 'Falta':
                return "Revisar justificación"
            return "Falta checada de salida"
            
        df_resumen['Observaciones'] = df_resumen['Estatus'].apply(generar_observacion)

        # --- INICIA LO NUEVO: AGREGAR COLUMNAS DEL PDF ---
        df_resumen['Retardos'] = 0       
        df_resumen['Faltas'] = 0         
        df_resumen['Horas extra'] = 0
        df_resumen['Horas pagadas'] = 0
        df_resumen['Sueldo'] = 0.0
        # --- TERMINA LO NUEVO ---

    # ==========================================
    # INTERFAZ VISUAL
    # ==========================================
    
    st.subheader("📋 Reporte de Asistencia Formateado")
    
    # Filtro interactivo opcional
    departamentos = df_resumen['Departamento'].unique()
    depto_sel = st.selectbox("Filtrar por Departamento:", ["Todos"] + list(departamentos))
    if depto_sel != "Todos":
        df_resumen = df_resumen[df_resumen['Departamento'] == depto_sel]

    # Aplicar los colores a la tabla
    tabla_coloreada = df_resumen.style.map(colorear_estatus, subset=['Estatus'])
    
    # Mostrar en Streamlit (¡Ahora es editable!)
    st.data_editor(tabla_coloreada, use_container_width=True, height=500)
    
    # Botón de Descarga
    st.download_button(
        label="📥 Descargar Datos Limpios (CSV)",
        data=df_resumen.to_csv(index=False).encode('utf-8'),
        file_name='asistencia_automatizada.csv',
        mime='text/csv'
    )
    # Botón de Descarga
    # (Opcional: puedes exportarlo a Excel para que conserve los colores)
    st.download_button(
        label="📥 Descargar Datos Limpios (CSV)",
        data=df_resumen.to_csv(index=False).encode('utf-8'),
        file_name='asistencia_automatizada.csv',
        mime='text/csv'
    )
else:
    st.info("👈 Sube tu archivo Excel en el panel izquierdo para generar el reporte semaforizado.")