import json
import sqlite3

from modules.client import *
from modules.db import RRDB
from modules.parser import *

logger=logging.getLogger(__name__)

class RRscraper:
    def __init__(self,login=True,base_url='https://www.royalroad.com',db_name='RoyalRoad.db'):
        self.load_config()
        self.DB=RRDB(db_name)
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
    # def load_titles_from_index_page(self,link):
    #     pass
    # def get_links_to_index_pages(self,
    #                              link: str,
    #                              end_page: int=None):
    #     first_page_response=self.client.load_page(link)
    #     total_pages,_=self.parser.parse_pages(first_page_response)
    #     if end_page and end_page < total_pages:
    #         total_pages=end_page
    #     index_pages_links=[f'{link}?page={page_number}' for page_number in range(2,total_pages+1)]
    #     return index_pages_links, first_page_response
    def load_titles_from_index_page(self,
                                    link: str,
                                    end_page: int=None
                                    ) -> dict:
        index_page_response=self.client.load_page(link)
        total_pages,_=self.parser.parse_pages(index_page_response)
        if end_page is not None and end_page<total_pages:
            total_pages=end_page
        # index_pages_links, index_page_response=self.get_links_to_index_pages(link,end_page)
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
        return all_titles
    def load_meta_of_titles(self,
                            all_titles: dict) -> dict:
        for i,(name, dic) in enumerate(all_titles.items()):
            link=dic['link']
            response=self.client.load_page(link)
            dic.update(self.parser.parse_meta(response))
            logger.info(f'{i+1} Loaded metadata of:{name} ')
            time.sleep(1)

        logger.info(f'Loaded {len(all_titles)} titles')
        return all_titles
    def load_full_data_from_index(self,
                              link: str,
                              end_page: int=None,
                              skip_ids: list=None) :
        all_titles=self.load_titles_from_index_page(link,end_page)
        titles_to_load=all_titles.copy()
        if skip_ids and len(skip_ids) > 0:
            titles_to_load={title:data for title,data in titles_to_load.items() if data['id'] not in skip_ids}
        full_tittles=self.load_meta_of_titles(titles_to_load)
        return full_tittles, all_titles
    def load_titles_to_db_from_index(self,
                          link: str,
                          end_page: int=None,
                          category: str=None,
                          skip_less_then_days: int=None):
        ids = []

        if skip_less_then_days is not None :           
            ids=self.DB.query_titles(select='id',
                                    where=f'(julianday("now") - julianday(created_at))<{skip_less_then_days}')
            ids=[id[0] for id in ids]

        with_skip,without_skip=self.load_full_data_from_index(link,end_page,skip_ids=ids)
        titles_input=self.DB.transform_titles(with_skip)        

        self.DB.add_titles(titles_input)

        if category:
            category_input=[(x['id'],category) for x in without_skip.values()]

            self.DB.add_category(category_input)
        return with_skip