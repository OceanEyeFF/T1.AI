"""TuShare JSON transport for managed collectors."""

import requests

from ashare_infra.data.tushare_rate_limit import acquire_tushare_call


def query(endpoint, params, token, *, fields="", session=None):
    post = session.post if session is not None else requests.post
    payload = {"api_name": endpoint, "token": token, "params": params, "fields": fields}
    for attempt in range(2):
        acquire_tushare_call(endpoint)
        try:
            with post(
                "https://api.tushare.pro", json=payload, timeout=(8, 12), allow_redirects=False
            ) as response:
                if response.status_code == 429:
                    raise RuntimeError(f"TuShare {endpoint}: too many requests (HTTP 429)")
                if response.status_code != 200:
                    raise RuntimeError(f"TuShare {endpoint}: HTTP {response.status_code}")
                result = response.json()
            break
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 1:
                raise
    if not isinstance(result, dict) or result.get("code") != 0:
        code = result.get("code") if isinstance(result, dict) else None
        message = str(result.get("msg") or "") if isinstance(result, dict) else "invalid response"
        raise RuntimeError(f"TuShare {endpoint} ({code}): {message.replace(token, '[redacted]')}")
    data = result.get("data")
    if not isinstance(data, dict):
        raise TypeError(f"TuShare {endpoint}: missing response data")
    return data
