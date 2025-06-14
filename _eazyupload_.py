import requests
import json
import os
from dotenv import load_dotenv
import datetime
from elasticsearch import Elasticsearch
from typing import List, Optional, Dict
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("api_key")

ELASTIC_ENDPOINT = os.getenv("ELASTIC_ENDPOINT")
ELASTICAPI_KEY = os.getenv("ELASTICAPI_KEY")


class eazybase:
    def __init__(
        self,
        company_: str,
        register_url_: str,
        login_url: str,
        hist_url: str,
        usr_: str,
        pwd_: str,
    ):
        self.base_url = register_url_
        self.login_url = login_url
        self.hist_url = hist_url
        self.company_owner = company_
        self.usr = usr_
        self.pwd = pwd_
        self.token_end_time = datetime.datetime.now() - datetime.timedelta(minutes=500)
        self._dologin()

    def _dologin(self):
        self.loginpayload = {"loginDs": self.usr, "pwdCd": self.pwd}
        token_ = self._submit_request(self.loginpayload, self.login_url, "dologin")
        self.token_ = token_["TOKEN_CD"]
        self.token_end_time = datetime.datetime.now() + datetime.timedelta(
            minutes=token_["TOKEN_VALIDITY_MIN_NM"]
        )

    def _submit_request(self, json_, url: str, action_: str = "execute") -> dict:
        # Get current time
        current_time = datetime.datetime.now()

        # Calculate remaining time in minutes
        remaining_minutes = (self.token_end_time - current_time).total_seconds() / 60
        if remaining_minutes <= 5 and action_ != "dologin":
            self._dologin()

        req = requests.post(url, data=json.dumps(json_))
        req_ = req.json()
        return req_

    def _register_message(
        self, inmsg: str, outmsg: str, phone_: str, name_: str
    ) -> dict:
        json_ = {
            "token": self.token_,
            "rawdata": {
                "phone": phone_,
                "name": name_,
                "companyowner": self.company_owner,
                "in_msg": inmsg,
                "out_msg": outmsg,
            },
        }
        try:
            return self._submit_request(self.base_url, json_)
        except:
            return False

    def _get_hist_messages(self, phone_: str, name_: str):
        json_ = {
            "token": self.token_,
            "rawdata": {
                "phone": phone_,
                "profile_name": name_,
                "companyowner": str(self.company_owner),
                "type": "json",
            },
        }
        return self._submit_request(json_, self.hist_url)


class dbdata:
    def __init__(self):
        self.endpoint = ELASTIC_ENDPOINT
        self.key = ELASTICAPI_KEY
        self.es = Elasticsearch(self.endpoint, api_key=self.key)
        self.index_name = "te_reservation"

    def insert_record(self, phone_: str, date_: str, location_: str) -> Dict:
        doc = {"phone_": phone_, "date_res": date_, "location_": location_}
        try:
            result = self.es.index(index=self.index_name, body=doc)
            return result
        except Exception as e:
            print(f"❌ Error al insertar en Elasticsearch: {str(e)}")
            return {"error": "No se pudo registrar la cita en Elasticsearch"}
