import re

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# 1. Configurar conexión (Pon tu contraseña aquí)
cadena_conexion = 'mysql+pymysql://root:sqlproneil23>@localhost/recursos_humanos'
engine = create_engine(cadena_conexion)

def procesar_y_cargar_asistencia(ruta_archivo):
    print("1. Leyendo y limpiando el archivo de ZKTeco...")
    df_raw = pd.read_excel(ruta_archivo, sheet_name='Reporte de Asistencia', header=None)
    periodo_str = str(df_raw.iloc[2, 2])
    año_mes = periodo_str[0:7] 
    
    registros = []
    
    # 2. Romper el formato cruzado
    for i in range(4, len(df_raw), 2):
        fila_datos = df_raw.iloc[i]
        fila_checadas = df_raw.iloc[i+1]
        
        if str(fila_datos[0]).strip() != "ID:": continue
            
        id_emp = fila_datos[2]
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
                        'id_empleado': id_emp,
                        'nombre': nombre_emp,
                        'departamento': departamento,
                        'fecha_hora': f"{fecha} {hora}:00"
                    })

    df_completo = pd.DataFrame(registros)
    df_completo['fecha_hora'] = pd.to_datetime(df_completo['fecha_hora'])
    print(f"-> Se extrajeron {len(df_completo)} registros limpios.\n")

    print("2. Cargando datos a MySQL (Normalización 3NF)...")
 # Insertar Departamentos
    deptos_unicos = pd.DataFrame({'nombre_departamento': df_completo['departamento'].unique()})
    
    with engine.connect() as conn:
        for depto in deptos_unicos['nombre_departamento']:
            try:
                # Envolvemos el string con text()
                conn.execute(text(f"INSERT IGNORE INTO departamentos (nombre_departamento) VALUES ('{depto}')"))
            except IntegrityError:
                pass
        conn.commit()  # <-- Confirmamos que se guarden los cambios
   # Insertar Empleados
    df_deptos_db = pd.read_sql("SELECT * FROM departamentos", engine)
    emp_unicos = df_completo[['id_empleado', 'nombre', 'departamento']].drop_duplicates(subset=['id_empleado'])
    emp_unicos = emp_unicos.merge(df_deptos_db, left_on='departamento', right_on='nombre_departamento', how='left')
    
    with engine.connect() as conn:
        for index, row in emp_unicos.iterrows():
            try:
                # Envolvemos el string con text()
                conn.execute(text(f"INSERT IGNORE INTO empleados (id_empleado, nombre, id_departamento) VALUES ({row['id_empleado']}, '{row['nombre']}', {row['id_departamento']})"))
            except IntegrityError:
                pass
        conn.commit()  # <-- Confirmamos que se guarden los cambios
    # Insertar Asistencia (Hechos)
    asistencia = df_completo[['id_empleado', 'fecha_hora']]
    asistencia.to_sql('asistencia', con=engine, if_exists='append', index=False)
    
    print("¡Proceso terminado exitosamente! Datos cargados en la base de datos.")

# ==========================================
# ESTA ES LA PARTE QUE HACE QUE SE EJECUTE
# ==========================================
if __name__ == "__main__":
    # Ejemplo si está en una USB:
    procesar_y_cargar_asistencia(r"C:\Users\tibur\OneDrive\Escritorio\Proyecto_ZKTeco\1_StandardReport.xls")