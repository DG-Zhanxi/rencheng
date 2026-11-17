"""Huawei RDS PostgreSQL and DCS Redis adapters, configured server-side."""
import os,sqlite3,time
from pathlib import Path
class PGCursor:
 def __init__(self,c,lastrowid=None):self.c=c;self.lastrowid=lastrowid
 def fetchone(self):return self.c.fetchone()
 def fetchall(self):return self.c.fetchall()
 def __iter__(self):return iter(self.c)
class PGConnection:
 def __init__(self,url):
  import psycopg
  from psycopg.rows import dict_row
  self.c=psycopg.connect(url,row_factory=dict_row,connect_timeout=10)
 def __enter__(self):return self
 def __exit__(self,*args):
  if args[0]:self.c.rollback()
  else:self.c.commit()
  self.c.close()
 def execute(self,sql,params=()):
  sql=sql.replace('?', '%s')
  if sql.startswith('INSERT OR REPLACE INTO objects'):
   sql=sql.replace('INSERT OR REPLACE','INSERT')+' ON CONFLICT(id) DO UPDATE SET owner=EXCLUDED.owner,kind=EXCLUDED.kind,body=EXCLUDED.body,created=EXCLUDED.created'
  user_insert=sql.startswith('INSERT INTO users(')
  if user_insert:sql+=' RETURNING id'
  try:
   cur=self.c.execute(sql,params)
   return PGCursor(cur,cur.fetchone()['id'] if user_insert else None)
  except Exception as e:
   if getattr(e,'sqlstate',None)=='23505':raise sqlite3.IntegrityError('duplicate key') from e
   raise
 def executescript(self,script):
  script=script.replace('id INTEGER PRIMARY KEY','id BIGSERIAL PRIMARY KEY').replace(' REAL',' DOUBLE PRECISION')
  for statement in script.split(';'):
   if statement.strip():self.c.execute(statement)
def database(path):
 url=os.getenv('DATABASE_URL','')
 if url:return PGConnection(url)
 c=sqlite3.connect(path,timeout=30);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');return c
def redis_client():
 url=os.getenv('REDIS_URL','')
 if not url:return None
 import redis
 return redis.Redis.from_url(url,decode_responses=True,socket_connect_timeout=3,socket_timeout=3)
def connection_status():
 result={'database':os.getenv('DB_PROVIDER','PostgreSQL') if os.getenv('DATABASE_URL') else 'SQLite WAL','redis':'未配置'}
 if os.getenv('REDIS_URL'):
  try:
   r=redis_client();r.ping();r.set('rencheng:health',str(time.time()),ex=30);result['redis']='连接正常'
  except Exception:result['redis']='连接失败'
 return result
