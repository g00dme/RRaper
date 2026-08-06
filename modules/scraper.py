import json

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
    def get_links_to_index_pages(self,
                                 link: str,
                                 end_page: int=None):
        first_page_response=self.client.load_page(link)
        total_pages,_=self.parser.parse_pages(first_page_response)
        if end_page and end_page < total_pages:
            total_pages=end_page
        index_pages_links=[f'{link}?page={page_number}' for page_number in range(2,total_pages+1)]
        return index_pages_links, first_page_response
    def load_links_from_index_page(self,*,
                                    link: str=None,
                                    page: httpx.Response=None,
                                    ext_dict: dict=None
                                    ) -> dict:
        if not page:
            page=self.client.load_page(link)
        loaded_titles,skipped=self.parser.parse_titles_links(page)

        logger.info(f'Loaded {len(loaded_titles)} titles, skipped {skipped}, page {link if link else page.url}')
        if ext_dict is not None:
            ext_dict.update(loaded_titles)
        return loaded_titles
    # def load_full_title_from_page(self,
    #                               link: str
    #                               ) -> dict:
        
    def load_titles_from_index_range(self,
                                    link: str,
                                    end_page: int=None,
                                    ) -> dict:
        '''Loads all titles in index pages'''
        index_pages_links, index_page_response=self.get_links_to_index_pages(link,end_page)
        all_titles={}

        self.load_links_from_index_page(page=index_page_response,ext_dict=all_titles)
        # loads all_titles inside function
        for link in index_pages_links:
            self.load_links_from_index_page(link=link,ext_dict= all_titles)

            time.sleep(1)
        return all_titles
    def load_meta_of_titles(self,
                            all_titles: dict) -> dict:
        for i,(id, dic) in enumerate(all_titles.items()):
            link=dic['link']
            response=self.client.load_page(link)
            dic.update(self.parser.parse_meta(response))
            logger.info(f'{i+1} Loaded metadata of:{dic['title']} id: {dic['id']}')
            time.sleep(1)

        logger.info(f'Loaded {len(all_titles)} titles')
        return all_titles
    def load_full_data_from_index(self,
                              link: str,
                              end_page: int=None,
                              skip_ids: list=None) :
        index_pages_links, index_page_response=self.get_links_to_index_pages(link,end_page)
        loaded_titles={}
        full_tittles={}
        self.load_links_from_index_page(page=index_page_response,ext_dict=loaded_titles)

        meta_to_load=loaded_titles.copy()

        #process first page separatly, so i dont need to reload it
        if skip_ids and len(skip_ids) > 0:
            meta_to_load={id:data for id,data in meta_to_load.items() if id not in skip_ids}
            logger.info(f'''loading metadata of {len(meta_to_load)}
            titles out of {len(loaded_titles)}, the rest were recently loaded''')
        full_tittles=full_tittles | self.load_meta_of_titles(meta_to_load)

        for link in index_pages_links:
            meta_to_load=self.load_links_from_index_page(link=link,ext_dict=loaded_titles)
            if skip_ids and len(skip_ids) > 0:
                meta_to_load={id:data for id,data in meta_to_load.items() if id not in skip_ids}
                logger.info(f'''loading metadata of {len(meta_to_load)}
                titles out of {len(loaded_titles)}, the rest were recently loaded''')
            full_tittles=full_tittles | self.load_meta_of_titles(meta_to_load)
        return full_tittles, loaded_titles
    def process_links_list(self,
                           links: list) -> Dict[int,Dict[str,Any]]:
        output={}
        for link in links:
            dummy={}
            dummy['link']=link
            id=int(re.search(r'\d+',link).group())
            dummy['id']=id
            output[id]=dummy
        return output
    def load_full_data_from_links(self,
                              links: str) :
        full_tittles={}
        meta_to_load=self.process_links_list(links)
        #process first page separatly, so i dont need to reload it

        full_tittles= full_tittles | self.load_meta_of_titles(meta_to_load)
        
        return full_tittles, meta_to_load

    def load_titles_to_db(self,
                          index_link: str=None,
                          links: str=None,
                          end_page: int=None,
                          category: str=None,
                          skip_less_then_days: int=None):
        ids = []
        if index_link is not None:
            if skip_less_then_days is not None :           
                ids=self.DB.query_titles(select='id',
                                        where=f'(julianday("now") - julianday(created_at))<{skip_less_then_days}')
                ids=[id[0] for id in ids]

            with_skip,without_skip=self.load_full_data_from_index(index_link,end_page,skip_ids=ids)
        elif links:
            with_skip,without_skip=self.load_full_data_from_links(links)
        else:
            logger.error('supply either index_link or links to load titles')
        titles_input=self.DB.transform_titles(with_skip)        
        self.DB.add_titles(titles_input)

        if category:
            category_input=[(x['id'],category) for x in without_skip.values()]

            self.DB.add_category(category_input)
        return with_skip
