"""Rewrite of smip_io using a class"""

from concurrent.futures import Future, as_completed
from typing import List, cast

import jwt
import requests
from requests_futures.sessions import FuturesSession

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

# GraphQL query to clear data from SMIP
MUTATION_CLEARDATA = """
mutation ClearData($startTime: Datetime, $endTime: Datetime, $id: BigInt) {
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


class SMIP:
    def __init__(self, endpoint: str, authenticator: str, role: str, userName: str, password: str) -> None:
        self.__endpoint = endpoint
        self.__session = requests.Session()
        self.__futureSession = FuturesSession(session=self.__session)
        self.__authenticator = authenticator
        self.__role = role
        self.__userName = userName
        self.__password = password
        self.token = self.get_token()

    def get_token(self) -> str:
        """Posts GraphQL mutations to get an auth token."""
        r = self.__session.post(self.__endpoint, json={
            "query": MUTATION_CHALLENGE,
            "variables": {
                "authenticator": self.__authenticator,
                "role": self.__role,
                "userName": self.__userName
            }
        })
        r.raise_for_status()
        challenge = r.json()[
            'data']['authenticationRequest']['jwtRequest']['challenge']
        r = self.__session.post(self.__endpoint, json={
            "query": MUTATION_TOKEN,
            "variables": {
                "authenticator": self.__authenticator,
                "signedChallenge": challenge + '|' + self.__password
            }
        })
        r.raise_for_status()
        token = r.json()['data']['authenticationValidation']['jwtClaim']
        return token

    def update_token(self) -> bool:
        """Helper function to check if a token is valid and updates it if not.
        Returns True if token is valid, False if token was updated.
        """
        try:
            jwt.decode(self.token, algorithms="HS256", options={
                "verify_signature": False, "verify_exp": True})
            return True
        except:
            self.token = self.get_token()
            return False

    def add_data(self, id: int, entries: List[dict], timeout: float = None, async_mode: bool = False) -> requests.Response:
        """Sends timeseries to SMIP."""
        s = self.__futureSession if async_mode else self.__session
        json = {
            "query": MUTATION_ADDDATA,
            "variables": {
                "id": id,
                "entries": entries
            }
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        r = s.post(
            self.__endpoint, json=json, headers=headers, timeout=timeout)
        return r

    @staticmethod
    def batcher(toSplit, n: int = 1000):
        """Yields generator that splits long list into chunks of length n."""
        l = len(toSplit)
        for ndx in range(0, l, n):
            yield toSplit[ndx:min(ndx + n, l)]

    def add_data_serial(self, id: int, entries: List[dict], timeout: float = None):
        """Breaks up timeseries into chunks of 8000 and uploads serially, returns a list of Responses"""
        resp_list = [self.add_data(id, batch, timeout)
                     for batch in self.batcher(entries, 8000)]
        for r in resp_list:
            r.raise_for_status()
        return resp_list

    def add_data_async(self, id: int, entries: List[dict], timeout: float = None):
        """Breaks up timeseries into chunks of 1000 and uploads asynchronously, returns a list of Futures"""
        post = [self.add_data(id, batch, timeout, async_mode=True)
                for batch in self.batcher(entries)]
        post = cast(List[Future], post)
        resp_list = [cast(requests.Response, future.result())
                     for future in as_completed(post)]
        for r in resp_list:
            r.raise_for_status()
        return resp_list

    def clear_data(self, start_time: str, end_time: str, id: int, timeout: float = None) -> requests.Response:
        """Clears timeseries from SMIP."""
        json = {
            "query": MUTATION_CLEARDATA,
            "variables": {
                "endTime": end_time,
                "startTime": start_time,
                "id": id
            }
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        r = self.__session.post(
            self.__endpoint, json=json, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r

    def get_data(self, start_time: str, end_time: str, ids: List[int], timeout: float = None) -> requests.Response:
        """Gets timeseries from SMIP."""
        json = {
            "query": QUERY_GETDATA,
            "variables": {
                "endTime": end_time,
                "startTime": start_time,
                "ids": ids
            }
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        r = self.__session.post(
            self.__endpoint, json=json, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r


if __name__ == '__main__':
    conn = SMIP("https://smtamu.cesmii.net/graphql", "test",
                "smtamu_group", "parthdave", "parth1234")
    print(conn.token)
