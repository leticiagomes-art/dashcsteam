# 🐯 Tiger CS Dashboard — Guia de Atualização

## Como atualizar o dashboard

### Passo a passo (2 minutos)

**1. Exporte os CSVs do Freshdesk**

No Freshdesk, filtre por agente e exporte um CSV para cada um:

| Agente | Nome do arquivo |
|---|---|
| Heitor Ribeiro | `freshdesk_Heitor.csv` |
| Natália Alencar | `freshdesk_Natalia.csv` |
| Neythan Cauã | `freshdesk_Neythan.csv` |
| Yasmim Sobral | `freshdesk_Yasmin.csv` |

> **Como exportar:** Tickets → Filtrar por Agente → Export → CSV

---

**2. Suba os CSVs para o GitHub**

Acesse o repositório no GitHub e arraste os arquivos para a pasta `data/`.

```
tiger-dashboard/
└── data/
    ├── freshdesk_Heitor.csv    ← arraste aqui
    ├── freshdesk_Natalia.csv
    ├── freshdesk_Neythan.csv
    └── freshdesk_Yasmin.csv
```

**3. Aguarde ~1 minuto**

O GitHub Actions roda automaticamente, processa os CSVs e atualiza o `index.html`. O GitHub Pages publica em seguida.

Você pode acompanhar em: `Repositório → Actions → 🐯 Atualizar Dashboard CS`

---

## Estrutura do repositório

```
tiger-dashboard/
├── index.html                          # Dashboard (atualizado automaticamente)
├── data/
│   └── freshdesk_*.csv                 # CSVs exportados do Freshdesk
├── scripts/
│   └── process.py                      # Script de processamento
└── .github/
    └── workflows/
        └── update-dashboard.yml        # Automação GitHub Actions
```

---

## Configurações do GitHub Pages

1. Vá em **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / pasta **/ (root)**
4. Salvar

O dashboard fica disponível em:
`https://SEU-USUARIO.github.io/tiger-dashboard/`

---

## Dicas

- Você pode rodar o workflow manualmente em **Actions → Run workflow** sem precisar subir um CSV novo
- Se quiser testar localmente: `python scripts/process.py` (precisa ter Python e pandas instalados)
- Os dados do Formulário (até 08/05) nunca mudam — só o Freshdesk é atualizado automaticamente
