variable "region_name" {
  description = "The region where the OBS bucket is located"
  type        = string
}

variable "access_key" {
  description = "The access key of the IAM user"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "The secret key of the IAM user"
  type        = string
  sensitive   = true
}

variable "bucket_encryption" {
  description = "Whether to enable server-side encryption on the OBS bucket"
  type        = bool
  default     = false
}

variable "bucket_encryption_key_id" {
  description = "Existing KMS key ID for encryption (empty string to auto-create)"
  type        = string
  default     = ""
  nullable    = false
}

variable "key_alias" {
  description = "Alias for the auto-created KMS key (required only when encryption=true and no existing key provided)"
  type        = string
  default     = ""
}

variable "key_usage" {
  description = "KMS key usage"
  type        = string
  default     = "ENCRYPT_DECRYPT"
}

variable "bucket_name" {
  description = "The name of the OBS bucket"
  type        = string
}

variable "bucket_storage_class" {
  description = "Storage class: STANDARD, WARM, COLD"
  type        = string
  default     = "STANDARD"
}

variable "bucket_acl" {
  description = "ACL: private, public-read, public-read-write"
  type        = string
  default     = "private"
}

variable "bucket_sse_algorithm" {
  description = "SSE algorithm when encryption is enabled"
  type        = string
  default     = "kms"
}

variable "bucket_force_destroy" {
  description = "Force destroy bucket even if it contains objects"
  type        = bool
  default     = true
}

variable "bucket_tags" {
  description = "Tags for the bucket"
  type        = map(string)
  default     = {}
}
