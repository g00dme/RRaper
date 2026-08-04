import logging

from modules.scraper import RRscraper

def configure_logging(level=logging.INFO):
    logging.basicConfig(level=level,
                        format='%(asctime)s %(levelname)s [%(filename)s:%(funcName)s:%(lineno)d]: %(message)s')
    root=logging.getLogger()
    if root.handlers:
        root.handlers.clear()


    handler=logging.StreamHandler()
    handler.setLevel(level)

    logging.getLogger("httpx").setLevel(logging.WARNING)

    root.addHandler(handler)
    handler = logging.handlers.RotatingFileHandler(
    'logs.log', 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
    )
    root.addHandler(handler)

def main():
    configure_logging()
    
    scraper=RRscraper()

    result=scraper.load_titles_to_db_from_index('/my/readlater',category='ReadLater',end_page=1,
                                                skip_less_then_days=7)
    return result,scraper
if __name__ == "__main__":
    main()
