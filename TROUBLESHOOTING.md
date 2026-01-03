# Troubleshooting - Instalação e Setup

## Problema: "ModuleNotFoundError: No module named 'loguru'" ou similar

### Causa
As dependências Python não foram instaladas corretamente no virtual environment.

### Solução ✅ RESOLVIDA
Execute o script de instalação (atualizado):

```bash
sudo bash install_deps.sh
```

O script irá:
1. Instalar pacotes do sistema necessários (bluez, python3-dbus, python3-gi, etc)
2. Criar um virtual environment com acesso aos pacotes do sistema (`--system-site-packages`)
3. Instalar dependências Python (loguru, cryptography, bleak, simplepyble, typer, rich)

Os scripts `iot-node` e `iot-sink` agora ativam automaticamente o venv!

---

## Problema: "error: the following arguments are required: --cert, --key, --ca-cert"

### Causa
Os scripts `iot-node` ou `iot-sink` não estão detectando automaticamente os certificados.

### Solução ✅ RESOLVIDA
Os scripts foram atualizados para auto-detectar certificados. Execute simplesmente:

```bash
./iot-node interactive        # Para Node
./iot-sink interactive hci0   # Para Sink
```

Se tiver múltiplos certificados, o script usa o primeiro automaticamente. Para especificar outro:

```bash
./iot-node interactive --cert certs/meu_cert.pem --key certs/meu_key.pem
```

---

## Problema: "Unable to locate package hcitool"

### Causa
O pacote `hcitool` não existe como pacote separado nas versões modernas do Ubuntu.

### Solução ✅ RESOLVIDA
Já corrigido no `install_deps.sh`. O `hcitool` faz parte do pacote `bluez` que é instalado automaticamente.

Para verificar Bluetooth use:
```bash
hciconfig              # Lista adaptadores
bluetoothctl scan on   # Scan de dispositivos
```

---

## Problema: Erro ao importar `gi` (PyGObject) ou `dbus`

### Causa
Estes pacotes precisam de bibliotecas do sistema e são complicados de instalar no venv.

### Solução
O `install_deps.sh` foi atualizado para:
1. Instalar `python3-dbus` e `python3-gi` via apt (pacotes do sistema)
2. Criar venv com `--system-site-packages` para ter acesso a esses pacotes

Se ainda tiver problemas, instale manualmente:
```bash
sudo apt-get install -y python3-dbus python3-gi libdbus-1-dev libgirepository1.0-dev
```

---

## Problema: Scripts `iot-node` ou `iot-sink` não encontram módulos Python

### Causa
O virtual environment não está sendo ativado.

### Solução
Os scripts foram atualizados para ativar o venv automaticamente. Certifique-se de que:
1. Executou `sudo bash install_deps.sh`
2. O diretório `venv/` existe no projeto
3. Os scripts têm permissão de execução: `chmod +x iot-node iot-sink`

---

## Verificação Rápida

Após executar `install_deps.sh`, teste:

```bash
# 1. Verificar que o venv foi criado
ls -la venv/

# 2. Verificar pacotes instalados
source venv/bin/activate
pip list | grep -E "loguru|cryptography|bleak|typer|rich"
python3 -c "import dbus; import gi; print('✅ Pacotes do sistema OK')"
deactivate

# 3. Testar os scripts
./iot-node --help
./iot-sink --help
```

---

## Instalação Manual (se o script falhar)

Se o `install_deps.sh` falhar, instale manualmente:

```bash
# 1. Pacotes do sistema
sudo apt-get update
sudo apt-get install -y \
    bluez bluez-tools libbluetooth-dev \
    python3-dbus python3-gi libglib2.0-dev \
    python3-dev python3-pip python3-venv \
    build-essential pkg-config \
    libdbus-1-dev libgirepository1.0-dev \
    bluetooth

# 2. Virtual environment com acesso aos pacotes do sistema
python3 -m venv --system-site-packages venv
source venv/bin/activate

# 3. Dependências Python
pip install --upgrade pip
pip install loguru python-dotenv typer rich cryptography bleak

# 4. Verificar
python3 -c "import loguru, cryptography, bleak, dbus, gi; print('✅ Tudo OK')"
```

---

## Contacto

Se continuar com problemas, verifique:
- Versão do Python: `python3 --version` (deve ser >= 3.8)
- Versão do Ubuntu: `lsb_release -a`
- Logs de instalação do apt
