#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日财经新闻看板 · 自包含刷新脚本 v1.0.1
=========================================
流程：抓取（东方财富 宏观政策/财经要闻 双栏目）→ 情绪 + 行业板块 + 个股 三维分类
      → 重建自包含看板 HTML（KPI/板块菜单可点击聚合过滤、新闻行点击查看详情弹层）

用法：
    python3 refresh_daily_news.py                 # 单次刷新，覆盖输出看板
    python3 refresh_daily_news.py --loop 600      # 常驻模式：每 600 秒（10 分钟）自动刷新
    python3 refresh_daily_news.py --out 我的看板.html   # 自定义输出路径

依赖：仅 Python 3.8+ 标准库（urllib / json / re / html），零第三方依赖，离线可打包分发。
数据源：东方财富资讯列表 API（column 345 宏观政策 / 344 财经要闻），公开接口。
"""
import sys, re, json, html, time, argparse, urllib.request
from datetime import datetime

# ---------- 可配置项 ----------
REFRESH_SEC = 600          # 自动刷新周期（秒），页面倒计时与此保持一致
DEFAULT_OUT = "每日财经新闻_板块分类.html"

EM_NEWS_API = ("https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
               "?client=web&biz=web_news_col&column={column}&order=1"
               "&needInteractData=0&page_index=1&page_size={size}&req_trace={ts}")
EM_COLUMNS = {345: "东方财富-宏观政策", 344: "东方财富-财经要闻"}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
      "Accept": "application/json,text/html,*/*;q=0.8",
      "Accept-Language": "zh-CN,zh;q=0.9"}

# ---------- 情绪词典（可按需增删） ----------
POS_KW = ["利好","上涨","增长","超预期","走强","大涨","新高","获批","突破","政策支持","降准","降息","补贴","减税","订单","中标","签署","回购","增持","分红","提振","回暖","复苏","扩产","加码","提速","创新高","净流入","涨停","机遇","红利","协同","加速","景气","高增","赋能","加仓","逆市走强","放量","资金流入","和解","终止调查","解除质押","胜诉"]
NEG_KW = ["利空","下跌","下滑","走弱","亏损","处罚","违规","减持","退市","风险","警告","下调","暴跌","立案","调查","诉讼","收缩","裁员","停产","爆雷","违约","遇冷","承压","收窄","流拍","清仓","跌停","净流出","降温","警戒","限制","禁令","质押","商誉减值"]
POS_W, NEG_W = 2, 2   # 单词命中权重（命中次数 × 权重，利好>0 / 利空<0）

# ---------- 15 类行业板块词典（新闻将注明所属板块） ----------
SECTORS = [
    ("银行保险证券", ["银行","保险","券商","证券","投行","信托","基金","资管","金融","北向","两融","汇率","利率"]),
    ("地产建筑",     ["地产","房地产","楼市","房贷","物业","基建","建筑","土木","保障房","城中村","住建"]),
    ("医药生物",     ["医药","医疗","药","疫苗","创新药","器械","CXO","医院","医保","生物","健康"]),
    ("食品饮料",     ["食品","饮料","乳业","白酒","啤酒","调味","零食","餐饮","农产品","猪肉","养殖"]),
    ("汽车与新能源车",["汽车","新能源车","电动车","整车","车企","锂电","电池","充电","智能驾驶","自动驾驶","零部件"]),
    ("半导体芯片",   ["半导体","芯片","晶圆","光刻","封测","存储","EDA","功率器件","国产替代","集成电路"]),
    ("人工智能算力", ["人工智能","AI","大模型","算力","数据中心","GPU","服务器","机器人","智能体","算法","AI眼镜","AI手机"]),
    ("通信与5G",     ["通信","5G","6G","光模块","运营商","卫星","网络","光纤","基站"]),
    ("电子消费",     ["手机","消费电子","面板","PCB","元件","显示","VR","AR","耳机","折叠屏","果链"]),
    ("电力能源",     ["电力","电网","光伏","风电","核电","储能","氢能","煤炭","油气","石油","天然气","能源","特高压","虚拟电厂"]),
    ("有色金属",     ["稀土","有色","铜","铝","锂","钴","镍","黄金","贵金属","钨","小金属","锌"]),
    ("钢铁化工",     ["钢铁","化工","化学","水泥","玻璃","建材","纯碱","塑料","橡胶","化肥","磷","氟"]),
    ("机械与军工",   ["军工","国防","机械","机床","工业母机","装备","船舶","航空","航天","无人机","雷达","导弹"]),
    ("交通运输",     ["航空","机场","航运","港口","物流","快递","铁路","公路","免税","旅游","出行"]),
    ("农业与环保",   ["种业","粮食","农业","环保","污水","固废","碳中和","碳交易","绿电","生态"]),
]
SECTOR_ICON = {"银行保险证券":"🏦","地产建筑":"🏗️","医药生物":"💊","食品饮料":"🍜","汽车与新能源车":"🚗","半导体芯片":"💾","人工智能算力":"🤖","通信与5G":"📡","电子消费":"📱","电力能源":"⚡","有色金属":"⛏️","钢铁化工":"🏭","机械与军工":"🚀","交通运输":"🚄","农业与环保":"🌾"}

# ---------- 个股词典（60 只常用 A 股）+ 6 位代码识别 ----------
STOCKS = {"贵州茅台":"600519","五粮液":"000858","宁德时代":"300750","比亚迪":"002594","中国平安":"601318","招商银行":"600036","兴业银行":"601166","美的集团":"000333","格力电器":"000651","海康威视":"002415","隆基绿能":"601012","通威股份":"600438","中远海控":"601919","万华化学":"600309","恒瑞医药":"600276","迈瑞医疗":"300760","药明康德":"603259","立讯精密":"002475","工业富联":"601138","京东方A":"000725","中兴通讯":"000063","中际旭创":"300308","新易盛":"300502","紫金矿业":"601899","北方稀土":"600111","中国稀土":"000831","江西铜业":"600362","宝钢股份":"600019","中国船舶":"600150","中国重工":"601989","中航沈飞":"600760","航发动力":"600893","长江电力":"600900","中国核电":"601985","三峡能源":"600905","伊利股份":"600887","海天味业":"603288","金龙鱼":"300999","牧原股份":"002714","温氏股份":"300498","保利发展":"600048","万科A":"000002","中国建筑":"601668","中信证券":"600030","东方财富":"300059","同花顺":"300033","恒生电子":"600570","科大讯飞":"002230","寒武纪":"688256","中科曙光":"603019","浪潮信息":"000977","海光信息":"688041","金山办公":"688111","长安汽车":"000625","长城汽车":"601633","上汽集团":"600104","赛力斯":"601127","福耀玻璃":"600660","三一重工":"600031","顺丰控股":"002352"}
CODE_RE = re.compile(r"(?<![0-9])([063]\d{5})(?![0-9])")

# ==================== 抓取 ====================
def _http_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))

def _fetch_column(column, limit):
    """抓取东财单一资讯栏目，返回 [{title,url,source,date,summary}, ...]"""
    out = []
    try:
        data = _http_json(EM_NEWS_API.format(column=column, size=limit, ts=int(time.time()*1000)))
        for it in (data or {}).get("data", {}).get("list", []) or []:
            title = (it.get("title") or "").strip()
            href = it.get("url") or ""
            if not title or not href:
                continue
            out.append({"title": title, "url": href,
                        "source": EM_COLUMNS[column],
                        "date": (it.get("showTime") or "")[:10],
                        "summary": ""})
    except Exception as e:
        print(f"  [warn] 栏目 {column} 抓取失败: {e}", file=sys.stderr)
    return out

def fetch_news(limit_per_col=40):
    rows = []
    for col in EM_COLUMNS:
        rows.extend(_fetch_column(col, limit_per_col))
    seen, uniq = set(), []
    for r in rows:
        if r["title"] not in seen:
            seen.add(r["title"]); uniq.append(r)
    return uniq[:60]

# ==================== 分类 ====================
def classify(n):
    text = n["title"] + " " + n["summary"]
    score, hits = 0, []
    for kw in POS_KW:
        c = text.count(kw)
        if c: score += POS_W * c; hits.append(kw)
    for kw in NEG_KW:
        c = text.count(kw)
        if c: score -= NEG_W * c; hits.append(kw)
    n["sentiment"] = "利好" if score > 0 else ("利空" if score < 0 else "中性")
    n["hits"] = hits[:4]
    secs = [name for name, kws in SECTORS if any(k.lower() in text.lower() for k in kws)]
    n["sectors"] = secs
    n["sector"] = secs[0] if secs else "综合宏观"
    st = [f"{k}({v})" for k in STOCKS if k in text]
    st += [f"代码{c}" for c in CODE_RE.findall(text)]
    n["stocks"] = list(dict.fromkeys(st))[:6]
    return n

# ==================== HTML 生成 ====================
def esc(s): return html.escape(str(s or ""))

def build_html(news, ts, refresh_sec=REFRESH_SEC):
    ts_fmt = datetime.fromtimestamp(ts/1000).strftime("%Y-%m-%d %H:%M")
    total = len(news)
    pos = [n for n in news if n["sentiment"] == "利好"]
    neg = [n for n in news if n["sentiment"] == "利空"]
    neu = total - len(pos) - len(neg)
    nstk_news = sum(1 for n in news if n["stocks"])
    nstock = len({s for n in news for s in n["stocks"]})
    nsec = sum(1 for name, _ in SECTORS if any(name in n["sectors"] for n in news))

    menu_names = [name for name, _ in SECTORS if any(name in n["sectors"] for n in news)] + ["综合宏观"]
    menu = "".join(
        f'<a class="mchip" id="mc_{esc(name)}" onclick="setSector(\'{esc(name)}\')">{SECTOR_ICON.get(name,"🌐")} {esc(name)}</a>'
        for name in menu_names)

    data_js = json.dumps(news, ensure_ascii=False).replace("</", "<\\/")
    icon_js = json.dumps(SECTOR_ICON, ensure_ascii=False)
    order_js = json.dumps(menu_names, ensure_ascii=False)
    next_ts = ts + refresh_sec * 1000

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>每日财经新闻 · 板块分类</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font:13px/1.45 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#f4f6fa;color:#1f2733;padding:10px 14px 40px}}
.hd{{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
.hd h1{{font-size:17px;color:#0f2540}} .hd h1 span{{color:#c0392b}}
.meta{{margin-left:auto;font-size:12px;color:#667;display:flex;gap:12px;align-items:baseline}}
.meta b{{color:#e67e22;font-variant-numeric:tabular-nums}}
.kpis{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}}
.kpi{{background:#fff;border:1px solid #e3e8f0;border-radius:8px;padding:5px 12px;font-size:12px;color:#556;cursor:pointer;user-select:none;transition:all .15s}}
.kpi:hover{{border-color:#1a5fb4;transform:translateY(-1px)}}
.kpi b{{font-size:16px;margin-right:4px;font-variant-numeric:tabular-nums}}
.kpi.on{{background:#1a5fb4;color:#fff;border-color:#1a5fb4}} .kpi.on b{{color:#fff}}
.kpi.t b{{color:#c0392b}} .kpi.f b{{color:#1e8e4f}} .kpi.n b{{color:#7a8699}} .kpi.s b{{color:#1a5fb4}}
.menubar{{position:sticky;top:0;z-index:9;background:#eef1f7ee;backdrop-filter:blur(4px);border:1px solid #dde3ee;border-radius:8px;padding:6px 8px;display:flex;gap:6px;overflow-x:auto;margin-bottom:4px;transition:box-shadow .3s}}
.menubar.flash{{box-shadow:0 0 0 3px #e67e22aa}}
.mchip{{flex:none;font-size:12px;background:#fff;border:1px solid #dde3ee;border-radius:20px;padding:3px 10px;text-decoration:none;color:#345;white-space:nowrap;cursor:pointer}}
.mchip:hover,.mchip.on{{background:#1a5fb4;color:#fff;border-color:#1a5fb4}}
.filterbar{{display:none;align-items:center;gap:8px;margin:4px 2px 8px;font-size:12px;color:#1a5fb4}}
.filterbar.show{{display:flex}}
.filterbar b{{color:#e67e22}}
.resetbtn{{cursor:pointer;background:#fff;border:1px solid #1a5fb4;color:#1a5fb4;border-radius:14px;padding:1px 10px;font-size:12px}}
.resetbtn:hover{{background:#1a5fb4;color:#fff}}
section{{margin-bottom:12px}}
.sechead{{font-size:14px;font-weight:700;color:#0f2540;padding:4px 2px;border-left:4px solid #1a5fb4;padding-left:8px;margin-bottom:4px;display:flex;gap:8px;align-items:baseline}}
.sechead small{{color:#890;font-weight:400}} .sechead .neg{{color:#1e8e4f}}
ul{{list-style:none}}
li.row{{display:flex;align-items:center;gap:8px;padding:4px 8px;background:#fff;border:1px solid #edf0f6;border-radius:6px;margin-bottom:3px;cursor:pointer}}
li.row:hover{{border-color:#1a5fb4;background:#f7faff}}
.dot{{flex:none;width:8px;height:8px;border-radius:50%;background:#b8c2d0}}
.dot.p{{background:#e74c3c;box-shadow:0 0 4px #e74c3c88}} .dot.f{{background:#27ae60}}
.tm{{flex:none;font-size:11px;color:#99a3b5;font-variant-numeric:tabular-nums;width:118px}}
.tt{{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tags{{flex:none;display:flex;gap:4px}}
.tag{{font-size:11px;padding:1px 7px;border-radius:10px;white-space:nowrap}}
.tag.sec{{background:#eef3ff;color:#1a5fb4;border:1px solid #d5e2ff}}
.tag.p{{background:#fdeceb;color:#c0392b;border:1px solid #f5c6c2}}
.tag.f{{background:#e8f6ef;color:#1e8e4f;border:1px solid #bfe8d2}}
.tag.stk{{background:#fff7e8;color:#b9770e;border:1px solid #f3ddb0}}
.hint{{font-size:11px;color:#8a95a8;margin:6px 2px 0}}
.empty{{text-align:center;color:#8a95a8;padding:30px 0;background:#fff;border:1px dashed #dde3ee;border-radius:8px}}
.mask{{display:none;position:fixed;inset:0;background:#0f254066;z-index:99;align-items:center;justify-content:center}}
.mask.show{{display:flex}}
.dialog{{background:#fff;border-radius:12px;max-width:640px;width:92%;max-height:78vh;overflow:auto;padding:18px 20px;box-shadow:0 12px 40px #0f254055}}
.dialog h3{{font-size:16px;color:#0f2540;margin-bottom:8px;line-height:1.5}}
.dmeta{{font-size:12px;color:#778;margin-bottom:10px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
.dsum{{font-size:13px;color:#334;line-height:1.7;white-space:pre-wrap;background:#f6f8fb;border-radius:8px;padding:10px 12px;margin-bottom:10px}}
.dkw span{{display:inline-block;font-size:11px;background:#fff7e8;color:#b9770e;border:1px solid #f3ddb0;border-radius:10px;padding:1px 8px;margin:2px 4px 2px 0}}
.dlink{{display:inline-block;margin-top:8px;font-size:13px;color:#1a5fb4;text-decoration:none}}
.xclose{{float:right;cursor:pointer;color:#99a;font-size:18px;line-height:1;padding:2px 6px}}
@media(max-width:640px){{ .tm{{display:none}} }}
</style></head><body>

<div class="hd">
  <h1>📰 每日财经新闻 <span>· 板块分类</span></h1>
  <div class="meta">
    <span>数据更新：{ts_fmt}</span>
    <span>自动刷新：<b id="cd">10:00</b></span>
  </div>
</div>

<div class="kpis">
  <div class="kpi" id="kAll" onclick="resetFilter()"><b>{total}</b>今日新闻</div>
  <div class="kpi t" id="kP" onclick="setSent('利好')"><b>{len(pos)}</b>🔴 利好</div>
  <div class="kpi f" id="kF" onclick="setSent('利空')"><b>{len(neg)}</b>🟢 利空</div>
  <div class="kpi n" id="kN" onclick="setSent('中性')"><b>{neu}</b>⚪ 中性</div>
  <div class="kpi s" id="kS" onclick="flashMenu()"><b>{nsec}</b>📂 板块</div>
  <div class="kpi s" id="kStk" onclick="setStk()"><b>{nstock}</b>🏷️ 个股({nstk_news}条)</div>
</div>

<div class="menubar" id="menubar">{menu}</div>
<div class="filterbar" id="fbar">
  <span>🔎 当前聚合：<b id="ftext"></b></span>
  <span class="resetbtn" onclick="resetFilter()">✕ 显示全部</span>
</div>

<div id="board"></div>

<p class="hint">💡 顶部 KPI 卡与板块菜单均可点击聚合过滤（再点一次取消）；点击新闻行查看详情（摘要、判定依据、原文链接）。数据每 10 分钟自动重新抓取，倒计时归零自动载入。</p>

<div class="mask" id="mask" onclick="if(event.target===this)closeDlg()">
  <div class="dialog">
    <span class="xclose" onclick="closeDlg()">✕</span>
    <h3 id="dTitle"></h3>
    <div class="dmeta" id="dMeta"></div>
    <div class="dsum" id="dSum"></div>
    <div class="dkw" id="dKw"></div>
    <a class="dlink" id="dLink" target="_blank">🔗 查看原文 →</a>
  </div>
</div>

<script>
const DATA = {data_js};
DATA.forEach((n,i)=>n._id=i);
const ICON = {icon_js};
const ORDER = {order_js};
const NEXT = {next_ts};

function esc(s){{return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}}

let fSent = null, fSector = null, fStk = false;

function match(n){{
  if(fSent && n.sentiment !== fSent) return false;
  if(fStk && !(n.stocks && n.stocks.length)) return false;
  if(fSector && !(n.sectors||[]).includes(fSector) && !(fSector==='综合宏观' && !(n.sectors||[]).length)) return false;
  return true;
}}
function rowHtml(n){{
  const dot = n.sentiment==='利好'?'dot p':(n.sentiment==='利空'?'dot f':'dot');
  const stag = n.sentiment==='利好'?'tag p':(n.sentiment==='利空'?'tag f':'tag');
  let tags = `<span class="${{stag}}">${{n.sentiment}}</span><span class="tag sec">${{ICON[n.sector]||'🌐'}} ${{esc(n.sector)}}</span>`;
  (n.stocks||[]).slice(0,2).forEach(s=>tags+=`<span class="tag stk">🏷️ ${{esc(s)}}</span>`);
  return `<li class="row" onclick="openDlg(${{n._id}})"><span class="${{dot}}"></span><span class="tm">${{esc((n.date||'').slice(5))}}</span><span class="tt">${{esc(n.title)}}</span><span class="tags">${{tags}}</span></li>`;
}}
function secBlock(name, lst){{
  const p = lst.filter(n=>n.sentiment==='利好').length, g = lst.filter(n=>n.sentiment==='利空').length;
  let badge = p?`<small>🔴利好 ${{p}}</small>`:''; if(g) badge+=`<small class="neg">🟢利空 ${{g}}</small>`;
  return `<section><div class="sechead">${{ICON[name]||'🌐'}} ${{esc(name)}} <small>(${{lst.length}})</small> ${{badge}}</div><ul>${{lst.map(rowHtml).join('')}}</ul></section>`;
}}
function render(){{
  let html = '';
  if(fSector){{
    const lst = DATA.filter(match);
    html = lst.length ? secBlock(fSector, lst) : emptyBox();
  }} else {{
    let used = 0;
    ORDER.forEach(name=>{{
      if(name==='综合宏观') return;
      const lst = DATA.filter(n=>(n.sectors||[]).includes(name) && match(n));
      if(!lst.length) return;
      lst.forEach(n=>used++);
      html += secBlock(name, lst);
    }});
    const other = DATA.filter(n=>!(n.sectors||[]).length && match(n));
    if(other.length){{ other.forEach(n=>used++); html += secBlock('综合宏观', other); }}
    if(!used) html = emptyBox();
  }}
  document.getElementById('board').innerHTML = html;
  const fb = document.getElementById('fbar');
  const parts = [];
  if(fSent) parts.push(fSent);
  if(fSector) parts.push('板块：'+fSector);
  if(fStk) parts.push('含个股');
  if(parts.length){{
    document.getElementById('ftext').textContent = parts.join(' + ');
    fb.classList.add('show');
  }} else fb.classList.remove('show');
}}
function emptyBox(){{return '<div class="empty">当前聚合条件下暂无匹配新闻</div>'}}

function setSent(s){{ fSent = (fSent===s)?null:s; if(fSent) fStk=false; syncKpi(); render(); }}
function setStk(){{ fStk = !fStk; if(fStk) fSent=null; syncKpi(); render(); }}
function setSector(name){{
  fSector = (fSector===name)?null:name;
  ORDER.forEach(nm=>{{
    const el = document.getElementById('mc_'+nm);
    if(el) el.classList.toggle('on', nm===fSector);
  }});
  render();
}}
function resetFilter(){{ fSent=null; fSector=null; fStk=false; syncKpi();
  ORDER.forEach(nm=>{{const el=document.getElementById('mc_'+nm); if(el) el.classList.remove('on');}});
  render(); }}
function syncKpi(){{
  document.getElementById('kP').classList.toggle('on', fSent==='利好');
  document.getElementById('kF').classList.toggle('on', fSent==='利空');
  document.getElementById('kN').classList.toggle('on', fSent==='中性');
  document.getElementById('kStk').classList.toggle('on', fStk);
}}
function flashMenu(){{
  const mb = document.getElementById('menubar');
  mb.classList.add('flash'); mb.scrollIntoView({{behavior:'smooth', block:'nearest'}});
  setTimeout(()=>mb.classList.remove('flash'), 1200);
}}

function openDlg(i){{
  const n = DATA[i];
  const cls = n.sentiment==='利好'?'tag p':(n.sentiment==='利空'?'tag f':'tag');
  document.getElementById('dTitle').textContent = n.title;
  document.getElementById('dMeta').innerHTML =
    `<span class="${{cls}}">${{n.sentiment}}</span>` +
    `<span class="tag sec">${{ICON[n.sector]||'🌐'}} ${{esc(n.sector)}}</span>` +
    `<span>📅 ${{esc(n.date)}}</span><span>📮 ${{esc(n.source)}}</span>` +
    ((n.stocks&&n.stocks.length)?`<span>🏷️ ${{n.stocks.map(esc).join('、')}}</span>`:'');
  document.getElementById('dSum').textContent = n.summary || '（暂无正文摘要，点击下方链接查看原文）';
  const kws = (n.hits||[]).map(k=>`<span>${{esc(k)}}</span>`).join('');
  document.getElementById('dKw').innerHTML = kws ? '<b style="font-size:12px;color:#778">判定依据：</b>'+kws : '';
  const lk = document.getElementById('dLink');
  if(n.url){{ lk.href=n.url; lk.style.display='inline-block'; }} else lk.style.display='none';
  document.getElementById('mask').classList.add('show');
}}
function closeDlg(){{ document.getElementById('mask').classList.remove('show'); }}
document.addEventListener('keydown', e=>{{ if(e.key==='Escape') closeDlg(); }});

function tick(){{
  const left = Math.max(0, NEXT - Date.now());
  const m = Math.floor(left/60000), s = Math.floor(left%60000/1000);
  document.getElementById('cd').textContent = m + ':' + String(s).padStart(2,'0');
  if(left<=0) location.reload();
}}
setInterval(tick, 500); tick();
render();
</script>
</body></html>"""

# ==================== 入口 ====================
def run_once(out, refresh_sec=REFRESH_SEC):
    news = [classify(n) for n in fetch_news()]
    if not news:
        print("抓取失败：无新闻数据", file=sys.stderr); return 1
    ts = int(datetime.now().timestamp() * 1000)
    with open(out, "w", encoding="utf-8") as f:
        f.write(build_html(news, ts, refresh_sec))
    pos = sum(1 for n in news if n["sentiment"] == "利好")
    neg = sum(1 for n in news if n["sentiment"] == "利空")
    print(f"[{datetime.now():%H:%M:%S}] 刷新完成：{len(news)}条 | 利好{pos} 利空{neg} | 已写入 {out}")
    return 0

def main():
    ap = argparse.ArgumentParser(description="每日财经新闻看板刷新脚本")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出 HTML 路径（默认当前目录）")
    ap.add_argument("--loop", type=int, default=0, metavar="SEC",
                    help="常驻模式：每 SEC 秒自动刷新一次（如 600 = 10 分钟）；不传则单次刷新")
    ap.add_argument("--refresh-sec", type=int, default=REFRESH_SEC, metavar="SEC",
                    help="页面倒计时刷新周期（默认 600 秒），应与 --loop 一致")
    args = ap.parse_args()
    if args.loop > 0:
        print(f"常驻模式：每 {args.loop}s 刷新一次，输出 {args.out}（Ctrl+C 退出）")
        while True:
            run_once(args.out, args.refresh_sec)
            time.sleep(args.loop)
    else:
        sys.exit(run_once(args.out, args.refresh_sec))

if __name__ == "__main__":
    main()
