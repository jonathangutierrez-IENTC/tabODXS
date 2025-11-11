import os
import requests

ISO_API_URL: str = os.environ.get("ISO_API_URL", "https://api-iso-prod.ientc.dev")
ISO_CLIENT_ID: str = os.environ.get("ISO_CLIENT_ID", "7u8e8r61t8l0ntfgr9vj3ihi7e")
ISO_CLIENT_SECRET: str = os.environ.get("ISO_CLIENT_SECRET", "kqoc3hc22eogbeek7rees6vj1o5pqa39qr88iefgp7a4nv7uiqq")

def get_iso_bearer_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": ISO_CLIENT_ID,
        "client_secret": ISO_CLIENT_SECRET
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Hacer la petición
    response = requests.post( 
        url=f"{ISO_API_URL}/auth/jwt/token",
        data=data,
        headers=headers)

    # Mostrar resultado
    if response.status_code == 200:
        token_info = response.json()
        access_token = token_info.get("access_token")
        return access_token
    else:
        print("ERROR RESPONSE: ", response.text)
        return None
