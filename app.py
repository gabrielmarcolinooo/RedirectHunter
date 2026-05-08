#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║         RedirectHunter - Analisador de Redirecionamentos     ║
║              Desenvolvido para Python 3.8+                   ║
╚══════════════════════════════════════════════════════════════╝

Aplicação profissional para rastrear redirecionamentos HTTP/HTTPS,
detectar URLs finais e identificar links de download em páginas web.
"""

import sys
import os
import re
import json
import time
import random
import argparse
import logging
from datetime import datetime
from urllib.parse import urlparse, urljoin, unquote
from typing import Optional

# ──────────────────────────────────────────────
# Verificação de dependências
# ──────────────────────────────────────────────
def check_and_install_dependencies():
    """Verifica e instala dependências necessárias."""
    required = {
        "requests": "requests",
        "bs4": "beautifulsoup4",
        "colorama": "colorama",
        "lxml": "lxml",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"\n[SETUP] Instalando dependências ausentes: {', '.join(missing)}")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing, "--quiet"])
        print("[SETUP] Dependências instaladas com sucesso!\n")

check_and_install_dependencies()

# ──────────────────────────────────────────────
# Importações principais
# ──────────────────────────────────────────────
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from colorama import init, Fore, Back, Style

init(autoreset=True)  # Inicializa colorama (necessário no Windows)

# ──────────────────────────────────────────────
# Configurações globais
# ──────────────────────────────────────────────
VERSION = "2.0.0"
DEFAULT_TIMEOUT = 20
MAX_RETRIES = 3
RETRY_DELAY = 2

# User-Agents modernos e realistas
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
]

# Extensões que indicam links de download
DOWNLOAD_EXTENSIONS = {
    # Arquivos comprimidos
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.zst',
    # Executáveis e instaladores
    '.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.appimage',
    # Documentos
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    # Mídia
    '.mp4', '.mp3', '.avi', '.mkv', '.mov', '.wav', '.flac', '.m4a',
    # Imagens
    '.iso', '.img', '.bin',
    # Outros
    '.apk', '.ipa', '.torrent',
}

# Palavras-chave em URLs que indicam download
DOWNLOAD_KEYWORDS = [
    'download', 'baixar', 'descargar', 'télécharger', 'herunterladen',
    'dl', 'get', 'fetch', 'file', 'arquivo', 'release', 'asset',
    'attach', 'export', 'direct-link', 'mirror',
]

# ──────────────────────────────────────────────
# Classe de Interface Visual (CLI)
# ──────────────────────────────────────────────
class UI:
    """Gerencia toda a interface visual do terminal com cores e formatação."""

    WIDTH = 70

    # Paleta de cores
    PRIMARY   = Fore.CYAN
    SUCCESS   = Fore.GREEN
    WARNING   = Fore.YELLOW
    ERROR     = Fore.RED
    INFO      = Fore.WHITE
    DIM       = Fore.LIGHTBLACK_EX
    ACCENT    = Fore.MAGENTA
    BOLD      = Style.BRIGHT

    @classmethod
    def banner(cls):
        """Exibe o banner principal da aplicação."""
        lines = [
            "",
            f"{cls.PRIMARY}{cls.BOLD}{'═' * cls.WIDTH}",
            f"{cls.PRIMARY}{cls.BOLD}{'RedirectHunter v' + VERSION:^{cls.WIDTH}}",
            f"{cls.DIM}{'Analisador Profissional de Redirecionamentos HTTP':^{cls.WIDTH}}",
            f"{cls.PRIMARY}{cls.BOLD}{'═' * cls.WIDTH}",
            "",
        ]
        for line in lines:
            print(line)

    @classmethod
    def section(cls, title: str):
        """Exibe um cabeçalho de seção."""
        print(f"\n{cls.PRIMARY}{'─' * cls.WIDTH}")
        print(f"{cls.BOLD}{cls.ACCENT}  ▶  {title}")
        print(f"{cls.PRIMARY}{'─' * cls.WIDTH}")

    @classmethod
    def info(cls, label: str, value: str, indent: int = 2):
        """Exibe um par label/valor formatado."""
        pad = " " * indent
        print(f"{pad}{cls.DIM}{label:<22}{cls.INFO}{value}")

    @classmethod
    def success(cls, msg: str):
        print(f"  {cls.SUCCESS}✔  {msg}")

    @classmethod
    def warning(cls, msg: str):
        print(f"  {cls.WARNING}⚠  {msg}")

    @classmethod
    def error(cls, msg: str):
        print(f"  {cls.ERROR}✖  {msg}")

    @classmethod
    def step(cls, n: int, total: int, msg: str):
        """Exibe um passo numerado."""
        print(f"  {cls.DIM}[{n}/{total}]{cls.INFO} {msg}")

    @classmethod
    def redirect_arrow(cls, from_url: str, to_url: str, code: int):
        """Exibe um redirecionamento de forma visual."""
        color = cls.SUCCESS if code < 400 else cls.WARNING
        from_short = cls._truncate(from_url, 55)
        to_short   = cls._truncate(to_url,   55)
        print(f"  {cls.DIM}{from_short}")
        print(f"  {color}  └─[{code}]──▶  {cls.INFO}{to_short}")

    @classmethod
    def download_link(cls, url: str, reason: str):
        """Exibe um link de download detectado."""
        short = cls._truncate(url, 58)
        print(f"  {cls.SUCCESS}⬇  {cls.INFO}{short}")
        print(f"     {cls.DIM}({reason})")

    @classmethod
    def footer(cls, elapsed: float):
        """Exibe o rodapé com tempo de execução."""
        print(f"\n{cls.PRIMARY}{'─' * cls.WIDTH}")
        print(f"  {cls.DIM}Tempo total: {elapsed:.2f}s  |  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"{cls.PRIMARY}{'═' * cls.WIDTH}\n")

    @classmethod
    def _truncate(cls, text: str, max_len: int) -> str:
        """Trunca texto longo com reticências."""
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + "..."


# ──────────────────────────────────────────────
# Classe principal: RedirectHunter
# ──────────────────────────────────────────────
class RedirectHunter:
    """
    Motor principal de rastreamento de redirecionamentos HTTP.
    Utiliza requests + BeautifulSoup com fallback para Playwright/Selenium.
    """

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, max_retries: int = MAX_RETRIES,
                 verbose: bool = False, save_output: bool = False, output_file: str = None,
                 use_dynamic: bool = False, dynamic_engine: str = "playwright"):

        self.timeout       = timeout
        self.max_retries   = max_retries
        self.verbose       = verbose
        self.save_output   = save_output
        self.output_file   = output_file
        self.use_dynamic   = use_dynamic
        self.dynamic_engine = dynamic_engine

        # Histórico da análise
        self.results = {
            "original_url":    "",
            "final_url":       "",
            "final_status":    0,
            "redirects":       [],
            "download_links":  [],
            "page_title":      "",
            "meta_links":      [],
            "js_links":        [],
            "elapsed":         0.0,
            "timestamp":       "",
            "user_agent":      "",
        }

        # Configura logging interno
        log_level = logging.DEBUG if verbose else logging.WARNING
        logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
        self.logger = logging.getLogger("RedirectHunter")

        # Cria sessão HTTP com retry automático
        self.session = self._build_session()

    # ──────────────────────────────────────
    # Construção da sessão HTTP
    # ──────────────────────────────────────
    def _build_session(self) -> requests.Session:
        """Cria e configura a sessão HTTP com retry, headers e cookies."""
        session = requests.Session()

        # Estratégia de retry: tenta em falhas de rede e erros 5xx
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://",  adapter)

        # Seleciona User-Agent aleatório
        ua = random.choice(USER_AGENTS)
        self.results["user_agent"] = ua

        # Headers que simulam um navegador real
        session.headers.update({
            "User-Agent":      ua,
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT":             "1",
            "Connection":      "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest":  "document",
            "Sec-Fetch-Mode":  "navigate",
            "Sec-Fetch-Site":  "none",
            "Sec-Fetch-User":  "?1",
            "Cache-Control":   "max-age=0",
        })

        return session

    # ──────────────────────────────────────
    # Método principal: analyze()
    # ──────────────────────────────────────
    def analyze(self, url: str) -> dict:
        """
        Analisa uma URL: segue redirecionamentos, detecta links de download
        e coleta informações da página final.
        """
        start_time = time.time()
        self.results["original_url"] = url
        self.results["timestamp"]    = datetime.now().isoformat()

        UI.banner()

        # ── Etapa 1: Validação da URL ──
        UI.section("1. Validando URL de entrada")
        if not self._validate_url(url):
            UI.error(f"URL inválida: {url}")
            UI.warning("Certifique-se de incluir http:// ou https://")
            return self.results

        UI.success(f"URL válida: {url}")
        UI.info("User-Agent:", self.results["user_agent"][:60] + "...")

        # ── Etapa 2: Rastreamento de redirecionamentos ──
        UI.section("2. Rastreando Redirecionamentos HTTP")
        response = self._follow_redirects(url)

        if response is None:
            UI.error("Não foi possível acessar a URL após múltiplas tentativas.")
            return self.results

        self.results["final_url"]    = response.url
        self.results["final_status"] = response.status_code

        # ── Etapa 3: Análise da página final ──
        UI.section("3. Analisando Página Final")
        self._analyze_page(response)

        # ── Etapa 4: Análise dinâmica (opcional) ──
        if self.use_dynamic:
            UI.section("4. Análise Dinâmica (JavaScript)")
            self._analyze_dynamic(self.results["final_url"])
        
        # ── Etapa 5: Resumo dos resultados ──
        UI.section("5. Resumo dos Resultados")
        self._print_summary()

        # ── Salvar resultados ──
        self.results["elapsed"] = round(time.time() - start_time, 2)
        if self.save_output:
            self._save_results()

        UI.footer(self.results["elapsed"])
        return self.results

    # ──────────────────────────────────────
    # Validação de URL
    # ──────────────────────────────────────
    def _validate_url(self, url: str) -> bool:
        """Valida se a URL tem formato correto."""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme in ("http", "https"), parsed.netloc])
        except Exception:
            return False

    # ──────────────────────────────────────
    # Rastreamento de redirecionamentos
    # ──────────────────────────────────────
    def _follow_redirects(self, url: str) -> Optional[requests.Response]:
        """
        Faz a requisição seguindo todos os redirecionamentos
        e registra o histórico completo.
        """
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,  # Segue redirecionamentos automaticamente
                stream=False,
            )

            # Processa o histórico de redirecionamentos
            redirect_chain = list(response.history) + [response]

            if len(redirect_chain) <= 1:
                UI.info("Redirecionamentos:", "Nenhum encontrado (acesso direto)")
            else:
                UI.info("Redirecionamentos:", f"{len(response.history)} encontrado(s)")
                print()

                for i, (prev, curr) in enumerate(zip(redirect_chain, redirect_chain[1:])):
                    step_data = {
                        "step":   i + 1,
                        "from":   prev.url,
                        "to":     curr.url,
                        "status": prev.status_code,
                        "reason": prev.reason,
                    }
                    self.results["redirects"].append(step_data)
                    UI.redirect_arrow(prev.url, curr.url, prev.status_code)
                    print()

            return response

        except requests.exceptions.SSLError as e:
            UI.warning("Erro SSL detectado. Tentando sem verificação de certificado...")
            try:
                response = self.session.get(
                    url, timeout=self.timeout,
                    allow_redirects=True, verify=False
                )
                UI.warning("Conexão estabelecida sem verificação SSL (não seguro)")
                return response
            except Exception as e2:
                UI.error(f"Falha mesmo sem SSL: {e2}")
                return None

        except requests.exceptions.ConnectionError as e:
            UI.error(f"Erro de conexão: {e}")
            return None

        except requests.exceptions.Timeout:
            UI.error(f"Timeout após {self.timeout}s. Tente aumentar o valor com --timeout")
            return None

        except requests.exceptions.TooManyRedirects:
            UI.error("Loop de redirecionamento detectado! (mais de 30 redirects)")
            return None

        except requests.exceptions.RequestException as e:
            UI.error(f"Erro na requisição: {e}")
            return None

    # ──────────────────────────────────────
    # Análise da página HTML
    # ──────────────────────────────────────
    def _analyze_page(self, response: requests.Response):
        """
        Analisa o HTML da página final usando BeautifulSoup.
        Extrai título, meta-tags, links e detecta links de download.
        """
        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type:
            UI.info("Tipo de conteúdo:", content_type)
            UI.warning("A URL aponta diretamente para um arquivo (não HTML)")
            # A própria URL final pode ser um download
            if self._is_download_url(response.url):
                self.results["download_links"].append({
                    "url":    response.url,
                    "text":   "URL Final (arquivo direto)",
                    "reason": "Content-Type indica arquivo",
                })
            return

        try:
            # Detecta encoding correto
            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "lxml")

            # ── Título da página ──
            title_tag = soup.find("title")
            if title_tag:
                self.results["page_title"] = title_tag.get_text(strip=True)
                UI.info("Título da página:", self.results["page_title"][:60])

            # ── Meta refresh (redirecionamento via HTML) ──
            meta_refresh = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
            if meta_refresh:
                content = meta_refresh.get("content", "")
                match = re.search(r"url=(.+)", content, re.I)
                if match:
                    refresh_url = match.group(1).strip().strip("'\"")
                    UI.warning(f"Meta-refresh detectado → {refresh_url}")
                    self.results["meta_links"].append(refresh_url)

            # ── Coleta todos os links <a> ──
            all_links = []
            for tag in soup.find_all("a", href=True):
                href = tag.get("href", "").strip()
                text = tag.get_text(strip=True)[:80]
                if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    abs_url = urljoin(response.url, href)
                    all_links.append({"url": abs_url, "text": text, "tag": "a"})

            # ── Coleta links em <source>, <audio>, <video> ──
            for tag in soup.find_all(["source", "audio", "video", "embed", "object"]):
                src = tag.get("src") or tag.get("data") or ""
                if src:
                    abs_url = urljoin(response.url, src)
                    all_links.append({"url": abs_url, "text": tag.name, "tag": tag.name})

            # ── Coleta botões de formulário com action ──
            for form in soup.find_all("form", action=True):
                action = form.get("action", "").strip()
                if action:
                    abs_url = urljoin(response.url, action)
                    all_links.append({"url": abs_url, "text": "form-action", "tag": "form"})

            UI.info("Links encontrados:", str(len(all_links)))

            # ── Filtra links de download ──
            download_count = 0
            seen_urls = set()
            for link in all_links:
                link_url = link["url"]
                if link_url in seen_urls:
                    continue
                seen_urls.add(link_url)

                is_dl, reason = self._is_download_url(link_url, link["text"])
                if is_dl:
                    self.results["download_links"].append({
                        "url":    link_url,
                        "text":   link["text"],
                        "reason": reason,
                        "tag":    link["tag"],
                    })
                    download_count += 1

            # ── Extrai URLs de scripts JS (links embutidos) ──
            js_links = self._extract_js_links(soup, response.url)
            self.results["js_links"] = js_links
            if js_links:
                UI.info("URLs em JavaScript:", str(len(js_links)))

            UI.success(f"Links de download detectados: {download_count}")

        except Exception as e:
            UI.error(f"Erro ao analisar HTML: {e}")
            self.logger.debug(f"Detalhe do erro: {e}", exc_info=True)

    # ──────────────────────────────────────
    # Detecção de links de download
    # ──────────────────────────────────────
    def _is_download_url(self, url: str, link_text: str = "") -> tuple:
        """
        Verifica se uma URL aponta para um arquivo de download.
        Retorna (bool, motivo_string).
        """
        try:
            parsed = urlparse(url)
            path   = parsed.path.lower()
            query  = parsed.query.lower()
            url_lower = url.lower()

            # 1) Extensão de arquivo no path
            for ext in DOWNLOAD_EXTENSIONS:
                if path.endswith(ext):
                    return True, f"Extensão de arquivo: {ext}"

            # 2) Extensão no parâmetro de query (ex: ?file=algo.zip)
            for ext in DOWNLOAD_EXTENSIONS:
                if ext in query:
                    return True, f"Extensão na query string: {ext}"

            # 3) Palavra-chave na URL
            for kw in DOWNLOAD_KEYWORDS:
                if f"/{kw}/" in url_lower or f"/{kw}?" in url_lower or url_lower.endswith(f"/{kw}"):
                    return True, f"Palavra-chave na URL: '{kw}'"

            # 4) Texto do link sugere download
            text_lower = link_text.lower()
            for kw in ["download", "baixar", "descargar", "baixe", "get", "install"]:
                if kw in text_lower:
                    return True, f"Texto do link: '{kw}'"

            return False, ""

        except Exception:
            return False, ""

    # ──────────────────────────────────────
    # Extração de URLs em JavaScript
    # ──────────────────────────────────────
    def _extract_js_links(self, soup: BeautifulSoup, base_url: str) -> list:
        """
        Busca URLs embutidas em blocos <script> usando regex.
        Útil para detectar links gerados dinamicamente no código JS.
        """
        js_urls = []
        seen    = set()

        # Padrão para capturar URLs em strings JS
        url_pattern = re.compile(
            r'["\']((https?://[^\s"\'<>]+|/[^\s"\'<>]{3,}))["\']'
        )

        for script in soup.find_all("script"):
            script_text = script.string or ""
            if not script_text:
                continue
            for match in url_pattern.finditer(script_text):
                found_url = match.group(1)
                if found_url.startswith("/"):
                    found_url = urljoin(base_url, found_url)
                if found_url not in seen and len(found_url) > 10:
                    seen.add(found_url)
                    is_dl, reason = self._is_download_url(found_url)
                    if is_dl:
                        js_urls.append({"url": found_url, "reason": reason})
                        self.results["download_links"].append({
                            "url":    found_url,
                            "text":   "detectado em script JS",
                            "reason": reason,
                            "tag":    "script",
                        })

        return js_urls

    # ──────────────────────────────────────
    # Análise dinâmica com Playwright/Selenium
    # ──────────────────────────────────────
    def _analyze_dynamic(self, url: str):
        """
        Usa Playwright ou Selenium para renderizar JavaScript
        e capturar links gerados dinamicamente.
        """
        if self.dynamic_engine == "playwright":
            self._analyze_with_playwright(url)
        else:
            self._analyze_with_selenium(url)

    def _analyze_with_playwright(self, url: str):
        """Análise dinâmica via Playwright."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            UI.warning("Playwright não instalado. Execute: pip install playwright && playwright install chromium")
            return

        UI.info("Engine:", "Playwright (Chromium headless)")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=random.choice(USER_AGENTS))
                page    = context.new_page()

                # Intercepta requisições de rede para capturar downloads
                intercepted_urls = []
                def handle_request(req):
                    if any(req.url.lower().endswith(ext) for ext in DOWNLOAD_EXTENSIONS):
                        intercepted_urls.append(req.url)
                page.on("request", handle_request)

                page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")
                time.sleep(2)  # Aguarda JS finalizar

                # Extrai links do DOM renderizado
                links = page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => ({url: a.href, text: a.innerText.trim().substring(0, 80)}))
                        .filter(l => l.url.startsWith('http'));
                }""")

                # Verifica links de download no DOM renderizado
                new_dl = 0
                existing = {dl["url"] for dl in self.results["download_links"]}
                for link in links:
                    if link["url"] not in existing:
                        is_dl, reason = self._is_download_url(link["url"], link["text"])
                        if is_dl:
                            self.results["download_links"].append({
                                "url":    link["url"],
                                "text":   link["text"],
                                "reason": f"[Playwright] {reason}",
                                "tag":    "a",
                            })
                            new_dl += 1

                # Adiciona URLs interceptadas
                for iurl in intercepted_urls:
                    if iurl not in existing:
                        self.results["download_links"].append({
                            "url":    iurl,
                            "text":   "interceptado via rede",
                            "reason": "[Playwright] Requisição de arquivo detectada",
                            "tag":    "network",
                        })
                        new_dl += 1

                browser.close()
                UI.success(f"Playwright: {new_dl} novos links de download encontrados")

        except Exception as e:
            UI.error(f"Erro no Playwright: {e}")

    def _analyze_with_selenium(self, url: str):
        """Análise dinâmica via Selenium (fallback)."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
        except ImportError:
            UI.warning("Selenium não instalado. Execute: pip install selenium")
            return

        UI.info("Engine:", "Selenium (Chrome headless)")
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
            options.add_argument("--disable-blink-features=AutomationControlled")

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.get(url)
            time.sleep(3)

            links = driver.execute_script("""
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({url: a.href, text: a.innerText.substring(0, 80)}))
                    .filter(l => l.url.startsWith('http'));
            """)

            new_dl = 0
            existing = {dl["url"] for dl in self.results["download_links"]}
            for link in links:
                if link["url"] not in existing:
                    is_dl, reason = self._is_download_url(link["url"], link["text"])
                    if is_dl:
                        self.results["download_links"].append({
                            "url":    link["url"],
                            "text":   link["text"],
                            "reason": f"[Selenium] {reason}",
                            "tag":    "a",
                        })
                        new_dl += 1

            driver.quit()
            UI.success(f"Selenium: {new_dl} novos links de download encontrados")

        except Exception as e:
            UI.error(f"Erro no Selenium: {e}")

    # ──────────────────────────────────────
    # Exibição do resumo final
    # ──────────────────────────────────────
    def _print_summary(self):
        """Exibe o resumo completo dos resultados."""

        # URL original → final
        UI.info("URL Original:",  self.results["original_url"])
        UI.info("URL Final:",     self.results["final_url"])
        UI.info("Status HTTP:",   str(self.results["final_status"]))

        if self.results["page_title"]:
            UI.info("Título:",    self.results["page_title"][:60])

        # Redirecionamentos
        n_redirects = len(self.results["redirects"])
        if n_redirects:
            UI.info("Redirects:",  f"{n_redirects} salto(s) detectado(s)")
        else:
            UI.info("Redirects:",  "Nenhum (acesso direto)")

        # Links de download
        downloads = self.results["download_links"]
        print()
        if downloads:
            print(f"  {UI.BOLD}{UI.SUCCESS}⬇  Links de Download Detectados ({len(downloads)}):")
            print()
            seen = set()
            for dl in downloads:
                if dl["url"] not in seen:
                    seen.add(dl["url"])
                    UI.download_link(dl["url"], dl["reason"])
                    print()
        else:
            UI.warning("Nenhum link de download detectado nesta página.")

        # Links JS extras
        if self.results["js_links"]:
            print(f"\n  {UI.DIM}Links adicionais encontrados em JavaScript: {len(self.results['js_links'])}")

    # ──────────────────────────────────────
    # Salvamento dos resultados
    # ──────────────────────────────────────
    def _save_results(self):
        """Salva os resultados em arquivo .txt ou .json."""
        if not self.output_file:
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain = urlparse(self.results["original_url"]).netloc.replace(".", "_")
            self.output_file = f"redirect_result_{domain}_{ts}.txt"

        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write(f"  RedirectHunter v{VERSION} - Relatório de Análise\n")
                f.write(f"  Gerado em: {self.results['timestamp']}\n")
                f.write("=" * 70 + "\n\n")

                f.write(f"URL Original : {self.results['original_url']}\n")
                f.write(f"URL Final    : {self.results['final_url']}\n")
                f.write(f"Status HTTP  : {self.results['final_status']}\n")
                f.write(f"Título       : {self.results['page_title']}\n")
                f.write(f"User-Agent   : {self.results['user_agent']}\n")
                f.write(f"Tempo (s)    : {self.results['elapsed']}\n\n")

                f.write("─" * 70 + "\n")
                f.write(f"REDIRECIONAMENTOS ({len(self.results['redirects'])})\n")
                f.write("─" * 70 + "\n")
                for r in self.results["redirects"]:
                    f.write(f"  [{r['step']}] {r['status']} {r['reason']}\n")
                    f.write(f"       DE: {r['from']}\n")
                    f.write(f"       PARA: {r['to']}\n\n")

                f.write("─" * 70 + "\n")
                f.write(f"LINKS DE DOWNLOAD ({len(self.results['download_links'])})\n")
                f.write("─" * 70 + "\n")
                seen = set()
                for dl in self.results["download_links"]:
                    if dl["url"] not in seen:
                        seen.add(dl["url"])
                        f.write(f"  URL   : {dl['url']}\n")
                        f.write(f"  Texto : {dl.get('text', '')}\n")
                        f.write(f"  Motivo: {dl['reason']}\n\n")

                f.write("=" * 70 + "\n")

            UI.success(f"Resultados salvos em: {self.output_file}")

        except IOError as e:
            UI.error(f"Erro ao salvar arquivo: {e}")


# ──────────────────────────────────────────────
# Interface de linha de comando (CLI)
# ──────────────────────────────────────────────
def build_cli() -> argparse.ArgumentParser:
    """Constrói e retorna o parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        prog="RedirectHunter",
        description="Analisador profissional de redirecionamentos HTTP/HTTPS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python app.py https://bit.ly/exemplo
  python app.py https://t.co/abc123 --save
  python app.py https://exemplo.com --timeout 30 --dynamic --engine playwright
  python app.py https://exemplo.com --output meu_resultado.txt --verbose
        """,
    )

    parser.add_argument(
        "url",
        help="URL para analisar (encurtada, redirecionada ou direta)",
        nargs="?",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=DEFAULT_TIMEOUT,
        metavar="SEG",
        help=f"Timeout em segundos por requisição (padrão: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--retries", "-r",
        type=int,
        default=MAX_RETRIES,
        metavar="N",
        help=f"Número máximo de tentativas em caso de falha (padrão: {MAX_RETRIES})",
    )
    parser.add_argument(
        "--dynamic", "-d",
        action="store_true",
        help="Ativar análise dinâmica via Playwright ou Selenium (para páginas com JavaScript)",
    )
    parser.add_argument(
        "--engine", "-e",
        choices=["playwright", "selenium"],
        default="playwright",
        help="Engine para análise dinâmica: playwright (padrão) ou selenium",
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Salvar resultados em arquivo .txt automaticamente",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="ARQUIVO",
        help="Nome do arquivo de saída (implica --save)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Exibir logs detalhados de debug",
    )

    return parser


# ──────────────────────────────────────────────
# Ponto de entrada principal
# ──────────────────────────────────────────────
def main():
    parser = build_cli()
    args   = parser.parse_args()

    # Modo interativo: pede URL se não foi fornecida
    if not args.url:
        UI.banner()
        print(f"  {Fore.CYAN}Digite a URL para analisar (ex: https://bit.ly/abc):")
        print(f"  {Fore.WHITE}", end="")
        try:
            url = input().strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {Fore.YELLOW}Operação cancelada.")
            sys.exit(0)
        if not url:
            print(f"  {Fore.RED}URL não fornecida. Encerrando.")
            sys.exit(1)
        args.url = url

    # Garante que a URL tem scheme
    if not args.url.startswith(("http://", "https://")):
        args.url = "https://" + args.url

    save = args.save or bool(args.output)

    # Instancia e executa o analisador
    hunter = RedirectHunter(
        timeout=args.timeout,
        max_retries=args.retries,
        verbose=args.verbose,
        save_output=save,
        output_file=args.output,
        use_dynamic=args.dynamic,
        dynamic_engine=args.engine,
    )

    try:
        hunter.analyze(args.url)
    except KeyboardInterrupt:
        print(f"\n\n  {Fore.YELLOW}⚠  Análise interrompida pelo usuário.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()