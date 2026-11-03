"""Cache a bounded set of first-page thumbnails for reliable, fast rendering."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import urllib.request


def ensure_covers(streams, root, limit=168, cover_folder="assets/covers"):
    folder = Path(root) / cover_folder
    folder.mkdir(parents=True,exist_ok=True)
    candidates = {}
    for key, count in (("daily",96),("picks",48),("editorial",6),("archive",24)):
        for row in streams.get(key, [])[:count]:
            if re.fullmatch(r"BV[0-9A-Za-z]{10}",row["bvid"]) and row.get("pic"):
                candidates.setdefault(row["bvid"],row["pic"])
    def fetch(pair):
        bvid,url=pair
        path=folder/(bvid+".webp")
        if path.exists():return True
        url=url.replace("http:","https:")
        if not re.match(r"https://i[0-9]+\.hdslb\.com/",url):return False
        request=urllib.request.Request(url+"@480w_300h_1c.webp",headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.bilibili.com/"})
        try:
            with urllib.request.urlopen(request,timeout=12) as response:
                data=response.read(1500000)
            if data[:4]!=b"RIFF" or len(data)<100:return False
            path.write_bytes(data)
            return True
        except Exception:return False
    with ThreadPoolExecutor(max_workers=6) as executor:
        result=list(executor.map(fetch,list(candidates.items())[:limit]))
    return {"requested":len(result),"available":sum(result)}
