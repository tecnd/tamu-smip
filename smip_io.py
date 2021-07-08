"""Handles authentication and communication with SMIP via GraphQL"""

from typing import List

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


def add_data(id: int, entries: List[dict], token: str, session: requests.Session = None, timeout: float = None) -> requests.Response:
    """Sends timeseries to SMIP."""
    json = {
        "query": MUTATION_ADDDATA,
        "variables": {
            "id": id,
            "entries": entries
        }
    }
    headers = {"Authorization": f"Bearer {token}"}
    if session is None:
        r = requests.post(ENDPOINT, json=json,
                          headers=headers, timeout=timeout)
    else:
        r = session.post(ENDPOINT, json=json, headers=headers, timeout=timeout)
    return r


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


def get_data(start_time: str, end_time: str, ids: List[int], token: str, session: requests.Session = None, timeout: float = None) -> requests.Response:
    """Gets timeseries from SMIP."""
    json = {
        "query": QUERY_GETDATA,
        "variables": {
            "endTime": end_time,
            "startTime": start_time,
            "ids": ids
        }
    }
    headers = {"Authorization": f"Bearer {token}"}
    if session is None:
        r = requests.post(ENDPOINT, json=json,
                          headers=headers, timeout=timeout)
    else:
        r = session.post(ENDPOINT, json=json, headers=headers, timeout=timeout)
    return r


if __name__ == '__main__':
    import timeit
    start_time = timeit.default_timer()
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    print('get_token:', timeit.default_timer() - start_time)
    print(token)
    start_time = timeit.default_timer()
    update_token(token, "test", "smtamu_group", "parthdave", "parth1234")
    print('update_token:', timeit.default_timer() - start_time)
