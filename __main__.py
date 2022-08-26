from clases import Object
from utils import readJSON, fold, unfold, enablePrint, disablePrint, encodeJson
import re

# CLI
if __name__ == '__main__':
    from sys import argv
    from mgprint import mprint
    mode = argv[1]
    attr = argv[2:]
    if mode == 'buildExamples' and len(attr) >= 1:
        from itertools import product as combinator
        input = attr[0]
        output = attr[1] if len(attr) > 1 else 'out_'+input
        contentData = readJSON(input)
        base = {}
        variations = []
        cases = []
        if type(contentData) == dict:
            contentData = [contentData]
        for content in contentData:
            for key, value in unfold(content).items():
                if type(value) == list:
                    variations.append([[key, v] for v in value])
                else:
                    base[key] = value
            for case in combinator(*variations):
                tmp = {k: v for k, v in case}
                tmp = {**base, **tmp}
                cases.append(fold(tmp))
        file = open(output, 'w+')
        file.write(encodeJson({'documents': cases}, indent=4))
        file.close()
    elif mode == 'runTest' and len(attr) > 0:
        from sys import argv
        from database import db
        from openpyxl import Workbook
        # from openpyxl.styles import NamedStyle, PatternFill, Font, Alignment
        from utils import xlsxFormatter
        opname = attr[0].split('.py')[0]
        fileOut = f'./{opname}_test.xlsx'
        configFile = attr[1] if len(attr) > 1 else None
        if configFile:
            fileOut = f"{''.join(configFile.split('/')[-1].split('.')[:-1])}.xlsx"
            configFile = readJSON(configFile)
        operation_test = {}
        report = []
        exec(f'import {opname} as operation_test')
        disablePrint()
        for fil in db.getRows('documents'):
            ret = operation_test.run(fil.uuid)
            tmp = fil.debug(ret)
            tmp = tmp if configFile is None else {k: tmp[v] for k, v in configFile.items() if v in tmp}
            report.append({**tmp})
        enablePrint()
        if len(report) > 0:
            wb = Workbook()
            ws = wb.active
            head = [k for k in report[0].keys()]
            ws.append(head)
            collect = []
            for r in report:
                values = [str(r[k]) if k in r else '' for k in head]
                uq = '||'.join(values)
                if uq not in collect:
                    ws.append(values)
                    collect.append(uq)
            xlsxFormatter(ws)
            wb.save(fileOut)
    elif mode == 'export' and len(attr) > 0:
        from utils import uncomment, deleteComment, matchRgx
        op = attr[0]
        buildedFile = []
        with open(op, 'r') as content:
            content = content.read()
            for line in content.split('\n'):
                matches = matchRgx(line, r'\s+?\#\s+?@\w+[^\n]+$')
                if len(matches) > 0:
                    if any(r in line for r in ('@dev', '@DEV', '@Dev')):
                        continue
                    elif any(r in line for r in ('@prod', '@PROD', '@Prod')):
                        line = deleteComment(uncomment(line))
                    else:
                        line = deleteComment(line)
                buildedFile.append(line)
        with open(f'{op}.export', 'w+') as file:
            file.write('\n'.join(buildedFile))
else:
    from database import db
    File = Object(
        objects=Object(
            get=lambda uuid: db.getRow('documents', lambda doc: str(doc.uuid) == str(uuid)),
            first=lambda: db.getRows('documents')[0],
            last=lambda: db.getRows('documents')[-1],
            all=lambda: db.getRows('documents')
        )
    )
