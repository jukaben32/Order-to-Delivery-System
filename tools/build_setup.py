import sys
sys.path.insert(0, sys.argv[1])
from n8nbuild import *

MOVE_COLS = ['Movement_ID', 'Time', 'SKU', 'Product', 'Type', 'Qty', 'Stock_After', 'Unit_Cost', 'Value', 'Ref_ID', 'Notes', 'Source']
base = 'https://sheets.googleapis.com/v4/spreadsheets/' + SHEET_ID

w = Wf('TmpSetupSheet001', 'TEMP - Demo Traders add inventory ledger')
a = w.add(manual('Start setup'))
b = w.add(http_sheets('Add Inventory_Movements tab', 'POST', base + ':batchUpdate',
                      {'requests': [{'addSheet': {'properties': {'title': 'Inventory_Movements'}}}]}))
c = w.add(http_sheets('Write movement headers', 'PUT', base + '/values/Inventory_Movements!A1:L1?valueInputOption=RAW',
                      {'values': [MOVE_COLS]}))
d = w.add(http_sheets('Write Cost header', 'PUT', base + '/values/Products!I1?valueInputOption=RAW',
                      {'values': [['Cost']]}))
w.chain(a, b, c, d)
w.save(sys.argv[2])
