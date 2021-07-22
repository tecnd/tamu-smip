"""Handles authentication and communication with SMIP via GraphQL"""

from concurrent.futures import Future, as_completed
from typing import List, cast

import jwt
import requests
from requests_futures.sessions import FuturesSession

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


def batcher(iterable, n: int = 1000):
    """Yields generator that splits long list into chunks of length n."""
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def add_data_serial(id: int, entries: List[dict], token: str, session: requests.Session = None, timeout: float = None):
    """Breaks up timeseries into chunks of 8000 and uploads serially, returns a list of Responses"""
    if session is None:
        with requests.Session() as s:
            resp_list = [add_data(id, batch, token, s, timeout)
                         for batch in batcher(entries, 8000)]
    else:
        resp_list = [add_data(id, batch, token, session, timeout)
                     for batch in batcher(entries, 8000)]
    return resp_list


def add_data_async(id: int, entries: List[dict], token: str, session: requests.Session = None, timeout: float = None):
    """Breaks up timeseries into chunks of 1000 and uploads asynchronously, returns a list of Futures"""
    with FuturesSession(session=session) as s:
        post = [add_data(id, batch, token, s, timeout)
                for batch in batcher(entries)]
        post = cast(List[Future], post)
        resp = [future.result() for future in as_completed(post)]
    return resp


MUTATION_CLEARDATA = """
mutation AddData($startTime: Datetime, $endTime: Datetime, $id: BigInt) {
  replaceTimeSeriesRange(
    input: {
        endTime: $endTime
        startTime: $startTime
        attributeOrTagId: $id,
    }
  ) {
    json
  }
}
"""


def clear_data(start_time: str, end_time: str, id: int, token: str, timeout: float = None) -> requests.Response:
    """Clears timeseries from SMIP."""
    json = {
        "query": MUTATION_CLEARDATA,
        "variables": {
            "endTime": end_time,
            "startTime": start_time,
            "id": id
        }
    }
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(ENDPOINT, json=json, headers=headers, timeout=timeout)
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
    token = get_token("test", "smtamu_group", "parthdave", "parth1234")
    print(token)
