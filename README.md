# RedirectHunter 🚀

Ferramenta profissional desenvolvida em Python para rastreamento de redirecionamentos HTTP/HTTPS, análise de URLs finais e detecção de links de download. O projeto conta com suporte a análise dinâmica utilizando Playwright e Selenium, além de recursos avançados para automação, análise web e inspeção de links.

---

## ✨ Funcionalidades

* 🔗 Rastreamento completo de redirecionamentos HTTP/HTTPS
* 🎯 Identificação da URL final real
* ⬇️ Detecção automática de links de download
* 🧠 Análise dinâmica de páginas com JavaScript
* 🌐 Suporte a Playwright e Selenium
* 🔄 Retry automático em falhas de conexão
* 🛡️ Simulação de navegador real com User-Agent aleatório
* 📄 Exportação dos resultados em `.txt`
* 🎨 Interface CLI moderna com cores e logs detalhados
* ⚡ Suporte a páginas com redirects complexos e meta-refresh

---

## 🛠 Tecnologias Utilizadas

* Python 3
* Requests
* BeautifulSoup4
* Playwright
* Selenium
* Colorama
* LXML

---

## 📦 Instalação

Clone o repositório:

```bash
git clone https://github.com/gabrielmarcolinooo/RedirectHunter.git
```

Entre na pasta do projeto:

```bash
cd RedirectHunter
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Instale o Chromium do Playwright:

```bash
playwright install chromium
```

---

## ▶️ Como Utilizar

### Uso básico

```bash
python app.py https://example.com
```

### Com salvamento automático

```bash
python app.py https://example.com --save
```

### Análise dinâmica com Playwright

```bash
python app.py https://example.com --dynamic --engine playwright
```

### Análise dinâmica com Selenium

```bash
python app.py https://example.com --dynamic --engine selenium
```

### Modo verbose

```bash
python app.py https://example.com --verbose
```

---

## 📸 Recursos Detectados

O RedirectHunter é capaz de identificar:

* Histórico completo de redirects
* URLs finais reais
* Links de download
* Meta refresh
* URLs presentes em JavaScript
* Arquivos diretos (.zip, .rar, .pdf, .exe, etc.)
* Links gerados dinamicamente

---

## 📁 Estrutura do Projeto

```text
RedirectHunter/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── screenshots/
```

---

## 👨‍💻 Autor

### Gabriel Marcolino de Oliveira

Estudante de Análise e Desenvolvimento de Sistemas
Desenvolvedor Web | Python | PHP | Automação | Backend

* LinkedIn: https://www.linkedin.com/in/gabriel-marcolino-de-oliveira-29b706197
* GitHub: https://github.com/gabrielmarcolinooo

---

## ⭐ Objetivo do Projeto

Este projeto foi desenvolvido com foco em aprendizado prático, automação web, análise de requisições HTTP e fortalecimento do portfólio profissional na área de desenvolvimento de software e segurança/análise web.

---
