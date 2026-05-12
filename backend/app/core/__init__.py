"""Paquete raíz de core. Mantenido mínimo para evitar imports circulares.

Usa imports directos desde subpaquetes para código nuevo.
La compatibilidad hacia atrás se maneja mediante archivos de
re-exportación individuales.
"""

# Root __init__.py - keep minimal to avoid circular imports
# Use subpackage imports directly for new code
# Backward compatibility is handled by individual re-export files
