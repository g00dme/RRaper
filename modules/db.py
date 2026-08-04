import logging
import sqlite3
from typing import List

logger=logging.getLogger(__name__)
class RRDB:
    def __init__(self,db_name):
        self.db_name=db_name
        self.titles='Titles'
        self.categories='Cat_long'
        self.titles_col=['link', 'id', 'tags', 'created_at', 'Overall_Score', 'Style_Score',
                        'Story_Score', 'Grammar_Score', 'Character_Score', 'Tot_Views',
                        'Avr_Views', 'Followers', 'Favorites', 'Ratings', 'Pages', 'title']
        self.col_except_id=[col for col in self.titles_col if col !='id']
        self._con=None
        self._init_db()
    @property
    def con(self):
        if self._con is None:
            self._con=sqlite3.connect(self.db_name)
        return self._con
    def _init_db(self):
        self.con.executescript(
            '''CREATE TABLE IF NOT EXISTS Titles(
                link TEXT,
                id INTEGER PRIMARY KEY,
                tags TEXT,
                created_at TEXT,
                Overall_Score REAL,
                Style_Score REAL,
                Story_Score REAL,
                Grammar_Score REAL,
                Character_Score REAL,
                Tot_Views INTEGER,
                Avr_Views INTEGER,
                Followers INTEGER,
                Favorites INTEGER,
                Ratings INTEGER,
                Pages INTEGER,
                title TEXT);

                CREATE TABLE IF NOT EXISTS Cat_long(
                title_id INTEGER,
                category TEXT,
                PRIMARY KEY(title_id, category),
                FOREIGN KEY(title_id) REFERENCES Titles(id) ON DELETE CASCADE);''')
        self.con.commit()
    def add_titles(self,
                    data: tuple):
        if not data:
            logger.info('Passed empty tuple, no titles to add')
            return 0
        cur=self.con.cursor()

        placeholders=', '.join(['?' for _ in range(len(data[0]))])
        columns=', '.join(self.titles_col)
        
        update=[f'{col}=excluded.{col}' for col in self.col_except_id]
        response=cur.executemany(f'''INSERT INTO {self.titles} ({columns}) VALUES ({placeholders})
                                ON CONFLICT(id) DO UPDATE SET {', '.join(update)}'''
                                ,data)
        self.con.commit()
        return response
    def add_category(self,data):
        '''takes tuple or list, first value is Title id, second category name'''
        cur=self.con.cursor()
        response=cur.executemany(f'''INSERT OR IGNORE INTO {self.categories} VALUES(?,?)''',(data))
        self.con.commit()
        return response
    def transform_titles(self,titles: dict) -> List[tuple]:
        data=[]
        for title, meta in titles.items():
            meta['title']=title
            if type(meta['tags'])==list:
                meta['tags']="|".join(meta['tags'])
            values=tuple(meta.values())
            data.append(values)
        return data
    def query_titles(self,
                       category_name: str=None,
                       select: str='*',
                       where: str=None,
                       groupby: str=None) -> tuple:
        cur=self.con.cursor()
        cond=[]
        if category_name:
             cond.append(f"{self.categories}.category = '{category_name}'")
        if where:
             cond.append(f'{where}')
        cond=' AND '.join(cond)
        
        response=cur.execute(f'''
                    SELECT {select}
                    FROM {self.titles}
                    JOIN {self.categories} ON {self.titles}.id={self.categories}.title_id 
                         
                    {f'WHERE {cond}' if cond else ''}
                    {f'GROUP BY {groupby} ' if groupby is not None else ""}
                    ''')
        response=response.fetchall()
        return response
    def delete_titles(self,
                     ids: list,
                     names: list,
                     days: int=None):
        cond=[]
        params=[]
        if days is not None:
            cond.append('(julianday("now") - julianday(created_at)) > ?')
            params.append(days)
        if names:
                    cond.append(f'title IN ({', '.join(['?' for _ in names])})')
                    params.extend(names)
        if ids:
                    cond.append(f'id IN ({', '.join(['?' for _ in ids])})')
                    params.extend(ids)
        if not cond:
             logger.info('No condition supplied, so nothing to delete')
             return
        cond=' OR '.join(cond)
        sql=f'''
            DELETE FROM {self.titles}
            WHERE {cond}
            '''
        cur=self.con.cursor()
        logger.info(f'Executing {sql} with params: {params}')
        response=cur.execute(sql,params)
        self.con.commit()
        logger.info(f'Deleted {response.rowcount} rows')
        return response
