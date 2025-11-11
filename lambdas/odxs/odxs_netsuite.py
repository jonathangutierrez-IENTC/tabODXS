from auth_utils import get_iso_bearer_token
from iso_utils import iso_netsuite_generic_search
from database_utils import PostgresDB, MySQLDB
from utils import flatten_record, normalize_trandate
from typing import Any
from datetime import datetime, timedelta
import sys

def lambda_handler(start_date, end_date, access_token) -> Any:
    try:
        print('facturas_cabecera__lambda_handler')
        logs = {
            "name": "facturas_cabecera__lambda_handler"
        }
        print(access_token)
        sys.exit()
        if access_token is None:
            logs["access_token"] = "Error al obtener access token."
            print(logs)
            raise Exception("Error al obtener access token para el ISO.")

        # Load data
        facturas_cabecera = iso_netsuite_generic_search(
            access_token=access_token,
            forceCache=False,
            record_type='invoice',
            columns='["subsidiary", "internalid","tranid","trandate","custbody_ientc_cs_related_account","currency","exchangerate","amount","amountpaid","amountremaining","custbody_ientc_external_id_mongo","custbody_ientc_fact_cancelled","custbody_ientc_invoice_type"]',
            filters=f'[["type","anyof","CustInvc"],"AND",["mainline","is","T"],"AND",["taxline","is","F"],"AND",["systemnotes.type","ANY",""],"AND",["systemnotes.date","within","{start_date}","{end_date}"],"AND",["memo","isnot","SALDOINI 31-DIC-23"]]'
        )
        print(f"✅ {len(facturas_cabecera)} facturas de hoy")
        if facturas_cabecera == None:
            logs['facturas_cabecera'] = "Error al obtener facturas cabecera."
            print(logs)
            raise Exception("Error con la petición del servicio generico de Netsuite")

        # Connect database
        db = MySQLDB(
            user="root",
            password="",
            host="127.0.0.1",
            port=3306,        
            database="ientc"
        )
        db.connect()

        # Flatten data 
        flattened_data_cabecera = [flatten_record(rec) for rec in facturas_cabecera]

        # Rename keys and save in database
        for record in flattened_data_cabecera:
            record['account_number'] = record.pop('custbody_ientc_cs_related_account_text')
            record['total'] = record.pop('amount')
            record['paid'] = record.pop('amountpaid')
            record['debt'] = record.pop('amountremaining')
            record['id_mongo'] = record.pop('custbody_ientc_external_id_mongo')
            record['cancelled'] = record.pop('custbody_ientc_fact_cancelled')
            record['subsidiary'] = record.pop('subsidiary_text')
            record['numsubsidiary'] = record.pop('subsidiary_value')
            record['date'] = normalize_trandate(record.pop('trandate', None))

            # Revisamos si existe una factura en la base de datos
            factura = db.execute(
                "SELECT * FROM facturas WHERE id = :id",
                {"id": record['id']},
                fetch=True
            )

            if not factura:
                # Si no existe la factura insertamos la factura con total_pagos, total_nc y total_debt en 0.0
                columns = ", ".join(record.keys())
                placeholders = ", ".join([f":{k}" for k in record.keys()])
                sql = f"INSERT INTO facturas ({columns}) VALUES ({placeholders})"
                db.execute(sql, record)
            else:
                # Si la factura existe, actualizamos los datos dejando los datos total_pagos, total_nc y total_debt como se encuentren
                set_clause = ", ".join([f"{k} = :{k}" for k in record.keys() if k != "id"])
                sql = f"UPDATE facturas SET {set_clause} WHERE id = :id"
                db.execute(sql, record)
        
        db.close()
        print(logs)
    except Exception as e:
        logs["Error"] = f"Error en el código: {e}"
        print(logs)


def main():
    start_date = datetime.strptime("06/11/2025", "%d/%m/%Y") 
    end_date = datetime.strptime("06/11/2025", "%d/%m/%Y")
    access_token = get_iso_bearer_token()
    for i in range(365):    
        print(start_date.strftime("%d/%m/%Y"))
        lambda_handler(start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"), access_token)
        if start_date.strftime("%d/%m/%Y") == "06/11/2025":
            break
        
        start_date += timedelta(days=1)
        end_date += timedelta(days=1)

main()