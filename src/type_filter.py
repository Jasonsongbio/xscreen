"""候选类型过滤：识别 receptor/enzyme/drug/metabolite/noise（type_error）。

xscreen 的目标是辅助筛选信号分子（neuropeptide/biogenic amine/peptide hormone）
用于后续湿实验。受体、酶、药物、非信号代谢物、序列碎片对候选筛选无意义，
应从排名中过滤掉。

本模块是 src/ 与 tools/ 的共享分类逻辑（DRY 单一来源）：
- src/score.py 用 is_type_error() 在排名前过滤候选
- tools/uniprot_validation.py 用各 is_*() 做客观分类

注意：is_type_error 只识别"明确不是信号分子"的候选（保守策略）。
plausible_novel（潜在新发现）不在此类，全部保留让用户判断。
"""
import re

# 已知 biogenic amine / classical neurotransmitter（xscreen scope 内合法）
# 作为白名单优先于 is_noise()，防止 5-HT（数字开头+连字符）被误判为序列碎片。
KNOWN_AMINES = {
    "dopamine", "octopamine", "serotonin", "tyramine", "histamine",
    "GABA", "glutamate", "acetylcholine", "adrenaline", "noradrenaline",
    "5-HT", "5-HTP", "epinephrine", "norepinephrine", "melatonin",
}


def is_receptor(name: str) -> bool:
    """受体检测：显式词、-R/-HR 缩写后缀、5-HT/D/Am 受体亚型命名。"""
    n = name.strip()
    if re.search(r"receptor", n, re.IGNORECASE):
        return True
    # 5-HT 受体亚型：5-HT1A/2B/7 等（但 5-HT 本体和 5-HTP 前体不算）
    if re.match(r"^5-?HT\d", n, re.IGNORECASE) and n.upper() not in ("5-HTP",):
        return True
    # 多巴胺受体：D1R/D2R/Dop1R/Dop2R 等
    if re.match(r"^(D[1-5]R|Dop\dR|Amdop\d|Dop1R1)", n, re.IGNORECASE):
        return True
    # 物种前缀受体基因名：Amoa/Amtyr/Amdop/AalRh/NPYLR/Dar-/Grl
    if re.match(r"^(Amoa\d|Amtyr\d|Amdop\d|AalRh\d|NPYLR\d|Dar-\d|Grl\dHM|5HT\dR)", n, re.IGNORECASE):
        return True
    # -R / -HR 结尾缩写（AKHR, NPFR, CCHa2-R, SKR, TRPR, DHR, ACPR）
    # 肽本身不以 R 结尾（NPF=F, AKH=H, sNPF=F），所以以 R 结尾大概率是受体
    if re.search(r"[A-Za-z0-9]-?R[KL]?$", n) and len(n) >= 3:
        return True
    return False


def is_enzyme(name: str) -> bool:
    """酶检测：-ase 后缀 + 已知酶缩写。"""
    n = name.strip()
    if re.search(r"-ase$|kinase$|synthase|synthetase|peptidase|carboxypeptid|convertase|phosphatase|oxidase|dehydrogenase|transferase",
                 n, re.IGNORECASE):
        return True
    # 已知酶缩写
    if n.upper() in ("ACE", "Ddc", "Tdc", "Tbh", "PAH", "TH"):
        return True
    return False


def is_drug(name: str) -> bool:
    """药物检测：硬编码药物清单。"""
    drugs = ["flupenthixol", "chlorpromazine", "reserpine", "amphetamine", "cocaine",
             "methiothepin", "mianserin", "ketanserin", "6,7-ADTN", "8-OH-DPAT",
             "quinpirole", "haloperidol", "clozapine", "imipramine"]
    return any(d.lower() in name.lower() for d in drugs)


def is_metabolite(name: str) -> bool:
    """非信号分子的代谢物。"""
    nonsignal = ["trehalose", "glucose", "glycogen", "ATP", "cAMP", "IP3",
                 "nitric oxide", "lactate", "pyruvate", "fructose", "glycerol"]
    return any(n.lower() == name.lower() or n.lower() in name.lower() for n in nonsignal)


def is_noise(name: str) -> bool:
    """序列碎片 / 非命名实体。"""
    n = name.strip()
    # 纯数字或带括号的序列碎片
    if re.match(r"^\d", n) and re.search(r"\[|\(|-", n):
        return True
    # 太长的序列串（>25 字符且无空格，可能是肽序列）
    if len(n) > 25 and " " not in n and "-" not in n:
        return True
    # 基因符号格式（如 CG1234）但不是肽
    if re.match(r"^CG\d+$", n):
        return True
    return False


def is_type_error(name: str) -> bool:
    """聚合判断：候选是否为 type_error（receptor/enzyme/drug/metabolite/noise）。

    已知胺白名单优先，防止 5-HT/5-HTP 被 is_noise 误捕
    （5-HT 以数字开头+连字符，匹配 is_noise 的序列碎片规则）。

    返回 True = 应从排名过滤（不是用户要的信号分子）。
    返回 False = 合法候选（肽/胺/肽激素/ plausible_novel），保留。
    """
    n = name.strip()
    if n.upper() in {a.upper() for a in KNOWN_AMINES}:
        return False
    return (is_receptor(n) or is_enzyme(n) or is_drug(n)
            or is_metabolite(n) or is_noise(n))
