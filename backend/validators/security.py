DESTRUCTIVE_OPERATIONS: frozenset[str] = frozenset({
    "DeleteVpc", "DeleteSubnet", "NovaDeleteServer", "DeleteRdsInstance",
    "DeleteLoadBalancer", "DeleteSecurityGroup", "DeleteVolume",
    "DeletePublicIp", "DeleteNatGateway", "DeleteDnsRecordset",
    "DeleteCluster", "DeleteFunction", "DeleteBucket",
})

DESTRUCTIVE_KEYWORDS: frozenset[str] = frozenset({
    "delete", "destroy", "remove", "terminate", "purge", "drop",
})


def is_destructive_operation(operation: str) -> bool:
    if operation in DESTRUCTIVE_OPERATIONS:
        return True
    op_lower = operation.lower()
    return any(kw in op_lower for kw in DESTRUCTIVE_KEYWORDS)


def requires_confirmation(service: str, operation: str) -> bool:
    return is_destructive_operation(operation)


def get_confirmation_message(service: str, operation: str) -> str:
    return (
        f"⚠️ You are about to execute a destructive operation: "
        f"`hcloud {service} {operation}`. This action may be irreversible. "
        f"Please confirm to proceed."
    )
