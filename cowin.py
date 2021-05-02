import time
import json
import requests
import traceback
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
#from helper import footer

class CoWIN:

    def __init__(self):
        st.set_page_config(
            page_title="Cowin Vaccination",
            initial_sidebar_state="expanded"
            )

    @st.cache(show_spinner=False)
    def call_calender_api(self, pincode, date):
        url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin"
        data = []
        try:
            params = {
                "pincode": pincode,
                "date": date
                }
            resp = requests.get(url, params=params, timeout=5)
            resp = resp.json()
            data = resp['centers']
        except Exception as e:
            traceback.print_exc()
        return data

    @st.cache(show_spinner=False)
    def call_daily_api(self, pincode, date):
        url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin"
        data = {}
        try:
            start_date = self.str_to_date(date)
            end_date = start_date + timedelta(days=6)
            while start_date <= end_date:
                params = {
                    "pincode": pincode,
                    "date": self.date_to_str(start_date)
                    }
                resp = requests.get(url, params=params, timeout=5)
                print(resp.reason, resp.status_code, resp.request.headers)
                resp = resp.json()
                resp = {i["session_id"]:i for i in resp["sessions"]}
                data.update(resp)
                start_date += timedelta(days=1)
                time.sleep(1)
        except Exception as e:
            traceback.print_exc()
        return data

    def str_to_date(self, date):
        return datetime.strptime(date, "%d-%m-%Y")

    def date_to_str(self, date):
        return datetime.strftime(date, "%d-%m-%Y")

    def preprocess_data(self, calender_info, daily_info, age):
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
                if session["min_age_limit"] == age:
                    data_dict.setdefault(center_name, {})
                    session_info = daily_info.get(session["session_id"])
                    if session_info and session_info["vaccine"] and dose_count:
                        dose_count = f"{session_info['vaccine']} - {dose_count}"

                    dose_count = str(dose_count) if dose_count else None
                    data_dict[center_name][date] = dose_count
        return data_dict

    def main(self):
        pincode = st.sidebar.text_input('Enter Pincode', max_chars=6, value=416505)
        date = st.sidebar.date_input("Enter Date", min_value=datetime.today())
        date = self.date_to_str(date)
        age = st.sidebar.radio("Age", options=["45+","18+"])
        age = int(age[:-1])

        if pincode.isnumeric():
            pincode = int(pincode)
            with st.spinner("Please wait.."):
                calender_info = self.call_calender_api(pincode, date)
                daily_info = self.call_daily_api(pincode, date)
                data = self.preprocess_data(calender_info, daily_info, age)
                df = pd.DataFrame(data)
                df = df.fillna("-")
                df = df.T
                df = df.sort_index()
            if df.empty:
                st.warning("No vaccination slot available!")
            else:
                st.info("Planned vaccination sessions")
                st.dataframe(df)
        else:
            st.error("Invalid Pincode")
            st.stop()
        #footer()

if __name__ == "__main__":
    CoWIN().main()
