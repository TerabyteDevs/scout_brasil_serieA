
import scrapy

class FbrefSpider(scrapy.Spider):
    name = 'fbref_stats'
    allowed_domains = ['fbref.com']

    async def start(self, response=None):
        """
        Método inicializador do Scrapy. Começa pela página principal.
        """
        url = 'https://fbref.com/en/comps/24/stats/Serie-A-Stats'
        yield scrapy.Request(url, meta={'playwright': True}, callback=self.parse_main_page)

    def parse_main_page(self, response):
        """
        Este método processa a página principal, encontra os links das
        categorias e cria requisições para cada uma delas.
        """
        self.log("Parseando a página inicial para encontrar os links das categorias.")
        xpath_selector = "//*[@id='inner_nav']/ul/li[5]/div/ul/li/a"
        category_links = response.xpath(xpath_selector)

        for link in category_links:
            category_name = link.xpath('.//text()').get().strip()
            url = response.urljoin(link.xpath('.//@href').get())

            yield scrapy.Request(
                url=url,
                callback=self.parse_stats_table,
                meta={'playwright': True, 'category': category_name}
            )

    def parse_stats_table(self, response):
        """
        Este método usa um mapa para encontrar a tabela correta com base
        no seletor exato fornecido pelo usuário para cada categoria.
        """
        category = response.meta['category']
        self.log(f"Parseando a tabela para a categoria: {category}")

        # Mapa que associa o nome da categoria ao seletor exato fornecido
        selector_map = {
            "Standard Stats": "#stats_standard",
            "Goalkeeping": "#stats_keeper",
            "Advanced Goalkeeping": "#stats_keeper_adv",
            "Shooting": "#stats_shooting",
            "Passing": "#stats_passing",
            "Pass Types": "#stats_passing_types",
            "Goal and Shot Creation": "#stats_gca",
            "Defensive Actions": "#stats_defense",
            "Possession": "#stats_possession",
            "Playing Time": "#stats_playing_time",
            "Miscellaneous Stats": "#stats_misc"
        }

        # Pega o seletor correto do mapa
        table_selector = selector_map.get(category)

        if not table_selector:
            self.log(f"AVISO: Categoria '{category}' não encontrada no mapa de seletores. Pulando.")
            return

        # Usa o seletor específico para encontrar a tabela
        table = response.css(table_selector)
        
        if not table:
             self.log(f"ERRO: Tabela não encontrada usando o seletor '{table_selector}' para a categoria '{category}'")
             return

        # O restante da lógica para extrair os dados da tabela permanece o mesmo
        headers = table.css('thead tr:last-child th::attr(data-stat)').getall()
        player_rows = table.css('tbody tr')

        for row in player_rows:
            if row.css('th[scope="row"]').get() is None:
                continue

            player_data = {'category': category}
            all_cells = row.css('th, td')
            for index, cell in enumerate(all_cells):
                if index < len(headers):
                    header_key = headers[index]
                    cell_value = cell.css('a::text').get() or cell.css('::text').get()
                    player_data[header_key] = cell_value.strip() if cell_value else None
            

            yield player_data