# Huawei Cloud Smart Voice & CLI Assistant

## Objetivo Principal

El objetivo de este proyecto es proveer un **asistente de voz y texto inteligente** que permita a los usuarios administrar, consultar y comprender sus **recursos activos**, **facturación mensual** y gestionar infraestructura en Huawei Cloud. Se pueden utilizar comandos en lenguaje natural (inglés o español), como _"¿Cuánto gasté en marzo de 2026?"_ o _"Crea una nueva VPC"_.

Al centralizar la información en un panel interactivo y dotarlo de inteligencia con modelos LLM y herramientas de línea de comandos, se busca simplificar significativamente el monitoreo y gestión de múltiples servicios cloud.

---

## Estructura del Proyecto

El proyecto está compuesto por tres componentes/carpetas principales integradas:

### 1. `huawei_cloud_smart_assistant/`

Contiene la aplicación principal (full-stack):

- **Frontend:** Construido con React y Vite (`frontend/`). Provee la interfaz gráfica que incluye un panel de chat, vistas para grabación de voz con el micrófono, y un dashboard para mostrar tablas y gráficos de recursos y facturación obtenidos mediante las APIs de Huawei.
- **Backend:** Una API basada en FastAPI (`backend/app/main.py`). Se encarga de procesar audios, interactuar con los motores de transcripción (Huawei Cloud SIS API o módulos Whisper ASR), evaluar intenciones y extraer parámetros con un LLM de IA (DeepSeek vía ModelArts), ejecutar SDKs (RMS y BSS Intl) y unificar los conectores hacia el agente conversacional subyacente.

### 2. `koocli-assitant/`

Agente conversacional de despliegue y gestión potenciado por **LangGraph** y **LangChain**:

- Ejecuta e infiere parámetros para la línea de comandos interactiva de Huawei (`hcloud` o KooCLI), traduciendo así peticiones complejas al formato CLI para inspeccionar y abstraer recursos.
- **Auto-depuración activa:** Si faltan parámetros clave de `hcloud`, el bot es capaz de ejecutar automáticamente su archivo de ayuda en terminal e inyectar un payload JSON con las directrices resueltas.
- Alberga los JSON de mapeo API de la infraestructura (`services_schema/`).

### 3. `context_koocli_assistant/`

Directorio de contexto y scaffolding:

- **Scripts de inicialización:** Principalmente contiene el script PowerShell `generate_all_services_json.ps1`, el cual extrae automatizadamente descripciones y estructuras de los comandos disponibles desde el CLI (`hcloud`) a formato JSON para nutrir el cerebro del agente `koocli-assitant`.

---

## Tecnologías Utilizadas

- **Frontend:** React 18, Vite, Recharts, Lucide React.
- **Backend:** Python 3, FastAPI, Uvicorn.
- **Inteligencia Artificial / NLP:** Modelo DeepSeek-V3.2 (Huawei ModelArts / MaaS), Interacción vía LangGraph y LangChain, Transcripción con Huawei Cloud SIS y Whisper ASR.
- **Cloud & CLI:** Huawei Cloud SDK, KooCLI (`hcloud`).

---

## Configuración del Entorno (`.env`)

Asegúrate de contar con el comando de [KooCLI](https://support.huaweicloud.com/intl/en-us/qs-hcli/hcli_02_003.html) en tu entorno y de que `hcloud` responda adecuadamente antes de arrancar los servicios de gestión.

Para levantar todo el ecosistema crea tu archivo `.env` en la raíz mapeando todos tus credenciales:

```env
# ---------- Huawei Cloud Credentials ----------
HUAWEI_REGION=ap-southeast-3
HUAWEI_PROJECT_ID=tu_project_id
HUAWEI_PROJECT_ID_SIS=tu_project_id
HUAWEI_AK=tu_access_key
HUAWEI_SK=tu_secret_key
CLOUD_SDK_DOMAIN_ID=tu_domain_id

# IAM (for SIS / voice transcription)
HUAWEI_IAM_ENDPOINT=https://iam.ap-southeast-3.myhuaweicloud.com
HUAWEI_SIS_ENDPOINT=https://sis-ext.ap-southeast-3.myhuaweicloud.com
HUAWEI_USERNAME=tu_usuario
HUAWEI_DOMAIN_NAME=tu_domain
HUAWEI_PASSWORD=tu_password

# ---------- SIS Config ----------
SIS_PROPERTY=english_16k_common # Propiedad de engine SIS
SIS_ADD_PUNC=yes
SIS_DIGIT_NORM=yes
SIS_NEED_WORD_INFO=no

# ---------- MaaS (ModelArts - DeepSeek) ----------
MAAS_API_KEY=tu_api_key_de_maas
MAAS_API_URL=https://api-ap-southeast-1.modelarts-maas.com/v2/chat/completions
OPEN_API_BASE=https://api-ap-southeast-1.modelarts-maas.com/openai/v1

# ---------- Backend (FastAPI) ----------
APP_NAME=Huawei Smart Assistant
APP_ENV=local
BACKEND_CORS_ORIGINS=http://localhost:5173
MAX_UPLOAD_MB=5
TEMP_DIR=tmp_audio

# ---------- Frontend ----------
VITE_API_BASE_URL=http://localhost:8003
WHISPER_ASR_URL=http://110.238.82.203:9000/asr
```

---

## Ejecución Local

### 1. Entorno Backend API y Agentes (Python)

Debes iniciar el backend corriendo tanto los módulos de FastAPI que conectan con el modelo de LangGraph / Koocli.

```bash
# Configurar y Activar entorno virtual
# Windows
.\koocli-assitant\.venv\Scripts\Activate.ps1

# Linux / Mac
source koocli-assitant/.venv/bin/activate

# Instalar las dependencias integradas:
pip install -r koocli-assitant/requirements.txt
pip install -r huawei_cloud_smart_assistant/requirements.txt

# Ejecutar el servidor apuntando al archivo principal de FastAPI desde la ruta base:
# Modifica el puerto de acuerdo con la variable VITE_API_BASE_URL
python -m uvicorn huawei_cloud_smart_assistant.backend.app.main:app --reload --host 0.0.0.0 --port 8003
```

### 2. Frontend (React + Vite)

Abre otra pestaña de la terminal e inicializa el nodo web.

```bash
cd huawei_cloud_smart_assistant/frontend

npm install
npm run dev
```

### Acceso a la Interfaz y Casos de Uso

Al iniciar el nodo de React dirígete a http://localhost:5173 para explorar:

**Módulo de Consulta por Voz (Dashboard Gráfico)**
Usa tu voz en Español o Inglés para recolectar información tabulada sobre RMS o facturación BSS en un dashboard inmersivo con React y Recharts:

- _"Show me my active services"_
- _"Please give me the billing info of March 2026"_
- _"¿Cuánto gasté en marzo de 2026?"_

**Módulo Chat HCLI Autónomo (Administración vía LangGraph)**
Interacción de nivel infraestructura mediante la capa base LangGraph gestionando llamadas de sistema integradas por KooCLI.

- _"Lista todas mis instancias ECS actuales."_
- _"Crea una red nueva."_ (El sistema pedirá confirmaciones o deducirá el --help para armarlo)
- _"Muéstrame un resumen usando RMS CollectAllResourcesSummary en Singapur (ap-southeast-1)"_
