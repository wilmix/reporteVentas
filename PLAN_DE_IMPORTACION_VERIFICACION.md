# PLAN_DE_IMPORTACION_VERIFICACION.md

## Objetivo

Documentar y guiar el proceso para importar los datos de verificación de facturas (por ejemplo, `verificacion_completa_01_2025.csv`) generados por Ventas-Plus a una nueva base de datos y tabla destinada al sistema contable.

---

## Plan Paso a Paso

### 1. Análisis y Diseño

#### Estructura de la tabla destino (contabilidad)

```sql
CREATE TABLE `sales_registers` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `invoice_date` date NOT NULL,
  `invoice_number` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `authorization_code` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `customer_nit` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `complement` varchar(5) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_name` varchar(240) COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_sale_amount` decimal(14,2) NOT NULL,
  `ice_amount` decimal(14,2) NOT NULL,
  `iehd_amount` decimal(14,2) NOT NULL,
  `ipj_amount` decimal(14,2) NOT NULL,
  `fees` decimal(14,2) NOT NULL,
  `other_non_vat_items` decimal(14,2) NOT NULL,
  `exports_exempt_operations` decimal(14,2) NOT NULL,
  `zero_rate_taxed_sales` decimal(14,2) NOT NULL,
  `subtotal` decimal(14,2) NOT NULL,
  `discounts_bonuses_rebates_subject_to_vat` decimal(14,2) NOT NULL,
  `gift_card_amount` decimal(14,2) NOT NULL,
  `debit_tax_base_amount` decimal(14,2) NOT NULL,
  `debit_tax` decimal(14,2) NOT NULL,
  `status` char(1) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'A=Anulada, V=Válida, C=Contingencia, L=Libre consignación',
  `control_code` varchar(17) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Código hexadecimal de control de factura antiguas computarizadas según SIAT',
  `sale_type` char(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `consolidation_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  `branch_office` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Internal use - issuing branch office',
  `modality` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Internal use - issuance modality',
  `emission_type` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Internal use - emission type (manual, electronic, etc.)',
  `invoice_type` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Internal use - internal invoice type',
  `sector` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Internal use - business or system sector',
  `obs` text COLLATE utf8mb4_unicode_ci COMMENT 'Internal use - technical notes or flags',
  `author` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Internal use - record author',
  `observations` text COLLATE utf8mb4_unicode_ci COMMENT 'Internal use - audit notes or extra comments',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_authorization_code` (`authorization_code`),
  CONSTRAINT `sales_registers_chk_1` CHECK ((`status` in (_utf8mb4'A',_utf8mb4'V'))),
  CONSTRAINT `sales_registers_chk_10` CHECK ((`subtotal` >= 0)),
  CONSTRAINT `sales_registers_chk_11` CHECK ((`discounts_bonuses_rebates_subject_to_vat` >= 0)),
  CONSTRAINT `sales_registers_chk_12` CHECK ((`gift_card_amount` >= 0)),
  CONSTRAINT `sales_registers_chk_13` CHECK ((`debit_tax_base_amount` >= 0)),
  CONSTRAINT `sales_registers_chk_14` CHECK ((`debit_tax` >= 0)),
  CONSTRAINT `sales_registers_chk_15` CHECK ((`status` in (_utf8mb4'A',_utf8mb4'V',_utf8mb4'C',_utf8mb4'L'))),
  CONSTRAINT `sales_registers_chk_2` CHECK ((`total_sale_amount` >= 0)),
  CONSTRAINT `sales_registers_chk_3` CHECK ((`ice_amount` >= 0)),
  CONSTRAINT `sales_registers_chk_4` CHECK ((`iehd_amount` >= 0)),
  CONSTRAINT `sales_registers_chk_5` CHECK ((`ipj_amount` >= 0)),
  CONSTRAINT `sales_registers_chk_6` CHECK ((`fees` >= 0)),
  CONSTRAINT `sales_registers_chk_7` CHECK ((`other_non_vat_items` >= 0)),
  CONSTRAINT `sales_registers_chk_8` CHECK ((`exports_exempt_operations` >= 0)),
  CONSTRAINT `sales_registers_chk_9` CHECK ((`zero_rate_taxed_sales` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

- El campo `authorization_code` debe ser único (UNIQUE KEY).
- El campo `status` solo puede tener los valores 'A', 'V', 'C', 'L'.
- Todos los importes y montos deben ser mayores o iguales a cero.
- Los campos de uso interno (`branch_office`, `modality`, `emission_type`, `invoice_type`, `sector`, `obs`, `author`, `observations`) pueden ser nulos.
- Los campos `created_at` y `updated_at` pueden ser nulos y pueden ser llenados automáticamente por la base de datos o el script.

- Mapear los campos del CSV a los de la tabla destino.
- Configurar un archivo de conexión separado para la nueva base de datos (por ejemplo, `db_config_contabilidad.ini`).
- Validar los datos antes de la inserción (tipos, nulos, duplicados, valores permitidos y restricciones de unicidad).

> **Nota importante:**
> En la importación, todos los campos NOT NULL numéricos se rellenan con 0.0 si no hay dato, y los campos string NOT NULL se rellenan con '0' si no hay dato.

### 2. Implementación
- Crear un módulo/función Python para:
  - Leer el CSV con pandas.
  - Validar y limpiar los datos.
  - Insertar los datos en la tabla destino (idealmente con bulk insert).
- Implementar manejo de errores y logging.
- Controlar duplicados antes de insertar (por ejemplo, por código de autorización y fecha).

### 3. Seguridad y Buenas Prácticas
- Mantener separadas las conexiones a inventarios y contabilidad.
- Usar archivos de configuración o variables de entorno para credenciales.
- Usar transacciones para asegurar atomicidad.
- Realizar backups antes de cargas masivas.

### 4. Automatización y Usabilidad
- El script debe ser reutilizable y parametrizable (archivo CSV, tabla destino, config de conexión).
- Integrar opcionalmente con el flujo actual para ofrecer la subida automática tras la validación.

### 5. Documentación y Pruebas
- Documentar el proceso y los requisitos.
- Realizar pruebas con archivos de ejemplo y verificar la correcta inserción.

---

### Comparación previa antes de eliminar/importar

Antes de eliminar los registros existentes y proceder con la importación, el script debe:

1. Leer los registros existentes en la base de datos para el periodo seleccionado.
2. Comparar la cantidad de registros entre la base y el archivo CSV.
3. Comparar las claves principales (`authorization_code`) para identificar:
   - Registros solo en la base
   - Registros solo en el CSV
   - Registros en ambos
4. Para los registros en ambos, comparar campos relevantes (`total_sale_amount`, `status`, `customer_nit`, `customer_name`, `invoice_date`, etc.) y mostrar cuántos tienen diferencias.
5. Mostrar un resumen claro de las diferencias y pedir confirmación informada al usuario antes de eliminar/importar.

Esto permite tomar decisiones informadas y evita la pérdida accidental de información relevante.

## Alternativas Técnicas

1. **Script Python dedicado** (recomendado): Un módulo/función que lea el CSV y lo suba a la nueva base de datos.
2. **Carga directa desde MySQL**: Usar `LOAD DATA INFILE` si el servidor lo permite.
3. **ETL externo**: Usar una herramienta ETL si el volumen y la complejidad lo justifican.

---

## Decisiones y Notas
- Se recomienda la opción 1 por flexibilidad y control.
- Mantener este archivo actualizado con los avances, decisiones y cambios en el proceso.

---

## Pendientes
- [ ] Definir estructura SQL de la tabla destino.
- [ ] Crear archivo de configuración para la base de datos contable.
- [ ] Implementar el script de importación.
- [ ] Probar la importación con un archivo de ejemplo.
- [ ] Documentar el uso y actualizar este plan.

---

#### Mapeo de campos: CSV → sales_registers

A continuación se muestra el mapeo entre los campos del archivo CSV generado (`verificacion_completa_MM_YYYY.csv`) y los campos de la tabla `sales_registers` en la base de datos contable. Este mapeo se basa en la convención de nombres y la documentación del proyecto:

| Campo en CSV / SIAT                      | Campo en sales_registers (DB)                  |
|------------------------------------------|-----------------------------------------------|
| FECHA DE LA FACTURA                      | invoice_date                                  |
| N° DE LA FACTURA                         | invoice_number                                |
| CÓDIGO DE AUTORIZACIÓN                   | authorization_code                            |
| NIT / CI CLIENTE                         | customer_nit                                  |
| COMPLEMENTO                              | complement                                    |
| NOMBRE O RAZÓN SOCIAL                    | customer_name                                 |
| IMPORTE TOTAL DE LA VENTA                | total_sale_amount                             |
| IMPORTE ICE                              | ice_amount                                    |
| IMPORTE IEHD                             | iehd_amount                                   |
| IMPORTE IPJ                              | ipj_amount                                    |
| TASAS                                    | fees                                          |
| OTROS NO SUJETOS AL IVA                  | other_non_vat_items                           |
| EXPORTACIONES Y OPERACIONES EXENTAS      | exports_exempt_operations                     |
| VENTAS GRAVADAS A TASA CERO              | zero_rate_taxed_sales                         |
| SUBTOTAL                                 | subtotal                                      |
| DESCUENTOS, BONIFICACIONES Y REBAJAS...  | discounts_bonuses_rebates_subject_to_vat      |
| IMPORTE GIFT CARD                        | gift_card_amount                              |
| IMPORTE BASE PARA DÉBITO FISCAL          | debit_tax_base_amount                         |
| DÉBITO FISCAL                            | debit_tax                                     |
| ESTADO                                   | status                                        |
| CÓDIGO DE CONTROL                        | control_code                                  |
| TIPO DE VENTA                            | sale_type                                     |
| ESTADO CONSOLIDACION                     | consolidation_status                          |
| SUCURSAL                                 | branch_office                                 |
| MODALIDAD                                | modality                                      |
| TIPO EMISION                             | emission_type                                 |
| TIPO FACTURA                             | invoice_type                                  |
| SECTOR                                   | sector                                        |
| _obs / OBSERVACIONES                     | obs / observations                            |
| _autor                                   | author                                        |

Notas:
- Los campos `created_at` y `updated_at` pueden ser llenados automáticamente por la base de datos o el script.
- Si algún campo no existe en el CSV, debe asignarse un valor por defecto o nulo según corresponda.
- Revisar el archivo `sales_register_field_mapping.md` para detalles adicionales de equivalencias.
