"""
Tiger CS Dashboard — Atualizador automático
===========================================
Rode este script todo dia às 20h no seu computador Windows.
Ele puxa os dados do Freshdesk e atualiza o dashboard automaticamente.

Requisitos:
    pip install requests pandas

Como usar:
    1. Coloque este arquivo na mesma pasta que o index.html
    2. Clique duas vezes em atualizar_dashboard.bat
    OU
    3. python atualizar_dashboard.py
"""

import requests, base64, json, re, os, sys
from datetime import date, timedelta, datetime
import pandas as pd

# ── Configurações ──────────────────────────────────────────────────────────────
API_KEY  = '0DbVDZ4HHrcU-GZTYVAw'
DOMAIN   = 'tigeroffers-support.freshdesk.com'
HTML_PATH = os.path.join(os.path.dirname(__file__), 'index.html')

AGENTS_MAP = {
    'Neythan Cauã':    'Neythan',
    'Yasmim Sobral':   'Yasmin',
    'Heitor Ribeiro':  'Heitor',
    'Natália Alencar': 'Natália',
}
TARGET = ['Heitor', 'Natália', 'Neythan', 'Yasmin']

PROD_NORM = {
    'glucorecover':'GlucoRecover','gluco recover':'GlucoRecover',
    'nervolyn':'NervoLyn','audileaf':'AudiLeaf',
    'visium pro':'VisiumPro','visiumpro':'VisiumPro',
    'prostafense':'ProstaFense','lipovive':'Lipovive',
    'marobrain':'MaroBrain','vigorlong':'VigorLong',
    'reduburn':'ReduBurn','boosterxt':'BoosterXT','oatzem':'Oatzem',
}

OPEN_STATUSES = [2, 3, 6, 7]  # open, pending, waiting on customer, waiting on third party
STATUS_NAMES  = {2:'Open', 3:'Pending', 4:'Resolved', 5:'Closed', 6:'Waiting on Customer', 7:'Waiting on Third Party'}
PRIORITY_NAMES = {1:'Low', 2:'Medium', 3:'High', 4:'Urgent'}

# ── API helpers ────────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.auth = (API_KEY, 'X')
SESSION.headers.update({'Content-Type': 'application/json'})
BASE = f'https://{DOMAIN}/api/v2'

def api(path, params=None):
    r = SESSION.get(f'{BASE}/{path}', params=params)
    r.raise_for_status()
    return r.json()

def all_pages(path, params=None, max_pages=10):
    params = params or {}
    params['per_page'] = 100
    results = []
    for page in range(1, max_pages + 1):
        params['page'] = page
        data = api(path, params)
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
    return results

# ── Helpers ────────────────────────────────────────────────────────────────────
def norm_prod(p):
    s = str(p).split(' + ')[0].strip()
    r = PROD_NORM.get(s.lower(), s)
    return None if r in ('nan', 'None', '') else r

def dict_count(lst):
    out = {}
    for v in lst:
        if v: out[v] = out.get(v, 0) + 1
    return out

def empty_agent():
    return dict(tickets_criados=0, tickets_trabalhados=0, fechados=0, abertos=0,
                interacoes_agente=0, interacoes_cliente=0, valor_total=0.0, upsell=0,
                resolvidos_atividade=0, reabertos_atividade=0, notas_privadas=0,
                status={}, tipo={}, prioridade={}, produtos={}, motivos={}, resultado={}, tier={})

def add_dicts(a, b):
    r = dict(a)
    for k, v in b.items(): r[k] = r.get(k, 0) + v
    return r

# ── Fetch tickets ──────────────────────────────────────────────────────────────
def get_agent_ids():
    """Returns {freshdesk_id: normalized_name}"""
    agents = all_pages('agents')
    result = {}
    for a in agents:
        name = a['contact']['name']
        norm = AGENTS_MAP.get(name)
        if norm:
            result[a['id']] = norm
    print(f"  Agentes encontrados: {result}")
    return result

def fetch_tickets_updated_on(date_str, agent_ids):
    """Fetch all tickets updated on a given date, filter by our agents."""
    tickets = all_pages('tickets', {
        'updated_since': f'{date_str}T00:00:00Z',
        'order_by': 'updated_at',
        'order_type': 'asc',
    })
    # filter to only today
    day_tickets = [t for t in tickets
                   if t.get('updated_at', '').startswith(date_str)
                   and t.get('responder_id') in agent_ids]
    return day_tickets

def fetch_tickets_created_on(date_str, agent_ids):
    """Fetch tickets created on a given date by our agents."""
    tickets = all_pages('tickets', {
        'created_since': f'{date_str}T00:00:00Z',
    })
    return [t for t in tickets
            if t.get('created_at', '').startswith(date_str)
            and t.get('responder_id') in agent_ids]

# ── Build day entry ────────────────────────────────────────────────────────────
def build_day_entry(date_str, agent_ids):
    print(f"  Buscando tickets criados em {date_str}...")
    cri_all  = fetch_tickets_created_on(date_str, agent_ids)
    print(f"  Buscando tickets trabalhados em {date_str}...")
    trab_all = fetch_tickets_updated_on(date_str, agent_ids)

    entry = {}
    for ag_id, ag_name in agent_ids.items():
        g_cri  = [t for t in cri_all  if t.get('responder_id') == ag_id]
        g_trab = [t for t in trab_all if t.get('responder_id') == ag_id]

        prods = {}
        for t in g_cri:
            cf = t.get('custom_fields', {})
            p = cf.get('cf_nome_do_produto') or cf.get('cf_product_name') or ''
            nm = norm_prod(p)
            if nm: prods[nm] = prods.get(nm, 0) + 1

        status_list   = [STATUS_NAMES.get(t['status'], str(t['status'])) for t in g_trab]
        prio_list     = [PRIORITY_NAMES.get(t['priority'], str(t['priority'])) for t in g_trab]
        motivo_list   = [t.get('custom_fields', {}).get('cf_motivo_da_solicitacao','') for t in g_cri]
        resultado_list= [t.get('custom_fields', {}).get('cf_resultado','') for t in g_trab]
        tier_list     = [t.get('custom_fields', {}).get('cf_tier_do_cliente','') for t in g_cri]
        tipo_list     = [t.get('type','') for t in g_trab]

        open_list = ['Open','Pending','Waiting on Customer','Waiting on Third Party']
        closed_list = ['Closed','Resolved']

        valor = sum(float(re.findall(r'[\d.]+', str(t.get('custom_fields',{}).get('cf_valor_total','0') or '0'))[0] or 0)
                    for t in g_cri if re.findall(r'[\d.]+', str(t.get('custom_fields',{}).get('cf_valor_total','0') or '0')))

        entry[ag_name] = {
            'tickets_criados':    len(g_cri),
            'tickets_trabalhados':len(g_trab),
            'fechados':           sum(1 for s in status_list if s in closed_list),
            'abertos':            sum(1 for s in status_list if s in open_list),
            'status':             dict_count(status_list),
            'tipo':               {k:v for k,v in dict_count(tipo_list).items() if k},
            'prioridade':         dict_count(prio_list),
            'produtos':           prods,
            'valor_total':        round(valor, 2),
            'motivos':            {k:v for k,v in dict_count(motivo_list).items() if k},
            'resultado':          {k:v for k,v in dict_count(resultado_list).items() if k},
            'tier':               {k:v for k,v in dict_count(tier_list).items() if k},
            'interacoes_agente':  0,
            'interacoes_cliente': 0,
            'resolvidos_atividade': 0,
            'reabertos_atividade':  0,
            'notas_privadas':       0,
            'upsell':               0,
        }

    # Aggregate subs
    subs = {}
    for field, key in [('status','_status'),('tipo','_tipo'),('prioridade','_prioridade'),
                       ('produtos','_produtos'),('motivos','_motivos'),('resultado','_resultado'),('tier','_tier')]:
        agg = {}
        for ag in TARGET:
            agg = add_dicts(agg, entry.get(ag, {}).get(field, {}))
        subs[key] = agg

    entry['_totals'] = {
        'tickets_criados':    sum(entry.get(ag,{}).get('tickets_criados',0) for ag in TARGET),
        'tickets_trabalhados':sum(entry.get(ag,{}).get('tickets_trabalhados',0) for ag in TARGET),
        'fechados':           sum(entry.get(ag,{}).get('fechados',0) for ag in TARGET),
        'abertos':            sum(entry.get(ag,{}).get('abertos',0) for ag in TARGET),
        'valor_total':        round(sum(entry.get(ag,{}).get('valor_total',0) for ag in TARGET), 2),
        'interacoes_agente':  0,
        'resolvidos_atividade': 0,
        'reabertos_atividade':  0,
        'notas_privadas':       0,
    }
    entry.update(subs)
    return entry

# ── Build Morning Brief ────────────────────────────────────────────────────────
def build_morning(agent_ids):
    today     = date.today().strftime('%Y-%m-%d')
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

    print("  Buscando tickets abertos...")
    open_tickets = all_pages('tickets', {'filter': 'open'})
    open_tickets += all_pages('tickets', {'filter': 'pending'})

    def classify(t):
        cri = t.get('created_at','')[:10]
        cri_h = int(t.get('created_at','T00')[11:13])
        if cri == today: return 'hoje'
        if cri == yesterday and cri_h >= 17: return 'pos17h_ontem'
        return 'retroativo'

    agents_data = {}
    all_open = [t for t in open_tickets if t.get('responder_id') in agent_ids]

    for ag_id, ag_name in agent_ids.items():
        g = [t for t in all_open if t.get('responder_id') == ag_id]
        cats = [classify(t) for t in g]
        prios = [PRIORITY_NAMES.get(t['priority'], '') for t in g]
        stats = [STATUS_NAMES.get(t['status'], '') for t in g]

        prods = {}
        for t in g:
            p = norm_prod(t.get('custom_fields',{}).get('cf_nome_do_produto',''))
            if p: prods[p] = prods.get(p,0)+1

        agents_data[ag_name] = {
            'total_abertos': len(g),
            'criados_hoje':  cats.count('hoje'),
            'pos17h_ontem':  cats.count('pos17h_ontem'),
            'retroativos':   cats.count('retroativo'),
            'status':        dict_count(stats),
            'prioridade':    dict_count(prios),
        }

    all_cats = [classify(t) for t in all_open]
    prod_all = {}
    for t in all_open:
        p = norm_prod(t.get('custom_fields',{}).get('cf_nome_do_produto',''))
        if p: prod_all[p] = prod_all.get(p,0)+1

    return {
        'date': today,
        'hora_exportacao': datetime.now().strftime('%H:%M'),
        'totals': {
            'total_abertos': len(all_open),
            'criados_hoje':  all_cats.count('hoje'),
            'pos17h_ontem':  all_cats.count('pos17h_ontem'),
            'retroativos':   all_cats.count('retroativo'),
        },
        'agents':   agents_data,
        'produtos': dict(sorted(prod_all.items(), key=lambda x: -x[1])),
    }

# ── Inject into HTML ───────────────────────────────────────────────────────────
def inject(html, var_name, data):
    new_val = json.dumps(data, ensure_ascii=False)
    new_html, n = re.subn(rf'(const {var_name} = )\{{.*?\}};',
                          f'const {var_name} = {new_val};', html, flags=re.DOTALL)
    print(f"  {'✓' if n else '✗'} {var_name} {'atualizado' if n else 'NÃO encontrado'}")
    return new_html

def rebuild_total(fd):
    day_keys = sorted(k for k in fd if re.match(r'^\d{4}-\d{2}-\d{2}$', k))
    tot = {'tickets_criados':0,'tickets_trabalhados':0,'fechados':0,'abertos':0,
           'valor_total':0.0,'interacoes_agente':0,'resolvidos_atividade':0,
           'reabertos_atividade':0,'notas_privadas':0}
    agg  = {ag: empty_agent() for ag in TARGET}
    subs = {k:{} for k in ['_status','_tipo','_prioridade','_produtos','_motivos','_resultado','_tier']}
    for dk in day_keys:
        e = fd[dk]; t = e.get('_totals', {})
        for f in tot: tot[f] = tot.get(f,0) + (t.get(f) or 0)
        for ag in TARGET:
            a = e.get(ag, {})
            for f in ['tickets_criados','tickets_trabalhados','fechados','abertos',
                      'interacoes_agente','interacoes_cliente','upsell',
                      'resolvidos_atividade','reabertos_atividade','notas_privadas']:
                agg[ag][f] = agg[ag].get(f,0) + (a.get(f) or 0)
            agg[ag]['valor_total'] = agg[ag].get('valor_total',0) + (a.get('valor_total') or 0)
            for sub in ['status','tipo','prioridade','produtos','motivos','resultado','tier']:
                agg[ag][sub] = add_dicts(agg[ag].get(sub,{}), a.get(sub,{}))
        for sub,key in [('status','_status'),('tipo','_tipo'),('prioridade','_prioridade'),
                        ('produtos','_produtos'),('motivos','_motivos'),('resultado','_resultado'),('tier','_tier')]:
            subs[key] = add_dicts(subs[key], e.get(key,{}))
    tot['valor_total'] = round(tot['valor_total'],2)
    r = dict(agg); r['_totals']=tot; r.update(subs)
    return r

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print(f"\n🐯 Tiger CS Dashboard — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")

    if not os.path.exists(HTML_PATH):
        print(f"❌ index.html não encontrado em: {HTML_PATH}")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    # Test connection
    print("🔗 Conectando ao Freshdesk...")
    try:
        me = api('agents/me')
        print(f"  ✓ Conectado como: {me['contact']['name']}")
    except Exception as e:
        print(f"  ✗ Erro de conexão: {e}")
        print("\n  Possíveis causas:")
        print("  - API Key inválida ou expirada")
        print("  - Restrição de IP no Freshdesk")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    agent_ids = get_agent_ids()
    if not agent_ids:
        print("❌ Nenhum agente encontrado. Verifique o AGENTS_MAP.")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    m = re.search(r'const DATA_FD = (\{.*?\});', html, re.DOTALL)
    fd = json.loads(m.group(1)) if m else {}

    today = date.today().strftime('%Y-%m-%d')

    # 1. Update today
    print(f"\n📊 Atualizando dados de hoje ({today})...")
    fd[today] = build_day_entry(today, agent_ids)
    fd['total'] = rebuild_total(fd)
    html = inject(html, 'DATA_FD', fd)

    # 2. Morning Brief
    print(f"\n🌅 Atualizando Morning Brief...")
    morning = build_morning(agent_ids)
    morning_js = f"""const MORNING_DATA = {{
  date: '{morning['date']}',
  hora_exportacao: '{morning['hora_exportacao']}',
  totals: {json.dumps(morning['totals'], ensure_ascii=False)},
  produtos: {json.dumps(morning['produtos'], ensure_ascii=False)},
  agents: {json.dumps(morning['agents'], ensure_ascii=False)}
}};"""
    html = re.sub(r'const MORNING_DATA = \{.*?\};', morning_js, html, flags=re.DOTALL)
    print(f"  ✓ MORNING_DATA atualizado — {morning['totals']['total_abertos']} abertos")

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Dashboard atualizado com sucesso!")
    print(f"   Arquivo: {HTML_PATH}")
    print(f"   Hoje: {fd[today]['_totals']['tickets_criados']} criados | {fd[today]['_totals']['tickets_trabalhados']} trabalhados")
    print(f"   Fila aberta: {morning['totals']['total_abertos']} tickets")

    # Auto-push to GitHub if git available
    try:
        import subprocess
        result = subprocess.run(['git', 'add', 'index.html'], capture_output=True, cwd=os.path.dirname(HTML_PATH))
        if result.returncode == 0:
            ts = datetime.now().strftime('%d/%m/%Y %H:%M')
            subprocess.run(['git', 'commit', '-m', f'🐯 Dashboard atualizado — {ts}'],
                          capture_output=True, cwd=os.path.dirname(HTML_PATH))
            push = subprocess.run(['git', 'push'], capture_output=True, cwd=os.path.dirname(HTML_PATH))
            if push.returncode == 0:
                print("   ✓ Push para GitHub Pages feito!")
            else:
                print("   ⚠ Git push falhou — atualize manualmente no GitHub")
    except:
        print("   ⚠ Git não encontrado — faça upload manual do index.html")

    input("\nPressione Enter para fechar...")

if __name__ == '__main__':
    main()
