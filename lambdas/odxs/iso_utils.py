import os
import requests
from typing import List, Dict, Any

# Carga la URL de la API desde las variables de entorno.
ISO_API_URL: str = os.environ.get("ISO_API_URL", "https://api-iso-prod.ientc.dev")
ISO_CLIENT_ID: str = os.environ.get("ISO_CLIENT_ID", "7u8e8r61t8l0ntfgr9vj3ihi7e")
ISO_CLIENT_SECRET: str = os.environ.get("ISO_CLIENT_SECRET", "kqoc3hc22eogbeek7rees6vj1o5pqa39qr88iefgp7a4nv7uiqq")

# Tiempo de espera por defecto para todas las peticiones.
req_timeout = 30

def iso_netsuite_generic_search(access_token: str, forceCache: bool, record_type: str, columns: str, filters: str) -> List[Dict[str, Any]]:
    """ Recupera datos de Netsuite utilizando un proceso de dos pasos: 
        1. Obtener la información de paginación (número total de páginas).
        2. Iterar sobre las páginas para obtener todos los registros.
        
        Sustituye el bucle infinito por un bucle FOR controlado para prevenir 
        alertas de error innecesarias.
        
        :param access_token: Token de autorización.
        :param forceCache: Indica si se debe forzar la recarga de caché.
        :param record_type: Tipo de registro de Netsuite a buscar.
        :param columns: Columnas a retornar.
        :param filters: Filtros de búsqueda.
        :return list: Lista de registros de Netsuite o None en caso de error.
    """
    
    # Tamaño de página fijo, como en el script original
    PAGE_SIZE = 500

    if not access_token:
        print("Error: Access token es requerido y no se encontró.")
        return None

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    all_results = []
    
    # ----------------------------------------------------------------------
    # PASO 1: Petición para obtener la información de paginación (pages_info='true')
    # ----------------------------------------------------------------------

    page_info_params = {
        'forceCache': forceCache,
        'record_type': record_type,
        'columns': columns,
        'filters': filters,
        'page': 0, 
        'page_size': PAGE_SIZE,
        'pages_info': 'true' 
    }

    try:
        response_info = requests.get(
            f"{ISO_API_URL}/iso/api/netsuite/generic-search", 
            headers=headers, 
            params=page_info_params,
            timeout=req_timeout
        )
        
        # Levanta un error HTTP si la respuesta fue 4xx o 5xx
        response_info.raise_for_status() 

        info_data = response_info.json()
    
    except requests.exceptions.HTTPError as e:
        # Manejo de errores HTTP
        print(f"ISO NETSUITE ERROR HTTP (Paso 1, Estado {response_info.status_code}): {e}")
        try:
             print("ISO NETSUITE RESPUESTA (Paso 1): ", response_info.json())
        except:
             print("ISO NETSUITE RESPUESTA (Paso 1): ", response_info.text)
        return None
    except requests.exceptions.RequestException as e:
        # Manejo de errores de conexión/timeout
        print(f"ISO NETSUITE ERROR DE CONEXIÓN (Paso 1): {e}")
        return None
    except requests.JSONDecodeError:
        print("Error al decodificar JSON de la información de página (Paso 1).")
        return None
        
    # Extraer el número total de páginas.
    pages = info_data.get('pages', 0)
    print(f"{pages} paginas")
    
    # Revisa si la primera respuesta ya incluye los registros de la página 0.
    records_page_0 = info_data.get('records') or info_data.get('data')

    # Si hay 0 o 1 páginas (o menos de PAGE_SIZE registros), retornamos lo que ya tenemos.
    if pages <= 1 and isinstance(records_page_0, list):
         # Si pages=0, o pages=1 y los registros están aquí, terminamos.
        return records_page_0

    # Si hay varias páginas, determinamos la página inicial para el bucle.
    if isinstance(records_page_0, list) and records_page_0:
        all_results.extend(records_page_0)
        start_page = 1
    else:
        # Si no hay registros en el paso 1, empezamos desde la página 0.
        start_page = 0
    
    # Si 'pages' es 0, pero no encontramos registros, retornamos una lista vacía.
    if pages == 0 and not records_page_0:
        return []

    # ----------------------------------------------------------------------
    # PASO 2: Bucle FOR para traer los datos de cada página restante
    # ----------------------------------------------------------------------

    # El bucle FOR itera desde start_page hasta pages - 1
    for page in range(start_page, pages):
        
        # Parámetros para obtener los datos (sin 'pages_info').
        data_params = {
            'forceCache': forceCache,
            'record_type': record_type,
            'columns': columns,
            'filters': filters,
            'page': page,
            'page_size': PAGE_SIZE
        }

        try:
            response_data = requests.get(
                f"{ISO_API_URL}/iso/api/netsuite/generic-search", 
                headers=headers, 
                params=data_params,
                timeout=req_timeout
            )
            
            response_data.raise_for_status() # Levanta error si es 4xx/5xx
            data = response_data.json()
        
        except requests.exceptions.HTTPError as e:
            print(f"ISO NETSUITE ERROR HTTP (Paso 2, Página {page}, Estado {response_data.status_code}): {e}")
            try:
                print(f"ISO NETSUITE RESPUESTA (Paso 2, Página {page}): ", response_data.json())
            except:
                print(f"ISO NETSUITE RESPUESTA (Paso 2, Página {page}): ", response_data.text)
            return None
        except requests.exceptions.RequestException as e:
            print(f"ISO NETSUITE ERROR DE CONEXIÓN (Paso 2, Página {page}): {e}")
            return None
        except requests.JSONDecodeError:
            print(f"Error al decodificar JSON de los datos de la página {page} (Paso 2).")
            return None
            
        
        # Asegura que 'data' sea una lista o extrae registros si es un diccionario
        if isinstance(data, list):
            all_results.extend(data)
        elif isinstance(data, dict):
            # Intenta extraer la lista de registros bajo 'records' o 'data'
            list_data = data.get('records') or data.get('data')
            if isinstance(list_data, list):
                all_results.extend(list_data)

    return all_results