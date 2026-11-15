import json
import requests

LAT = 47.13     # replace with your field's latitude
LON = -118.37   # replace with your field's longitude

URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"

QUERY = f"""
SELECT mu.mukey, mu.muname, c.compname, c.comppct_r, c.majcompflag, c.slope_r,
       ch.hzdept_r, ch.hzdepb_r, ch.claytotal_r, ch.om_r, ch.ph1to1h2o_r, ch.kwfact
FROM mapunit mu
LEFT JOIN component c ON c.mukey = mu.mukey
LEFT JOIN chorizon ch ON ch.cokey = c.cokey
WHERE mu.mukey IN (
    SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({LON} {LAT})')
)
ORDER BY c.comppct_r DESC, ch.hzdept_r
"""

response = requests.post(URL, data={"query": QUERY, "format": "JSON+COLUMNNAME"}, timeout=60)
print(response.status_code)
print(response.text[:300])
data = response.json()
print(data.keys())