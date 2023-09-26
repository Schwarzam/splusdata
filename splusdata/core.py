import requests
import getpass

import json

## Error handling
class AuthenticationError(Exception):
    pass

class Core:
    BASE_URL = "https://splus.cloud/api"

    def __init__(self, username=None, password=None):
        # Initialize session for making requests
        self.session = requests.Session()
        self.authenticate(username, password)

    def authenticate(self, username=None, password=None):
        if not username:
            username = input("splus.cloud username: ")
        if not password:    
            password = getpass("splus.cloud password: ")

        data = {'username': username, 'password': password}
        response = self.session.post(f"{self.BASE_URL}/auth/login", data=data)

        if response.status_code != 200:
            raise AuthenticationError("Authentication failed")

        user_data = json.loads(response.content)
        self.token = user_data['token']
        self.headers = {'Authorization': 'Token ' + self.token}

        response = self.session.post(f"{self.BASE_URL}/auth/collab", headers=self.headers)
        collab = json.loads(response.content)

        self.collab = collab.get('collab') == 'yes'
        
    def _make_request(self, method, url, data=None, params=None):
        response = self.session.request(method, url, data=data, params=params)
        #response.raise_for_status()  # Raise an exception for HTTP errors
        return response
    


if __name__ == "__main__":
    core = Core()
    core.frame('SPLUS-s17s01')