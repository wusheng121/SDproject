from __future__ import annotations

import requests
import warnings
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 禁用SSL警告（针对开发环境）
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class TMDBClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("TMDB_API_KEY 为空")
        self.api_key = api_key
        self.base = "https://api.themoviedb.org/3"
        self.img_base = "https://image.tmdb.org/t/p/w500"
        
        # 创建带重试机制的session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get(self, path: str, params: dict | None = None):
        params = params or {}
        params["api_key"] = self.api_key
        
        try:
            r = self.session.get(f"{self.base}{path}", params=params, timeout=15, verify=False)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.SSLError:
            # SSL错误时自动重试一次
            print(f"SSL error for {path}, retrying...")
            time.sleep(1)
            r = self.session.get(f"{self.base}{path}", params=params, timeout=15, verify=False)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {path}: {e}")
            raise

    def search_movie(self, title: str, year: int | None = None):
        params = {"query": title, "include_adult": "false", "language": "zh-CN"}
        if year:
            params["year"] = int(year)
        data = self._get("/search/movie", params=params)
        results = data.get("results") or []
        return results

    def movie_detail(self, tmdb_id: int):
        return self._get(f"/movie/{int(tmdb_id)}", params={"language": "zh-CN"})

    def movie_credits(self, tmdb_id: int):
        return self._get(f"/movie/{int(tmdb_id)}/credits", params={"language": "zh-CN"})

    def poster_url(self, poster_path: str | None):
        if not poster_path:
            return None
        return f"{self.img_base}{poster_path}"




















