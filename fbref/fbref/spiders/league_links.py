# fbref/spiders/league_links.py (VERSÃO CORRETA E FINAL)
import scrapy
from scrapy_playwright.page import PageMethod

class LeagueLinksSpider(scrapy.Spider):
    name = 'league_links'
    
    def start_requests(self):
        """
        Inicia o pedido para a página de competições usando Playwright
        e espera a primeira tabela carregar.
        """
        url = 'https://fbref.com/en/comps/'
        yield scrapy.Request(
            url,
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_selector", '#comps_1_fa_club_league_senior'),
                ],
            },
            callback=self.parse,
        )

    def parse(self, response):
        """
        Processa a página de competições e extrai as URLs das ligas
        seguindo as regras definidas.
        """
        self.log("Página carregada, extraindo links das competições...")

        # Junta todas as linhas de todas as tabelas de ligas em uma única lista
        all_rows = response.xpath('//table[contains(@id, "_fa_club_league_senior")]/tbody/tr[not(contains(@class, "hidden"))]')
        
        # Processa a primeira tabela (Big 5 e outras principais)
        for row in all_rows:
            # Regra: Apenas gênero 'M' (masculino) ou se a coluna de gênero não existir
            gender = row.xpath('./td[@data-stat="gender"]/text()').get()
            if gender and gender.strip() != "M":
                continue # Pula esta linha se o gênero for 'F'

            # Pega o link da coluna "Competition Name", que leva para a página de estatísticas
            competition_link = row.xpath('./th[@data-stat="league_name"]/a/@href').get()
            
            if competition_link:
                competition_name = row.xpath('./th[@data-stat="league_name"]/a/text()').get('').strip()
                
                # O link para a página de stats já é o link principal da competição,
                # então podemos usá-lo diretamente.
                # Exemplo de link: /en/comps/21/Liga-Profesional-Argentina-Stats
                yield {
                    'competition': competition_name,
                    'url': response.urljoin(competition_link)
                }