"""
extract.py
Paso 1 del ETL: extraer los datos crudos de la hoja "Reporte de Asistencia"
del archivo exportado por el reloj checador ZKTeco TE10.
"""

import openpyxl

RUTA_EXCEL = "1_StandardReport.xls"   # ajusta la ruta si tu archivo está en otra carpeta


def extraer_datos_crudos(ruta_excel: str) -> list[dict]:
    """
    Lee la hoja 'Reporte de Asistencia' y regresa una lista de diccionarios,
    uno por empleado, con sus datos crudos del mes (sin procesar horas todavía).
    """
    wb = openpyxl.load_workbook(ruta_excel, data_only=True)
    ws = wb["Reporte de Asistencia"]
    rows = list(ws.iter_rows(values_only=True))

    dias = rows[2]  # fila 3: números de día del mes (1..31)

    registros_crudos = []
    i = 4  # los datos de empleados empiezan en la fila 5 (índice 4)
    while i < len(rows):
        fila_id = rows[i]
        # cada bloque de empleado son 2 filas: (ID/Nombre/Depto) + (marcas por día)
        if fila_id and fila_id[0] == "ID:":
            id_empleado = fila_id[2]
            nombre = fila_id[10]
            departamento = fila_id[20]
            fila_datos = rows[i + 1] if i + 1 < len(rows) else None

            registros_crudos.append({
                "id_empleado": int(id_empleado),
                "nombre": nombre,
                "departamento": departamento,
                "dias": dias,
                "marcas_por_dia": fila_datos,
            })
            i += 2
        else:
            i += 1

    return registros_crudos


if __name__ == "__main__":
    datos = extraer_datos_crudos(RUTA_EXCEL)
    print(f"Empleados extraídos: {len(datos)}")
    for d in datos[:3]:
        print(d["id_empleado"], d["nombre"], d["departamento"])