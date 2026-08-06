import logging
from math import log
import re
from datetime import datetime
from typing import Any, Dict, Tuple
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
import httpx

def clean_spaces(string):
    string=string.strip()
    string=re.sub(r'\s+',' ',string)
    return string

class NoTitlesFound(Exception):
    "Riased when no titles found on page"
    pass

class NoPagesFound(Exception):
    "Riased when no list of pages found on page"
    pass

logger=logging.getLogger(__name__)

class Parser:
    def __init__(self):
        pass
    def parse_titles_links(self,
                           response: httpx.Response,
                           first: str='h2',
                           first_class: str='fiction-title',
                           second:str='a'
                           ) -> Tuple[Dict[str,Any],int]:
        page=BeautifulSoup(response, 'html.parser')
        titles={}
        skipped=0
        all_titles=page.find_all(first,class_=first_class)
        if len(all_titles)==0:
            logger.warning(f'No titles were found on the page {response.url}')
            raise NoTitlesFound()
        for el in all_titles:
            title=clean_spaces(el.get_text())
            a=el.find(second)
            if a:
                link=a.get('href')
                id=int(re.search(r'\d+',link).group())
                titles[id]={'link':link,'id':id}
            else:
                logger.warning(f'{title} has no link')
                skipped+=1
        return titles,skipped 
    def parse_stat_meta(self,
                       response: httpx.Response,
                       metadata: dict,
                       first: str='li',
                       first_class: str='bold uppercase',
                       second: str='li') -> dict:
        soup=BeautifulSoup(response, 'html.parser')
        elements=soup.find_all(first,class_=first_class)
        for el in elements:
            name=el.text.replace(':','').strip().replace(' ','_')
            value=el.find_next_sibling(second)
            if not value:
                logger.warning(f'cant find value of {name} in {el}, link: {response.url}')
                continue
            try:
                value=int(value.text.strip().replace(',',''))
                metadata[name]=value
            except Exception:
                logger.warning(f'error transforming {value.text} into int')
        return metadata

    def parse_stars(self,
                    response: httpx.Response,
                    metadata: dict,
                    first: str='span',
                    first_attr: str='data-original-title',
                    value_attr: str='aria-label'
                    ) -> dict:
        soup=BeautifulSoup(response, 'html.parser')
        elements=soup.find_all(first,attrs={first_attr:True})
        if 'This fiction has not received enough ratings yet to have a score.' in soup.text:
            logger.info(f'Not enough ratings for scores on {response.url}')
            metadata['Overall_Score']= None
            metadata['Style_Score']= None
            metadata['Story_Score']= None
            metadata['Grammar_Score']= None
            metadata['Character_Score']= None
            return metadata
        elif len(elements)==0:
            logger.error(f'Did not find Scores on {response.url}')
        for el in elements:
            name=el.get(first_attr).strip().replace(' ','_')
            raw_value=el.get(value_attr) 
            if not raw_value:
                logger.warning(f'element {name}, of {el} has no value in attr {value_attr}')
                continue
            try:
                match=re.search(r'\d+.?\d*',raw_value)
                if not match:
                    logger.warning(fr'Cant extract number from {raw_value}, via re "\d+.?\d*"')
                    continue
                value=float(match.group())
                metadata[name]=value
            except ValueError as e:
                logger.warning(f'Cant parse {raw_value} into float, name:{name}, error:{e}')
            except Exception as e:
                logger.error(f'Unexpected error parsing {raw_value} into float,name:{name}, error:{e}')
        return metadata
    def parse_meta(self,
                  response: httpx.Response,
                  tags_tag: str='a',
                  tag_class: str='fiction-tag'
                  ) -> dict: 
            
        metadata={}
        
        soup=BeautifulSoup(response, 'html.parser')

        # tags
        tags=soup.find_all(tags_tag,class_=tag_class)
        if not tags:
            logger.warning(f'No tags found on page {response.url}')
        metadata['tags']=[tag.text for tag in tags]
        metadata['time']=datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        title=soup.title
        if title:
            metadata['title']=title.text.split(' | ')[0].strip()
        else:
            logger.warning(f'cant find the title of {response.url}')

        self.parse_stars(response,metadata)

        self.parse_stat_meta(response,metadata)

        return metadata
    def parse_pages(self,
                    response: httpx.Response,
                    first: str='ul',
                    first_class: str='pagination justify-content-center',
                    second: str='li'
                    ) -> Tuple[int,str]:
        soup = BeautifulSoup(response, 'html.parser')

        element=soup.find_all(first,class_=first_class)
        # logger.debug(f'''operation: soup.find_all({first},class_={first_class})\n
        #              result: {element}, on {response.url}''')
        if not element:
            logger.error(f'Cant load last page,cant find {first} with class {first_class}')
            raise NoPagesFound()
        page_list=element[0].find_all(second)
        if not page_list:
            logger.error(f'Cant load last page,cant find {second} in {element[0]}')
            raise NoPagesFound()
        
        last_link=page_list[-1].find('a')
        if not last_link:
            logger.error(f'cant find "a" tag in {page_list[-1]}')
            raise NoPagesFound(f"Missing <a> tag in {response.url}")
        last_page_link=last_link.get('href')
        if not last_page_link:
            logger.error(f'cant find link href in {last_link}')
            raise NoPagesFound(f"Missing href in last page link")
        match=re.search(r'\d+',last_page_link)
        if not match:
            logger.error(f'cant find page number in {last_page_link}')
            raise ValueError()
        total_pages=int(match.group())

        logger.info(f'Number of pages: {total_pages}, on {response.url}')

        return total_pages,last_page_link