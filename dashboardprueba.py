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
def clasificar_asistencia(hora):
    # 1. Si la celda está vacía o no existe registro de entrada, es Falta porque no llegó
    if pd.isna(hora) or str(hora).strip() == "" or str(hora).strip() == "nan":
        return "Falta 🔴"
    
    hora_str = str(hora).strip()
    
    # 2. Rango de llegada puntual
    if hora_str <= "09:15:59":
        return "Puntual ✅"
        
    # 3. Cualquier registro después de las 9:15 es retardo (quitamos el límite de las 10 AM)
    else:
        return "Retardo 🟡"
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

def enviar_correo_asistencia(nombre, correo_destino, df_empleado):
    correo_rh = st.secrets["correo_rh"]
    password = st.secrets["password_correo"]
    
    mensaje = MIMEMultipart()
    mensaje['From'] = correo_rh
    mensaje['To'] = correo_destino
    mensaje['Subject'] = f"Reporte de Asistencia y Alertas - {nombre}"
    
    # Contar si hay registros incompletos para generar una alerta
    olvidos = (df_empleado['Estatus'] == 'Registro Incompleto ⚠️').sum()
    
    alerta_texto = ""
    if olvidos > 0:
        alerta_texto = f"""
        <div style="background-color: #ffcccc; padding: 10px; border-left: 5px solid red; margin-bottom: 15px;">
            <strong style="color: red;">⚠️ ATENCIÓN:</strong> Tienes <b>{olvidos} día(s)</b> donde olvidaste registrar tu entrada o salida (marcados como Registro Incompleto).
        </div>
        """
    
    columnas = ['Fecha', 'Hora Entrada', 'Hora Salida', 'Estatus']
    tabla_html = df_empleado[columnas].to_html(index=False, justify='center')
    
    cuerpo = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h3>Hola {nombre},</h3>
        <p>Adjunto encontrarás tu reporte completo de asistencias.</p>
        
        {alerta_texto}
        
        <p>Por favor, revisa la columna <b>Estatus</b> en la siguiente tabla:</p>
        {tabla_html}
        
        <br>
        <p>Cualquier duda, favor de contactar a Recursos Humanos.</p>
      </body>
    </html>
    """
    mensaje.attach(MIMEText(cuerpo, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as servidor:
            servidor.starttls()
            servidor.login(correo_rh, password)
            servidor.send_message(mensaje)
        return True
    except smtplib.SMTPException as e:
        return False

# ==========================================
# MOTOR DEL DASHBOARD
# ==========================================
st.sidebar.header("⚙️ Panel de Control")

# 1er Botón: Reporte ZKTeco
archivo_subido = st.sidebar.file_uploader("Sube el reporte ZKTeco (Excel)", type=["xls", "xlsx"])

# 2do Botón: Directorio de Correos
archivo_correos = st.sidebar.file_uploader("Sube el Directorio de Correos (Excel)", type=["xls", "xlsx"])

# Leer el Excel de correos y convertirlo en diccionario si el usuario ya lo subió
correos_empleados = {}
if archivo_correos is not None:
    df_correos = pd.read_excel(archivo_correos)
    # Convierte las dos columnas del Excel (Nombre y Correo) en un diccionario automático
    correos_empleados = dict(zip(df_correos['Nombre'], df_correos['Correo']))
    st.sidebar.success(f"¡Directorio cargado! {len(correos_empleados)} empleados listos para notificación.")
else:
    st.sidebar.info("Sube el directorio de correos para habilitar el botón de envío.")

if archivo_subido is not None:
    st.sidebar.success("¡Archivo ZKTeco cargado! Procesando datos...")
    # ... (AQUÍ CONTINÚA TU CÓDIGO NORMAL CON EL WITH ST.SPINNER...)
    
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
       # --- TRANSFORMACIÓN (Entradas y Salidas Diarias) ---
        df_inicial = df_limpio.groupby(['Fecha', 'Departamento', 'Nombre'])['Hora'].agg(['min', 'max']).reset_index()
        df_inicial.columns = ['Fecha', 'Departamento', 'Nombre', 'Hora Entrada', 'Hora Salida']

        # === 1. INYECTAR CALENDARIO OBLIGATORIO (SOLO L-V) ===
        fechas_unicas = df_inicial['Fecha'].dropna().unique()
        empleados_unicos = df_inicial[['Departamento', 'Nombre']].drop_duplicates()
        
        df_calendario = pd.DataFrame({'Fecha': fechas_unicas}).merge(empleados_unicos, how='cross')
        df_calendario['dia_semana'] = pd.to_datetime(df_calendario['Fecha']).dt.weekday
        
        # Exigimos asistencia SOLO de Lunes(0) a Viernes(4)
        df_calendario = df_calendario[df_calendario['dia_semana'] < 5].drop(columns=['dia_semana'])

        # OUTER JOIN: Cruza el calendario L-V con los registros reales (para no perder las horas del sábado)
        df_resumen = pd.merge(df_calendario, df_inicial, on=['Fecha', 'Departamento', 'Nombre'], how='outer')
        
        # Limpiar filas vacías si alguien no fue en fin de semana (no es falta)
        df_resumen['dia_semana'] = pd.to_datetime(df_resumen['Fecha']).dt.weekday
        mascara_borrar = df_resumen['Hora Entrada'].isna() & (df_resumen['dia_semana'] >= 5)
        df_resumen = df_resumen[~mascara_borrar]
        
        # === 2. LÓGICA DE ESTATUS Y CÁLCULO DE HORAS ===
        df_resumen.loc[df_resumen['Hora Entrada'] == df_resumen['Hora Salida'], 'Hora Salida'] = None
        df_resumen['Estatus'] = df_resumen['Hora Entrada'].apply(clasificar_asistencia)

        mascara_incompleta = df_resumen['Hora Entrada'].notna() & df_resumen['Hora Salida'].isna()
        df_resumen.loc[mascara_incompleta, 'Estatus'] = 'Registro Incompleto ⚠️'

        # Calcular horas en formato decimal restando salida de entrada
        df_resumen['Horas Diarias'] = 0.0
        mascara_validas = df_resumen['Hora Entrada'].notna() & df_resumen['Hora Salida'].notna()
        df_resumen.loc[mascara_validas, 'Entrada_dt'] = pd.to_datetime(df_resumen.loc[mascara_validas, 'Fecha'].astype(str) + ' ' + df_resumen.loc[mascara_validas, 'Hora Entrada'].astype(str))
        df_resumen.loc[mascara_validas, 'Salida_dt'] = pd.to_datetime(df_resumen.loc[mascara_validas, 'Fecha'].astype(str) + ' ' + df_resumen.loc[mascara_validas, 'Hora Salida'].astype(str))
        df_resumen.loc[mascara_validas, 'Horas Diarias'] = (df_resumen.loc[mascara_validas, 'Salida_dt'] - df_resumen.loc[mascara_validas, 'Entrada_dt']).dt.total_seconds() / 3600
        
        # Segmentar las horas del mes
        df_resumen['Horas L-V'] = df_resumen.apply(lambda row: row['Horas Diarias'] if row['dia_semana'] < 5 else 0, axis=1)
        df_resumen['Horas Sábado'] = df_resumen.apply(lambda row: row['Horas Diarias'] if row['dia_semana'] == 5 else 0, axis=1)

        df_resumen['Hora Entrada'] = df_resumen['Hora Entrada'].fillna('Sin registro')
        df_resumen['Hora Salida'] = df_resumen['Hora Salida'].fillna('Sin registro')

        # --- 3. AGRUPACIÓN TOTAL POR EMPLEADO (NÓMINA) ---
        
       # --- 3. AGRUPACIÓN TOTAL POR EMPLEADO (NÓMINA) ---
        
        # A. Contar Días Asistidos
        # 1. Total exacto como lo cuenta ZKTeco (Cualquier día que sí haya ido)
        asistencias_totales = df_resumen[df_resumen['Estatus'] != 'Falta 🔴']
        df_dias_total = asistencias_totales.groupby(['Departamento', 'Nombre'])['Fecha'].count().reset_index()
        df_dias_total.rename(columns={'Fecha': 'Días Asistidos (Total)'}, inplace=True)
        
        # 2. Interno para matemáticas (Solo L-V)
        asistencias_lv = df_resumen[(df_resumen['Estatus'] != 'Falta 🔴') & (df_resumen['dia_semana'] < 5)]
        df_dias_lv = asistencias_lv.groupby(['Departamento', 'Nombre'])['Fecha'].count().reset_index()
        df_dias_lv.rename(columns={'Fecha': 'Días Asistidos (L-V)'}, inplace=True)
        
        # Unir ambos conteos
        df_dias = pd.merge(df_dias_total, df_dias_lv, on=['Departamento', 'Nombre'], how='left')
        
        # B. Contar incidencias (Faltas, Retardos, etc.)
        df_estatus = df_resumen.groupby(['Departamento', 'Nombre', 'Estatus']).size().unstack(fill_value=0).reset_index()
        for col in ['Puntual ✅', 'Retardo 🟡', 'Falta 🔴', 'Registro Incompleto ⚠️']:
            if col not in df_estatus.columns:
                df_estatus[col] = 0
                
        # C. Sumar totales de horas del mes por empleado
        df_horas = df_resumen.groupby(['Departamento', 'Nombre'])[['Horas L-V', 'Horas Sábado']].sum().reset_index()
        
        # D. Consolidar todas las tablas
        df_final = pd.merge(df_dias, df_estatus, on=['Departamento', 'Nombre'], how='right').fillna({
            'Días Asistidos (Total)': 0, 
            'Días Asistidos (L-V)': 0
        })
        df_final = pd.merge(df_final, df_horas, on=['Departamento', 'Nombre'])
        
       # E. Regla de Negocio: Horas Pendientes (Jornadas Dinámicas por Nombre)
       # E. Regla de Negocio: Horas Pendientes (Jornadas Dinámicas)
        
        # 1. Por defecto, jornada completa de 8 horas para todos (40 hrs semanales)
        df_final['Horas Base'] = 8
        
        # 2. Lista de Medio Tiempo / Talentos (5 horas diarias = 25 hrs semanales)
        medio_tiempo = [
            'JENIFER',
            'Eunice',
            'Abel',
            'Iemimah'
        ]
        df_final.loc[df_final['Nombre'].isin(medio_tiempo), 'Horas Base'] = 5

        # 3. Caso Especial: Arelett (7.2 horas diarias = 36 hrs semanales)
        df_final.loc[df_final['Nombre'] == 'Arelett', 'Horas Base'] = 7.2

        # 4. Matemáticas de horas pendientes
        df_final['Días Esperados (Mes)'] = df_final['Días Asistidos (L-V)'] + df_final['Falta 🔴']
        df_final['Horas Pendientes L-V'] = (df_final['Días Esperados (Mes)'] * df_final['Horas Base']) - df_final['Horas L-V']
        
        # Limpiar números negativos
        df_final['Horas Pendientes L-V'] = df_final['Horas Pendientes L-V'].apply(lambda x: round(x, 2) if x > 0 else 0)
        df_final['Horas Sábado (Reposición)'] = df_final['Horas Sábado'].round(2)
        # Si no deben nada, se queda en 0. Redondeamos todo a 2 decimales.
        df_final['Horas Pendientes L-V'] = df_final['Horas Pendientes L-V'].apply(lambda x: round(x, 2) if x > 0 else 0)
        df_final['Horas Sábado (Reposición)'] = df_final['Horas Sábado'].round(2)
        
        # Organizar visualmente la tabla final para Recursos Humanos
        columnas_finales = [
            'Departamento', 'Nombre', 'Días Asistidos (Total)', 'Días Asistidos (L-V)', 'Falta 🔴', 
            'Puntual ✅', 'Retardo 🟡', 'Registro Incompleto ⚠️', 
            'Horas Pendientes L-V', 'Horas Sábado (Reposición)'
        ]
        df_final = df_final[columnas_finales]
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