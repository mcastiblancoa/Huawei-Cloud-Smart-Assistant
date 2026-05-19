resource "huaweicloud_kms_key" "obs_kms_key" {
  count       = var.bucket_encryption && var.bucket_encryption_key_id == "" ? 1 : 0
  key_alias   = var.key_alias
  key_usage   = var.key_usage
}

resource "huaweicloud_obs_bucket" "obs_bucket" {
  bucket        = var.bucket_name
  storage_class = var.bucket_storage_class
  acl           = var.bucket_acl
  force_destroy = var.bucket_force_destroy
  tags          = var.bucket_tags

  dynamic "encryption" {
    for_each = var.bucket_encryption ? [1] : []
    content {
      sse_algorithm = var.bucket_sse_algorithm
      kms_key_id    = var.bucket_encryption_key_id != "" ? var.bucket_encryption_key_id : (length(huaweicloud_kms_key.obs_kms_key) > 0 ? huaweicloud_kms_key.obs_kms_key[0].id : null)
    }
  }

  lifecycle {
    ignore_changes = [
      encryption
    ]
  }
}
