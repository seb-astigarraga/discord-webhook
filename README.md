# Webhook de Discord para Alarmas de AWS CloudWatch (Lambda, Python 3.12)

Este proyecto contiene una función de AWS Lambda que recibe notificaciones de alarmas de CloudWatch desde SNS y las reenvía a un webhook de Discord como un embed enriquecido.

## Características

- Analiza mensajes de SNS de CloudWatch Alarm y formatea embeds de Discord
- Cliente HTTP robusto con timeouts y reintentos con backoff exponencial
- Dependencias mínimas (solo librería estándar)
- Desplegable vía AWS CloudFormation Git Sync o actualización manual de .zip en Lambda

## Requisitos

- Una URL de Webhook de Discord

## Uso con AWS CloudFormation Git Sync (recomendado)

Este flujo crea el stack con CloudFormation a partir de tu repositorio (Git Sync) y luego actualiza el código de la Lambda cargando un archivo .zip generado en tu máquina.

1. Prepara parámetros y template

- Asegúrate de tener estos archivos en el root del repo:
  - `template.yaml`: plantilla de CloudFormation (crea la Lambda, el tópico SNS y sus permisos).
  - `deployment.yaml`: manifiesto para Git Sync, que indica el template y parámetros.
- Edita `deployment.yaml` y coloca tu webhook de Discord en `parameters.DiscordWebhookUrl`.

2. Crea el stack desde Git (CloudFormation Git Sync)

- En la consola de AWS: CloudFormation → Create stack → With Git repository.
- Conecta tu proveedor Git (GitHub, etc.), selecciona el repo/branch y apunta a `deployment.yaml` como archivo de despliegue.
- Revisa los parámetros y crea el stack. Espera a que el stack termine en estado CREATE_COMPLETE.
- En los Outputs verás `FunctionName` (nombre de la Lambda) y `SnsTopicArn` (ARN del tópico SNS).

3. Empaquetar el código local en .zip

- macOS / Linux (Bash):

```bash
cd /Users/sebas-astigarraga/Documents/github/discord-webhook
zip -r function.zip discord_webhook_lambda -x "**/__pycache__/*" "*.pyc" ".DS_Store"
```

- Windows (PowerShell):

```powershell
cd C:\ruta\al\repo\discord-webhook
Compress-Archive -Path .\discord_webhook_lambda -DestinationPath .\function.zip -Force
```

- Windows (opcional, con 7-Zip si necesitas exclusiones avanzadas):

```powershell
7z a -r .\function.zip .\discord_webhook_lambda\ -x!__pycache__ -x!*.pyc
```

Notas importantes del .zip:

- El `Handler` definido es `discord_webhook_lambda.handler.lambda_handler`, por lo que el .zip debe incluir la carpeta `discord_webhook_lambda/` en su raíz.
- No es necesario incluir dependencias externas: el proyecto usa solo la librería estándar de Python.

4. Actualizar el código de la Lambda con el .zip

- Vía AWS CLI:

```bash
aws lambda update-function-code \
  --function-name <FunctionName> \
  --zip-file fileb://function.zip \
  --region <tu-region>
```

Si prefieres S3:

```bash
aws s3 cp function.zip s3://<tu-bucket>/lambda/function.zip
aws lambda update-function-code \
  --function-name <FunctionName> \
  --s3-bucket <tu-bucket> \
  --s3-key lambda/function.zip \
  --region <tu-region>
```

- Vía Consola AWS: ve a Lambda → tu función → Code → Upload from → .zip file → selecciona `function.zip` → Deploy.

5. Probar fin a fin

- Publica un mensaje de prueba en el tópico SNS (`SnsTopicArn`) o configura una alarma de CloudWatch para que envíe notificaciones a ese tópico. Verifica que llegue el embed a tu webhook de Discord.

## Configuración de desarrollo local

```bash
cd /Users/sebas-astigarraga/Documents/github/discord-webhook
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Configuración

- Debe configurarse la variable de entorno `DISCORD_WEBHOOK_URL` (el template de CloudFormation la conecta vía parámetro).

## Estructura del proyecto

```
discord_webhook_lambda/
  handler.py            # Punto de entrada de AWS Lambda
  discord_client.py     # Cliente HTTP para el webhook de Discord
  formatter.py          # Mensaje de CloudWatch → Embed de Discord
template.yaml           # Plantilla de CloudFormation (base del stack)
deployment.yaml         # Manifiesto de CloudFormation Git Sync
README.md
```

## Verificación manual

Puedes probar end-to-end sin tests unitarios:

1. Configura la variable de entorno e invoca el handler localmente:

```python
from discord_webhook_lambda.handler import lambda_handler
import os

os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/..."

# JSON de alarma de CloudWatch (ejemplo mínimo)
lambda_handler({
  "Records": [
    {"Sns": {"Message": '{"AlarmName":"TestAlarm","NewStateValue":"OK","Region":"us-east-1","StateChangeTime":"2024-01-01T00:00:00Z","NewStateReason":"Example reason"}'}}
  ]
}, None)
```

## Licencia

MIT
