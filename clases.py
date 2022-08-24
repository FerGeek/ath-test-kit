from json import dumps as encodeJson, loads as decodeJson
from uuid import uuid4, UUID


def metaformat(m):
    return m if 'metadata.' in m else f'metadata.{m}'


class Object(object):
    def __init__(self, **kargs):
        for k, v in kargs.items():
            self.__dict__[k] = v

    def __dict(self):
        ret = {}
        for k, v in self.__dict__.items():
            if type(v) != dict:
                ret[k] = v
            else:
                ret[k] = self.__dict(v)
        return ret

    def json(self):
        return self.__dict()


class Document(Object):
    def __init__(self, uuid=None, meta={}, lfState='Draft', author=None):
        super()
        self.__dict__['life_cycle_state'] = Object(name=lfState)
        self.__dict__['author'] = author or Object(email='')
        self.__initialState__ = lfState
        self.__dict__['uuid'] = UUID(uuid) if type(uuid) == str else uuid if uuid is not None else uuid4()
        self.__dict__['__meta__'] = {metaformat(k): v for k, v in meta.items()}
        self.__events__ = []

    def gmv(self, meta):
        return self.__dict__['__meta__'][meta] if meta in self.__dict__['__meta__'] else None

    def set_metadata(self, name, value, *args, **kargs):
        tmp = self.gmv(name)
        value = str(value)
        self.__dict__['__meta__'][name] = value
        self.__events__.append([[args, kargs], f'set_metadata("{name}") from "{tmp}" to "{value}"'])
        return value

    def change_life_cycle_state(self, name, *args, **kargs):
        tmp = self.life_cycle_state.name
        self.life_cycle_state.name = name
        self.__events__.append([[args, kargs], f'change_life_cycle_state("{name}") from "{tmp}" to "{name}"'])

    def addEventDebug(self, args, event):
        self.__events__.append([args, event])

    def getDebugData(self):
        return self.__events__

    def debug(self, additionalData):
        msg = additionalData['msg'] if 'msg' in additionalData else None
        msg_type = additionalData['msg_type'] if 'msg_type' in additionalData else None
        ret_redirect = additionalData['redirect'] if 'redirect' in additionalData else None
        return {
            'uuid': str(self.uuid),
            **self.__dict__['__meta__'],
            'initialState': self.__initialState__,
            'finalState': self.life_cycle_state.name,
            'internalExecutions': '\n'.join(d + f' | ARGS[{args}]' for args, d in self.__events__),
            'msg': msg,
            'msg_type': msg_type,
            'redirect': ret_redirect,
        }


class Database:
    def __init__(self, file):
        self.__file__ = file
        self.__content__ = {}
        content = decodeJson(open(file, 'r',  encoding='utf8').read())
        for table, contents in content.items():
            for ele in contents:
                if table == 'documents':
                    if 'uuid' in ele:
                        del ele['uuid']
                    ele = Document(**{**ele, 'author': Object(**ele['author'])})
                self.insert(ele, table, False)

    def insert(self, ele, table, update=True):
        if table in self.__content__:
            self.__content__[table].append(ele)
        else:
            self.__content__[table] = [ele]
        if update:
            self.__update__()

    def getRow(self, table=None, cond=lambda x: True):
        content = self.getRows(table, cond)
        if len(content) == 0:
            print('File not found')
        return content[0] if len(content) > 0 else None

    def getRows(self, table=None, cond=lambda x: True):
        if table in self.__content__ and table is not None:
            return [x for x in self.__content__[table] if cond(x)]
        else:
            return []

    def commit(self):
        self.__update__()

    def reload(self):
        self.__init__(self.__file__)

    def __update__(self):
        with open(self.__file__, 'w+') as file:
            file.write(encodeJson(self.__content__))
