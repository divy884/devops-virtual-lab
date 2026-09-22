terraform {
  required_version = ">= 1.0"
}

resource "null_resource" "devops_lab" {
  provisioner "local-exec" {
    command = "echo 'Terraform provisioned the local DevOps lab environment'"
  }
}
