import requests
import json

url = "https://api.9now.com.au/web/tab-by-id?device=web&variables=%7B%22elementType%22%3A%22TAB%22%2C%22dynamicElementId%22%3A%22LIVE_CHANNELS_LISTINGS_LIST%22%2C%22region%22%3A%22overseas%22%2C%22streamParams%22%3A%22web%2Cchrome%2Clinux%22%7D&token="

response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    
    with open("9now_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print("✅ Datos guardados en 9now_data.json")
else:
    print(f"⚠ Error en la solicitud: {response.status_code}")
