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
        print('odxs_lambda_handler')
        logs = {
            "name": "odxs_lambda_handler"
        }
        if access_token is None:
            logs["access_token"] = "Error al obtener access token."
            print(logs)
            raise Exception("Error al obtener access token para el ISO.")
        
        # Load data
        odxs = iso_netsuite_generic_search(
            access_token=access_token,
            forceCache=False,
            record_type='salesorder',
            columns='["internalid","custbody_ientc_order_support","custbody_ientc_order_assigned_tech","custbody_ientc_order_type",' \
            '"custbody_ientc_order_updatetype","startdate","enddate","tranid","custbody_ientc_order_odxmemo","custbody_ientc_order_status",' \
            '"custbody_ientc_order_account","total","custbody_ientc_order_cancelby","custbody_ientc_order_account.custrecord_ientc_cs_latitude",' \
            '"custbody_ientc_order_account.custrecord_ientc_cs_longitude", "datecreated", "salesrep"]',
            filters=f'[["datecreated","within","{start_date}","{end_date}"],"AND",["mainline","is","T"]]'
        )
        print(f"✅ {len(odxs)} odxs descargadas desde NetSuite")
        
        
        if odxs == None:
            logs['odxs'] = "Error al obtener odxs."
            print(logs)
            raise Exception("Error con la petición del servicio generico de Netsuite")

        # Aplanar
        flattened_data_cabecera = [flatten_record(rec) for rec in odxs]
            

        print(f"✅ {len(flattened_data_cabecera)} odxs de hoy")   

        # Connect database
        db = MySQLDB(
            host= "170.239.148.19",
            user= "ientc-pbi",
            password= "K3nw00d.1%40",
            database= "ientc-db",
            port= 3306
        )
        db.connect()



        # Rename keys and save in database
        for record in flattened_data_cabecera:
            record['technicalUser'] = record.pop('custbody_ientc_order_assigned_tech_text', None)
            record.pop('custbody_ientc_order_assigned_tech', None)  # ✅ elimina lista si existe
            record['createdBy'] = record.pop('salesrep_text', None)
            record.pop('salesrep', None)  # ✅ elimina lista si existe
            record['supportUser'] = record.pop('custbody_ientc_order_support_text', None)
            record.pop('custbody_ientc_order_support', None)  # ✅ elimina lista si existe
            record['typeValue'] = {"1": "ODT", "2": "ODS", "3": "ODR", "4": "ODD", "5": "ODA"}.get((v := record.pop('custbody_ientc_order_type_value', None)), v)
            record['startedAt'] = normalize_trandate(s) if (s := record.pop('startdate', None)) not in ("", None) else None
            record['finishedAt'] = normalize_trandate(e) if (e := record.pop('enddate', None)) not in ("", None) else None
            record['createdAt'] = normalize_trandate((record.pop('datecreated', None) or '').split(' ')[0] or None)
            record['odx'] = record.pop('tranid')
            record['totalAccount'] = (float(v) if (v := record.pop('custbody_ientc_order_account.custrecord_ientc_cs_total', "")) not in ("", None) else None)
            record['comments'] = record.pop('custbody_ientc_order_odxmemo')
            record['statusValue'] = record.pop('custbody_ientc_order_status_text', None)
            record.pop('custbody_ientc_order_status', None)  # ✅ elimina lista si existe
            record['updateaccount'] = record.pop('custbody_ientc_order_updatetype')
            record['accountNumber'] = record.pop('custbody_ientc_order_account_text', None)
            record.pop('custbody_ientc_order_account', None)  # ✅ elimina lista si existe
            record['chargeAmount'] = record.pop('total')
            record['chargeType'] = record.pop('custbody_ientc_order_type_text', None)
            record.pop('custbody_ientc_order_type', None)  # ✅ elimina lista si existe
            record['cancelledBy'] = record.pop('custbody_ientc_order_cancelby_text', None)
            record.pop('custbody_ientc_order_cancelby', None)  # ✅ elimina lista si existe
            record['latitude'] = (lambda v:
                (float(m.group(0)) if (m := re.search(r"-?\d+(?:\.\d+)?", v.replace(',', '.'))) else None)
                if v and (v := v.strip()).lower() not in ("na", "") else None)(record.pop('custbody_ientc_order_account.custrecord_ientc_cs_latitude', None))
            record['longitude'] = (lambda v:
                (float(m.group(0)) if (m := re.search(r"-?\d+(?:\.\d+)?", v.replace(',', '.'))) else None)
                if v and (v := v.strip()).lower() not in ("na", "") else None)(record.pop('custbody_ientc_order_account.custrecord_ientc_cs_longitude', None))
            
            for key, value in record.items():
                if isinstance(value, list):
                    record[key] = None

            # Revisamos si existe una odxs en la base de datos
            preodxs = db.execute(
                "SELECT * FROM odxs WHERE odx = :odx",
                {"odx": record['odx']},
                fetch=True
            )

            if not preodxs:
                # Si no existe la odxs insertamos la odxs con total_pagos, total_nc y total_debt en 0.0
                columns = ", ".join(record.keys())
                placeholders = ", ".join([f":{k}" for k in record.keys()])
                sql = f"INSERT INTO odxs ({columns}) VALUES ({placeholders})"
                db.execute(sql, record)
            else:
                # Si la odxs existe, actualizamos los datos
                set_clause = ", ".join([f"{k} = :{k}" for k in record.keys() if k != "id"])
                sql = f"UPDATE odxs SET {set_clause} WHERE odx = :odx"
                db.execute(sql, record)
        
        db.close()
        print(logs)
    except Exception as e:
        logs["Error"] = f"Error en el código: {e}"
        print(traceback.format_exc())  # 🔥 Muestra exactamente la línea del error
        print(logs)


def main():
    start_date = datetime.strptime("18/11/2025", "%d/%m/%Y") 
    end_date = datetime.strptime("18/11/2025", "%d/%m/%Y")
    access_token = get_iso_bearer_token()
    for i in range(365):    
        print(start_date.strftime("%d/%m/%Y"))
        lambda_handler(start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"), access_token)
        if start_date.strftime("%d/%m/%Y") == "18/11/2025":
            break
        
        start_date += timedelta(days=1)
        end_date += timedelta(days=1)

main()