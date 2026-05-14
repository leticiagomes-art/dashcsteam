# Como agendar atualização automática no Windows

## Opção 1 — Agendador de Tarefas do Windows (recomendado)

Roda automaticamente todo dia às 20h, mesmo sem você fazer nada.

### Passo a passo:

1. Pressione **Win + R** → digite `taskschd.msc` → Enter

2. No painel direito, clique em **"Criar Tarefa Básica..."**

3. Preencha:
   - **Nome:** `Tiger CS Dashboard`
   - **Descrição:** `Atualiza o dashboard CS automaticamente`

4. **Disparador:** Diário → horário `20:00`

5. **Ação:** Iniciar um programa
   - **Programa:** `C:\caminho\para\atualizar_dashboard.bat`
   - *(clique em Procurar e selecione o arquivo .bat)*

6. Marque **"Abrir a caixa de diálogo Propriedades..."** → OK

7. Na aba **Condições**:
   - Desmarque "Iniciar a tarefa somente se o computador estiver conectado à alimentação CA"

8. **OK** → pronto!

---

## Opção 2 — Rodar manualmente (quando quiser)

Basta dar **duplo clique** no arquivo `atualizar_dashboard.bat`.

Uma janela vai abrir, mostrar o progresso e fechar sozinha.

---

## O que o script faz automaticamente:

1. Conecta na API do Freshdesk
2. Busca todos os tickets criados e trabalhados hoje
3. Busca a fila de tickets abertos (Morning Brief)
4. Atualiza o `index.html` do dashboard
5. Faz push automático para o GitHub Pages (se o repositório estiver configurado)

---

## Estrutura de arquivos necessária:

```
tiger-dashboard/
├── index.html                  ← dashboard
├── atualizar_dashboard.bat     ← clique duas vezes aqui
└── scripts/
    └── atualizar_dashboard.py  ← script principal
```

---

## Requisitos:

- Python 3.8+ instalado (com "Add to PATH" marcado)
- Git instalado (para push automático ao GitHub)
- Conexão com internet
- Computador ligado no horário agendado

---

## Solução de problemas:

**"Python não encontrado"**
→ Instale em python.org, marque "Add Python to PATH"

**"Erro de conexão: 403 Forbidden"**
→ A API Key pode ter expirado. Gere uma nova em Profile Settings no Freshdesk.

**"Git push falhou"**
→ Faça upload manual do index.html no GitHub. O dashboard local já está atualizado.
