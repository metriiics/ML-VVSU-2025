import json
import requests

url = "https://api.hh.ru/professional_roles"
request = requests.get(url=url)

data = request.json()

df = []

for i in range(27):
    cat_id = data["categories"][i]["id"]
    cat_name = data["categories"][i]["name"]

    cat_role = data["categories"][i]["roles"]

    df_roles_idn = {}

    for j in range(len(cat_role)):
        cat_role_id = data["categories"][i]["roles"][j]["id"]
        cat_role_name = data["categories"][i]["roles"][j]["name"]

        df_roles_idn[cat_role_id] = cat_role_name

    df.append([cat_id, cat_name, df_roles_idn])


with open("spec.json", "w", encoding="utf-8") as file:
    json.dump(df, file, indent=4, ensure_ascii=False)
