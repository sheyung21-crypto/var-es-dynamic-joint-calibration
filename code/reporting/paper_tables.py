"""Table specifications built from the archived result CSVs.

Values are copied from ../publication_zh_20261024/source_en/paper/tables/*.csv. Only the method
labels, the number of decimals shown for mean differences, and the minus sign are changed.
Each builder returns a dict: header (rows of (text, span)), body (rows of cells), align, size.
"""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "outputs/reproduced/table_sources"

ARM = {"A0": "EW", "A1": "EW+BCm", "A1d": "EW+BCd", "A2": "EW+DJC", "A3": "EW+YE",
       "A3f": "EW+YEf", "F": "EW+DJC-FIX", "C0": "MCS", "C1": "MCS+BCm", "C1d": "MCS+BCd",
       "C2": "MCS+DJC", "C3": "MCS+YE", "R0": "GJR"}
ARM_ORDER = ["A0", "A2", "F", "A1d", "A1", "A3", "A3f", "C0", "C2", "C1d", "C1", "C3", "R0"]
HYP = {"H1": ("A2", "A0"), "H2": ("A2", "A1d"), "H3": ("A2", "A3")}
M = "−"

T = {
    "zh": {
        "hyp": "假說", "cmp": "比較", "mean": "平均評分差", "ci": "95% 信賴區間",
        "p1": "單尾 p 值", "holm": "Holm p 值", "arm": "比較組", "block": "區塊長度",
        "lvl": "水準", "date": "起始日", "event": "事件", "state": "期間", "days": "日數",
        "hac": "HAC 95% 信賴區間", "group": "訊號組別", "range": "訊號範圍", "panel": "樣本",
        "raw": "p 值", "ind": "美國產業", "idx": "國際指數",
        "fz": "FZ0", "viol": "違反率", "l975": "97.5% 水準", "l99": "99% 水準",
        "app": "日圓急升期間", "other": "其他日子", "g": {"1": "低", "2": "中", "3": "高"},
        "code": "代號", "def": "定義",
        "events": {"1987-10-19": "黑色星期一", "1998-08-17": "俄羅斯債務危機",
                   "2001-09-17": "九一一事件後復市", "2008-09-15": "雷曼兄弟破產",
                   "2011-08-08": "美國主權評等調降", "2015-08-24": "全球股市急跌",
                   "2020-02-24": "新冠疫情爆發"},
        "arms": [
            ("EW", "十個基礎模型 VaR 與 ES 預測的等權組合（未校準）"),
            ("EW+DJC", "對 EW 套用本研究的 DJC"),
            ("EW+DJC-FIX", "對 EW 套用 DJC 的四個專家，權重固定為 1/4"),
            ("EW+BCd、EW+BCm", "對 EW 套用批次校準，分別每日及每 20 個交易日重新估計"),
            ("EW+YE、EW+YEf", "對 EW 套用改編的 Ye 型控制器，步長分別為 0.01 及 0.05"),
            ("MCS", "以 MCS 篩選後的等權組合（未校準）"),
            ("MCS+DJC、MCS+BCd、\nMCS+BCm、MCS+YE", "對 MCS 組合套用各校準方法"),
            ("GJR", "單一 GJR-GARCH-t 模型"),
        ],
    },
    "en": {
        "hyp": "Hyp.", "cmp": "Comparison", "mean": "Mean diff.", "ci": "95% CI",
        "p1": "One-sided $p$", "holm": "Holm $p$", "arm": "Method", "block": "Block",
        "lvl": "Level", "date": "Start date", "event": "Event", "state": "Period", "days": "Days",
        "hac": "HAC 95% CI", "group": "Signal group", "range": "Signal range", "panel": "Sample",
        "raw": "$p$", "ind": "US industries", "idx": "Intl. indices",
        "fz": "FZ0", "viol": "Violations", "l975": "97.5% level", "l99": "99% level",
        "app": "Sharp appreciation", "other": "Other days",
        "g": {"1": "Low", "2": "Middle", "3": "High"},
        "code": "Label", "def": "Definition",
        "events": {"1987-10-19": "Black Monday", "1998-08-17": "Russian default",
                   "2001-09-17": "Reopening after 9/11", "2008-09-15": "Lehman bankruptcy",
                   "2011-08-08": "US rating downgrade", "2015-08-24": "Global sell-off",
                   "2020-02-24": "COVID-19 outbreak"},
        "arms": [
            ("EW", "Equal-weight combination of the ten base VaR and ES forecasts (uncalibrated)"),
            ("EW+DJC", "DJC applied to EW"),
            ("EW+DJC-FIX", "The four DJC experts applied to EW, with weights fixed at 1/4"),
            ("EW+BCd, EW+BCm", "Batch calibration of EW, re-estimated daily or every 20 trading days"),
            ("EW+YE, EW+YEf", "Adapted Ye-type controller on EW, with step size 0.01 or 0.05"),
            ("MCS", "Equal-weight combination after MCS selection (uncalibrated)"),
            ("MCS+DJC, MCS+BCd,\nMCS+BCm, MCS+YE", "Each calibration method applied to the MCS combination"),
            ("GJR", "Single GJR-GARCH-t model"),
        ],
    },
}


def rows(name):
    with open(SRC / f"{name}.csv", encoding="utf-8") as f:
        return list(csv.reader(f))[1:]


def num(s, nd=None):
    s = s.strip()
    if s in ("--", ""):
        return "–"
    if nd is not None:
        s = f"{float(s):.{nd}f}"
    return s.replace("-", M)


def ci(s):
    return s.replace("-", M)


def contrast(code):
    a, b = code.split("--")
    return f"{ARM[a]} {M} {ARM[b]}"


def level(s):
    return s.replace("\\%", "%")


def spec(header, body, align, size=20):
    if header and isinstance(header[0], str):
        header = [[(h, 1) for h in header]]
    return {"header": header, "body": body, "align": align, "size": size}


def arms(lang):
    t = T[lang]
    return spec([t["code"], t["def"]], [[a, b] for a, b in t["arms"]], "ll")


def primary(lang):
    t = T[lang]
    body = [[r[0], contrast(r[1]), num(r[2], 4), ci(r[3]), num(r[4]), num(r[5])] for r in rows("study1_primary")]
    return spec([t["hyp"], t["cmp"], t["mean"], t["ci"], t["p1"], t["holm"]], body, "llrcrr")


def metrics(name, lang):
    t = T[lang]
    data = {r[0]: r for r in rows(name)}
    body = [[ARM[c]] + [num(x) for x in data[c][1:]] for c in ARM_ORDER]
    header = [[("", 1), (t["l975"], 3), (t["l99"], 3)],
              [(t["arm"], 1), (t["fz"], 1), (t["viol"], 1), ("$Z_2$", 1), (t["fz"], 1), (t["viol"], 1), ("$Z_2$", 1)]]
    return spec(header, body, "lrrrrrr")


def secondary(lang):
    t = T[lang]
    order = ["A2--F", "A2--A1", "A2--A3f", "A2--R0", "C0--A0", "C2--C0", "C2--A2", "C1d--A1d", "C3--A3"]
    data = {r[0]: r for r in rows("study1_secondary")}
    body = [[contrast(c), num(data[c][1], 4), ci(data[c][2])] for c in order]
    return spec([t["cmp"], t["mean"], t["ci"]], body, "lrc")


def crisis(lang):
    t = T[lang]
    body = [[r[0], t["events"][r[0]], num(r[1]), num(r[2]), num(r[3])] for r in rows("study1_crisis")]
    return spec([t["date"], t["event"], "EW", "EW+DJC", f"EW+DJC {M} EW"], body, "llrrr")


def robustness(lang):
    t = T[lang]
    body = []
    for r in rows("study1_robustness"):
        a, b = HYP[r[0]]
        body.append([r[0], f"{ARM[a]} {M} {ARM[b]}", r[1], num(r[2], 4), ci(r[3]), num(r[4])])
    return spec([t["hyp"], t["cmp"], t["block"], t["mean"], t["ci"], t["p1"]], body, "llrrcr")


def secondary99(lang):
    t = T[lang]
    body = []
    for r in rows("study1_secondary99"):
        a, b = HYP[r[2]]
        panel = t["ind"] if r[0] == "industries" else t["idx"]
        body.append([panel, level(r[1]), r[2], f"{ARM[a]} {M} {ARM[b]}", num(r[3]), ci(r[4]), num(r[5]), num(r[6])])
    return spec([t["panel"], t["lvl"], t["hyp"], t["cmp"], t["mean"], t["ci"], t["raw"], t["holm"]],
                body, "llllrcrr", size=18)


def yen_tests(lang):
    t = T[lang]
    body = [[level(r[0]), f"{float(r[1]):g}", num(r[2], 4), ci(r[3]), num(r[4])] for r in rows("study2_tests")]
    return spec([t["lvl"], t["block"], t["mean"], t["ci"], t["p1"]], body, "lrrcr")


def yen_comparators(lang):
    t = T[lang]
    body = [[level(r[0]), f"EW+DJC {M} {ARM[r[1]]}", num(r[2], 4), ci(r[3])] for r in rows("study2_comparators")]
    return spec([t["lvl"], t["cmp"], t["mean"], t["ci"]], body, "llrc")


def yen_appreciation(lang):
    t = T[lang]
    body = [[level(r[0]), t["app"] if r[1].startswith("Sharp") else t["other"], f"{int(r[2]):,}",
             num(r[3], 4), ci(r[4])] for r in rows("study2_appreciation")]
    return spec([t["lvl"], t["state"], t["days"], t["mean"], t["hac"]], body, "llrrc")


def yen_tertiles(lang):
    t = T[lang]
    body = [[level(r[0]), t["g"][r[1]], f"{int(r[2]):,}", ci(r[3]), num(r[4], 4), ci(r[5])]
            for r in rows("study2_tertiles")]
    return spec([t["lvl"], t["group"], t["days"], t["range"], t["mean"], t["hac"]], body, "llrcrc")


def yen_crisis(lang):
    t = T[lang]
    data = sorted(rows("study2_crisis"), key=lambda r: (r[0] != "97.5\\%", r[1]))
    body = [[level(r[0]), r[1], t["events"][r[1]], num(r[2]), num(r[3]), num(r[4])] for r in data]
    return spec([t["lvl"], t["date"], t["event"], "EW", "EW+DJC", f"EW+DJC {M} EW"], body, "lllrrr")


BUILDERS = {
    "arms": arms,
    "primary": primary,
    "metrics_us": lambda lang: metrics("study1_metrics", lang),
    "secondary": secondary,
    "crisis_us": crisis,
    "robustness": robustness,
    "secondary99": secondary99,
    "yen_tests": yen_tests,
    "yen_comparators": yen_comparators,
    "yen_appreciation": yen_appreciation,
    "yen_tertiles": yen_tertiles,
    "metrics_yen": lambda lang: metrics("study2_allarms", lang),
    "crisis_yen": yen_crisis,
}


def table(name, lang):
    return BUILDERS[name](lang)
