# Barra de progreso amigable para consola
import sys
import time

def barra_progreso(iterable, mensaje="Procesando", total=None, longitud=60, delay=0.1):
    """
    Muestra una barra de progreso simple en consola.
    Uso:
        for _ in barra_progreso(range(10), "Consultando API", total=10):
            ...
    """
    if total is None:
        try:
            total = len(iterable)
        except TypeError:
            total = None
    for i, item in enumerate(iterable):
        if total:
            completado = int(longitud * (i+1) / total)
            barra = "█" * completado + "-" * (longitud - completado)
            sys.stdout.write(f"\r{mensaje} |{barra}| {i+1}/{total}")
        else:
            sys.stdout.write(f"\r{mensaje} {i+1}")
        sys.stdout.flush()
        yield item
        if delay:
            time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()
