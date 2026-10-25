"""Export the existing final-paper table specifications, without rewriting the manuscript."""
import csv
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('paper_tables',Path(__file__).with_name('paper_tables.py'))
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
MAPPING={'1':'arms','2':'primary','3':'secondary','4':'crisis_us','5':'yen_tests',
         '6':'yen_comparators','7':'yen_appreciation','8':'yen_tertiles','9':'robustness',
         'C1':'metrics_us','C2':'secondary99','C3':'metrics_yen','C4':'crisis_yen'}
dest=ROOT/'outputs/reproduced/tables'; dest.mkdir(parents=True,exist_ok=True)
cells=[]
for label,name in MAPPING.items():
    table=module.table(name,'en')
    (dest/f'Table_{label}.json').write_text(json.dumps(table,indent=2,ensure_ascii=False),encoding='utf-8')
    with (dest/f'Table_{label}.csv').open('w',newline='',encoding='utf-8-sig') as f:
        csv.writer(f).writerows(table['body'])
    for row,values in enumerate(table['body'],1):
        for col,value in enumerate(values,1):
            cells.append({'table':label,'row':row,'column':col,'displayed_text':str(value)})
with (dest/'all_table_cells.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(cells[0])); w.writeheader(); w.writerows(cells)
print(f'Exported {len(MAPPING)} tables and {len(cells)} cells.')
