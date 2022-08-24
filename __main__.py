from json import dumps as encodeJson, loads as decodeJson
import sys
import os
from clases import Object


def disablePrint():
    sys.stdout = open(os.devnull, 'w')


def enablePrint():
    sys.stdout = sys.__stdout__


def readJSON(file):
    with open(file, 'r') as file:
        ret = decodeJson(file.read())
    return ret


def unfold(obj, ret={}, prefix=''):
    if type(obj) == dict:
        for x in obj:
            if type(obj[x]) != dict or obj[x] == {}:
                ret[f'{prefix}{"." if prefix != "" else ""}{x}'] = obj[x]
            else:
                ret = unfold(obj[x], ret, f'{prefix}{"." if prefix != "" else ""}{x}')
    return ret


def fold(obj):
    ret, c = {}, "'"
    for entry in obj:
        tmp = entry.split('.')
        for x in range(len(tmp)):
            if not eval(f'\'{tmp[x]}\' in ret{"".join(f"[{c}{k}{c}]" for k in tmp[:x])}'):
                exec(f'ret{"".join(f"[{c}{k}{c}]" for k in tmp[:x+1])} = {{}}')
        exec(f'ret{"".join(f"[{c}{k}{c}]" for k in tmp)} = obj[entry]')
    return ret


# CLI
if __name__ == '__main__':
    from sys import argv
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
        from openpyxl.styles import NamedStyle, PatternFill, Font, Alignment
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
            ws.append([k for k in report[0].keys()])
            collect = []
            for r in report:
                uq = '||'.join(c for c in r.values())
                if uq not in collect:
                    ws.append([c for c in r.values()])
                    collect.append(uq)
            fr = ws['B2']
            ws.freeze_panes = fr
            ws.auto_filter.ref = ws.dimensions
            custom_header = NamedStyle(name="custom_header")
            custom_header.fill = PatternFill("solid", fgColor="000000")
            custom_header.font = Font(color="FFFFFF")
            custom_header.alignment = Alignment(vertical="center")
            normal_cell = NamedStyle(name="normal_cell")
            normal_cell.alignment = Alignment(vertical="center")
            firstRow = ws['1']
            for cell in firstRow:
                cell.style = custom_header
            ws.row_dimensions[1].height = 23
            for i, row in enumerate([c for c in ws.iter_rows()][1:]):
                ws.row_dimensions[i+2].height = 23
                for cell in row:
                    cell.style = normal_cell
            for coll in ws.columns:
                length = max(len(str(cell.value)) for cell in coll)
                ws.column_dimensions[coll[0].column_letter].width = length if length > 15 else 15
            wb.save(fileOut)
    elif mode == 'export' and len(attr) > 0:
        import re
        rx = re.compile(r'\s+?\#[\s|@]+?(DEV|dev|PROD|prod)')
        rp = re.compile(r'(#[\s|\t]+|#)')
        op = attr[0]
        buildedFile = []
        with open(op, 'r') as content:
            content = content.read()
            for line in content.split('\n'):
                matches = [c.string for c in rx.finditer(line)]
                replacers = [c.string for c in rp.finditer(line)]
                if len(matches) > 0:
                    if 'dev' not in matches[0].lower():
                        for r in replacers:
                            line = line.replace(r, '')
                            print(r)
                        print(line)
                    else:
                        continue
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
