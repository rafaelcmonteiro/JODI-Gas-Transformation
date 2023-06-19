import urllib.request
import shutil
import json
import csv
import sqlite3
import os
import glob

DATA_URL = "https://www.jodidata.org/_resources/files/downloads/gas-data/jodi_gas_csv_beta.zip"


class Points():
    def __init__(self, serie_id, points):
        self.serie_id = serie_id
        self.points = points


class Fields():
    def __init__(self, energy_product, flow_breakdown, unit_measure, assessment_code):
        self.energy_product = energy_product
        self.flow_breakdown = flow_breakdown
        self.unit_measure = unit_measure
        self.assessment_code = assessment_code


# Download and Unzip
def download_file(url=DATA_URL):
    local_filename = url.split('/')[-1]
    urllib.request.urlretrieve(url, local_filename)


# Turning csv handleable.
def unzip_data():
    shutil.unpack_archive("jodi_gas_csv_beta.zip", ".", "zip")


# Creating connection
def creating_conn():
    conn = sqlite3.connect("jodi_gas")
    return conn

# Creating table
def create_table(cur):
    drop_table(cur)
    cur.execute("CREATE TABLE IF NOT EXISTS jodigas (REF_AREA,TIME_PERIOD,ENERGY_PRODUCT,FLOW_BREAKDOWN,UNIT_MEASURE,OBS_VALUE,ASSESSMENT_CODE);")

    with open("jodi_gas_beta.csv", "r") as file:
        dr = csv.DictReader(file)
        to_db = [(i['REF_AREA'], i['TIME_PERIOD'], i['ENERGY_PRODUCT'], i['FLOW_BREAKDOWN'], i['UNIT_MEASURE'], i['OBS_VALUE'], i['ASSESSMENT_CODE']) for i in dr]
    cur.executemany("INSERT INTO jodigas (REF_AREA,TIME_PERIOD,ENERGY_PRODUCT,FLOW_BREAKDOWN,UNIT_MEASURE,OBS_VALUE,ASSESSMENT_CODE) VALUES (?,?,?,?,?,?,?)", to_db)
    conn.commit()


# Drop Table if exists
def drop_table(cur):
    cur.execute("DROP TABLE IF EXISTS jodigas;")
    conn.commit()


# Selecting time series
def get_data(cur):
    res = cur.execute("""
    SELECT
    REF_AREA,
    group_concat(TIME_PERIOD || "," || OBS_VALUE, ";") as series,
    ENERGY_PRODUCT,
    FLOW_BREAKDOWN,
    UNIT_MEASURE,
    group_concat(DISTINCT ASSESSMENT_CODE) as ASSESSMENT_CODE
    FROM jodigas WHERE FLOW_BREAKDOWN = 'TOTDEMO' AND UNIT_MEASURE = 'M3' GROUP BY REF_AREA ORDER BY REF_AREA, TIME_PERIOD
    """)
    data_output = res.fetchall()
    return data_output


# Transforming the data to json
def preparing_data():
    json_variable = []
    for data in data_output:
        dados = data[1].split(';')
        result = [value.split(',') for value in dados]
        new_list = []
        for list in result:
            new_list.append([str(list[0]), float(list[1])])
        serie_obj = Points(serie_id=data[0], points=new_list)
        fields_obj = Fields(energy_product=data[2],flow_breakdown = data[3],unit_measure=data[4],assessment_code=data[5])
        json_variable.append(json.dumps({**serie_obj.__dict__, "fields":{ **fields_obj.__dict__}}))
    return json_variable


def cleaning_station():
    file = 'jodi_gas*'
    location = os.getcwd()
    path = os.path.join(location, file)
    existing_files = glob.glob(path)
    [os.remove(file) for file in existing_files if file != f"{location}/jodi_gas_transformation.py"]


if __name__ == "__main__":
    download_file()
    unzip_data()

    conn = creating_conn()
    cur = conn.cursor()

    create_table(cur)
    data_output = get_data(cur)
    json_variable = preparing_data()

    conn.close()

    for data in json_variable:
        print(data)
    
    cleaning_station()

