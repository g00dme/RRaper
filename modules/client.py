import time

import httpx
import logging

logger=logging.getLogger(__name__)

class Client:
    def __init__(self,login_data,cookies,headers,base_url='https://www.royalroad.com',auto_login=True):
        self.base_url=base_url

        self.login_data = login_data
        self.cookies = cookies
        self.headers = headers

        self.login_url=r'https://www.royalroad.com/account/login?returnurl=%2Fhome'
        if auto_login:
            self.auth()
        else:
            self.client= httpx.Client(follow_redirects=True)
    def auth(self,base_delay=1,max_retries=5):
        client = httpx.Client(follow_redirects=True)
        logger.info(f'Trying to connect to auth on {self.login_url}')
        for tries in range(1,max_retries+1):
            try:
                self.login_response = client.post(self.login_url,
                                                cookies=self.cookies,
                                                headers=self.headers,
                                                data=self.login_data)
                self.login_response.raise_for_status()

                logger.info('Succussfully connected client ✅')
                self.client=client
                return
            except httpx.HTTPStatusError as e:
                delay=base_delay*(2**tries)
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    logger.warning(f'''error on auth status code: {e.response.status_code} 
                                   retrying in {delay} , attempt {tries}/{max_retries}''')
                    time.sleep(delay)
                else:
                    logger.error(f'error on auth status code: {e.response.status_code}')
                    raise
            except httpx.TimeoutException as e:
                if tries==max_retries:
                    logger.error(f'Connection timed out, tried {tries}/{max_retries}')
                    raise 
                delay=base_delay*(2**tries)
                logger.warning(f'''timeout excepcion for posting on:{self.login_url} 
                                \n retrying in {delay} , attempt {tries}/{max_retries}''')
                time.sleep(delay)
                
            except Exception as e:
                logger.error('Something went wrong when trying to authenticate with POST ❌')
                raise 
    def load_page(self,
                  link: str,
                  base_delay: int=1,
                  max_retries: int=5,
                  timeout: int=15,
                  new_base: str=None,
                  write: bool=False,
                  file_name: str='output.html'
                  ) -> httpx.Response:
        if link.startswith(('http://', 'https://')):
            url = link
        else:
            url = (new_base or self.base_url) + link
        for tries in range(1,max_retries+1):
            try:
                response=self.client.get(url,timeout=timeout)
                logger.debug(f'loaded:{url}')
                if tries>1:
                    logger.info(f'Successfully loaded:{url} after {tries} retries')
                if response.url !=url:
                    logger.error(f'Loaded wrong page, {response.url}, instead of {url}')
                    continue
                if write==True:
                    with open(file_name,'w') as f:
                        f.write(response.text)

                return response
            except httpx.TimeoutException as e:
                delay=base_delay*(2**tries)
                logger.warning(f'''timeout excepcion for:{url} 
                               \n retrying in {delay} , attempt {tries}/{max_retries}''')
                if tries == max_retries:
                    logger.error(f'Failed to load {url} after {max_retries} attempts')
                    raise   
                else:
                    time.sleep(delay)
            except httpx.HTTPStatusError as e:
                delay=base_delay*(2**tries)
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    logger.warning(f'''error status code: {e.response.status_code} link:{url} \n 
                                   retrying in {delay} , attempt {tries}/{max_retries}''')
                    if tries == max_retries:
                        logger.error(f'Error status code: {e.response.status_code} {url} after {max_retries} attempts')
                        raise   
                    else:
                        time.sleep(delay)
                else:
                    logger.error(f'error status code: {e.response.status_code} link:{url}')
                    raise
            except httpx.RequestError as e:
                delay=base_delay*(2**tries)
                logger.warning(f'''error during request to link:{url}\n
                               retrying in {delay} , attempt {tries}/{max_retries}''')
                if tries == max_retries:
                    logger.error(f'Request issue, failed to load {url} after {max_retries} attempts')
                    raise 
                else:
                    time.sleep(delay)
            except Exception as e:
                logger.error(f'unexpected error loading: {url}')
                raise    
    def close_client(self):
        if isinstance(self.client, httpx.Client):
            self.client.close()
            self.client = None
            print("Client connection closed.")