"""Offline regression checks; never contacts Bilibili or changes raw data."""
from pathlib import Path
import json
import math
import tempfile
import unittest

from mining_data import (band_percentile, build_bands, historical_seed_approved,
                         load_flow_nodes, load_population, load_reference, percentile,
                         reference_manifest, normalize_video)
from preference_hint import PreferenceHint, TASTE_WEIGHT
from review_miner import (PROFILE, SCHEMA, checked_reviews, evaluate, is_blacklisted,
                          make_batch, review_status, safe_script_json)
from v3_rules import v3_tier


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def raw(b='BV1234567890', view=10000, coin=100, fav=30, like=200):
    return {'bvid': b, 'title': '原创短片', 'view': view, 'duration': 120,
            'owner': {'mid': 17, 'name': '作者'},
            'stat': {'coin': coin, 'favorite': fav, 'like': like}}


def review(**updates):
    return {'craft': 3, 'resonance': 2, 'watched': True, 'reason': 'craft_expression',
            'evidence': '02:15 的声音和镜头形成呼应', **updates}


def row(i, **updates):
    return {'bvid': 'BV'+str(i).zfill(10), 'title': '原创音乐', 'owner': str(i),
            'coin_percentile': .95, 'reference_n': 50, 'motive_cues': [], **updates}


class PercentileTests(unittest.TestCase):
    def test_extreme_out_of_reference_cannot_exceed_one(self):
        self.assertEqual(percentile([.01,.02,.03], .8), 1)

    def test_ties_use_strict_empirical_cdf(self):
        self.assertEqual(percentile([1,2,2,3], 2), .25)

    def test_sparse_band_abstains(self):
        for values in ([], [1], [1,2]):
            self.assertIsNone(percentile(values, 3))

    def test_all_values_bounded_and_monotonic(self):
        values = [0,.01,.01,.03,.3]
        scores = [percentile(values, v) for v in [0,.001,.01,.02,.3,20]]
        self.assertEqual(scores, sorted(scores))
        self.assertTrue(all(0<=s<=1 for s in scores))

    def test_invalid_numbers_and_new_video(self):
        self.assertIsNone(percentile([1,2,3], math.nan))
        self.assertIsNone(band_percentile({}, 2999, .9))


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.mine, self.samples = self.root/'mine', self.root/'samples'
        self.mine.mkdir(); self.samples.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_counts_are_one_snapshot_even_when_new_counts_decrease(self):
        dump(self.mine/'favmine_20260902_100000.json', {'videos':[raw(coin=900)]})
        dump(self.mine/'favmine_daily_20260904.json', {'videos':[raw(view=9000,coin=30)]})
        rec=next(iter(load_population(self.mine,self.samples).values()))
        self.assertEqual((rec['view'],rec['coin']),(9000,30))

    def test_reference_frozen_and_deduplicated(self):
        dump(self.mine/'favmine_20260902_100000.json', {'videos':[raw()]})
        dump(self.mine/'favmine_flowH2_20260903_110000.json', {'videos':[raw()]})
        before=load_reference(self.mine,self.samples)
        dump(self.mine/'favmine_daily_20261103.json', {'videos':[raw(coin=9999),raw('BV0000000001')]})
        self.assertEqual(load_reference(self.mine,self.samples),before)
        self.assertEqual(len(before),1)
        self.assertEqual(len(load_population(self.mine,self.samples)),2)

    def test_source_order_uses_capture_date_not_prefix(self):
        dump(self.mine/'favmine_flowH2_20260903_110000.json', {'videos':[raw(coin=900)]})
        dump(self.mine/'favmine_daily_20261103.json', {'videos':[raw(coin=40)]})
        self.assertEqual(next(iter(load_population(self.mine,self.samples).values()))['coin'],40)

    def test_raw_immutable_and_manifest_replay(self):
        p=self.mine/'favmine_20260902_100000.json';dump(p,{'videos':[raw()]})
        before=p.read_bytes();manifest=reference_manifest(self.mine,self.samples)
        load_population(self.mine,self.samples);load_reference(self.mine,self.samples)
        self.assertEqual(before,p.read_bytes())
        self.assertEqual(manifest,reference_manifest(self.mine,self.samples))

    def test_changed_frozen_reference_is_reported(self):
        path=self.mine/'favmine_20260902_100000.json';dump(path,{'videos':[raw()]})
        dump(self.root/'reference/mining_v4_manifest.json', reference_manifest(self.mine,self.samples))
        load_reference(self.mine,self.samples)
        dump(path,{'videos':[raw(coin=500)]})
        with self.assertRaises(ValueError):load_reference(self.mine,self.samples)

    def test_missing_counters_are_not_fabricated_zero(self):
        v=raw();del v['stat']['coin']
        self.assertIsNone(normalize_video(v,'test'))

    def test_owner_dict_is_normalized_with_mid(self):
        r=normalize_video(raw(),'test')
        self.assertEqual((r['owner'],r['owner_mid']),('作者','17'))
        self.assertTrue(is_blacklisted(r,{'owners':[{'mid':17}]}))

    def test_flat_owner_mid_is_preserved(self):
        v=raw();v['owner']='作者';v['owner_mid']=17
        self.assertEqual(normalize_video(v,'source')['owner_mid'],'17')

    def test_all_flow_days_retained_and_latest_atomic(self):
        folder=self.root/'flow';folder.mkdir()
        def node(b,rate):return {'bvid':b,'view':10000,'coin_rate':rate,'fav_rate':.03,'like_rate':.1}
        dump(folder/'godflowdaily_20260904_100000.json',{'flows':[{'nodes':[node('A',.3),node('B',.2)]}]})
        dump(folder/'godflowdaily_20260905_100000.json',{'flows':[{'nodes':[node('A',.1),node('C',.4)]}]})
        nodes=load_flow_nodes(folder)
        self.assertEqual(set(nodes),{'A','B','C'})
        self.assertEqual(nodes['A']['coin_rate'],.1)

    def test_partial_flow_does_not_destroy_complete_counts(self):
        folder=self.root/'flow';folder.mkdir()
        dump(folder/'godflowdeep_20260903_100000.json',{'flows':[{'nodes':[
            {'bvid':'A','view':10000,'coin_rate':.3,'fav_rate':.03,'like_rate':.1}]}]})
        dump(folder/'godflowdeep_20260904_100000.json',{'flows':[{'nodes':[{'bvid':'A','title':'补标题'}]}]})
        n=load_flow_nodes(folder)['A']
        self.assertEqual(n['coin_rate'],.3);self.assertEqual(n['title'],'补标题')


class LegacyTests(unittest.TestCase):
    def test_support_cannot_undo_short_video_caps(self):
        for dur,expected in [(20,'一般候选'),(60,'优秀候选')]:
            self.assertEqual(v3_tier(.99,dur,.03,.12,.2)[0],expected)

    def test_support_not_quality_upgrade(self):
        self.assertEqual(v3_tier(.87,120,.03,.12,.2)[0],'优秀候选')

    def test_seed_uses_explicit_human_verdict(self):
        for verdict in ['＿＿＿','感谢类视频，建议惩罚','优秀但不是神作','值得鼓励，神作','肝得辛苦，神作']:
            self.assertFalse(historical_seed_approved({'bvid':'A','v3':'神作','verdict':verdict}))
        self.assertTrue(historical_seed_approved({'bvid':'A','v3':'一般','verdict':'原创优秀制作，值得神作'}))


class ReviewTests(unittest.TestCase):
    def test_no_counts_or_machine_tier_can_confirm(self):
        self.assertEqual(review_status({'tier':'神作','coin_percentile':1}), 'unreviewed')

    def test_dual_axes_and_actual_observation_required(self):
        self.assertEqual(review_status(review()),'confirmed')
        self.assertEqual(review_status(review(resonance=1)),'not_fit')
        self.assertEqual(review_status(review(watched=False)),'unreviewed')
        self.assertEqual(review_status(review(evidence='')),'incomplete')

    def test_sentiment_effort_utility_cannot_confirm(self):
        for reason in ['sentiment_only','effort_only','utility_only']:
            self.assertEqual(review_status(review(reason=reason)),'not_fit')

    def test_old_stamps_not_new_training_labels(self):
        with self.assertRaises(ValueError):checked_reviews({'ann':{'BV1234567890':{'stamp':'god'}}})

    def test_invalid_review_values_rejected(self):
        for val in [-1,4,math.nan,True,'3']:
            with self.assertRaises(ValueError):
                checked_reviews({'schema':SCHEMA,'profile_id':PROFILE,'reviews':{'BV1234567890':review(craft=val)}})

    def test_injected_status_ignored(self):
        cleaned=checked_reviews({'schema':SCHEMA,'profile_id':PROFILE,
                                 'reviews':{'BV1234567890':review(status='confirmed',watched=False)}})
        self.assertEqual(review_status(cleaned['BV1234567890']),'unreviewed')

    def test_script_end_tag_cannot_inject(self):
        self.assertNotIn('</script>',safe_script_json({'title':'</script><script>alert(1)</script>'}))

    def test_batch_deterministic_diverse_and_unjudged(self):
        rows=[row(i,owner=str(i//3),motive_cues=['耗时'] if i%4==0 else []) for i in range(80)]
        reviews={rows[0]['bvid']:review()}
        a=make_batch(rows,reviews);b=make_batch(rows,reviews)
        self.assertEqual(a,b);self.assertEqual(len(a['assignments']),24)
        self.assertEqual(len({x['bvid'] for x in a['assignments']}),24)
        self.assertNotIn(rows[0]['bvid'],[x['bvid'] for x in a['assignments']])
        self.assertEqual({x['arm'] for x in a['assignments']},{'recall','motive_check','explore'})

    def test_no_unreviewed_false_negatives_in_evaluation(self):
        batch={'meta':{'catalog_id':'C'},'experiment':{'id':'X','assignments':[
            {'bvid':'BV1234567890','arm':'recall'},{'bvid':'BV0000000001','arm':'recall'}]}}
        doc={'schema':SCHEMA,'profile_id':PROFILE,'catalog_id':'C','experiment_id':'X',
             'reviews':{'BV1234567890':review()}}
        result=evaluate(batch,doc)['arms']['recall']
        self.assertEqual(result['coverage'],.5);self.assertEqual(result['precision_among_judged'],1)
        doc['experiment_id']='other'
        with self.assertRaises(ValueError):evaluate(batch,doc)


class PreferenceTests(unittest.TestCase):
    def test_favorites_never_quality_labels_and_weight_bounded(self):
        hint=PreferenceHint({'videos':[{'bvid':'BV1234567890','title':'陶喆 音乐现场'}]})
        rows=[row(0,title='陶喆 音乐现场',status='unreviewed')]
        hint.apply(rows);r=rows[0]
        self.assertEqual(r['status'],'unreviewed')
        self.assertLessEqual(abs(r['recall_priority']-r['coin_percentile']),TASTE_WEIGHT)
        self.assertGreater(hint.similarity('陶喆 音乐现场'),hint.similarity('偏微分方程课程'))

    def test_no_favorites_preserves_base_priority(self):
        hint=PreferenceHint({});rows=[row(0)];hint.apply(rows)
        self.assertEqual(rows[0]['recall_priority'],rows[0]['coin_percentile'])


if __name__=='__main__':unittest.main(verbosity=2)
