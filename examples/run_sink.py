#!/usr/bin/env python3
"""
Script de exemplo para executar o Sink Device.

Uso:
    sudo python3 examples/run_sink.py hci0
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sink.sink_device import main

if __name__ == '__main__':
    sys.exit(main())
