from datetime import datetime

def flatten_record(record: dict) -> dict:
    flat = {"recordType": record.get("recordType"), "id": record.get("id")}

    values = record.get("values", {})
    for key, value in values.items():
        if isinstance(value, list) and value:
            item = value[0]
            if isinstance(item, dict):
                flat.update({
                    f"{key}_value": item.get("value"),
                    f"{key}_text": item.get("text"),
                })
        elif isinstance(value, dict):
            flat.update({f"{key}_{k}": v for k, v in value.items()})
        else:
            flat[key] = value

    # Simplificación del type
    flat["type"] = "Recurrente" if "custbody_ientc_invoice_type_text" in flat else "No recurrente"

    if "custbody_ientc_cs_related_account" in flat:
        flat["custbody_ientc_cs_related_account_text"] = "Sin Cuenta"

    # Eliminamos llaves innecesarias de un solo golpe
    remove_fields = {
        "recordType",
        "id",
        "internalid_value",
        "internalid_text",
        "type",
        "custbody_ientc_order_account_value",
        "custbody_ientc_order_status_value",
        "custbody_ientc_order_support_value",
        "custbody_ientc_order_cancelby_value",
        "custbody_ientc_order_assigned_tech_value",
        "salesrep_value"

    }
    flat = {k: v for k, v in flat.items() if k not in remove_fields}
    return flat

def normalize_trandate(val: str | datetime | None) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")  # formato recomendado para MySQL DATE
    s = str(val).strip()
    for fmt in ("%d/%m/%Y","%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d"): #####CORRECCIÓN IMPORTANTE
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # último recurso: déjalo como viene (si tu columna es TEXT lo aceptará)
    return s