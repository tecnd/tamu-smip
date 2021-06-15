# Handles authenticating with SMIP and getting a token

import requests, jwt

ENDPOINT = "https://smtamu.cesmii.net/graphql"

# GraphQL mutation to generate a challenge for user
challenge_payload = """
mutation Challenge($authenticator: String, $role: String, $userName: String) {
    authenticationRequest(
        input: {
            authenticator: $authenticator,
            role: $role,
            userName: $userName
        }
    ) {
        jwtRequest {
            challenge
        }
    }
}"""

# GraphQL mutation to generate token using challenge and password
token_payload = """
mutation Token($authenticator: String, $signedChallenge: String) {
    authenticationValidation(
        input: {
            authenticator: $authenticator,
            signedChallenge: $signedChallenge
        }
    ) {
        jwtClaim
    }
}"""

# Makes the required GraphQL mutations to get an auth token
def get_token(authenticator: str, role: str, userName: str, password: str)->str:
    r = requests.post(ENDPOINT, json={
        "query": challenge_payload,
        "variables": {
            "authenticator": authenticator,
            "role": role,
            "userName": userName
        }
    })
    challenge = r.json()['data']['authenticationRequest']['jwtRequest']['challenge']
    r = requests.post(ENDPOINT, json={
        "query": token_payload,
        "variables": {
            "authenticator": authenticator,
            "signedChallenge" : challenge + '|' + password
        }
    })
    token = r.json()['data']['authenticationValidation']['jwtClaim']
    return token

# Helper function to check if a token is valid and updates it if not
def update_token(token:str, authenticator: str, role: str, userName: str, password: str)->str:
    try:
        jwt.decode(token, algorithms="HS256", options={"verify_signature": False, "verify_exp": True})
        return token
    except:
        return get_token(authenticator, role, userName, password)

if __name__ == '__main__':
    print(get_token("test", "smtamu_group", "parthdave", "parth1234"))