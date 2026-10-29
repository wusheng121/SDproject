from utils.security import decrypt_phone, mask_phone


def user_roles(user):
    return sorted({ur.role.name for ur in user.user_roles if ur.role})


def user_permissions(user):
    permissions = set()
    for user_role in user.user_roles:
        if not user_role.role:
            continue
        for rp in user_role.role.role_permissions:
            if rp.permission:
                permissions.add(rp.permission.name)
    return sorted(permissions)


def user_public(user, include_permissions: bool = False):
    phone = decrypt_phone(user.phone_ciphertext)
    data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "user_type": user.user_type,
        "phone": mask_phone(phone),
        "email_verified": user.is_email_verified,
        "is_active": user.is_active,
        "preferred_categories": user.get_preferred_categories_list(),
        "roles": user_roles(user),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
    if include_permissions:
        data["permissions"] = user_permissions(user)
    return data


def product_public(product, include_description: bool = False):
    data = {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "condition": product.condition,
        "image_url": product.image_url,
        "status": product.status,
        "categories": [pc.category.name for pc in product.categories if pc.category],
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }
    if include_description:
        data["description"] = product.description
        data["seller"] = (
            {"id": product.seller.id, "username": product.seller.username}
            if product.seller
            else None
        )
    return data


def operation_log_public(log):
    return {
        "id": log.id,
        "actor_id": log.actor_id,
        "actor": log.actor_snapshot,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "before": log.before_json,
        "after": log.after_json,
        "ip": log.ip,
        "user_agent": log.user_agent,
        "trace_id": log.trace_id,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def pagination(page: int, page_size: int, total: int):
    return {"page": page, "page_size": page_size, "total": total}
