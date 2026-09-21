import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
    if pd.isna(hora_entrada):
        return "Falta Registro"
    
    limite_puntual = time(9, 15)    # Cualquier hora hasta las 9:15 es Puntual
    limite_retardo = time(10, 0)    # De 9:16 a 10:00 es Retardo
    
    if hora_entrada <= limite_puntual:
        return "Puntual"
    elif hora_entrada <= limite_retardo:
        return "Retardo"
    else:
        return "Falta" # Asigné las 10:00 AM como límite para que se considere Falta
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
#   PARA ENVIAR A EMPLEDOS POR CORREO
# ==========================================
# Diccionario de empleados (Asegúrate de que el nombre coincida EXACTAMENTE con el de ZKTeco)
correos_empleados = {
    "Arelett": "neilfloresescobedo5@gmail.com"
}
def enviar_correo_asistencia(nombre, correo_destino, df_empleado):
    # Credenciales del remitente (Recursos Humanos)
    correo_rh = "floresneil070@gmail.com"
    password = "majk jluc nonh rrsb" # Más abajo te explico cómo sacar esta contraseña
    
    mensaje = MIMEMultipart()
    mensaje['From'] = correo_rh
    mensaje['To'] = correo_destino
    mensaje['Subject'] = f"Registro de Asistencia Mensual - {nombre}"
    
    # Convertir la tabla del empleado a formato HTML para el correo
    columnas = ['Fecha', 'Hora Entrada', 'Hora Salida', 'Estatus']
    tabla_html = df_empleado[columnas].to_html(index=False, justify='center')
    
    cuerpo = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h3>Hola {nombre},</h3>
        <p>Adjunto encontrarás tu registro de entradas y salidas.</p>
        {tabla_html}
        <p>Si notas alguna anomalía, favor de contactar a Recursos Humanos.</p>
      </body>
    </html>
    """
    mensaje.attach(MIMEText(cuerpo, 'html'))
    
    # Conexión al servidor de Gmail y envío
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as servidor:
            servidor.starttls()
            servidor.login(correo_rh, password)
            servidor.send_message(mensaje)
        return True
    except Exception as e:
        return False

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
        # 3. Aplicar Lógica de Negocio (Clasificación Diaria)
        df_resumen['Estatus'] = df_resumen['Hora Entrada'].apply(clasificar_asistencia)
        
        # --- NUEVO: AGRUPACIÓN TOTAL POR EMPLEADO ---
        
        # A. Contar cuántos días en total asistió cada empleado
        df_dias = df_resumen.groupby(['Departamento', 'Nombre'])['Fecha'].count().reset_index()
        df_dias.rename(columns={'Fecha': 'Días Asistidos'}, inplace=True)
        
        # B. Contar cuántas veces tuvo cada estatus (Retardo, Falta, Puntual)
        df_estatus = df_resumen.groupby(['Departamento', 'Nombre', 'Estatus']).size().unstack(fill_value=0).reset_index()
        
        # C. Asegurar que las columnas existan (por si en un mes nadie tiene faltas)
        for col in ['Puntual', 'Puntualidad al ras', 'Retardo', 'Falta']:
            if col not in df_estatus.columns:
                df_estatus[col] = 0
                
        # D. Unir todo en la tabla final
        df_final = pd.merge(df_dias, df_estatus, on=['Departamento', 'Nombre'])
        
        # E. Agregar las columnas para captura manual
        df_final['Observaciones'] = ""
# ==========================================
    # 4. INTERFAZ VISUAL: REGISTRO GENERAL
    # ==========================================
    st.subheader("⏱️ Registro General de Entradas y Salidas")
    st.write("Historial diario completo de todos los trabajadores.")
    
    # Mostrar la tabla completa con colores
    st.dataframe(
        df_resumen.style.map(colorear_estatus, subset=['Estatus']), 
        use_container_width=True,
        height=400
    )
    
    # Botón para descargar este registro detallado
    st.download_button(
        label="📥 Descargar Registro Diario (CSV)",
        data=df_resumen.to_csv(index=False).encode('utf-8-sig'),
        file_name='registro_diario_completo.csv',
        mime='text/csv',
        key='descarga_diaria'
    )
    
    st.markdown("---")

    # ==========================================
    # 5. INTERFAZ VISUAL: REPORTE CONSOLIDADO (Lo que ya tenías)
    # ==========================================
    st.subheader("📋 Resumen Mensual para Nómina")
    
    # Mostrar la tabla consolidada y editable en Streamlit
    tabla_editable = st.data_editor(
        df_final, 
        use_container_width=True, 
        height=500,
        # Bloqueamos las columnas calculadas para que no se borren por error
        disabled=['Departamento', 'Nombre', 'Días Asistidos', 'Puntual', 'Puntualidad al ras', 'Retardo', 'Falta'] 
    )
    
   # Botón de Descarga
    st.download_button(
        label="📥 Descargar Reporte Consolidado (CSV)",
        data=tabla_editable.to_csv(index=False).encode('utf-8-sig'),
        file_name='reporte_nomina_agrupado.csv',
        mime='text/csv',
        key='descarga_nomina' # <--- ESTA LÍNEA SOLUCIONA EL ERROR
    )
    st.markdown("---")
    st.subheader("✉️ Notificaciones Automáticas")
    st.write("Enviar reporte individual detallado a cada trabajador por correo electrónico.")
    
    if st.button("Enviar correos a todos los empleados"):
        # Barra de progreso visual
        barra = st.progress(0)
        total_empleados = len(correos_empleados)
        empleados_procesados = 0
        
        for nombre, correo in correos_empleados.items():
            # Filtrar solo los datos de ese empleado
            df_filtro = df_resumen[df_resumen['Nombre'] == nombre]
            
            if not df_filtro.empty:
                exito = enviar_correo_asistencia(nombre, correo, df_filtro)
                if exito:
                    st.success(f"Correo enviado a {nombre} ({correo})")
                else:
                    st.error(f"Error al enviar a {nombre}")
            else:
                st.warning(f"No se encontraron registros para {nombre}")
                
            # Actualizar barra de progreso
            empleados_procesados += 1
            barra.progress(empleados_procesados / total_empleados)
            
        st.info("Proceso de envío finalizado.")