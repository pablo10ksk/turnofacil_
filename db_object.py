import os
import requests
from dotenv import load_dotenv

load_dotenv()

class DbObject_Elasticsearch:
    def __init__(self):
        self.elastic_url = os.getenv("ELASTIC_ENDPOINT")
        self.elastic_api_key = os.getenv("ELASTICAPI_KEY")
        self.index = "reservation_upsa"  # Cambia si tu índice tiene otro nombre

        self.headers = {
            "Authorization": f"ApiKey {self.elastic_api_key}",
            "Content-Type": "application/json"
        }

    def delete_reservation(self, phone, date):
        """
        Borra la reserva futura con ese teléfono y fecha.
        Devuelve True si éxito, False si no se encuentra o hay error.
        """
        # 1. Buscar el documento para obtener el _id
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"phone": phone}},
                        {"match": {"date": date}}
                    ]
                }
            }
        }
        search_url = f"{self.elastic_url}/{self.index}/_search"
        res = requests.get(search_url, headers=self.headers, json=query)
        try:
            hits = res.json().get("hits", {}).get("hits", [])
        except Exception as e:
            print("❌ Error al buscar reserva para borrar:", e)
            return False

        if not hits:
            return False  # No encontrado

        doc_id = hits[0]["_id"]

        # 2. Eliminar por _id
        delete_url = f"{self.elastic_url}/{self.index}/_doc/{doc_id}"
        del_res = requests.delete(delete_url, headers=self.headers)
        return del_res.status_code in [200, 202]

    def insert_value(self, doc: dict) -> bool:
        """
        Inserta un nuevo documento en Elastic.
        """
        url = f"{self.elastic_url}/{self.index}/_doc"
        try:
            res = requests.post(url, headers=self.headers, json=doc)
            return res.status_code in [200, 201]
        except Exception as e:
            print(f"❌ Error insertando en Elastic: {e}")
            return False

    def search_(self, phone: str) -> list:
        """
        Devuelve todas las reservas para un usuario (ordenadas por fecha descendente).
        """
        query = {
            "query": {"match": {"phone": phone}},
            "sort": [{"date": {"order": "desc"}}],
        }
        url = f"{self.elastic_url}/{self.index}/_search"
        try:
            res = requests.get(url, headers=self.headers, json=query)
            hits = res.json().get("hits", {}).get("hits", [])
            return hits
        except Exception as e:
            print(f"❌ Error buscando en Elastic: {e}")
            return []

    def get_future_events(self, phone: str, current_datetime: str) -> list:
        """
        Devuelve reservas futuras (>= ahora) para un usuario.
        """
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"phone": phone}},
                        {"range": {"date": {"gte": current_datetime}}}
                    ]
                }
            }
        }
        url = f"{self.elastic_url}/{self.index}/_search"
        try:
            res = requests.get(url, headers=self.headers, json=query)
            hits = res.json().get("hits", {}).get("hits", [])
            return [h["_source"] for h in hits]
        except Exception as e:
            print("❌ Error get_future_events:", e)
            return []

    def get_past_events(self, phone: str, current_datetime: str) -> list:
        """
        Devuelve reservas pasadas (<= ahora) para un usuario.
        """
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"phone": phone}},
                        {"range": {"date": {"lte": current_datetime}}}
                    ]
                }
            }
        }
        url = f"{self.elastic_url}/{self.index}/_search"
        try:
            res = requests.get(url, headers=self.headers, json=query)
            hits = res.json().get("hits", {}).get("hits", [])
            return [h["_source"] for h in hits]
        except Exception as e:
            print("❌ Error get_past_events:", e)
            return []

    def get_user_data_by_phone(self, phone):
        """
        Busca los datos del usuario por teléfono. Devuelve el documento encontrado o None.
        """
        query = {
            "query": {
                "match": {"telefono": phone}
            },
            "size": 1
        }
        search_url = f"{self.elastic_url}/{self.index}/_search"
        res = requests.get(search_url, headers=self.headers, json=query)
        try:
            hits = res.json().get("hits", {}).get("hits", [])
            if not hits:
                return None
            # Si guardas datos de usuario como parte de la reserva, puedes devolver así:
            doc = hits[0]["_source"]
            return {
                "nif": doc.get("nif"),
                "nombre": doc.get("nombre"),
                "apellido1": doc.get("apellido1"),
                "apellido2": doc.get("apellido2"),
                "telefono": doc.get("telefono"),
                "email": doc.get("email"),
                "motivo": doc.get("motivo"),
            }
        except Exception as e:
            print("❌ Error al buscar datos de usuario:", e)
            return None

    def get_all_reservations(self):
        query = {"query": {"match_all": {}}}
        url = f"{self.elastic_url}/{self.index}/_search"
        res = requests.get(url, headers=self.headers, json=query)
        hits = res.json().get("hits", {}).get("hits", [])
        return hits
