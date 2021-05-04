import os
import time
import json
import itertools
import requests
import traceback
import pandas as pd
import streamlit as st
from requests_aws4auth import AWS4Auth
from datetime import datetime, timedelta
from helper import footer

class CoWIN:

    def __init__(self):
        st.set_page_config(
            layout="wide",
            page_icon="https://www.cowin.gov.in/favicon.ico",
            page_title="CoWIN Vaccination"
            )
        self.api_error_msg = "API Error!! Please try after some time."
        self.available_vaccines = ["COVISHIELD","COVAXIN"]
        access_id = os.environ['AWS_ACCESS_ID']
        secret_token = os.environ['AWS_SECRET_TOKEN']
        self.aws_auth = AWS4Auth(access_id, secret_token, 'ap-south-1', 'execute-api')
        self.aws_api_url = "https://o9g9ndk5ra.execute-api.ap-south-1.amazonaws.com"

    @st.cache(show_spinner=False, suppress_st_warning=True)
    def call_calender_api(self, pincode, date):
        # url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin"
        url = f"{self.aws_api_url}/calendarByPin"
        data = []
        try:
            params = {
                "pincode": pincode,
                "date": date
                }
            resp = requests.get(url, params=params, auth=self.aws_auth, timeout=5)
            resp = resp.json()
            data = resp['centers']
        except Exception as e:
            traceback.print_exc()
            st.error(self.api_error_msg)
            st.stop()
        return data

    @st.cache(show_spinner=False, suppress_st_warning=True)
    def call_daily_api(self, pincode, date):
        # url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin"
        url = f"{self.aws_api_url}/findByPin"
        data = {}
        try:
            start_date = self.str_to_date(date)
            end_date = start_date + timedelta(days=6)
            while start_date <= end_date:
                params = {
                    "pincode": pincode,
                    "date": self.date_to_str(start_date)
                    }
                resp = requests.get(url, params=params, auth=self.aws_auth, timeout=5)
                resp = resp.json()
                resp = {i["session_id"]:i for i in resp["sessions"]}
                data.update(resp)
                start_date += timedelta(days=1)
        except Exception as e:
            traceback.print_exc()
            st.error(self.api_error_msg)
            st.stop()
        return data

    def str_to_date(self, date):
        return datetime.strptime(date, "%d-%m-%Y")

    def date_to_str(self, date):
        return datetime.strftime(date, "%d-%m-%Y")

    def preprocess_data(self, calender_info, daily_info, age, vaccine):
        data_dict = {}
        for center in calender_info:
            center_name = center["name"]
            # if center["fee_type"] == "Paid":
            #     center_name = f"{center_name} - Paid"
            #     if center.get("vaccine_fees"):
            #         vaccine_fees = map(lambda x: f"{x['vaccine']} - {x['fee']}/-", center["vaccine_fees"])
            #         center_name += "\n" + "\n".join(vaccine_fees)
            for session in center['sessions']:
                date = self.str_to_date(session["date"])
                date = datetime.strftime(date, "%d %b")
                dose_count = session['available_capacity']

                session_info = daily_info.get(session["session_id"])
                session_vaccine = session_info["vaccine"] if session_info else ""
                if session_vaccine and dose_count:
                    dose_count = f"{session_vaccine} - {dose_count}"

                if session["min_age_limit"] == age and session_vaccine in vaccine:
                    data_dict.setdefault(center_name, {})

                    dose_count = str(dose_count) if dose_count else None
                    data_dict[center_name][date] = dose_count
        return data_dict

    def main(self):
        col_1, col_2, col_3, col_4 = st.beta_columns([3,3,2,4])
        with col_1:
            pincode = st.text_input('Enter Pincode', max_chars=6, value=110001)
        with col_2:
            date = st.date_input("Enter Date", min_value=datetime.today())
            date = self.date_to_str(date)
        with col_3:
            age = st.radio("Age Group", options=["45+","18+"])
            age = int(age[:-1])
        with col_4:
            vaccine = st.multiselect("Select Vaccine", options=self.available_vaccines, default=self.available_vaccines)

        # check user input
        if pincode.isnumeric():
            pincode = int(pincode)
        else:
            st.error("Invalid Pincode")
            st.stop()
        if not vaccine:
            st.warning("Please select vaccine")
            st.stop()

        with st.spinner("Please wait.."):
            calender_info = self.call_calender_api(pincode, date)
            daily_info = self.call_daily_api(pincode, date)
            data = self.preprocess_data(calender_info, daily_info, age, vaccine)
            df = pd.DataFrame(data)
            df = df.fillna("-")
            df = df.T
            df = df.sort_index()
            all_unique_vals = list(set(itertools.chain.from_iterable(df.values.tolist())))
        if df.empty or all_unique_vals == ["-"]:
            st.warning("No vaccination slot available!")
        else:
            st.info("Planned vaccination sessions")
            st.dataframe(df)
        footer()

if __name__ == "__main__":
    CoWIN().main()
