from dataclasses import dataclass, field
import json
from typing import List

from modules.client import *
from modules.parser import *

# @dataclass
# class Title:
#     title: str
#     link: str
#     tags: List[str] = field(default_factory=list)

logger=logging.getLogger(__name__)

class RRaper:
    def __init__(self,login=True,base_url='https://www.royalroad.com'):
        self.load_config()

        self.client=Client(self.login_data,
                           self.cookies,
                           self.headers,
                           auto_login=login,base_url=base_url)
        self.parser=Parser()
    def load_config(self):
        with open('config.json') as f:
            config=json.load(f)
        
        self.login_data = config['login_data']
        self.cookies = config['cookies']
        self.headers = config['headers']

    def load_titles_from_index_page(self,
                        link: str) -> dict:
        index_page_response=self.client.load_page(link)
        total_pages,_=self.parser.parse_pages(index_page_response)

        logger.info(f'Number of pages: {total_pages} in {self.client.base_url+link}')

        all_titles={}

        loaded_titles,skipped=self.parser.parse_titles_links(index_page_response)
        all_titles=all_titles | loaded_titles
        logger.info(f'Loaded {len(loaded_titles)} titles, skipped {skipped}, page 1')

        for x in range(2,total_pages+1):
            page=self.client.load_page(f'{link}?page={x}')
            loaded_titles,skipped=self.parser.parse_titles_links(page)
            all_titles=all_titles | loaded_titles
            logger.info(f'loaded_titles: {loaded_titles}')
            logger.info(f'skiped: {skipped}')

            logger.info(f'Loaded {len(loaded_titles)} titles, page {x}')

            time.sleep(1)
        
        for name, dic in all_titles.items():
            link=dic['link']
            response=self.client.load_page(link)
            dic.update(self.parser.parse_meta(response))
            logger.info(f'Succesfully loaded metadata of:{name} ')
            time.sleep(1)

        logger.info(f'Succesfully loaded all {len(all_titles)} titles')
        return all_titles
