import requests

api_key = "3bf1c3e0a3688c169676c7556925e3eb0c7c80e6c24c109e8f9aed7d92aaf216"

def geocoder(ip_address):
    if ip_address == '127.0.0.1':
        return "UNITED STATES"
    else:
        base_url = "http://api.ipinfodb.com/v3/ip-country/?key={0}&ip=".format(api_key)
        r = requests.get(base_url + ip_address)
        return r.content.split(';')[4]
