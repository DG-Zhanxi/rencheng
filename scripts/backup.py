from pathlib import Path
import sqlite3,datetime
root=Path(__file__).resolve().parents[1];out=root/'backups';out.mkdir(exist_ok=True)
target=out/('rencheng-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
with sqlite3.connect(root/'data/app.sqlite3') as src,sqlite3.connect(target) as dst:src.backup(dst)
print(target)
