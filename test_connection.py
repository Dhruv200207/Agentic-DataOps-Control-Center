
import streamlit as st
from databricks import sql

try:
    with sql.connect(
        server_hostname=st.secrets["DATABRICKS_SERVER_HOSTNAME"],
        http_path=st.secrets["DATABRICKS_HTTP_PATH"],
        access_token=st.secrets["DATABRICKS_TOKEN"]
    ) as connection:

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchall()

    st.success("Databricks connection successful!")
    st.write("Test query result:", result)

except Exception as e:
    st.error("Connection failed. Check your settings.")
    st.code(str(e))
