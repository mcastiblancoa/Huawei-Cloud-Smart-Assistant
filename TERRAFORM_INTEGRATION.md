# Integración de Terraform en Huawei Cloud Smart Assistant

## Descripción

Esta integración permite desplegar recursos de Huawei Cloud usando Terraform en lugar de KooCLI para servicios que no están bien soportados o tienen problemas con KooCLI, específicamente:

1. **OBS (Object Storage Service)** - Creación de buckets con encriptación KMS
2. **ELB (Elastic Load Balancer)** - Despliegue completo de entornos ELB

## Por qué usar Terraform en lugar de KooCLI

- **Confiabilidad**: Terraform maneja mejor los errores y es idempotente
- **Infraestructura como código**: Configuración declarativa y reproducible
- **Estado**: Seguimiento del estado de los recursos
- **Dependencias**: Manejo automático de dependencias entre recursos
- **Rollback**: Mejor manejo de despliegues fallidos

## Herramientas disponibles

### 1. `deploy_obs_bucket_with_terraform`

Crea un bucket OBS con encriptación KMS usando Terraform.

**Parámetros:**
- `bucket_name`: Nombre del bucket (requerido, único globalmente)
- `region`: Región de Huawei Cloud (por defecto: de configuración)
- `storage_class`: Clase de almacenamiento: STANDARD, WARM, COLD
- `acl`: Control de acceso: private, public-read, etc.
- `encryption`: Habilitar encriptación (true/false)
- `sse_algorithm`: Algoritmo de encriptación: kms
- `encryption_key_id`: ID de clave KMS existente (opcional)
- `key_alias`: Alias para la clave KMS (requerido si no hay encryption_key_id)
- `key_usage`: Uso de clave: ENCRYPT_DECRYPT
- `force_destroy`: Forzar destrucción incluso con objetos
- `tags`: Etiquetas en formato JSON

**Ejemplo de uso:**
```
Crear un bucket OBS llamado "mi-bucket-produccion" en ap-southeast-3 con encriptación KMS
```

### 2. `deploy_elb_with_terraform`

Despliega un entorno completo ELB con Terraform:
- VPC y subred
- Grupo de seguridad
- Instancia ECS
- Balanceador de carga ELB
- Listener y pool backend
- Health check
- EIP opcional

**Parámetros principales:**
- `loadbalancer_name`: Nombre del ELB
- `vpc_name`: Nombre de la VPC
- `subnet_name`: Nombre de la subred
- `security_group_name`: Nombre del grupo de seguridad
- `instance_name`: Nombre de la instancia ECS
- `region`: Región (por defecto: de configuración)
- `associate_eip`: Asociar EIP (true/false)
- `listener_protocol`: Protocolo: HTTP, HTTPS, TCP, UDP
- `listener_port`: Puerto del listener

**Ejemplo de uso:**
```
Desplegar un ELB llamado "mi-balanceador" con una instancia ECS "mi-servidor" en la región ap-southeast-3
```

### 3. `list_terraform_deployments`

Lista los despliegues de Terraform (implementación básica).

## Cómo usar las herramientas

### Desde la interfaz del asistente

1. **Para OBS:**
   ```
   Usuario: "Crea un bucket OBS con Terraform llamado mi-bucket-datos"
   Asistente: Usará `deploy_obs_bucket_with_terraform` con parámetros por defecto
   
   Usuario: "Crea un bucket OBS en la región la-north-2 con encriptación KMS y alias mi-clave"
   Asistente: Usará `deploy_obs_bucket_with_terraform` con región y alias especificados
   ```

2. **Para ELB:**
   ```
   Usuario: "Despliega un ELB con Terraform para mi aplicación web"
   Asistente: Pedirá los parámetros necesarios y usará `deploy_elb_with_terraform`
   
   Usuario: "Crea un balanceador de carga HTTP en el puerto 8080 con una instancia Ubuntu"
   Asistente: Configurará los parámetros apropiados y desplegará con Terraform
   ```

### Parámetros automáticos

El asistente pedirá automáticamente los parámetros requeridos:
- Para OBS: nombre del bucket, región, configuración de encriptación
- Para ELB: nombres de recursos, región, configuración de red, tipo de instancia

## Estructura de módulos Terraform

```
terraform/
├── modules/
│   ├── obs/                    # Módulo para OBS
│   │   ├── main.tf            # Configuración principal
│   │   ├── variables.tf       # Variables de entrada
│   │   └── outputs.tf         # Valores de salida
│   └── elb/                   # Módulo para ELB
│       ├── main.tf            # Configuración principal
│       ├── variables.tf       # Variables de entrada
│       └── outputs.tf         # Valores de salida
├── example_variables.tfvars.json  # Ejemplo de variables
└── README.md                  # Documentación
```

## Credenciales

Las credenciales se obtienen automáticamente del archivo `.env`:
- `HUAWEI_AK`: Access Key
- `HUAWEI_SK`: Secret Key
- `HUAWEI_REGION`: Región por defecto

## Ejemplos de comandos completos

### Crear bucket OBS:
```python
deploy_obs_bucket_with_terraform(
    bucket_name="mi-bucket-produccion",
    region="ap-southeast-3",
    storage_class="STANDARD",
    acl="private",
    encryption=True,
    key_alias="kms-key-produccion",
    tags='{"Environment": "Production", "Project": "WebApp"}'
)
```

### Desplegar ELB:
```python
deploy_elb_with_terraform(
    loadbalancer_name="elb-aplicacion-web",
    vpc_name="vpc-produccion",
    subnet_name="subnet-publica",
    security_group_name="sg-web",
    instance_name="ecs-servidor-web",
    region="ap-southeast-3",
    associate_eip=True,
    listener_protocol="HTTP",
    listener_port=80,
    instance_cpu_cores=2,
    instance_memory_gb=4
)
```

## Consideraciones de seguridad

1. **Credenciales**: Se usan las credenciales del archivo `.env`
2. **Estado de Terraform**: Se maneja en directorios temporales
3. **Claves KMS**: Se pueden crear nuevas o usar existentes
4. **ACL**: Por defecto "private" para buckets OBS

## Solución de problemas

### Error: "Terraform no encontrado"
- Asegúrate de tener Terraform instalado: `terraform --version`
- La versión debe ser >= 1.9.0

### Error: "Credenciales inválidas"
- Verifica que `HUAWEI_AK` y `HUAWEI_SK` estén configuradas en `.env`
- Verifica los permisos de las credenciales

### Error: "Nombre de bucket ya existe"
- Los nombres de bucket OBS deben ser únicos globalmente
- Usa un nombre diferente

### Error: "Límites de recursos"
- Verifica los límites de tu cuenta de Huawei Cloud
- Algunas regiones pueden tener límites diferentes

## Mejoras futuras

1. **Persistencia de estado**: Almacenar estado de Terraform en OBS o backend remoto
2. **Módulos adicionales**: Añadir módulos para más servicios (RDS, VPC, etc.)
3. **Gestión de ciclo de vida**: Operaciones de actualización y eliminación
4. **Plantillas predefinidas**: Configuraciones comunes predefinidas
5. **Validación avanzada**: Validación de parámetros antes del despliegue

## Referencias

- [Documentación de Terraform HuaweiCloud Provider](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs)
- [Ejemplos oficiales de Huawei Cloud Terraform](https://github.com/huaweicloud/terraform-provider-huaweicloud/tree/main/examples)
- [Guía de OBS con Terraform](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/obs_bucket)
- [Guía de ELB con Terraform](https://registry.terraform.io/providers/huaweicloud/huaweicloud/latest/docs/resources/lb_loadbalancer)