# Ejemplos de Interacción con Terraform

## Ejemplo 1: Crear bucket OBS con encriptación KMS

**Usuario:**
```
Hola, necesito crear un bucket OBS para almacenar archivos de respaldo con encriptación. Usa Terraform por favor.
```

**Asistente:**
```
¡Claro! Para crear un bucket OBS con Terraform, necesito algunos detalles:

1. ¿Qué nombre quieres para el bucket? (debe ser único globalmente)
2. ¿En qué región? (por defecto: ap-southeast-3)
3. ¿Qué clase de almacenamiento prefieres? (STANDARD, WARM, COLD)
4. ¿Quieres usar una clave KMS existente o crear una nueva?

Por ejemplo, podrías decir: "Crea un bucket llamado mis-respaldos en ap-southeast-3 con clase STANDARD y crea una nueva clave KMS llamada clave-respaldos"
```

**Usuario:**
```
Crea un bucket llamado backup-empresa-2024 en ap-southeast-3 con clase STANDARD y crea una nueva clave KMS llamada kms-backup-empresa
```

**Asistente:**
```
✅ **OBS Bucket created successfully using Terraform!**

**Bucket Details:**
- **Name:** backup-empresa-2024
- **Region:** ap-southeast-3
- **Storage Class:** STANDARD
- **ACL:** private
- **Encryption:** Enabled
- **SSE Algorithm:** kms

**Outputs:**
- Bucket Domain Name: backup-empresa-2024.obs.ap-southeast-3.myhuaweicloud.com
- Bucket ID: backup-empresa-2024
- KMS Key ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

**Terraform Deployment:** Successfully provisioned using infrastructure as code.

El bucket se ha creado exitosamente con encriptación KMS. Puedes acceder a él en: https://backup-empresa-2024.obs.ap-southeast-3.myhuaweicloud.com
```

## Ejemplo 2: Desplegar ELB completo para aplicación web

**Usuario:**
```
Necesito desplegar un balanceador de carga ELB para mi aplicación web. Usa Terraform para mayor confiabilidad.
```

**Asistente:**
```
Perfecto. Para desplegar un ELB con Terraform, necesito:

1. ¿Qué nombre quieres para el ELB?
2. ¿Qué nombre para la VPC?
3. ¿Qué nombre para la subred?
4. ¿Qué nombre para el grupo de seguridad?
5. ¿Qué nombre para la instancia ECS?
6. ¿Quieres IP pública (EIP) asociada? (sí/no)
7. ¿Qué protocolo y puerto? (ej: HTTP/80, HTTPS/443)

Por ejemplo: "Despliega un ELB llamado web-elb con VPC vpc-web, subnet public-web, sg-web, instancia web-server-1, con EIP y protocolo HTTP puerto 80"
```

**Usuario:**
```
Despliega un ELB llamado produccion-web con VPC vpc-produccion, subnet subnet-publica, sg produccion-sg, instancia app-server-01, con EIP y protocolo HTTP puerto 8080
```

**Asistente:**
```
✅ **ELB Environment created successfully using Terraform!**

**Infrastructure Details:**
- **ELB Name:** produccion-web
- **Region:** ap-southeast-3
- **Availability Zone:** ap-southeast-3a

**Resources Created:**
1. **VPC:** vpc-produccion (CIDR: 172.16.0.0/16)
2. **Subnet:** subnet-publica
3. **Security Group:** produccion-sg
4. **ECS Instance:** app-server-01 (Flavor: s6.large.2)
5. **ELB Load Balancer:** produccion-web
6. **Listener:** HTTP:8080
7. **Backend Pool:** ROUND_ROBIN algorithm
8. **Health Check:** HTTP on path '/'
9. **EIP:** Yes

**Outputs:**
- ELB ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
- ECS Instance ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
- ECS Instance IP: 192.168.1.10
- EIP Address: 100.125.1.100
- VPC ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
- Subnet ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
- Security Group ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

**Access Information:**
- **ELB Endpoint:** http://100.125.1.100:8080
- **Backend Server:** 192.168.1.10:8080

**Terraform Deployment:** Successfully provisioned complete infrastructure as code.

El entorno ELB está listo. Tu aplicación web estará accesible en: http://100.125.1.100:8080
```

## Ejemplo 3: Crear bucket OBS con configuración avanzada

**Usuario:**
```
Crea un bucket OBS para archivos de log con clase WARM, encriptación usando mi clave existente KMS-12345, y etiquetas Environment=Development, Team=DevOps
```

**Asistente:**
```
✅ **OBS Bucket created successfully using Terraform!**

**Bucket Details:**
- **Name:** logs-desarrollo-2024
- **Region:** ap-southeast-3
- **Storage Class:** WARM
- **ACL:** private
- **Encryption:** Enabled
- **SSE Algorithm:** kms
- **KMS Key:** KMS-12345 (existente)

**Tags:**
- Environment: Development
- Team: DevOps

**Outputs:**
- Bucket Domain Name: logs-desarrollo-2024.obs.ap-southeast-3.myhuaweicloud.com
- Bucket ID: logs-desarrollo-2024

**Terraform Deployment:** Successfully provisioned using infrastructure as code.

El bucket de logs se ha creado con clase WARM (acceso infrecuente) y usando tu clave KMS existente.
```

## Ejemplo 4: Desplegar ELB HTTPS con certificado

**Usuario:**
```
Necesito un ELB con HTTPS en el puerto 443 para mi sitio seguro. Usa Terraform.
```

**Asistente:**
```
Para HTTPS necesito información adicional:

1. ¿Tienes un certificado SSL existente o necesitas crear uno?
2. Si tienes certificado existente, ¿cuál es el ID del contenedor TLS?
3. ¿Quieres usar HTTP/2?
4. ¿Necesitas políticas de cifrado TLS específicas?

Puedo configurar:
- Protocolo TERMINATED_HTTPS (SSL termination en ELB)
- Certificado SSL (existente o nuevo)
- Redirección HTTP a HTTPS opcional
- Políticas de seguridad TLS

Por ejemplo: "Configura ELB seguro con HTTPS puerto 443, certificado existente cert-12345, sin HTTP/2"
```

**Usuario:**
```
Configura ELB seguro con HTTPS puerto 443, sin certificado por ahora (puedo añadirlo después), con HTTP/2 habilitado
```

**Asistente:**
```
Para HTTPS necesito un certificado SSL. Te sugiero:

1. **Opción A:** Proporciona tu certificado existente (ID del contenedor TLS)
2. **Opción B:** Crea un ELB HTTP ahora y actualiza a HTTPS después con tu certificado
3. **Opción C:** Usa un certificado auto-firmado temporal (solo pruebas)

¿Cuál prefieres?
```

## Ejemplo 5: Listar despliegues Terraform

**Usuario:**
```
¿Qué recursos tengo desplegados con Terraform?
```

**Asistente:**
```
📋 **Terraform Deployment Status**

**Note:** Esta es una implementación básica. En producción, se rastrearían los archivos de estado de Terraform.

**Cómo funciona la integración de Terraform:**
1. **Despliegues OBS:** Crea buckets OBS con encriptación KMS
2. **Despliegues ELB:** Crea entornos ELB completos con VPC, ECS, etc.
3. **Gestión de estado:** Cada despliegue crea estado temporal de Terraform
4. **Confiabilidad:** Más confiable que KooCLI para despliegues complejos

**Módulos Terraform disponibles:**
1. **Módulo OBS:** Crea buckets OBS con encriptación KMS opcional
2. **Módulo ELB:** Crea VPC, subred, grupo seguridad, instancia ECS, ELB, listener, pool, health check, EIP

**Para desplegar recursos:**
- Usa `deploy_obs_bucket_with_terraform` para buckets OBS
- Usa `deploy_elb_with_terraform` para entornos ELB

**Beneficios sobre KooCLI:**
- Infraestructura como código declarativa
- Mejor manejo de errores y rollback
- Creación de recursos consistente
- Soporte para dependencias complejas
- Seguimiento de estado (cuando se implemente)
```

## Flujo de trabajo recomendado

### Para OBS:
1. Planifica el nombre único global del bucket
2. Decide la clase de almacenamiento según patrones de acceso
3. Configura encriptación KMS (nueva o existente)
4. Define etiquetas para organización
5. Usa `deploy_obs_bucket_with_terraform`

### Para ELB:
1. Define nombres para todos los recursos (VPC, subnet, SG, etc.)
2. Selecciona región y zona de disponibilidad
3. Configura protocolo y puerto
4. Decide si necesitas EIP
5. Configura health checks
6. Usa `deploy_elb_with_terraform`

## Mejores prácticas

1. **Nomenclatura:** Usa nombres descriptivos y consistentes
2. **Etiquetado:** Añade etiquetas para todos los recursos
3. **Seguridad:** Usa encriptación KMS para datos sensibles
4. **Monitoreo:** Configura alertas después del despliegue
5. **Documentación:** Mantén registro de los recursos creados
6. **Backup:** Considera snapshots para instancias ECS críticas