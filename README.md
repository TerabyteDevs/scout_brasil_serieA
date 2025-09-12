# 📊 Scout Brasileirão - Coleta e Dashboard

Este projeto realiza **web scraping de estatísticas de jogadores** do site [FBref](https://fbref.com) utilizando **Scrapy + Playwright**, organiza os dados em **Excel** com tratamento em pipeline e disponibiliza uma interface em **Streamlit** para análise interativa.

---

## 🚀 Estrutura do Projeto

- **`fbref.py`** → Spider Scrapy que coleta estatísticas (Standard Stats, Shooting, Passing, etc.).
- **`pipelines.py`** → Processa os dados, unifica estatísticas, calcula data de nascimento e exporta para `fbref_player_stats_final.xlsx`.
- **`settings.py`** → Configurações do Scrapy (com Playwright habilitado).
- **`stats_links.json`** → Lista de categorias e URLs a serem coletadas.
- **`dashboard.py`** → Dashboard em Streamlit para explorar os dados exportados.
- **`items.py`, `middlewares.py`** → Arquivos padrão do Scrapy (podem ser expandidos futuramente).

---

## ⚙️ Instalação e Uso

### 1️⃣ Clonar o repositório
```bash
git clone https://github.com/seu-usuario/scout_brasil_serieA.git
cd scout-brasileirao
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
streamlit run dashboard.py
.
