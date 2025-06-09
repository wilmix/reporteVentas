# Ventas-Plus

Sistema de procesamiento de datos de ventas a partir de archivos Excel comprimidos en ZIP y verificación de consistencia con sistema de inventarios.

## Descripción

Ventas-Plus es un sistema diseñado para procesar archivos de ventas en formato Excel comprimidos en ZIP. El sistema extrae información detallada de ventas, incluyendo datos como sucursales, tipos de emisión, sectores y más, a partir de los códigos de autorización contenidos en los archivos. También permite verificar la consistencia entre las facturas registradas en el SIAT (Servicio de Impuestos Nacionales) y el sistema de inventarios de la empresa.

## Características

- Procesamiento de archivos Excel desde ZIP
- Extracción automática de información desde códigos de autorización
- Análisis de ventas por sucursales y sectores
- Verificación de consistencia entre facturas del SIAT y el sistema de inventarios:
  - Detección de facturas faltantes en el sistema de inventarios
  - Detección de facturas no reportadas al SIAT
  - Verificación detallada de campos entre ambos sistemas:
    - FECHA DE LA FACTURA (fechaFac)
    - Nº DE LA FACTURA (nFactura)
    - NIT/CI CLIENTE (nit)
    - NOMBRE O RAZON SOCIAL (razonSocial)
    - IMPORTE TOTAL DE LA VENTA (importeTotal)
    - ESTADO (estado)
    - SUCURSAL (codigoSucursal)
  - Identificación de todas las discrepancias con observaciones detalladas
- Generación de reportes detallados
- Exportación de datos procesados y resultados de verificación a CSV

## Requisitos

- Python 3.x
- Dependencias listadas en `requirements.txt`

## Instalación

1. Clonar este repositorio
2. Crear un entorno virtual: `python -m venv venv`
3. Activar el entorno virtual:
   - En Windows: `. venv/Scripts/activate`
   - En Linux/Mac: `source venv/bin/activate`
4. Instalar dependencias: `pip install -r requirements.txt`

## Configuración

### Configuración básica
1. Copiar `db_config.ini.example` a `db_config.ini`
2. Editar `db_config.ini` con los datos de conexión a la base de datos:

```ini
[mysql]
host = localhost
user = usuario_db
password = contraseña_db
database = nombre_base_datos
port = 3306
```

### Estructura de directorios requerida
Para un correcto funcionamiento, debe existir la siguiente estructura de directorios:

```
ventas-plus/
├── data/
│   ├── YYYY/            # Carpetas para cada año (ej: 2025/)
│   │   └── MMVentasXlsx.zip  # Archivos ZIP mensuales del SIAT
│   └── output/          # Directorio para archivos de salida
```

## Uso

### Procesar datos de ventas

Para procesar datos de ventas del SIAT y obtener análisis detallados:

```bash
python main.py -m MM -y YYYY
```

Donde:
- `MM`: Mes a procesar (01-12)
- `YYYY`: Año a procesar

### Verificar consistencia de facturas

Para verificar la consistencia entre las facturas del SIAT y el sistema de inventarios:

```bash
python main.py -m MM -y YYYY -v
```

La opción `-v` o `--verify` activa el modo de verificación que:

1. Extrae los datos de facturas del archivo ZIP del SIAT
2. Consulta las facturas del sistema de inventarios para el mismo período
3. Compara ambos sistemas e identifica:
   - Facturas presentes en el SIAT pero no en el sistema de inventarios
   - Facturas presentes en el sistema de inventarios pero no reportadas al SIAT
   - Diferencias en los montos entre ambos sistemas para la misma factura

Los resultados de la verificación se exportan automáticamente a los siguientes archivos CSV:
- `data/output/missing_in_inventory_MM_YYYY.csv`: Facturas que están en SIAT pero no en inventarios
- `data/output/missing_in_siat_MM_YYYY.csv`: Facturas que están en inventarios pero no en SIAT
- `data/output/amount_differences_MM_YYYY.csv`: Facturas con diferencias en los montos
- `data/output/verificacion_completa_MM_YYYY.csv`: Informe completo con todas las facturas comparadas
- `data/output/discrepancias_MM_YYYY.csv`: Solo las facturas que presentan discrepancias con observaciones

Si no se especifican parámetros, el sistema solicitará el mes y año a procesar interactivamente.

### Verificar consistencia de facturas e importar a contabilidad

Para verificar la consistencia entre las facturas del SIAT y el sistema de inventarios **y opcionalmente importar el resultado a la base de datos contable**, ejecuta:

```bash
python main.py -m MM -y YYYY -v
```

- El sistema realiza la verificación SIAT vs inventario y muestra los cuadros comparativos.
- Al finalizar, preguntará si deseas importar el archivo de verificación a la base de datos contable.
- Si respondes "s", se ejecuta el flujo de importación robusto (validación, resumen, reemplazo seguro y bulk insert).
- La salida es limpia: ya **no se muestran prints de columnas internas** del DataFrame ni de la tabla SQL, solo información relevante para el usuario.

#### Ejemplo de flujo:

```
¿Desea importar el archivo de verificación a la base de datos contable? (s/N): s
Leyendo archivo: data/output/verificacion_completa_01_2025.csv
...
Resumen en base de datos:
  Total registros: 562
  Suma total_sale_amount (solo V): 3,024,497.31
  ...
Resumen en archivo CSV:
  Total registros: 562
  ...
Si continúas, se eliminarán todos los registros del periodo en la base y se reemplazarán por los del CSV.
Revisa el resumen antes de confirmar.
¿Desea ELIMINAR los registros de ese periodo y reemplazarlos por los nuevos? (s/N): s
Se eliminaron 562 registros del periodo 01/2025.
...
Se insertaron 562 registros en sales_registers para 01/2025.
```

> **Nota:**
> El proceso de importación es seguro, validado y no muestra detalles técnicos de columnas internas. Toda la lógica de importación está integrada y automatizada tras la verificación con el flag `-v`.

## Estructura del proyecto

```
ventas-plus/
├── main.py             # Script principal y punto de entrada
├── requirements.txt    # Dependencias del proyecto
├── db_config.ini       # Configuración de la base de datos (creado por el usuario)
├── db_config.ini.example # Ejemplo de archivo de configuración
├── data/
│   ├── YYYY/          # Subdirectorios por año (ej: 2025/)
│   │   └── MMVentasXlsx.zip # Archivos ZIP de ventas mensuales del SIAT
│   └── output/        # Directorio para archivos de salida
│       ├── ventas_procesadas_MM_YYYY.csv     # Datos procesados del SIAT
│       ├── missing_in_inventory_MM_YYYY.csv  # Facturas en SIAT pero no en inventarios
│       ├── missing_in_siat_MM_YYYY.csv       # Facturas en inventarios pero no en SIAT
│       ├── amount_differences_MM_YYYY.csv    # Facturas con diferencias en montos
│       ├── verificacion_completa_MM_YYYY.csv # Informe completo de verificación
│       └── discrepancias_MM_YYYY.csv         # Facturas con discrepancias
├── ventas_plus/       # Módulo principal
│   └── core_logic.py  # Lógica central del procesamiento
└── tests/            # Pruebas unitarias
```

## Cambios de Estructura y Modularización (2025)

A partir de junio 2025, el proyecto fue refactorizado para mejorar su mantenibilidad y escalabilidad. La lógica central se dividió en módulos especializados:

- `ventas_plus/data_ingestion.py`: Funciones para la carga y lectura de archivos (Excel, ZIP, etc).
- `ventas_plus/db_utils.py`: Funciones para la configuración, conexión y consulta a la base de datos.
- `ventas_plus/ventas_processing.py`: Procesamiento y análisis de datos de ventas.
- `ventas_plus/comparison.py`: Lógica de comparación entre SIAT e inventario y reporte de discrepancias.
- `ventas_plus/branch_normalization.py`: Funciones para normalización de códigos de sucursal.

El archivo `core_logic.py` ahora solo orquesta el flujo principal y delega la lógica a los módulos anteriores. Esto facilita el mantenimiento, las pruebas y futuras ampliaciones.

**Importante:**
- Toda la lógica de comparación y reporte de discrepancias se encuentra ahora en `comparison.py`.
- El campo "razon social" ya no se compara ni reporta como discrepancia.
- El reporte de discrepancias se unificó en un solo archivo CSV: `discrepancias_MM_YYYY.csv`.

Revisa la sección "Estructura del proyecto" para ver la nueva organización de archivos.

## Formato de Archivos de Salida

### Verificación de Consistencia

Los archivos generados por la verificación de consistencia contienen los siguientes campos:

1. **missing_in_inventory_MM_YYYY.csv**:
   - `CODIGO DE AUTORIZACIÓN`: Código de autorización SIAT
   - `IMPORTE TOTAL DE LA VENTA`: Monto de la factura según SIAT
   - `ESTADO`: Estado de la factura (VALIDA/ANULADA)

2. **missing_in_siat_MM_YYYY.csv**:
   - `autorizacion`: Código de autorización en sistema de inventarios
   - `importeTotal`: Monto de la factura según sistema de inventarios
   - `estado`: Estado de la factura (V=válida, A=anulada)

3. **amount_differences_MM_YYYY.csv**:
   - `autorizacion`: Código de autorización SIAT/inventario
   - `importe_siat`: Monto según SIAT
   - `importe_inv`: Monto según sistema de inventarios
   - `diferencia_importe`: Diferencia entre ambos montos

4. **verificacion_completa_MM_YYYY.csv**:
   - `autorizacion`: Código de autorización SIAT/inventario
   - `fecha_siat`: Fecha según SIAT
   - `fecha_inv`: Fecha según sistema de inventarios
   - `nfactura_siat`: Número de factura según SIAT
   - `nfactura_inv`: Número de factura según sistema de inventarios
   - `nit_siat`: NIT/CI del cliente según SIAT
   - `nit_inv`: NIT/CI del cliente según sistema de inventarios
   - `razon_social_siat`: Nombre o razón social según SIAT
   - `razon_social_inv`: Nombre o razón social según sistema de inventarios
   - `importe_siat`: Monto según SIAT
   - `importe_inv`: Monto según sistema de inventarios
   - `diferencia_importe`: Diferencia entre montos
   - `estado_siat`: Estado según SIAT (VALIDA/ANULADA)
   - `estado_inv`: Estado según sistema de inventarios
   - `sucursal_siat`: Código de sucursal según SIAT
   - `sucursal_inv`: Código de sucursal según sistema de inventarios
   - `OBSERVACIONES`: Descripción de todas las discrepancias encontradas

5. **discrepancias_MM_YYYY.csv**:
   - Contiene los mismos campos que el archivo de verificación completa, pero incluye únicamente las facturas que presentan discrepancias en alguno de los campos comparados.

## Comparación SIAT vs Hergo (API externa)

A partir de la versión 2025-06, el sistema compara automáticamente los totales de ventas SIAT con los reportados por la API de Hergo para cada sucursal y el total general. El resultado se muestra en consola en formato tabla, indicando si los totales coinciden (OK) o hay diferencias (ERROR).

> **Nota importante:**
> La lógica de cálculo de los totales SIAT y Hergo es **idéntica** a la del reporte principal:
> - **CENTRAL (0000):** Suma todas las ventas válidas de sector 01 y sector 35.
> - **SANTA CRUZ (0005) y POTOSÍ (0006):** Suma solo las ventas válidas de sector 01.
> - **GENERAL:** Suma todas las ventas válidas de todas las sucursales, excluyendo únicamente alquileres (sector 02).
> 
> Los totales mostrados en la tabla comparativa SIAT vs Hergo coinciden exactamente con los del reporte principal para cada sucursal y el total general.

### Características:
- Consulta automática a la API Hergo por sucursal y general.
- Comparación de totales SIAT vs Hergo por sucursal y general.
- Visualización clara en consola con estado OK/ERROR.
- Depuración: si la API Hergo responde con error o un formato inesperado, el sistema imprime la respuesta cruda para facilitar el diagnóstico.

### Ejemplo de salida:

```
--- COMPARATIVO SIAT vs HERGO ---

Sucursal     |      Total SIAT |     Total Hergo |   Diferencia | Estado
--------------------------------------------------------------------

CENTRAL      |    1,184,244.32 |    1,184,244.32 |        0.00  |   OK
SANTA CRUZ   |    1,479,069.80 |    1,479,069.80 |        0.00  |   OK
POTOSI       |      252,571.19 |      252,571.19 |        0.00  |   OK
GENERAL      |    2,915,885.31 |    2,915,885.31 |        0.00  |   OK
--------------------------------------------------------------------
```

## Cambios recientes en el cuadro comparativo SIAT vs Inventario (junio 2025)

A partir de junio 2025, el cuadro comparativo SIAT vs Inventario se divide en **dos tablas separadas** para mayor claridad:

- **Cuadro 1: Totales en montos**
  - Muestra los totales monetarios por sucursal, alquileres, total inventario y total general.
  - Incluye columna de conciliación (✔/❌) para comparar montos SIAT vs Inventario.
  - La columna **DIFERENCIA** solo se muestra si existe al menos una diferencia distinta de cero; si todos los valores son cero, la columna se oculta para mayor claridad visual.
  - Las filas de ALQUILERES y TOTAL GENERAL no muestran check, ya que no son comparables.

- **Cuadro 2: Totales de número de facturas**
  - Muestra la cantidad de facturas válidas y anuladas por sucursal, alquileres, total inventario y total general.
  - Incluye columna de conciliación (✔/❌) para comparar cantidades SIAT vs Inventario.
  - Las columnas **DIF VAL** y **DIF ANU** solo se muestran si existe al menos una diferencia distinta de cero en la cantidad de válidas o anuladas, respectivamente; si todos los valores son cero, esas columnas se ocultan.
  - Las filas de ALQUILERES y TOTAL GENERAL no muestran check.

**Ventajas de la nueva presentación:**
- Permite comparar de forma independiente los montos y las cantidades de facturas.
- Mejora la legibilidad y la auditoría visual.
- Mantiene la lógica robusta de separación de alquileres y normalización de sucursales/estados.
- Oculta columnas de diferencia innecesarias cuando no hay discrepancias, haciendo el reporte más limpio y fácil de leer.

Estos cambios facilitan la revisión y conciliación entre SIAT e Inventario, permitiendo detectar rápidamente diferencias tanto en montos como en cantidades.

## Barra de estado amigable durante la consulta a Hergo

A partir de la versión 2025-06, al generar el comparativo SIAT vs Hergo, el sistema muestra una barra de progreso amigable en consola mientras consulta los totales al sistema de inventarios (Hergo). Esto ayuda a que el usuario sepa que el proceso está en curso y puede demorar unos segundos.

No requiere instalar dependencias adicionales, la barra es nativa y funciona en cualquier terminal.

### Solución de problemas con la API Hergo

Si la API Hergo no responde con un JSON válido (por ejemplo, devuelve HTML de error, mensaje vacío, etc.), el sistema imprime la respuesta cruda para ayudar a depurar. Posibles causas:
- La API está caída o no disponible.
- Requiere autenticación o headers especiales.
- El endpoint cambió o hay restricciones de red.
- Demasiadas consultas seguidas (rate limit).

**Acción recomendada:**
- Revisa el contenido impreso en consola para identificar el problema.
- Verifica manualmente la URL y los parámetros en un navegador o con Postman/curl.
- Si la API requiere autenticación, consulta con el administrador del sistema Hergo.

## Solución de Problemas

### Problemas Comunes

1. **Error de conexión a la base de datos**:
   - Verifique que el archivo `db_config.ini` existe y contiene la configuración correcta
   - Asegúrese de tener acceso a la base de datos desde su red

2. **No se encuentran archivos ZIP**:
   - Verifique que el archivo ZIP del SIAT está en la carpeta correcta (`data/YYYY/MMVentasXlsx.zip`)
   - Asegúrese de ingresar el mes y año correctos

## Configuración de credenciales Hergo (seguridad)

### Variables de entorno con archivo `.env`

Para mayor seguridad, las credenciales de Hergo **no deben estar en el código ni en archivos versionados**. Usa un archivo `.env` en la raíz del proyecto (no lo subas a git):

```
HERGO_USER=tu_usuario@hergo.com.bo
HERGO_PASS=tu_contraseña
```

Puedes guiarte por el archivo `.env.example` incluido.

Luego, el sistema las cargará automáticamente si tienes instalada la librería `python-dotenv` (ya incluida en `requirements.txt`)

**Importante:**
- El archivo `.env` debe estar en tu `.gitignore`.
- Nunca subas tus credenciales reales al repositorio.

No necesitas cambiar nada en el código: solo crea el `.env` y asegúrate de tener la librería instalada.

---

### Alternativa: variables de entorno en consola

También puedes definirlas temporalmente en la terminal antes de ejecutar el script:

**Windows (CMD):**
```
set HERGO_USER=tu_usuario@hergo.com.bo
set HERGO_PASS=tu_contraseña
python main.py -m MM -y YYYY
```

**Linux/Mac (bash):**
```
export HERGO_USER=tu_usuario@hergo.com.bo
export HERGO_PASS=tu_contraseña
python main.py -m MM -y YYYY
```

---

## Importación mensual de verificación SIAT a contabilidad

A partir de junio 2025, Ventas-Plus permite importar el archivo mensual de verificación SIAT (`verificacion_completa_MM_YYYY.csv`) al sistema contable, integrando los registros en la tabla `sales_registers` de una base de datos de contabilidad separada.

### Requisitos previos
- Archivo CSV de verificación generado por el sistema: `data/output/verificacion_completa_MM_YYYY.csv` (ver sección anterior).
- Acceso y credenciales a la base de datos contable (ver `db_config_contabilidad.ini`).
- Estructura de tabla `sales_registers` creada según lo documentado en `PLAN_DE_IMPORTACION_VERIFICACION.md`.
- Dependencias instaladas (ver `requirements.txt`).

### Configuración
1. Copia y edita el archivo de configuración de la base contable:
   - `cp db_config_contabilidad.ini.example db_config_contabilidad.ini`
   - Completa los datos de conexión a la base de datos contable.
2. Verifica la conexión ejecutando:
   ```bash
   python -m ventas_plus.db_utils_contabilidad
   ```

### Proceso de importación
1. Ejecuta el script de importación para el mes/año deseado:
   ```bash
   python -m ventas_plus.importar_verificacion_contabilidad -m MM -y YYYY
   ```
   Donde:
   - `MM`: Mes a importar (01-12)
   - `YYYY`: Año a importar
2. El script realiza:
   - Lectura y validación del archivo CSV de verificación.
   - Transformación y mapeo de campos según la estructura de `sales_registers`.
   - Chequeo de duplicados: si ya existen registros para ese mes/año, la importación se aborta.
   - Inserción masiva de los datos validados en la base contable.
   - Reporte de errores de integridad o duplicidad, si los hubiera.

### Validaciones y salvaguardas
- Validación de tipos de datos, nulos y unicidad antes de insertar.
- Abortado automático si ya existen registros para el período (mes/año) en la tabla destino.
- Manejo robusto de errores y reporte en consola.
- Documentación detallada del proceso en el propio script y en `PLAN_DE_IMPORTACION_VERIFICACION.md`.

### Referencias técnicas
- **Estructura y reglas de validación:** ver `PLAN_DE_IMPORTACION_VERIFICACION.md`.
- **Mapeo de campos:** ver `sales_register_field_mapping.md`.
- **Estructura SIAT:** ver `ventas_estandar_siatt.md` y `ventas_estandar_siatt.json`.

### Notas adicionales
- El proceso es repetible y seguro para ejecución mensual.
- Se recomienda revisar los logs y mensajes en consola tras cada importación.
- Para automatización, logging a archivo y pruebas automáticas, ver sugerencias en `PLAN_DE_IMPORTACION_VERIFICACION.md`.

---

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.
