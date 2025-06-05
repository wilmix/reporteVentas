"""
Módulo para conexión y prueba de acceso a la base de datos contable.
"""
import configparser
import mysql.connector

def get_db_config_contabilidad(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
    if 'mysql' not in config:
        raise ValueError("La sección 'mysql' no existe en el archivo de configuración")
    return {
        'host': config['mysql'].get('host', 'localhost'),
        'user': config['mysql'].get('user', 'root'),
        'password': config['mysql'].get('password', ''),
        'database': config['mysql'].get('database', ''),
        'port': config['mysql'].getint('port', 3306),
        'charset': config['mysql'].get('charset', 'utf8mb4')
    }

def test_connection_contabilidad(db_params):
    try:
        conn = mysql.connector.connect(**db_params)
        print("Conexión exitosa a la base de datos contable.")
        conn.close()
        return True
    except mysql.connector.Error as err:
        print(f"Error de conexión a la base de datos contable: {err}")
        return False

if __name__ == "__main__":
    config_path = "db_config_contabilidad.ini"
    db_params = get_db_config_contabilidad(config_path)
    test_connection_contabilidad(db_params)
