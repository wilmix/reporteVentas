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

## Solución de Problemas

### Problemas Comunes

1. **Error de conexión a la base de datos**:
   - Verifique que el archivo `db_config.ini` existe y contiene la configuración correcta
   - Asegúrese de tener acceso a la base de datos desde su red

2. **No se encuentran archivos ZIP**:
   - Verifique que el archivo ZIP del SIAT está en la carpeta correcta (`data/YYYY/MMVentasXlsx.zip`)
   - Asegúrese de ingresar el mes y año correctos

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.
