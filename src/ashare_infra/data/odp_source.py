from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

SUPPORTED_FIELDS: Sequence[str] = ("open", "high", "low", "close", "volume", "amount")
SUPPORTED_ENDPOINTS: Sequence[str] = (
    "equity/price/historical",
    "index/price/historical",
    "currency/price/historical",
    "derivatives/futures/historical",
)


@dataclass(frozen=True)
class ODPHistoricalRequest:
    """ODP 历史行情请求。"""

    endpoint: str
    symbol: str
    start_date: str  # YYYYMMDD / YYYY-MM-DD
    end_date: str  # YYYYMMDD / YYYY-MM-DD
    provider: str = "yfinance"
    interval: str = "1d"
    base_url: str | None = None
    prefer_rest: bool = False
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class ODPDailyBarsRequest:
    """ODP 股票日线请求（便于与现有适配器保持一致）。"""

    symbol: str
    start_date: str
    end_date: str
    provider: str = "yfinance"
    interval: str = "1d"
    base_url: str | None = None
    prefer_rest: bool = False
    timeout_seconds: float = 30.0


def _normalize_odp_equity_symbol(symbol: str, provider: str = "yfinance") -> str:
    raw = str(symbol).strip().upper()
    if not raw:
        raise ValueError("symbol 不能为空")

    if "." in raw:
        code, suffix = raw.split(".", 1)
        suffix = suffix.upper()
        if str(provider).lower() == "yfinance":
            if suffix == "SH":
                return f"{code}.SS"
            if suffix in {"SZ", "SS", "BJ"}:
                return f"{code}.{suffix}"
        return raw

    if len(raw) == 6 and raw.isdigit() and str(provider).lower() == "yfinance":
        if raw.startswith(("6", "9")):
            return f"{raw}.SS"
        if raw.startswith(("0", "3")):
            return f"{raw}.SZ"
        if raw.startswith(("8", "4")):
            return f"{raw}.BJ"
    return raw


def _normalize_endpoint(endpoint: str) -> str:
    ep = str(endpoint or "").strip().strip("/").lower()
    if ep not in SUPPORTED_ENDPOINTS:
        raise ValueError(
            f"unsupported ODP endpoint: {endpoint!r}, expected one of {tuple(SUPPORTED_ENDPOINTS)}"
        )
    return ep


def _normalize_date_str(value: str) -> str:
    ts = pd.to_datetime(value)
    return ts.strftime("%Y-%m-%d")


def _normalize_odp_payload_to_df(payload: Any) -> pd.DataFrame:
    if payload is None:
        return pd.DataFrame(columns=list(SUPPORTED_FIELDS))

    if isinstance(payload, Mapping):
        if "results" in payload:
            payload = payload.get("results")
        elif "data" in payload:
            payload = payload.get("data")

    if isinstance(payload, pd.DataFrame):
        df = payload.copy()
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        df = pd.DataFrame(list(payload))
    elif isinstance(payload, Mapping):
        df = pd.DataFrame([dict(payload)])
    else:
        return pd.DataFrame(columns=list(SUPPORTED_FIELDS))

    if df.empty:
        return pd.DataFrame(columns=list(SUPPORTED_FIELDS))

    work = df.copy()
    if "date" not in work.columns:
        for candidate in ("datetime", "timestamp", "time", "index"):
            if candidate in work.columns:
                work = work.rename(columns={candidate: "date"})
                break
        else:
            idx_name = str(work.index.name or "index")
            # ODP SDK 常见情况：日期在索引里（索引名为 date），但索引类型不一定是 DatetimeIndex。
            if idx_name.lower() in {"date", "datetime", "timestamp", "index"}:
                work = work.reset_index().rename(columns={idx_name: "date"})
            elif isinstance(work.index, pd.DatetimeIndex):
                work = work.reset_index().rename(columns={work.index.name or "index": "date"})
            else:
                raise ValueError("ODP payload missing date field")

    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["date"]).set_index("date").sort_index()
    work.index.name = "date"

    if "adj_close" in work.columns and "close" not in work.columns:
        work["close"] = work["adj_close"]

    out = work.reindex(columns=list(SUPPORTED_FIELDS)).copy()
    if "close" in work.columns:
        for price_col in ("open", "high", "low"):
            if price_col not in work.columns:
                out[price_col] = pd.to_numeric(work["close"], errors="coerce")

    for col in SUPPORTED_FIELDS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def _sdk_dispatch(req: ODPHistoricalRequest) -> Any:
    from openbb import obb  # type: ignore

    kwargs = {
        "symbol": req.symbol,
        "start_date": _normalize_date_str(req.start_date),
        "end_date": _normalize_date_str(req.end_date),
        "provider": req.provider,
    }
    if req.interval:
        kwargs["interval"] = req.interval

    ep = _normalize_endpoint(req.endpoint)
    if ep == "equity/price/historical":
        return obb.equity.price.historical(**kwargs)
    if ep == "index/price/historical":
        return obb.index.price.historical(**kwargs)
    if ep == "currency/price/historical":
        return obb.currency.price.historical(**kwargs)
    if ep == "derivatives/futures/historical":
        return obb.derivatives.futures.historical(**kwargs)
    raise ValueError(f"unsupported endpoint dispatch: {ep}")


def _fetch_odp_via_sdk(req: ODPHistoricalRequest) -> pd.DataFrame:
    raw = _sdk_dispatch(req)
    if hasattr(raw, "to_df"):
        return _normalize_odp_payload_to_df(raw.to_df())
    if hasattr(raw, "results"):
        return _normalize_odp_payload_to_df(getattr(raw, "results"))
    return _normalize_odp_payload_to_df(raw)


def _build_rest_url(req: ODPHistoricalRequest) -> str:
    base = str(req.base_url or os.environ.get("ODP_BASE_URL") or "http://127.0.0.1:8000").strip()
    if not base:
        raise ValueError("ODP base url is empty")

    params = {
        "symbol": req.symbol,
        "start_date": _normalize_date_str(req.start_date),
        "end_date": _normalize_date_str(req.end_date),
        "provider": req.provider,
    }
    if req.interval:
        params["interval"] = req.interval

    ep = _normalize_endpoint(req.endpoint)
    query = urlencode(params)
    return f"{base.rstrip('/')}/api/v1/{ep}?{query}"


def _fetch_odp_via_rest(req: ODPHistoricalRequest) -> pd.DataFrame:
    url = _build_rest_url(req)
    request = Request(url=url, method="GET")
    with urlopen(request, timeout=float(req.timeout_seconds)) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))
    return _normalize_odp_payload_to_df(payload)


def fetch_odp_historical_bars(req: ODPHistoricalRequest) -> pd.DataFrame:
    """获取 ODP 历史行情（优先 SDK，REST 兜底；可通过 prefer_rest 反转优先级）。"""
    if req.prefer_rest:
        try:
            return _fetch_odp_via_rest(req)
        except Exception:
            return _fetch_odp_via_sdk(req)

    try:
        return _fetch_odp_via_sdk(req)
    except Exception:
        return _fetch_odp_via_rest(req)


def _safe_symbol_for_path(symbol: str) -> str:
    out = str(symbol).strip()
    for old, new in (("/", "_"), ("\\", "_"), (":", "_"), ("*", "_"), ("?", "_"), ("|", "_")):
        out = out.replace(old, new)
    return out


def _read_cached(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=list(SUPPORTED_FIELDS))
    df = pd.read_parquet(path)
    if "date" not in df.columns:
        return pd.DataFrame(columns=list(SUPPORTED_FIELDS))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    df.index.name = "date"
    out = df.reindex(columns=list(SUPPORTED_FIELDS)).copy()
    for col in SUPPORTED_FIELDS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _write_cached(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        return
    out = df.copy().reset_index()
    if "date" not in out.columns and "index" in out.columns:
        out = out.rename(columns={"index": "date"})
    out.to_parquet(path, index=False)


def _odp_cache_paths(cache_dir: Path, endpoint: str, cache_name: str) -> tuple[Path, Path | None]:
    """Canonical cache path + optional legacy double-nested path.

    Pre-fix DataLake passed ``cache_dir/odp`` into the adapter which already
    prefixes ``odp/``, producing ``{cache}/odp/odp/...``. Reads still fall back
    to that legacy location; writes always go to the canonical path.
    """
    ep = endpoint.replace("/", "_")
    canonical = cache_dir / "odp" / ep / cache_name
    legacy = cache_dir / "odp" / "odp" / ep / cache_name
    return canonical, legacy if legacy != canonical else None


def load_or_fetch_historical_bars(
    req: ODPHistoricalRequest,
    cache_dir: Path,
    refresh: bool = False,
) -> pd.DataFrame:
    """加载或获取 ODP 历史行情（按 symbol/provider/interval 持久化缓存）。"""
    ep = _normalize_endpoint(req.endpoint)
    cache_name = f"{_safe_symbol_for_path(req.symbol)}_{req.provider}_{req.interval}.parquet"
    cache_path, legacy_path = _odp_cache_paths(cache_dir, ep, cache_name)

    start = pd.to_datetime(req.start_date)
    end = pd.to_datetime(req.end_date)

    cached = _read_cached(cache_path)
    if cached.empty and legacy_path is not None:
        cached = _read_cached(legacy_path)

    if not refresh:
        has_cover = (
            (not cached.empty) and (start >= cached.index.min()) and (end <= cached.index.max())
        )
        if has_cover:
            return cached.loc[(cached.index >= start) & (cached.index <= end)].copy()

    fetched = fetch_odp_historical_bars(req)
    # refresh 强制重取请求区间，但保留区间外已缓存行（fetched 在后 → keep="last" 覆盖旧行）
    frames = [x for x in (cached, fetched) if x is not None and not x.empty]
    merged = (
        pd.concat(frames).sort_index() if frames else pd.DataFrame(columns=list(SUPPORTED_FIELDS))
    )
    if not merged.empty:
        merged = merged[~merged.index.duplicated(keep="last")]
        merged.index.name = "date"
        _write_cached(merged, cache_path)

    if merged.empty:
        merged.index.name = "date"
        return merged.copy()
    return merged.loc[(merged.index >= start) & (merged.index <= end)].copy()


def fetch_odp_daily_bars(req: ODPDailyBarsRequest) -> pd.DataFrame:
    """ODP 股票日线（equity/price/historical）。"""
    hist_req = ODPHistoricalRequest(
        endpoint="equity/price/historical",
        symbol=_normalize_odp_equity_symbol(req.symbol, provider=req.provider),
        start_date=req.start_date,
        end_date=req.end_date,
        provider=req.provider,
        interval=req.interval,
        base_url=req.base_url,
        prefer_rest=req.prefer_rest,
        timeout_seconds=req.timeout_seconds,
    )
    return fetch_odp_historical_bars(hist_req)


def load_or_fetch_daily_bars(
    req: ODPDailyBarsRequest,
    cache_dir: Path,
    refresh: bool = False,
) -> pd.DataFrame:
    """加载或获取 ODP 股票日线缓存。"""
    hist_req = ODPHistoricalRequest(
        endpoint="equity/price/historical",
        symbol=_normalize_odp_equity_symbol(req.symbol, provider=req.provider),
        start_date=req.start_date,
        end_date=req.end_date,
        provider=req.provider,
        interval=req.interval,
        base_url=req.base_url,
        prefer_rest=req.prefer_rest,
        timeout_seconds=req.timeout_seconds,
    )
    return load_or_fetch_historical_bars(hist_req, cache_dir=cache_dir, refresh=refresh)
