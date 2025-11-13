from auth_utils import get_iso_bearer_token
from iso_utils import iso_netsuite_generic_search
from database_utils import PostgresDB, MySQLDB
from utils import flatten_record, normalize_trandate
from typing import Any
from datetime import datetime, timedelta
import os
import json
import sys
import traceback #para indicar linea donde hubo error
import re

def lambda_handler(start_date, end_date, access_token) -> Any:
    try:
        print('cuentas_lambda_handler')
        logs = {
            "name": "cuentas_lambda_handler"
        }
        if access_token is None:
            logs["access_token"] = "Error al obtener access token."
            print(logs)
            raise Exception("Error al obtener access token para el ISO.")
        
        # Load data
        cuentas = iso_netsuite_generic_search(
            access_token=access_token,
            forceCache=False,
            record_type='customrecord_ientc_service_master',
            columns='["internalid","externalid","name","custrecord_ientc_cs_ismaster","custrecord_ientc_cs_reference","custrecord_ientc_cs_servicestatus",' \
            '"custrecord_ientc_cs_service","custrecord_ientc_cs_type","custrecord_ientc_cs_forcedterm","custrecord_ientc_cs_forcedtermvalue","custrecord_ientc_cs_invoicereq",' \
            '"custrecord_ientc_cs_item","custrecord_ientc_cs_phone","custrecord_ientc_cs_isesim","custrecord_ientc_cs_total","custrecord_ientc_cs_subtotal","created",' \
            '"owner","custrecord_ientc_cs_activatedate","custrecord_ientc_cs_canceldate","custrecord_ientc_cs_cancelreason","custrecord_ientc_cs_canceledby",' \
            '"custrecord_ientc_cs_parent", "custrecord_ientc_cs_parent.custentity_mx_rfc", "custrecord_ientc_cs_parent.custentity_mx_sat_registered_name","custrecord_ientc_cs_parent.custentity_ientc_crm_secteconomico",' \
            '"custrecord_ientc_cs_state","custrecord_ientc_cs_municipio","custrecord_ientc_cs_colonia","custrecord_ientc_cs_localidad","custrecord_ientc_cs_latitude",' \
            '"custrecord_ientc_cs_longitude","custrecord_ientc_cs_dirreference"]',
            filters=f'[["created","within","{start_date}","{end_date}"]]'
        )

        print(f"✅ {len(cuentas)} cuentas de hoy")   
        
        if cuentas == None:
            logs['cuentas'] = "Error al obtener cuentas."
            print(logs)
            raise Exception("Error con la petición del servicio generico de Netsuite")

        # Connect database
        db = MySQLDB(
            user="root",
            password="",
            host="127.0.0.1",
            port=3306,        
            database="olimpo-db"
        )
        db.connect()

        # Flatten data 
        flattened_data_cabecera = [flatten_record(rec) for rec in cuentas]


        # Rename keys and save in database
        for record in flattened_data_cabecera:
            record['folio'] = record.pop('id')
            record['accountNumber'] = record.pop('name')
            record['isMaster'] = record.pop('custrecord_ientc_cs_ismaster')
            record['masterAccount'] = record.pop('custrecord_ientc_cs_reference_text', None)
            record.pop('custrecord_ientc_cs_reference', None)  # ✅ elimina lista si existe
            record['statusAccount'] = record.pop('custrecord_ientc_cs_servicestatus_text', None)
            record['category'] = record.pop('custrecord_ientc_cs_service_text', None)
            record.pop('custrecord_ientc_cs_service', None)  # ✅ elimina lista si existe
            record['typeAccount'] = record.pop('custrecord_ientc_cs_type_text', None)
            record.pop('custrecord_ientc_cs_type', None)  # ✅ elimina lista si existe
            record['isForcedTerm'] = record.pop('custrecord_ientc_cs_forcedtermvalue_value', None)
            record.pop('custrecord_ientc_cs_forcedtermvalue', None)  # ✅ elimina lista si existe
            record['forcedTermValue'] = (lambda t: int(m.group(1)) if (m := re.search(r"(\d+)\s*(?=meses)", t.lower())) else None)(record.pop('custrecord_ientc_cs_forcedtermvalue_text', "") or "")
            record['invoiceRequired'] = record.pop('custrecord_ientc_cs_invoicereq')
            record['productAccount'] = record.pop('custrecord_ientc_cs_item_text', None)
            record.pop('custrecord_ientc_cs_item', None)  # ✅ elimina lista si existe
            record['phone'] = record.pop('custrecord_ientc_cs_phone')
            record['sim'] = ("esim" if record.pop('custrecord_ientc_cs_isesim', False) else "sim")
            record['totalAccount'] = (lambda v: float(v) if v not in (None, "", " ") else None)(record.pop('custrecord_ientc_cs_total', None))
            record['subTotaLAccount'] = (lambda v: float(v) if v not in (None, "", " ") else None)(record.pop('custrecord_ientc_cs_subtotal', None))
            record['createdAtAccount'] = normalize_trandate((record.pop('created', None) or '').split(' ')[0] or None)
            record['activatedAtAccount'] = normalize_trandate((record.pop('custrecord_ientc_cs_activatedate', None) or '').split(' ')[0] or None)
            record['cancelledAtAccount'] = normalize_trandate((record.pop('custrecord_ientc_cs_canceldate', None) or '').split(' ')[0] or None)
            record['cancelledReason'] = record.pop('custrecord_ientc_cs_cancelreason')
            record['cancelledBy'] = record.pop('custrecord_ientc_cs_canceledby_text', None)
            record.pop('custrecord_ientc_cs_canceledby', None)  # ✅ elimina lista si existe
            record['businessName'] = record.pop('custrecord_ientc_cs_parent_text', None)
            record.pop('custrecord_ientc_cs_parent', None)  # ✅ elimina lista si existe
            record['rfc'] = record.pop('custrecord_ientc_cs_parent.custentity_mx_rfc')
            record['financialSector'] = record.pop('custrecord_ientc_cs_parent.custentity_ientc_crm_secteconomico_text', None)
            record.pop('custrecord_ientc_cs_parent.custentity_ientc_crm_secteconomico', None)  # ✅ elimina lista si existe
            record['estado'] = record.pop('custrecord_ientc_cs_state_text', None)
            record.pop('custrecord_ientc_cs_state', None)  # ✅ elimina lista si existe
            record['municipio'] = record.pop('custrecord_ientc_cs_municipio_text', None)
            record.pop('custrecord_ientc_cs_municipio', None)  # ✅ elimina lista si existe
            record['colonia'] = record.pop('custrecord_ientc_cs_colonia_text', None)
            record.pop('custrecord_ientc_cs_colonia', None)  # ✅ elimina lista si existe
            record['localidad'] = record.pop('custrecord_ientc_cs_localidad', None)
            record['latitude'] = (lambda v:
                (float(m.group(0)) if (m := re.search(r"-?\d+(?:\.\d+)?", v.replace(',', '.'))) else None)
                if v and (v := v.strip()).lower() not in ("na", "") else None)(record.pop('custrecord_ientc_cs_latitude', None))
            record['longitude'] = (lambda v:
                (float(m.group(0)) if (m := re.search(r"-?\d+(?:\.\d+)?", v.replace(',', '.'))) else None)
                if v and (v := v.strip()).lower() not in ("na", "") else None)(record.pop('custrecord_ientc_cs_longitude', None))
            record['accountReferences'] = record.pop('custrecord_ientc_cs_dirreference')

            for key, value in record.items():
                if isinstance(value, list):
                    record[key] = None

            # Revisamos si existe una cuenta en la base de datos
            precuenta = db.execute(
                "SELECT * FROM accounts WHERE folio = :folio",
                {"folio": record['folio']},
                fetch=True
            )

            if not precuenta:
                # Si no existe la cuenta insertamos la cuenta con total_pagos, total_nc y total_debt en 0.0
                columns = ", ".join(record.keys())
                placeholders = ", ".join([f":{k}" for k in record.keys()])
                sql = f"INSERT INTO accounts ({columns}) VALUES ({placeholders})"
                db.execute(sql, record)
            else:
                # Si la cuenta existe, actualizamos los datos
                set_clause = ", ".join([f"{k} = :{k}" for k in record.keys() if k != "id"])
                sql = f"UPDATE accounts SET {set_clause} WHERE folio = :folio"
                db.execute(sql, record)
        
        db.close()
        print(logs)
    except Exception as e:
        logs["Error"] = f"Error en el código: {e}"
        print(traceback.format_exc())  # 🔥 Muestra exactamente la línea del error
        print(logs)


def main():
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now() - timedelta(days=1)
    access_token = get_iso_bearer_token()
    for _ in range(2):    
        print(start_date.strftime("%d/%m/%Y"))
        lambda_handler(start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"), access_token)
        start_date += timedelta(days=1)
        end_date += timedelta(days=1)

main()