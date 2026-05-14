"""
Tiger CS Dashboard — Processador de dados
==========================================
Lê os CSVs exportados do Freshdesk e atualiza o DATA_FD e MORNING_DATA no dashboard HTML.

Uso:
    python scripts/process.py

Espera encontrar em data/:
    - freshdesk_AGENTE.csv  (um por agente, exportado individualmente)
    - morning_brief.csv     (exportação geral para o morning brief)

Todos são opcionais — o script atualiza só o que encontrar.
"""

import os, re, json, glob
from datetime import datetime, date, timedelta
import pandas as pd

# ── Configurações ──────────────────────────────────────────────────────────────
HTML_PATH   = "index.html"
DATA_DIR    = "data"
CUTOFF_FORMS = "2026-05-08"   # DATA (formulário) só até essa data

AGENTS_MAP = {
    "Neythan Cauã":    "Neythan",
    "Yasmim Sobral":   "Yasmin",
    "Heitor Ribeiro":  "Heitor",
    "Natália Alencar": "Natália",
}
TARGET = ["Heitor", "Natália", "Neythan", "Yasmin"]

PROD_NORM = {
    "glucorecover": "GlucoRecover", "nervolyn": "NervoLyn",
    "audileaf": "AudiLeaf", "visiumPro": "VisiumPro", "visium pro": "VisiumPro",
    "prostafense": "ProstaFense", "lipovive": "Lipovive", "marobrain": "MaroBrain",
    "vigorlong": "VigorLong", "reduburn": "ReduBurn", "boosterxt": "BoosterXT",
    "oatzem": "Oatzem",
}

OPEN_STATUSES = ["Open", "Pending", "Waiting on Customer", "Waiting on Third Party"]

# ── Helpers ────────────────────────────────────────────────────────────────────
def norm_prod(p):
    s = str(p).split(" + ")[0].strip()
    return PROD_NORM.get(s.lower(), s)

def parse_val(v):
    nums = re.findall(r"[\d]+\.?\d*", str(v).replace(",", "."))
    return float(nums[0]) if nums else 0.0

def safe_int(v):
    try: return int(v)
    except: return 0

def empty_agent():
    return dict(tickets=0, fechados=0, abertos=0, interacoes_agente=0,
                interacoes_cliente=0, valor_total=0.0, upsell=0,
                status={}, tipo={}, prioridade={}, produtos={},
                motivos={}, resultado={}, tier={})

def dict_count(series):
    return {k: int(v) for k, v in series.dropna().value_counts().items()}

def add_dicts(a, b):
    r = dict(a)
    for k, v in b.items():
        r[k] = r.get(k, 0) + v
    return r

# ── Load CSVs ──────────────────────────────────────────────────────────────────
def load_freshdesk_csvs():
    """Load all freshdesk_*.csv files from data/ directory."""
    dfs = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "freshdesk_*.csv"))):
        try:
            df = pd.read_csv(path)
            df["ag"] = df["Agente"].map(AGENTS_MAP)
            dfs.append(df)
            print(f"  ✓ {os.path.basename(path)} ({len(df)} rows)")
        except Exception as e:
            print(f"  ✗ {os.path.basename(path)}: {e}")
    if not dfs:
        return None
    df_all = pd.concat(dfs, ignore_index=True)
    df_all["data"] = pd.to_datetime(df_all["Hora da criação"], errors="coerce").dt.strftime("%Y-%m-%d")
    df_all["criado_dt"] = pd.to_datetime(df_all["Hora da criação"], errors="coerce")
    df_all["data_cri"] = df_all["criado_dt"].dt.strftime("%Y-%m-%d")
    df_all["hora_cri"] = df_all["criado_dt"].dt.hour
    df_all["valor_num"] = df_all["Valor total"].apply(parse_val) if "Valor total" in df_all.columns else 0.0
    df_all["int_ag"] = pd.to_numeric(df_all.get("Interações do agente", 0), errors="coerce").fillna(0)
    df_all["int_cl"] = pd.to_numeric(df_all.get("Interações do cliente", 0), errors="coerce").fillna(0)
    return df_all

# ── Build DATA_FD ──────────────────────────────────────────────────────────────
def build_agent_day(grp, ag):
    g = grp[grp["ag"] == ag]
    if len(g) == 0:
        return empty_agent()
    prods = {}
    if "Nome do produto" in g.columns:
        for p in g["Nome do produto"].dropna():
            nm = norm_prod(p)
            if nm and nm not in ("nan", "None", ""):
                prods[nm] = prods.get(nm, 0) + 1
    return {
        "tickets":            len(g),
        "fechados":           int(g["Status"].isin(["Closed", "Resolved"]).sum()),
        "abertos":            int(g["Status"].isin(OPEN_STATUSES).sum()),
        "status":             dict_count(g["Status"]),
        "tipo":               dict_count(g["Tipo"]) if "Tipo" in g.columns else {},
        "prioridade":         dict_count(g["Prioridade"]),
        "interacoes_agente":  int(g["int_ag"].sum()),
        "interacoes_cliente": int(g["int_cl"].sum()),
        "produtos":           prods,
        "plataforma":         dict_count(g["Plataforma"]) if "Plataforma" in g.columns else {},
        "valor_total":        round(float(g["valor_num"].sum()), 2),
        "motivos":            dict_count(g["Motivo da Solicitação"]) if "Motivo da Solicitação" in g.columns else {},
        "resultado":          dict_count(g["Resultado"]) if "Resultado" in g.columns else {},
        "tier":               dict_count(g["Tier do cliente"]) if "Tier do cliente" in g.columns else {},
        "upsell":             int(g["Tem upsell"].eq("Sim").sum()) if "Tem upsell" in g.columns else 0,
    }

def build_day_entry(grp):
    entry = {ag: build_agent_day(grp, ag) for ag in TARGET}
    totals = {
        "tickets":           sum(entry[ag]["tickets"] for ag in TARGET),
        "fechados":          sum(entry[ag]["fechados"] for ag in TARGET),
        "abertos":           sum(entry[ag]["abertos"] for ag in TARGET),
        "valor_total":       round(sum(entry[ag]["valor_total"] for ag in TARGET), 2),
        "interacoes_agente": sum(entry[ag]["interacoes_agente"] for ag in TARGET),
    }
    for field, key in [("status","_status"),("tipo","_tipo"),("prioridade","_prioridade"),
                       ("produtos","_produtos"),("motivos","_motivos"),("resultado","_resultado"),("tier","_tier")]:
        agg = {}
        for ag in TARGET:
            agg = add_dicts(agg, entry[ag].get(field, {}))
        entry[key] = agg
    entry["_totals"] = totals
    return entry

def build_total(data_fd):
    day_keys = [k for k in data_fd if re.match(r"^\d{4}-\d{2}-\d{2}$", k)]
    totals = {"tickets":0,"fechados":0,"abertos":0,"valor_total":0.0,"interacoes_agente":0}
    agg    = {ag: empty_agent() for ag in TARGET}
    subs   = {k:{} for k in ["_status","_tipo","_prioridade","_produtos","_motivos","_resultado","_tier"]}
    for dk in day_keys:
        e = data_fd[dk]
        t = e.get("_totals", {})
        for f in ["tickets","fechados","abertos","interacoes_agente"]:
            totals[f] += t.get(f, 0)
        totals["valor_total"] += t.get("valor_total", 0)
        for ag in TARGET:
            a = e.get(ag, {})
            if not a.get("tickets"): continue
            for f in ["tickets","fechados","abertos","interacoes_agente","interacoes_cliente","upsell"]:
                agg[ag][f] = agg[ag].get(f, 0) + (a.get(f) or 0)
            agg[ag]["valor_total"] = agg[ag].get("valor_total", 0) + (a.get("valor_total") or 0)
            for sub in ["status","tipo","prioridade","produtos","motivos","resultado","tier"]:
                agg[ag][sub] = add_dicts(agg[ag].get(sub,{}), a.get(sub,{}))
        for sub, key in [("status","_status"),("tipo","_tipo"),("prioridade","_prioridade"),
                         ("produtos","_produtos"),("motivos","_motivos"),("resultado","_resultado"),("tier","_tier")]:
            subs[key] = add_dicts(subs[key], e.get(key, {}))
    totals["valor_total"] = round(totals["valor_total"], 2)
    r = dict(agg); r["_totals"] = totals; r.update(subs)
    return r

def process_freshdesk(df_all):
    data_fd = {}
    for dt in sorted(df_all["data"].dropna().unique()):
        grp = df_all[df_all["data"] == dt]
        data_fd[dt] = build_day_entry(grp)
    data_fd["total"] = build_total(data_fd)
    return data_fd

# ── Build MORNING_DATA ─────────────────────────────────────────────────────────
def build_morning(df_all):
    today_str = date.today().strftime("%Y-%m-%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    all_open = df_all[df_all["ag"].isin(TARGET) & df_all["Status"].isin(OPEN_STATUSES)].copy()

    def classify(row):
        if row["data_cri"] == today_str:           return "hoje"
        if row["data_cri"] == yesterday_str and row["hora_cri"] >= 17: return "pos17h_ontem"
        return "retroativo"

    all_open["categoria"] = all_open.apply(classify, axis=1)

    agents = {}
    for ag in TARGET:
        g = all_open[all_open["ag"] == ag]
        agents[ag] = {
            "total_abertos": len(g),
            "criados_hoje":  int((g["categoria"] == "hoje").sum()),
            "pos17h_ontem":  int((g["categoria"] == "pos17h_ontem").sum()),
            "retroativos":   int((g["categoria"] == "retroativo").sum()),
            "status":        dict_count(g["Status"]),
            "prioridade":    dict_count(g["Prioridade"]),
        }

    produtos = {}
    if "Nome do produto" in all_open.columns:
        for p in all_open["Nome do produto"].dropna():
            nm = norm_prod(p)
            if nm and nm not in ("nan","None",""): produtos[nm] = produtos.get(nm,0)+1

    now = datetime.now()
    return {
        "date":             today_str,
        "hora_exportacao":  now.strftime("%H:%M"),
        "totals": {
            "total_abertos": len(all_open),
            "criados_hoje":  int((all_open["categoria"]=="hoje").sum()),
            "pos17h_ontem":  int((all_open["categoria"]=="pos17h_ontem").sum()),
            "retroativos":   int((all_open["categoria"]=="retroativo").sum()),
        },
        "agents":   agents,
        "produtos": produtos,
    }

# ── Inject into HTML ───────────────────────────────────────────────────────────
def inject_js_var(html, var_name, data):
    """Replace const VAR_NAME = {...}; in html."""
    new_val = json.dumps(data, ensure_ascii=False)
    pattern = rf"(const {var_name} = )\{{.*?\}};"
    replacement = rf"const {var_name} = {new_val};"
    new_html, n = re.subn(pattern, replacement, html, flags=re.DOTALL)
    if n == 0:
        print(f"  ⚠️  {var_name} not found in HTML")
    else:
        print(f"  ✓  {var_name} updated")
    return new_html

def update_topbar(html, data_fd):
    day_keys = sorted(k for k in data_fd if re.match(r"^\d{4}-\d{2}-\d{2}$", k))
    if not day_keys: return html
    start = datetime.strptime(day_keys[0], "%Y-%m-%d").strftime("%d/%m")
    end   = datetime.strptime(day_keys[-1], "%Y-%m-%d").strftime("%d/%m/%Y")
    new_sub = f"Dados: {start}–{end} · Freshdesk"
    return re.sub(r"Dados: .*?· Freshdesk", new_sub, html)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n🐯 Tiger CS Dashboard — Processando dados...\n")

    if not os.path.exists(HTML_PATH):
        print(f"❌ {HTML_PATH} não encontrado. Execute a partir da raiz do repositório.")
        return

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Load Freshdesk CSVs
    print("📂 Carregando CSVs do Freshdesk...")
    df_all = load_freshdesk_csvs()
    if df_all is None:
        print("  ⚠️  Nenhum CSV encontrado em data/freshdesk_*.csv — pulando DATA_FD e MORNING_DATA")
    else:
        print(f"  Total: {len(df_all)} registros | {df_all['data'].nunique()} dias")

        # 2. Process DATA_FD
        print("\n📊 Processando DATA_FD (Freshdesk)...")
        data_fd = process_freshdesk(df_all)
        html = inject_js_var(html, "DATA_FD", data_fd)
        html = update_topbar(html, data_fd)

        # 3. Process MORNING_DATA
        print("\n🌅 Processando MORNING_DATA...")
        morning = build_morning(df_all)
        html = inject_js_var(html, "MORNING_DATA", morning)

        print(f"\n  Fila atual: {morning['totals']['total_abertos']} abertos")
        for ag in TARGET:
            print(f"    {ag}: {morning['agents'][ag]['total_abertos']}")

    # 4. Save
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ {HTML_PATH} atualizado com sucesso!")
    print("   Commit e push para o GitHub Pages atualizar automaticamente.\n")

if __name__ == "__main__":
    main()
