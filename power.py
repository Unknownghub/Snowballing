#NASA power database#

#Summary of file: uses the URL on the 7th line to retrieve data based on the specified parameters and then processes the JSON response#

import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

params = {
    "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR",
    "community": "AG",
    "longitude": -118.37,
    "latitude": 47.13,
    "start": "20200101",
    "end": "20200110",
    "format": "JSON",
}

response = requests.get(URL, params=params, timeout=60)
print(response.status_code)
data = response.json()
print(data.keys())
print (data["properties"].keys())
print(data["properties"]["parameter"].keys())
print(data["properties"]["parameter"]["PRECTOTCORR"])
print(data["header"])
print(data["parameters"])