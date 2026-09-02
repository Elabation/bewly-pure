# 娲佸噣B绔?Clean Bilibili

![report](https://img.shields.io/badge/璋冩煡鎶ュ憡-鍦ㄧ嚎闃呰-334EAC) ![extension](https://img.shields.io/badge/鎵╁睍-Edge路Chrome-081F5C) ![samples](https://img.shields.io/badge/鏍锋湰-7,537鏉÷?019--2026-7096D1) ![license](https://img.shields.io/badge/绔嬪満-杩囨护浣庤川路涓嶅皝绁?7096D1)

> **馃摉 璋冩煡鎶ュ憡銆婄湅杩囷紝鍗翠笉缁欍€嬪湪绾块槄璇?鈫?https://elabation.github.io/bewly-pure/web/ecosystem-report.html**
>
> **鈿?娴忚鍣ㄦ墿灞曞畨瑁咃紙2 鍒嗛挓锛夆啋 鏁欑▼瑙?[docs/tutorial.md](docs/tutorial.md)**

> 杩囨护B绔欓椤垫帹鑽愮殑锛?*鐭棰?/ 绔栧睆瑙嗛 / 鐩存挱 / 浣庤川閲忚棰?*銆?
> PC 绔細**鍩轰簬 BewlyBewly锛圡IT锛夊仛澧為噺寮€鍙?*鈥斺€擴I/缃戞牸/鏃犻檺婊氬姩鐢ㄥ畠鐨勬垚鐔熸鏋讹紝鎺ㄨ崘杩囨护绠楁硶鏄垜浠嚜宸辩殑 CBI 鎰熻阿鎸囨暟銆?
> **棰勬瀯寤轰骇鐗╁湪 `extension-bewly/`**锛堜笅杞藉嵆瑁咃級锛屽閲忔簮鐮佷笌鏂规瑙?[docs/bewly-integration-plan.md](docs/bewly-integration-plan.md)锛岀増鏉冨垝鍒嗚 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)銆?
> 鎵嬫満绔紙鍏?root锛夛細Via/X锛圓ndroid锛? Userscripts锛坕OS锛夈€?
> 鍔ㄦ満锛氬ず鍥炴敞鎰忓姏锛屾嫆缁濄€屼笅婊戝埛瑙嗛銆嶇殑鎶曞杺璁捐銆?
>
> **鏍稿績绔嬪満锛堝厛鐢熷畾璋冿級锛氳繃婊や綆璐紝鑰屼笉鏄繚鐣欓珮璐ㄣ€?*
> 浣庤川鐨勫彲鎿嶄綔瀹氫箟 = **銆岀湅杩囷紝鍗翠笉缁欍€?*鈥斺€旀挱鏀鹃噺鏃╁凡娑堣€椾簡澶ч噺娉ㄦ剰鍔涳紝浜掑姩姣斿嵈浣庝簬鍚屾挱鏀炬鍩虹嚎銆?
> 鎵嬫悡楂樻姇鍏ュ唴瀹规瘮鍊艰櫧楂橈紝浣嗗搧鍛冲洜浜鸿€屽紓锛涚畻娉曞彧鐮嶃€屾敞鎰忓姏灏忓伔銆嶏紝涓嶅仛銆屽皝绁炲垽瀹樸€嶃€?

## 鏍稿績璇勫垎鏈哄埗锛堝叏閮ㄥ彲鎵嬭皟锛?

```
F7  鍔犳潈鎰熻阿鐜?= (鏀惰棌脳3.0 + 鎶曞竵脳2.0 + 鐐硅禐脳0.3) / 鎾斁
CBI 鎰熻阿鎸囨暟   = F7 梅 鍚屾挱鏀炬鍩虹嚎涓綅鏁帮紙6,734 鏉℃牱鏈粦绐楁嫙鍚堬紝鎵╁睍鍐呯疆鏇茬嚎锛?
```

- **姣斿€艰秺楂?鈫?瑙嗛璐ㄩ噺瓒婇珮**锛堟敹钘?鎶曞竵鏄己浠樺嚭琛屼负锛屽埛瀛愯棰戝埛涓嶅嚭鏉ワ級
- 鎾斁閲?< 3000 鈫?鍒?`unproven`锛堟瘮鐜囦笉鍙俊锛屾柊瑙嗛淇濇姢锛?
- 鎵€鏈夋潈閲嶃€侀槇鍊笺€佸紑鍏抽泦涓湪 **`config/clean.config.json`** 涓€涓枃浠堕噷锛涙墿灞曞垽瀹氭牳蹇冧笌瀹冨悓姝?

### 鎵嬭皟鎸囧崡锛堝厛鐢熸渶鍏冲績鐨勯儴鍒嗭級

| 鎯宠皟浠€涔?| 鏀瑰摢涓瓧娈?| 榛樿 | 璇存槑 |
|---|---|---|---|
| **CBI 鍒ゅ畾绾?* | `cbi.threshold` | 0.5 | 璋冨ぇ锛?.6锛夋洿涓ワ紝璋冨皬锛?.4锛夋洿瀹藉 |
| CBI 璧峰垽鎾斁 | `cbi.min_view` | 50000 | 鎾斁浣庝簬姝ゅ€间笉鍋?CBI 鍒ゅ畾 |
| 鐭棰戝垽瀹?| `filters.short_video_max_duration_sec` | 75s | 鏃堕暱 鈮?姝ゅ垽鐭棰?|
| 绔栧睆鍒ゅ畾 | `filters.portrait.wh_ratio_min` | 0.9 | 鏈夋晥瀹?楂?< 姝ゅ€煎垽绔栧睆 |
| 浣庢挱鏀剧‖杩囨护 | `filters.min_views` | 1000 | 鎬绘挱鏀句綆浜庢鐩存帴杩囨护 |
| 鏍囬绛惧悕 | `filters.block_keywords` | 绗琋闆?璇澛锋寫鎴樹綋 | 鍛戒腑鍗宠繃婊わ紙浠呮斁妫€楠岃繃鐨勭鍚嶏紝搂14锛?|
| 瀹樻柟鍖虹櫧鍚嶅崟 | `filters.zone_whitelist` | 鐢靛奖/鐢佃鍓?绾綍鐗?| 鐧藉悕鍗曞尯涓嶅仛浣庤川鍒ゅ畾 |

鏀瑰畬閰嶇疆鎬庝箞楠岃瘉鏁堟灉锛?

```bash
python engine\scoring.py --data data\samples\<鏍锋湰>.json   # 鎵归噺鎵撳垎锛岀湅 tier 鍒嗗竷
python engine\scoring.py --bvid BV1xxxx                    # 鍗曡棰戝湪绾胯瘯绠?
python engine\calibrate.py --data data\samples\<鏍锋湰>.json # 璁╃湡瀹炴暟鎹缓璁槇鍊?
```

## 鐩綍缁撴瀯

```
bilibili-clean/
鈹溾攢鈹€ config/clean.config.json      # 鍞竴鐪熸簮锛氭墍鏈夋潈閲?闃堝€?寮€鍏?
鈹溾攢鈹€ extension/                    # 娴忚鍣ㄦ墿灞?v1.0锛圗dge/Chrome锛孧V3锛?
鈹?  鈹溾攢鈹€ manifest.json             #   鎵╁睍娓呭崟
鈹?  鈹溾攢鈹€ content.js                #   鏍稿績锛歸bi绛惧悕鈫掓媺鎺ㄨ崘娴佲啋鍚屾杩囨护鈫掔綉鏍兼覆鏌撯啋鎳掑垽瀹?
鈹?  鈹溾攢鈹€ md5.js                    #   MD5锛坵bi 绛惧悕渚濊禆锛?
鈹?  鈹溾攢鈹€ content.css               #   缃戞牸甯冨眬鏍峰紡锛堜寒/鏆楀弻涓婚锛?
鈹?  鈹斺攢鈹€ README-INSTALL.md         #   瀹夎璇存槑
鈹溾攢鈹€ engine/
鈹?  鈹溾攢鈹€ collect_stats.py          # 鏁版嵁閲囬泦锛圔绔橝PI锛岄浂渚濊禆锛寃bi绛惧悕宸插唴缃級
鈹?  鈹溾攢鈹€ scoring.py                # 璇勫垎寮曟搸锛坱ier 鍒嗙骇 + 杩囨护鍘熷洜锛?
鈹?  鈹溾攢鈹€ calibrate.py              # 鏍″噯锛氭寜鍒嗕綅鏁板缓璁槇鍊硷紝鍑烘姤鍛?
鈹?  鈹溾攢鈹€ ecosystem_collect*.py     # 鐢熸€侀噰闆嗭紙姒滃崟/鐑棬/鎺ㄨ崘娴?鏂扮/鎼滅储娣遍〉锛?
鈹?  鈹溾攢鈹€ ecosystem_collect_v5.py   # 澶ч噰鏍凤細姣忓懆蹇呯湅387鏈?2020-2026)/鍏ョ珯蹇呭埛/鐑棬娣遍〉
鈹?  鈹溾攢鈹€ ecosystem_analysis.py     # 鐢熸€佸垎鏋愶紙鍏紡鎵弿/鍒嗕綅娈?鍥涜薄闄?鍒嗗尯鐢诲儚锛?
鈹?  鈹溾攢鈹€ deep_analysis.py          # 娣卞害缁熻瀹為獙锛氬亸鐩稿叧/CBI鍩虹嚎/娲涗鸡鍏?PCA/妫€楠?鏃朵唬婕斿寲/鏃堕暱鍒嗘瀽
鈹?  鈹溾攢鈹€ simulate_userscript.py    # 鍒ゅ畾閫昏緫绂荤嚎妯℃嫙鍣紙涓婄嚎鍓嶉獙璇佽繃婊ょ巼锛?
鈹?  鈹斺攢鈹€ build_report.py           # 鎶ュ憡缃戦〉鏋勫缓锛堝箓绛夋敞鍏ユ暟鎹級
鈹溾攢鈹€ data/
鈹?  鈹溾攢鈹€ samples/                  # 閲囬泦鏍锋湰锛坴5 绾?涓囨潯锛?020-2026 璺ㄥ害锛? 鏍″噯鎶ュ憡
鈹?  鈹斺攢鈹€ analysis/                 # 鐢熸€佸垎鏋?+ 娣卞害鍒嗘瀽缁撴灉 JSON
鈹溾攢鈹€ web/
鈹?  鈹斺攢鈹€ ecosystem-report.html     # 銆婄湅杩囷紝鍗翠笉缁欍€嬭皟鏌ユ姤鍛?v3锛堝崟鏂囦欢鍙垎浜紝15绔犺妭锛?
鈹溾攢鈹€ userscript/
鈹?  鈹斺攢鈹€ bilibili-clean-mobile.user.js  # 鎵嬫満绔剼鏈紙m.bilibili.com 涓夎偂娴佽繃婊わ級
鈹斺攢鈹€ docs/
    鈹溾攢鈹€ tutorial.md               # 瀹夎涓庝娇鐢ㄦ暀绋嬶紙鍥涚鏂瑰紡锛?
    鈹斺攢鈹€ mobile-plan.md            # 鎵嬫満绔厤root鏂规璇勪及
```

## 蹇€熷紑濮?

```bash
# 1. 閲囬泦鏍锋湰锛堢害1-2鍒嗛挓锛屼粎API鍏冩暟鎹紝涓嶄笅杞借棰戯級
python engine\collect_stats.py

# 2. 鏍″噯锛氱湡瀹炴暟鎹缓璁潈閲?闃堝€硷紝鎶ュ憡鍦?data/samples/calibration-report_*.md
python engine\calibrate.py --data data\samples\sample_xxx.json

# 3. 鎶婂缓璁槇鍊肩矘鍥?config/clean.config.json锛岃窇鎵撳垎楠岃瘉
python engine\scoring.py --data data\samples\sample_xxx.json
```

**PC 绔紙Edge/Chrome 鎵╁睍锛?*锛歚edge://extensions` 鈫?寮€鍙戜汉鍛樻ā寮?鈫?鍔犺浇瑙ｅ帇缂╃殑鎵╁睍 鈫?閫?`extension/` 鏂囦欢澶?鈫?鎵撳紑 bilibili.com 鍗崇綉鏍兼ā寮忋€傝瑙?[extension/README-INSTALL.md](extension/README-INSTALL.md)銆?

**鎵嬫満绔紙鍏?root锛屼富鎴樺満锛?*锛歏ia/X 娴忚鍣紙Android锛夋垨 Safari + Userscripts App锛坕OS锛夊畨瑁?`userscript/bilibili-clean-mobile.user.js`锛屾墦寮€ `m.bilibili.com` 鍗崇敓鏁堚€斺€旈椤电儹姒滐紙SSR锛?棰戦亾娴侊紙region/feed/rcmd锛?瑙嗛椤电浉鍏虫祦锛坅rchive/related锛変笁鑲″叏杩囨护锛屽垽瀹氭牳蹇冧笌 PC 鐗堥€愬瓧娈典竴鑷淬€傝瑙?`docs/mobile-plan.md`銆?

### 鎵╁睍 v1.0 鍒ゅ畾娴佺▼锛堝搴旀姤鍛?搂13 杩囨护鍣ㄨ璁★級

```
鍚屾灞傦紙鎷夋祦鍗虫护锛屽崱鐗囨牴鏈笉娓叉煋锛夛細
  鐩存挱 R1 / 鏃堕暱鈮?5s R1 / 鏍囬鍛戒腑绛惧悕姝ｅ垯 R7锛堢N闆?璇濄€佹寫鎴樹綋锛?

鎳掑垽瀹氬眰锛堝崱鐗囨粴杩戣鍙ｆ墠鏌ヨ鎯咃紝CBI 鏇茬嚎鍐呯疆锛夛細
  绔栧睆 R1 鈫?涓嶆覆鏌?
  鎾斁 < 1000 R1 鈫?涓嶆覆鏌?
  瀹樻柟鍖虹櫧鍚嶅崟锛堢數褰?鐢佃鍓?绾綍鐗囷級R4 鈫?璺宠繃 CBI锛屼笉鍒や綆璐?
  鎾斁 鈮?5涓?涓?CBI < 0.5 R2 鈫?涓嶆覆鏌撱€岀湅杩囦笉缁欍€?
  鎾斁 3鍗儈5涓?鍏ㄥ眬鍏滃簳 R2' 鈫?鍙爫 junk锛坙ow 鎵撴爣涓嶉殣钘忥級
  銆屾姇甯乆鏇存柊銆嶄篂璁ㄦ枃鏈?R8 鈫?瑙掓爣鎵撱€屼篂銆嶆爣锛屼笉鎯╃綒
```

鎺у埗鍙拌皟璇曪細`CleanBili.counts` 鐪嬪疄鏃惰繃婊ょ粺璁★紱`CleanBili.verdicts` 鐪嬫瘡鏉″垽瀹氭槑缁嗐€?

## 宸ヤ綔鍘熺悊

- **鏁版嵁灞?*锛氳嚜寤?wbi 绛惧悕鐩磋繛 `index/top/feed/rcmd`锛堟帹鑽愭祦锛変笌 `x/web-interface/view`锛堣鎯?stat/dimension/duration锛夛紝涓嶅姭鎸侀〉闈换浣曡姹?
- **绔栧睆璇嗗埆**锛歞imension 瀹?楂樻瘮锛堣€冭檻 rotate 鏃嬭浆鏍囧織锛夛紝涓嶄笅杞借棰戜笉鐢?FFmpeg
- **缃戞牸鎺ョ**锛欱 绔欓《鏍忥紙鎼滅储/澶村儚/鍘嗗彶/鏀惰棌锛夊師鐢熶繚鐣欙紝鎺ㄨ崘鍖烘浛鎹负鑷粯缃戞牸锛涙棤闄愭粴鍔?+ CBI 鎳掑垽瀹氾紱浣庤川鍗＄墖涓嶆覆鏌擄紝缃戞牸鑷姩閲嶆帓鏃犵┖娲烇紱鐘舵€佹潯涓€閿€屽垏鍥炲師鐗堛€?

## 璺嚎鍥剧姸鎬侊紙瀵圭収 HANDOFF.md锛?

| # | 闃舵 | 鐘舵€?|
|---|---|---|
| 1 | 鏁版嵁灞傦細API 閲囬泦鎾斁/鏀惰棌/鎶曞竵 | 鉁?閲囬泦浜斾欢濂?+ **姣忓懆蹇呯湅/鍏ョ珯蹇呭埛澶ч噰鏍?*锛堢疮璁?7000+ 鏉★紝2020-2026 涓冨勾璺ㄥ害锛?|
| 2 | 璇勫垎妯″瀷锛氶獙璇佸叕寮忋€佸畾鏉冮噸涓庨槇鍊?| 鉁?棣栬疆鏍″噯 + 31 閰嶇疆缃戞牸鎵弿锛堝竵/鎾?= 浣庤川鎺㈡祴鍐犲啗锛岃瑙佹姤鍛娐?锛?|
| 2.5 | 鐢熸€佽皟鏌ャ€婄湅杩囷紝鍗翠笉缁欍€?| 鉁呪渽 **绗笁鐗堬細鍗佷笁椤圭粺璁″疄楠?*锛堝亸鐩稿叧/鍒嗕綅鍥炲綊/娲涗鸡鍏?PCA/蠂虏/MWU/**鏃朵唬婕斿寲 2020-2026**/**鏃堕暱脳璐ㄩ噺**/**灞傞棿瀵规瘮**锛夛紝鍗曟爮鍙鎬ч噸鍐欙紝鎶ュ憡 web/ecosystem-report.html |
| 3 | 杩囨护楠岃瘉锛氱湡瀹為〉闈㈤獙璇佽鍒?| 鉁?**鎵╁睍 v1.0 鐪熸満鍏ㄩ摼璺疄娴?*锛坵bi 绛惧悕鐩磋繛 code 0銆佺綉鏍?17 鍗?CBI 瑙掓爣鍏ㄤ寒銆佺爫 3 鏉★級锛涘垽瀹氶€昏緫绂荤嚎妯℃嫙 feed 灞傜爫 32% 鍗＄墖鏀跺洖 54% 鎾斁浠介 |
| 3.5 | 寮曟搸 v2锛欳BI 鐩稿鍩虹嚎鍙栦唬鍏ㄥ眬闃堝€?| 鉁?璁捐+鍙傛暟钀藉湴锛歝onfig 鏂板 `cbi` 娈碉紙threshold 0.5 / min_view 5w锛? 8 鏉¤繃婊ゅ櫒瑙勫垯锛堟姤鍛娐?3锛夛紝鎵╁睍鍒ゅ畾鏍稿績鍚屾 |
| 4 | 鎵嬫満绔柟妗堬紙鍏?root锛?| 鉁?**鏈哄埗钀藉湴**锛歚userscript/bilibili-clean-mobile.user.js`锛坢.bilibili.com 棣栭〉鐑 SSR / 棰戦亾娴?/ 瑙嗛椤电浉鍏虫祦涓夎偂鍏ㄨ繃婊わ級锛屽崟娴?21/21 + 鐪熷疄鏍锋湰绔埌绔?23.3% 杩囨护鐜囬獙璇侊紝瀹夎鎸囧崡瑙?docs/mobile-plan.md锛屽緟鐪熸満瀹炴祴 |
| 5 | 鎴愭灉鍙戝竷 | 鉁?GitHub 鍏紑浠撳簱 + Pages 鎶ュ憡 + 鎵╁睍鏁欑▼榻愬 |

## 鐜版垚鏂规瀵规瘮锛堜负浠€涔堣嚜宸卞啓锛?

| 椤圭洰 | 骞冲彴 | 涓庢湰椤圭洰鍏崇郴 |
|---|---|---|
| [Bilibili-Evolved](https://github.com/the1812/Bilibili-Evolved) | PC | 鏈€寮哄寮哄浠讹紝鏈夐椤电畝鍖?灞忚斀锛涗絾鏃犮€屾敹钘?鎶曞竵姣斿€笺€嶈瘎鍒嗘満鍒?鈫?鎴戜滑寮曠敤瀹冨仛琛ュ厖锛屼笉閲嶅閫犺疆瀛?|
| [BlocksShortVideos](https://github.com/qiye45/BlocksShortVideos) | PC | 鍙睆钄界煭瑙嗛锛屾棤璇勫垎 |
| [Bilibili-Gate](https://github.com/magicdawn/bilibili-gate) | PC | 鑷畾涔夐椤?|
| [MBGA](https://github.com/Xposed-Modules-Repo/top.trangle.mbga) | 鎵嬫満 | 闇€ root锛圠SPosed锛夛紱鍏峳oot鐢ㄦ埛鐢ㄤ笉浜?鈫?鎴戜滑鐨勫樊寮傚寲绌洪棿 |

**宸紓鍖?*锛氣憼 PC 缃戞牸鎺ョ + 鎵嬫満鍏?root锛涒憽 鏀惰棌/鎶曞竵/鎾斁姣斿€肩殑璐ㄩ噺璇勫垎锛圕BI 鐩稿鍩虹嚎锛夛紝闃堝€煎叏鎵嬭皟銆?

> �ֿ�����˵����**bewly-pure** = BewlyBewly �Ĵ����ݽ��档UI/���/���޹����Ĺ������� [BewlyBewly](https://github.com/hakadao/BewlyBewly)��MIT, ? Hakadao�������ֿ������ֻ��һ�� CBI �����㷨����� [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)����������Ϊ��������Ϊ��������ֻ�Ǳ��ֿ�ĳɹ�֮һ��
