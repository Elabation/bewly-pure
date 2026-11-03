import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from discovery_site import build_site, prepare_streams
import daily_refresh
from mining_data import load_population


def row(i):
    return {"bvid":"BV"+str(i).zfill(10),"title":"作品 "+str(i),"owner":"作者 "+str(i),
            "pic":"","dur":180,"view":10000,"coin_percentile":.95,"recall_priority":.9,
            "reference_n":100,"motive_cues":[],"first_seen":"20261103","taste_hint":.1,"in_favorites":True}


class DiscoveryTests(unittest.TestCase):
    def test_large_catalog_does_not_enter_bootstrap(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);engine=root/"engine";engine.mkdir()
            for name in ("discovery_template.html","discovery_ui.js","discovery_search.js","discovery_companion.js"):
                shutil.copy2(Path(__file__).parent/name,engine/name)
            rows=[row(i) for i in range(40000)]
            rows[0]["title"]="</script><script>alert(1)</script>"
            result=build_site(rows,{"catalog_id":"C"},root/"site",root)
            html=(root/"site/god-shelf.html").read_text(encoding="utf-8")
            boot=json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S).group(1))
            self.assertLess(result["html_bytes"],100000)
            self.assertEqual(len(boot["initial"]),24)
            self.assertEqual(boot["total"],40000)
            self.assertNotIn("in_favorites",str(boot))
            self.assertNotIn("taste_hint",str(boot))
            self.assertNotIn("</script><script>alert",html)
            self.assertGreater(len(boot["streams"]["archive"]["chunks"]),400)
            for stream in boot["streams"].values():
                for filename in stream["chunks"]:self.assertTrue((root/"site"/filename).exists())

    def test_daily_uses_first_discovery_not_publication_or_latest_snapshot(self):
        old=row(1);old["first_seen"]="20260903";old["snapshot"]="favmine_daily_20261103.json"
        fresh=row(2);fresh["pubdate"]=123456
        streams,day=prepare_streams([old,fresh])
        self.assertEqual(day,"20261103")
        self.assertEqual([r["bvid"] for r in streams["daily"]],[fresh["bvid"]])


    def test_duration_boundary_and_screening_apply_to_daily_and_candidates(self):
        short=row(1);short['dur']=150
        eligible=row(2);eligible['dur']=151
        flagged=row(3);flagged['screen_flags']=['title_review']
        streams,day=prepare_streams([short,eligible,flagged])
        for key in ('daily','picks','day:20261103'):
            self.assertEqual([r['bvid'] for r in streams[key]],[eligible['bvid']])
        self.assertEqual(len(streams['archive']),3)
        self.assertEqual(streams['editorial'],[])

    def test_full_snapshot_updates_preserve_first_seen(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);mine=root/"mine";mine.mkdir();samples=root/"samples";samples.mkdir()
            v={"bvid":"BV1234567890","view":10000,"stat":{"coin":100,"favorite":50,"like":100}}
            (mine/"favmine_20260903_000001.json").write_text(json.dumps({"videos":[v]}),encoding="utf-8")
            v["stat"]["coin"]=200
            (mine/"favmine_daily_20261103_000001.json").write_text(json.dumps({"videos":[v]}),encoding="utf-8")
            result=load_population(mine,samples)[v["bvid"]]
            self.assertEqual(result["first_seen"],"20260903")
            self.assertEqual(result["coin"],200)

    def test_failed_api_does_not_overwrite_site_or_create_empty_raw(self):
        class Empty:
            def get_json(self,*a,**kw):return {"list":[]}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);site=root/"god-shelf.html";site.write_text("last good page",encoding="utf-8")
            with patch.object(daily_refresh,"ROOT",root):
                with self.assertRaises(RuntimeError):daily_refresh.collect(Empty(),pages=2,seeds=0)
            self.assertEqual(site.read_text(encoding="utf-8"),"last good page")
            self.assertFalse(list(root.rglob("favmine_*.json")))

    def test_collector_uses_popular_metadata_without_detail_request(self):
        class Client:
            calls=[]
            def get_json(self,url,*a,**kw):
                self.calls.append(url)
                return {"list":[{"bvid":"BV1234567890","title":"新作品","duration":120,
                                  "stat":{"view":10000,"coin":100,"favorite":100,"like":200}}]}
        with tempfile.TemporaryDirectory() as d:
            client=Client()
            with patch.object(daily_refresh,"ROOT",Path(d)):
                result=daily_refresh.collect(client,pages=1,seeds=0)
            self.assertEqual(result["new_videos"],1)
            self.assertEqual(len(client.calls),1)


if __name__=="__main__":unittest.main(verbosity=2)
