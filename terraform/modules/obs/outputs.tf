output "bucket_name" {
  description = "The name of the created OBS bucket"
  value       = huaweicloud_obs_bucket.obs_bucket.bucket
}

output "bucket_id" {
  description = "The ID of the created OBS bucket"
  value       = huaweicloud_obs_bucket.obs_bucket.id
}

output "bucket_domain_name" {
  description = "The domain name of the created OBS bucket"
  value       = huaweicloud_obs_bucket.obs_bucket.bucket_domain_name
}

output "bucket_region" {
  description = "The region of the created OBS bucket"
  value       = huaweicloud_obs_bucket.obs_bucket.region
}

output "bucket_storage_class" {
  description = "The storage class of the created OBS bucket"
  value       = huaweicloud_obs_bucket.obs_bucket.storage_class
}

output "bucket_acl" {
  description = "The ACL of the created OBS bucket"
  value       = huaweicloud_obs_bucket.obs_bucket.acl
}

output "bucket_encryption_enabled" {
  description = "Whether encryption is enabled on the bucket"
  value       = huaweicloud_obs_bucket.obs_bucket.encryption
}

output "kms_key_id" {
  description = "The ID of the KMS key used for encryption"
  value       = var.bucket_encryption && var.bucket_encryption_key_id == "" ? huaweicloud_kms_key.obs_kms_key[0].id : var.bucket_encryption_key_id
}

output "kms_key_alias" {
  description = "The alias of the KMS key used for encryption"
  value       = var.key_alias
}