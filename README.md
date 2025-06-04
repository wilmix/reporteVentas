# Ventas-Plus

Sistema de procesamiento de datos de ventas a partir de archivos Excel comprimidos en ZIP.

## Descripción

Ventas-Plus es un sistema diseñado para procesar archivos de ventas en formato Excel comprimidos en ZIP. El sistema extrae información detallada de ventas, incluyendo datos como sucursales, tipos de emisión, sectores y más, a partir de los códigos de autorización contenidos en los archivos.

## Características

- Procesamiento de archivos Excel desde ZIP
- Extracción automática de información desde códigos de autorización
- Análisis de ventas por sucursales y sectores
- Generación de reportes detallados
- Exportación de datos procesados a CSV

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

1. Copiar `db_config.ini.example` a `db_config.ini`
2. Editar `db_config.ini` con los datos de conexión a la base de datos

## Uso

Para procesar datos de ventas:

```bash
python main.py -m MM -y YYYY
```

Donde:
- `MM`: Mes a procesar (01-12)
- `YYYY`: Año a procesar

Si no se especifican parámetros, el sistema solicitará el mes y año a procesar interactivamente.

## Estructura de directorios

- `data/`: Directorio para archivos de datos
  - `YYYY/`: Subdirectorios por año
    - `MMVentasXlsx.zip`: Archivos ZIP de ventas mensuales
  - `output/`: Directorio para archivos de salida
- `ventas_plus/`: Módulo principal
  - `core_logic.py`: Lógica central del procesamiento
- `tests/`: Pruebas unitarias

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.
