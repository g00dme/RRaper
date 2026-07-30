import logging

from modules.scraper import RRaper

def configure_logging(level=logging.INFO):
    logging.basicConfig(filename='logs.log',
                        level=level,
                        format='%(asctime)s %(levelname)s [%(filename)s:%(funcName)s:%(lineno)d]: %(message)s')
    root=logging.getLogger()

    handler=logging.StreamHandler()
    handler.setLevel(level)

    root.addHandler(handler)

def main():
    configure_logging()
    
    scraper=RRaper()

    result=scraper.load_titles_from_index_page('/my/readlater')
    return result
if __name__ == "__main__":
    main()
