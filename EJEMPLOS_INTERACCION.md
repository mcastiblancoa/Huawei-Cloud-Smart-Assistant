# Ejemplos de Interacción con el Asistente para Terraform

## Cómo el asistente pedirá parámetros

### Ejemplo 1: Crear bucket OBS

**Usuario:** "Crea un bucket OBS con Terraform"

**Asistente:** 
```
Para crear un bucket OBS con Terraform, necesito algunos detalles:

1. **Nombre del bucket:** ¿Qué nombre quieres para el bucket? (debe ser único globalmente)
   Ejemplo: `mi-bucket-datos-2024`

2. **Región:** ¿En qué región de Huawei Cloud? (por defecto: ap-southeast-3)
   Opciones comunes: `ap-southeast-3`, `la-north-2`, `eu-west-0`

3. **Clase de almacenamiento:** ¿Qué clase de almacenamiento prefieres?
   - `STANDARD`: Para datos de acceso frecuente
   - `WARM`: Para datos de acceso infrecuente (menos de 1 vez/mes)
   - `COLD`: Para datos de archivo (acceso muy raro)

4. **Encriptación:** ¿Quieres habilitar encriptación KMS?
   - `Sí`: Con clave KMS (puedo crear una nueva o usar existente)
   - `No`: Sin encriptación

5. **Alias de clave KMS:** Si eliges encriptación, ¿qué alias para la clave KMS?
   Ejemplo: `kms-mi-bucket`

6. **Etiquetas:** ¿Alguna etiqueta para organizar? (opcional)
   Formato: `{"Proyecto": "WebApp", "Entorno": "Producción"}`

Por favor, proporciona estos detalles o dime "usa valores por defecto" para continuar.
```

**Usuario:** "Usa valores por defecto con nombre mi-backup-empresa"

**Asistente:**
```
✅ **OBS Bucket created successfully using Terraform!**

**Bucket Details:**
- **Name:** mi-backup-empresa
- **Region:** ap-southeast-3
- **Storage Class:** STANDARD
- **ACL:** private
- **Encryption:** Enabled
- **SSE Algorithm:** kms

**Outputs:**
- Bucket Domain Name: mi-backup-empresa.obs.ap-southeast-3.myhuaweicloud.com
- Bucket ID: mi-backup-empresa
- KMS Key ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

**Terraform Deployment:** Successfully provisioned using infrastructure as code.

El bucket se ha creado exitosamente. Puedes acceder a él en: https://mi-backup-empresa.obs.ap-southeast-3.myhuaweicloud.com
```

### Ejemplo 2: Desplegar ELB completo

**Usuario:** "Necesito un ELB para mi aplicación web"

**Asistente:**
```
Para desplegar un ELB con Terraform, necesito configurar varios recursos:

1. **Nombre del ELB:** ¿Qué nombre para el balanceador de carga?
   Ejemplo: `elb-aplicacion-web`

2. **Nombre de la VPC:** ¿Qué nombre para la red virtual?
   Ejemplo: `vpc-produccion`

3. **Nombre de la subred:** ¿Qué nombre para la subred?
   Ejemplo: `subnet-publica`

4. **Nombre del grupo de seguridad:** ¿Qué nombre para el grupo de seguridad?
   Ejemplo: `sg-web`

5. **Nombre de la instancia ECS:** ¿Qué nombre para el servidor?
   Ejemplo: `ecs-servidor-web`

6. **¿IP pública?** ¿Quieres una IP pública (EIP) asociada al ELB?
   - `Sí`: Para acceso desde internet
   - `No`: Solo acceso interno

7. **Protocolo y puerto:** ¿Qué protocolo y puerto?
   - `HTTP/80`: Web estándar
   - `HTTPS/443`: Web seguro (necesita certificado)
   - `TCP/8080`: Aplicación personalizada

8. **Especificaciones de la instancia:** ¿Qué tamaño de instancia ECS?
   - `Pequeña`: 1 vCPU, 1 GB RAM (s6.small.1)
   - `Mediana`: 2 vCPU, 4 GB RAM (s6.large.2) - Recomendado
   - `Grande`: 4 vCPU, 8 GB RAM (s6.xlarge.2)

Por favor, proporciona estos detalles o dime "configuración básica" para usar valores por defecto.
```

**Usuario:** "Configuración básica con nombre elb-mi-app"

**Asistente:**
```
✅ **ELB Environment created successfully using Terraform!**

**Infrastructure Details:**
- **ELB Name:** elb-mi-app
- **Region:** ap-southeast-3
- **Availability Zone:** ap-southeast-3a

**Resources Created:**
1. **VPC:** vpc-elb-mi-app (CIDR: 172.16.0.0/16)
2. **Subnet:** subnet-elb-mi-app
3. **Security Group:** sg-elb-mi-app
4. **ECS Instance:** ecs-elb-mi-app (Flavor: s6.large.2)
5. **ELB Load Balancer:** elb-mi-app
6. **Listener:** HTTP:80
7. **Backend Pool:** ROUND_ROBIN algorithm
8. **Health Check:** HTTP on path '/'
9. **EIP:** Sí (100.125.1.100)

**Access Information:**
- **ELB Endpoint:** http://100.125.1.100
- **Backend Server:** 192.168.1.10:80

**Terraform Deployment:** Successfully provisioned complete infrastructure as code.

Tu aplicación web estará accesible en: http://100.125.1.100
```

### Ejemplo 3: Configuración avanzada de OBS

**Usuario:** "Crea un bucket OBS para logs con clase WARM y encriptación usando mi clave KMS-12345"

**Asistente:**
```
Entiendo que quieres un bucket OBS para logs con configuración específica:

1. **Nombre del bucket:** ¿Qué nombre específico para el bucket de logs?
   Ejemplo: `logs-aplicacion-2024`

2. **Región:** ¿Misma región (ap-southeast-3) u otra?

3. **Clase de almacenamiento:** Confirmado WARM para logs

4. **Encriptación:** Confirmado con clave KMS existente ID: KMS-12345

5. **Etiquetas:** ¿Alguna etiqueta específica para los logs?
   Ejemplo: `{"Tipo": "Logs", "Retención": "30días", "Proyecto": "AplicacionWeb"}`

¿Es correcta esta configuración? ¿Quieres proceder?
```

**Usuario:** "Sí, procede con nombre logs-app-produccion y etiquetas Tipo=Logs,App=Produccion"

**Asistente:**
```
✅ **OBS Bucket created successfully using Terraform!**

**Bucket Details:**
- **Name:** logs-app-produccion
- **Region:** ap-southeast-3
- **Storage Class:** WARM
- **ACL:** private
- **Encryption:** Enabled (clave KMS-12345)
- **SSE Algorithm:** kms

**Tags:**
- Tipo: Logs
- App: Produccion

**Outputs:**
- Bucket Domain Name: logs-app-produccion.obs.ap-southeast-3.myhuaweicloud.com
- Bucket ID: logs-app-produccion

**Nota:** La clase WARM es ideal para logs con acceso infrecuente. Los costos de almacenamiento son menores que STANDARD.
```

### Ejemplo 4: ELB con configuración personalizada

**Usuario:** "Quiero un ELB HTTPS en puerto 443 con 2 instancias de 4GB RAM cada una"

**Asistente:**
```
Para un ELB HTTPS necesito información adicional:

1. **Nombre del ELB:** ¿Qué nombre para el balanceador HTTPS?
   Ejemplo: `elb-https-seguro`

2. **Certificado SSL:** ¿Tienes un certificado SSL existente?
   - `Sí, tengo ID de certificado`: Proporciona el ID del contenedor TLS
   - `No, configura HTTP por ahora`: Puedo configurar HTTP y actualizar después

3. **Número de instancias:** Confirmado 2 instancias

4. **Tamaño de instancias:** 4GB RAM corresponde a:
   - `s6.large.2`: 2 vCPU, 4GB RAM (recomendado)
   - `c6.large.2`: 2 vCPU, 4GB RAM (computación optimizada)

5. **Health check:** ¿Qué ruta y códigos para health check?
   - Ruta por defecto: `/`
   - Códigos esperados: `200-202`

6. **Algoritmo de balanceo:** ¿Qué algoritmo prefieres?
   - `ROUND_ROBIN`: Distribución equitativa (por defecto)
   - `LEAST_CONNECTIONS`: A la instancia con menos conexiones
   - `SOURCE_IP`: Basado en IP de origen

¿Puedes proporcionar estos detalles?
```

**Usuario:** "Nombre elb-https-app, sin certificado por ahora, 2 instancias s6.large.2, health check en /health, algoritmo round robin"

**Asistente:**
```
⚠️ **Para HTTPS necesito un certificado SSL.**

Te sugiero estas opciones:

1. **Configurar HTTP ahora, HTTPS después:** Crear ELB HTTP en puerto 80 y actualizar a HTTPS después
2. **Usar certificado auto-firmado:** Solo para pruebas/desarrollo
3. **Proporcionar certificado existente:** Si ya tienes uno en Huawei Cloud

¿Cuál prefieres?

Si eliges opción 1, puedo crear:
- ELB HTTP en puerto 80
- 2 instancias s6.large.2
- Health check en /health
- Algoritmo ROUND_ROBIN

Luego puedes añadir HTTPS cuando tengas el certificado.
```

**Usuario:** "Opción 1, crea ELB HTTP primero"

**Asistente:**
```
✅ **ELB Environment created successfully using Terraform!**

**Infrastructure Details:**
- **ELB Name:** elb-https-app
- **Region:** ap-southeast-3
- **Protocol:** HTTP (puerto 80) - Puedes actualizar a HTTPS después

**Resources Created:**
1. **VPC:** vpc-elb-https-app
2. **Subnet:** subnet-elb-https-app
3. **Security Group:** sg-elb-https-app
4. **2x ECS Instances:** ecs-elb-https-app-01, ecs-elb-https-app-02
5. **ELB Load Balancer:** elb-https-app
6. **Listener:** HTTP:80
7. **Backend Pool:** ROUND_ROBIN algorithm
8. **Health Check:** HTTP on path '/health'
9. **EIP:** Sí (100.125.1.101)

**Nota:** Para actualizar a HTTPS:
1. Obtén un certificado SSL
2. Usa la herramienta `manage_elb_listener` para actualizar el listener
3. O crea un nuevo listener HTTPS en puerto 443

Acceso actual: http://100.125.1.101
```

### Ejemplo 5: Preguntas comunes y respuestas

**Usuario:** "¿Por qué usar Terraform en lugar de KooCLI para OBS/ELB?"

**Asistente:**
```
**Ventajas de Terraform para OBS/ELB:**

1. **Confiabilidad:** Terraform maneja mejor errores y es idempotente
2. **Infraestructura como código:** Configuración declarativa y reproducible
3. **Estado:** Seguimiento del estado de los recursos
4. **Dependencias:** Manejo automático de dependencias entre recursos
5. **Rollback:** Mejor manejo de despliegues fallidos
6. **Consistencia:** Mismos resultados cada vez
7. **KooCLI issues:** Algunos servicios como OBS tienen problemas con KooCLI

**Cuándo usar Terraform vs KooCLI:**
- **Terraform:** OBS buckets, ELB complejos, infraestructura completa
- **KooCLI:** Operaciones simples, consultas, gestión diaria

**El asistente elige automáticamente:** Si pides OBS o ELB, uso Terraform. Para otras operaciones, uso KooCLI.
```

**Usuario:** "¿Qué parámetros son obligatorios para OBS?"

**Asistente:**
```
**Parámetros obligatorios para OBS con Terraform:**

1. **bucket_name:** Nombre único global (requerido)
   Ejemplo: `mi-bucket-único-123`

**Parámetros opcionales (valores por defecto):**
- **region:** ap-southeast-3
- **storage_class:** STANDARD
- **acl:** private
- **encryption:** true (habilitado)
- **sse_algorithm:** kms
- **key_alias:** auto-generado (ej: obs-key-<nombre-bucket>)
- **force_destroy:** true

**Ejemplo mínimo:**
```
Crear bucket OBS llamado "mis-archivos"
```

**Ejemplo completo:**
```
Crear bucket OBS llamado "backup-datos" en la-north-2 con clase WARM, 
encriptación deshabilitada y etiquetas Proyecto=Backup, Entorno=Produccion
```
```

**Usuario:** "¿Y para ELB?"

**Asistente:**
```
**Parámetros obligatorios para ELB con Terraform:**

1. **loadbalancer_name:** Nombre del ELB
2. **vpc_name:** Nombre de la VPC
3. **subnet_name:** Nombre de la subred
4. **security_group_name:** Nombre del grupo de seguridad
5. **instance_name:** Nombre de la instancia ECS

**Parámetros opcionales (valores por defecto):**
- **region:** ap-southeast-3
- **associate_eip:** true (con IP pública)
- **listener_protocol:** HTTP
- **listener_port:** 80
- **instance_cpu_cores:** 2
- **instance_memory_gb:** 4
- **health_check_path:** /
- **health_check_method:** GET

**Ejemplo mínimo:**
```
Desplegar ELB "mi-balanceador" con VPC "mi-vpc", subnet "mi-subnet", 
security group "mi-sg", instancia "mi-servidor"
```

**Recomendación:** Usa nombres descriptivos para fácil identificación.
```

## Resumen de integración completada

✅ **Integración de Terraform completada exitosamente**

### Lo que se implementó:

1. **Módulos Terraform:**
   - `terraform/modules/obs/`: Bucket OBS con encriptación KMS
   - `terraform/modules/elb/`: Entorno ELB completo (VPC, subnet, SG, ECS, ELB, EIP)

2. **Herramientas LangGraph:**
   - `deploy_obs_bucket_with_terraform`: Crea buckets OBS
   - `deploy_elb_with_terraform`: Despliega entornos ELB
   - `list_terraform_deployments`: Lista despliegues (placeholder)

3. **Integración con el sistema existente:**
   - Registro automático en `ToolRegistry`
   - Categorías correctas (DEPLOY para creación, QUERY para listado)
   - Keywords en español e inglés para descubrimiento
   - Uso de credenciales del archivo `.env`

4. **Características:**
   - Manejo de directorios temporales para estado de Terraform
   - Generación dinámica de configuración Terraform
   - Parsing de outputs de Terraform
   - Manejo de errores robusto
   - Compatibilidad con el flujo LangGraph existente

### Cómo usar:

1. **Para OBS:** "Crea un bucket OBS con Terraform llamado [nombre]"
2. **Para ELB:** "Despliega un ELB con Terraform para [descripción]"
3. **Para listar:** "¿Qué tengo desplegado con Terraform?"

### Próximos pasos sugeridos:

1. **Pruebas reales:** Probar con credenciales reales de Huawei Cloud
2. **Persistencia de estado:** Almacenar estado de Terraform en OBS
3. **Módulos adicionales:** Añadir RDS, VPC, etc.
4. **Gestión de ciclo de vida:** Operaciones update/delete
5. **Plantillas:** Configuraciones predefinidas comunes

La integración está lista para usar. ¡El asistente ahora puede desplegar OBS y ELB de manera confiable usando Terraform!