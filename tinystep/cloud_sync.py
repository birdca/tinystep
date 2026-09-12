import json
import ssl
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

CONFIG_PATH = Path.home() / ".tinystep" / "config.json"

def _get_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        try:
            return ssl.create_default_context()
        except Exception:
            return ssl._create_unverified_context()

SSL_CONTEXT = _get_ssl_context()

def get_sync_config() -> Optional[Dict[str, Any]]:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if cfg.get("sync_url"):
                return cfg
    except Exception:
        return None
    return None

def save_sync_config(sync_url: str, sync_token: str, auto_sync: bool = True):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg = {
        "sync_url": sync_url.rstrip("/"),
        "sync_token": sync_token,
        "auto_sync": auto_sync
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def pull_from_cloud(timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    cfg = get_sync_config()
    if not cfg:
        return None
    
    url = f"{cfg['sync_url']}/api/sync"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {cfg.get('sync_token', '')}",
        "User-Agent": "TinyStep-CLI/1.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data
    except Exception:
        return None
    return None

def push_to_cloud(data: Dict[str, Any], timeout: float = 4.0) -> bool:
    cfg = get_sync_config()
    if not cfg:
        return False
    
    url = f"{cfg['sync_url']}/api/sync"
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {cfg.get('sync_token', '')}",
        "Content-Type": "application/json",
        "User-Agent": "TinyStep-CLI/1.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
            return resp.status == 200
    except Exception:
        return False

def sync_data(storage, mode: str = "auto") -> Tuple[bool, str]:
    """
    雙向同步模組：
    - mode="push": 強制推送本機至雲端
    - mode="pull": 強制自雲端拉取
    - mode="auto": 先拉取雲端狀態；若雲端為空或初次同步，則將本機推至雲端
    """
    cfg = get_sync_config()
    if not cfg:
        return False, "尚未設定雲端同步。請使用 `tinystep config --sync-url ... --token ...` 配置！"
    
    local_data = storage.load()
    
    if mode == "push":
        ok = push_to_cloud(local_data)
        if ok:
            return True, "已成功將本機資料推送至 Cloudflare 雲端！"
        else:
            return False, "推送至雲端失敗，請檢查網路連線或金鑰設定。"

    # mode == "pull" or "auto"
    cloud_data = pull_from_cloud()
    if not cloud_data:
        return False, "無法連線至雲端服務 (請檢查網址或網路)。"
    
    # 若雲端無任何任務，但本機有任務，自動轉為推送
    if mode == "auto" and not cloud_data.get("tasks") and local_data.get("tasks"):
        push_ok = push_to_cloud(local_data)
        if push_ok:
            return True, "雲端初次使用，已自動將本機任務與身分資料同步至雲端！"

    # 以雲端為準更新本機
    storage.save(cloud_data)
    return True, "已成功自 Cloudflare 雲端同步最新狀態！"
