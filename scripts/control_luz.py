#!/usr/bin/env python3
"""
Script CLI para controlar luces WIZ desde línea de comandos.
Uso: python3 scripts/control_luz.py <nombre_luz> <accion> [valor]

Ejemplos:
    python3 scripts/control_luz.py pieza apagar
    python3 scripts/control_luz.py pieza encender
    python3 scripts/control_luz.py pieza brillo 50
    python3 scripts/control_luz.py pieza color rojo
    python3 scripts/control_luz.py todas apagar
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from utils.wiz_utils import control_light


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 scripts/control_luz.py <nombre_luz> <accion> [valor]")
        print("")
        print("Acciones: encender, apagar, brillo, color")
        print("Ejemplos:")
        print('  python3 scripts/control_luz.py pieza apagar')
        print('  python3 scripts/control_luz.py pieza encender')
        print('  python3 scripts/control_luz.py pieza brillo 50')
        print('  python3 scripts/control_luz.py pieza color rojo')
        print('  python3 scripts/control_luz.py todas apagar')
        sys.exit(1)
    
    name = sys.argv[1]
    action = sys.argv[2]
    value = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Run the async function
    result = asyncio.run(control_light(name, action, value))
    print(result)


if __name__ == "__main__":
    main()
