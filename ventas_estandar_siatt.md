# Estructura del Registro de Ventas Estándar SIAT

Este documento describe la estructura oficial del archivo de **Registro de Ventas Estándar** según la normativa del SIAT (Servicio de Impuestos Nacionales de Bolivia). Es útil para desarrolladores y usuarios que necesiten generar, validar o interpretar estos archivos.

## Tabla de Campos

| Nº | Nombre de Columna                                         | Tipo de Dato         | Longitud/Formato | Obligatorio | Descripción                                                                                                                                                                                                 |
|----|-----------------------------------------------------------|----------------------|------------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | N°                                                       | Numérico Entero      | 8                | Sí          | Número correlativo y secuencial del registro o fila.                                                                                                                                                        |
| 2  | ESPECIFICACION                                            | Numérico Entero      | 1                | No*         | Valor predeterminado “2”. Solo en importación del archivo debe estar en la segunda posición.                                                                         |
| 3  | FECHA DE LA FACTURA                                       | Fecha (DD/MM/AAAA)   | 10               | Sí          | Fecha de emisión de la factura o nota fiscal.                                                                                                                        |
| 4  | N° DE LA FACTURA                                          | Numérico Entero      | 15               | Sí          | Número de la factura o nota fiscal.                                                                                                                                   |
| 5  | CÓDIGO DE AUTORIZACIÓN                                    | Alfanumérico         | 15               | Sí          | Código de autorización de la factura o nota fiscal, distinto de cero.                                                                                                |
| 6  | NIT / CI CLIENTE                                          | Alfanumérico         | 15               | Sí          | NIT o documento de identidad del cliente. Usar 99001 (consulados), 99002 (control tributario), 99003 (ventas menores), o cero según corresponda.                     |
| 7  | COMPLEMENTO                                               | Alfanumérico         | 5                | Sí          | Complemento del documento de identidad. Si no existe, dejar en blanco.                                                                                               |
| 8  | NOMBRE O RAZÓN SOCIAL                                     | Alfanumérico         | 240              | Sí          | Nombre o razón social del cliente. Usar “Sin Nombre” o “S/N” si no existe información.                                                                               |
| 9  | IMPORTE TOTAL DE LA VENTA                                 | Numérico (2 dec.)    | 14.2             | Sí          | Importe total de la venta según factura, sin deducciones.                                                                                                            |
| 10 | IMPORTE ICE                                               | Numérico (2 dec.)    | 14.2             | Sí          | Importe correspondiente al ICE. Si no aplica, registrar cero.                                                                                                        |
| 11 | IMPORTE IEHD                                              | Numérico (2 dec.)    | 14.2             | Sí          | Importe correspondiente al IEHD. Si no aplica, registrar cero.                                                                                                       |
| 12 | IMPORTE IPJ                                               | Numérico (2 dec.)    | 14.2             | Sí          | Importe correspondiente al IPJ. Si no aplica, registrar cero.                                                                                                        |
| 13 | TASAS                                                     | Numérico (2 dec.)    | 14.2             | Sí          | Importe correspondiente a tasas. Si no aplica, registrar cero.                                                                                                       |
| 14 | OTROS NO SUJETOS AL IVA                                   | Numérico (2 dec.)    | 14.2             | Sí          | Otros conceptos no sujetos al IVA. Si no aplica, registrar cero.                                                                                                     |
| 15 | EXPORTACIONES Y OPERACIONES EXENTAS                       | Numérico (2 dec.)    | 14.2             | Sí          | Importe de exportaciones y operaciones exentas. Si no aplica, registrar cero.                                                                                        |
| 16 | VENTAS GRAVADAS A TASA CERO                               | Numérico (2 dec.)    | 14.2             | Sí          | Importe de ventas gravadas a tasa cero. Si no aplica, registrar cero.                                                                                                |
| 17 | SUBTOTAL                                                  | Numérico (2 dec.)    | 14.2             | Sí          | SUBTOTAL = IMPORTE TOTAL DE LA VENTA - IMPORTE ICE - IMPORTE IEHD - IMPORTE IPJ - TASAS - OTROS NO SUJETOS AL IVA - EXPORTACIONES Y OPERACIONES EXENTAS - VENTAS GRAVADAS A TASA CERO |
| 18 | DESCUENTOS, BONIFICACIONES Y REBAJAS SUJETAS AL IVA       | Numérico (2 dec.)    | 14.2             | Sí          | Importe de descuentos, bonificaciones y rebajas otorgadas. Si no aplica, registrar cero.                                                                             |
| 19 | IMPORTE GIFT CARD                                         | Numérico (2 dec.)    | 14.2             | Sí          | Importe de gift card. Si no aplica, registrar cero.                                                                                                                  |
| 20 | IMPORTE BASE PARA DÉBITO FISCAL                           | Numérico (2 dec.)    | 14.2             | Sí          | IMPORTE BASE PARA DÉBITO FISCAL = SUBTOTAL - DESCUENTOS, BONIFICACIONES Y REBAJAS - IMPORTE GIFT CARD                                                               |
| 21 | DÉBITO FISCAL                                             | Numérico (2 dec.)    | 14.2             | Sí          | DÉBITO FISCAL = IMPORTE BASE PARA DÉBITO FISCAL * 13%                                                                                                               |
| 22 | ESTADO                                                    | Carácter             | 1                | Sí          | Estado de la factura: A=Anulada, V=Válida, C=Contingencia, L=Libre consignación.                                                                                    |
| 23 | CÓDIGO DE CONTROL                                         | Alfanumérico         | 17               | Sí          | Código de control (hexadecimal, pares separados por guiones). Si no aplica, registrar cero.                                                                          |
| 24 | TIPO DE VENTA                                             | Numérico Entero      | 1                | Sí          | 0=Otros, 1=Gift Card.                                                                                                                                                |

*Nota: El campo ESPECIFICACION solo es obligatorio al importar el archivo.*

## Consideraciones
- El separador de miles es la **coma** y el de decimales es el **punto**.
- Todos los campos son obligatorios salvo que se indique lo contrario.
- Los cálculos de SUBTOTAL, IMPORTE BASE PARA DÉBITO FISCAL y DÉBITO FISCAL deben seguir las fórmulas indicadas.
- Para valores no aplicables, registrar **cero (0)** o dejar en blanco según corresponda.
- **Nota para importación a contabilidad:** Los campos obligatorios (NOT NULL) se rellenan con 0.0 (numéricos) o '0' (strings) si no hay dato, según el tipo de campo.

---

**Fuente:** [SIAT - Registro de Ventas Estándar](https://siatinfo.impuestos.gob.bo/index.php/registro-de-compras-y-ventas/registro-de-ventas/ventas-estandar)
