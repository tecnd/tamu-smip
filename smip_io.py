"""Handles authentication and communication with SMIP via GraphQL"""

import jwt
import requests

ENDPOINT = "https://smtamu.cesmii.net/graphql"

# GraphQL mutation to generate a challenge for user
MUTATION_CHALLENGE = """
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
MUTATION_TOKEN = """
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


def get_token(authenticator: str, role: str, userName: str, password: str) -> str:
    """Posts GraphQL mutations to get an auth token."""
    r = requests.post(ENDPOINT, json={
        "query": MUTATION_CHALLENGE,
        "variables": {
            "authenticator": authenticator,
            "role": role,
            "userName": userName
        }
    })
    challenge = r.json()[
        'data']['authenticationRequest']['jwtRequest']['challenge']
    r = requests.post(ENDPOINT, json={
        "query": MUTATION_TOKEN,
        "variables": {
            "authenticator": authenticator,
            "signedChallenge": challenge + '|' + password
        }
    })
    token = r.json()['data']['authenticationValidation']['jwtClaim']
    return token


def update_token(token: str, authenticator: str, role: str, userName: str, password: str) -> str:
    """Helper function to check if a token is valid and updates it if not."""
    try:
        jwt.decode(token, algorithms="HS256", options={
                   "verify_signature": False, "verify_exp": True})
        return token
    except:
        return get_token(authenticator, role, userName, password)


# GraphQL mutation to add data to SMIP
MUTATION_ADDDATA = """
mutation AddData($id: BigInt, $entries: [TimeSeriesEntryInput]) {
  replaceTimeSeriesRange(
    input: {
        attributeOrTagId: $id,
        entries: $entries
    }
  ) {
    json
  }
}
"""

# GraphQL query to get data from SMIP
QUERY_GETDATA = """
query GetData($startTime: Datetime, $endTime: Datetime, $ids: [BigInt]) {
  getRawHistoryDataWithSampling(
    endTime: $endTime
    startTime: $startTime
    ids: $ids
    maxSamples: 0
  ) {
    floatvalue
    ts
    id
  }
}
"""

if __name__ == '__main__':
    print(get_token("test", "smtamu_group", "parthdave", "parth1234"))
