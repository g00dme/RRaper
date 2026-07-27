import time

import httpx
import logging

logger=logging.getLogger(__name__)

class Crient:
    def __init__(self,base_url='https://www.royalroad.com',auto_login=True,login_data,cookies,headers):
        self.base_url=base_url

        self.login_data = login_data
        self.cookies = cookies
        self.headers = headers

        self.login_url='https://www.royalroad.com/account/login?returnurl=%2Fhome'
        if auto_login:
            self.auth()
        else:
            self.client= httpx.Client(follow_redirects=True)
    def auth(self,base_delay=1,max_retries=5):
        client = httpx.Client(follow_redirects=True)
        logger.info(f'Trying to connect to auth on {self.login_url}')
        logger.debug(f'''Auth parameters:\n
                        cookies: {self.cookies} 
                        headers: {self.headers}
                        login_data: {self.login_data}''')
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
            
            def auth(self):
        client = httpx.Client(follow_redirects=True)
        logger.debug(f'''Trying to connect to {self.base_url+r"/account/login?returnurl=%2Fhome"} with:
                       cookies: {self.cookies} 
                       headers: {self.headers}
                       login_data: {self.login_data}''')
        self.login_response = client.post(self.base_url+r'/account/login?returnurl=%2Fhome',
                                        cookies=self.cookies,headers=self.headers, data=self.login_data)
        self.client=client
        if self.login_response.status_code != 200:
            self.logger.error(f'status code: {self.login_response.status_code}')
            raise  RoyalRoadAuthError('Login failed')
        else:
            logger.info('Succussfully connected client')

