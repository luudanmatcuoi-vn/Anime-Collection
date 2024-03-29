import json
import requests
import secrets
import webbrowser
from os import path


CLIENT_ID = '01a75b8dcdd96c44b126be9fc60c89fc'
# CLIENT_SECRET = 'YOUR CLIENT SECRET'


# 1. Generate a new Code Verifier / Code Challenge.
def get_new_code_verifier() -> str:
    token = secrets.token_urlsafe(100)
    return token[:128]


# 2. Print the URL needed to authorise your application.
def print_new_authorisation_url(code_challenge: str):
    global CLIENT_ID

    url = f'https://myanimelist.net/v1/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&code_challenge={code_challenge}'
    print(f'Authorise your application by clicking here: {url}')
    print(f'or we will open it for you\n')
    webbrowser.open(url)


# 3. Once you've authorised your application, you will be redirected to the webpage you've
#    specified in the API panel. The URL will contain a parameter named "code" (the Authorisation
#    Code). You need to feed that code to the application.
def generate_new_token(authorisation_code: str, code_verifier: str) -> dict:
    global CLIENT_ID#, CLIENT_SECRET

    url = 'https://myanimelist.net/v1/oauth2/token'
    data = {
        'client_id': CLIENT_ID,
        # 'client_secret': CLIENT_SECRET,
        'code': authorisation_code,
        'code_verifier': code_verifier,
        'grant_type': 'authorization_code'
    }

    response = requests.post(url, data)
    response.raise_for_status()  # Check whether the request contains errors

    token = response.json()
    response.close()
    print('Token generated successfully!')

    with open('token.json', 'w') as file:
        json.dump(token, file, indent = 4)
        print('Token saved in "token.json"')

    return token


# 4. Test the API by requesting your profile information
def print_user_info(access_token: str):
    url = 'https://api.myanimelist.net/v2/users/@me'
    response = requests.get(url, headers = {
        'Authorization': f'Bearer {access_token}'
        })
    
    status = response.raise_for_status()
    user = response.json()
    response.close()

    print(f"\n>>> Greetings {user['name']}! <<<")
    if user['name'] != "":
        return True


if __name__ == '__main__':
    if path.exists("token.json"):
        file =open("token.json","r")
        token = json.load(file)
        if print_user_info(token['access_token']) == True:
            exit()
        else:
            pass
    code_verifier = code_challenge = get_new_code_verifier()
    print_new_authorisation_url(code_challenge)

    authorisation_code = input('Copy-paste the Authorisation Code: ').strip()
    if "code=" in authorisation_code:
        index = authorisation_code.index("code=")
        authorisation_code = authorisation_code[index+5:]
    token = generate_new_token(authorisation_code, code_verifier)

    print_user_info(token['access_token'])
    input()
