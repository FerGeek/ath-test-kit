from json import dumps as encodeJson, loads as decodeJson
from uuid import uuid4, UUID
from utils import qs
from utils import reduce
from utils import metaformat
from utils import dateFromISO
from time import time


class Object(object):
    def __init__(self, **kargs):
        for k, v in kargs.items():
            self.__dict__[k] = v if type(v) != dict else Object(**v)

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


class Metadata(Object):
    def __init__(self, name, value):
        self.name = name,
        self.value = value

    def set_value(self, value):
        self.value = value

    def __str__(self):
        return self.name


class Document(Object):

    def __init__(self, uuid=None, filename=None, meta={}, state='finished', lfState='Draft', author=None, creationDate=None, modifiedDate=None):
        super()
        self.modified_date = dateFromISO(modifiedDate)
        self.creation_date = dateFromISO(creationDate)
        self.__dict__['author'] = author or Object(email='')
        self.__initialState__ = lfState
        self.__dict__['state'] = state
        self.__dict__['uuid'] = UUID(uuid) if type(uuid) == str else uuid if uuid is not None else uuid4()
        self.__dict__['__meta__'] = {metaformat(k): v for k, v in meta.items()}
        self.__dict__['life_cycle_state'] = Object(name=lfState)
        self.__events__ = []
        self.__logContent__ = []
        self.filename = filename or f'TEST-DOCUMENT ({str(self.uuid)[-5:]})'

    def gmv(self, meta):
        return self.__dict__['__meta__'][meta] if meta in self.__dict__['__meta__'] else None

    def set_metadata(self, name, value, *args, **kargs):
        tmp = self.gmv(name)
        value = str(value)
        self.__dict__['__meta__'][name] = value
        self.__events__.append([[args, kargs], f'fil.set_metadata("{name}") from "{tmp}" to "{value}"'])
        return value

    def get_state(self):
        return self.state

    def set_state(self, value):
        self.state = value

    def change_life_cycle_state(self, name, *args, **kargs):
        tmp = self.life_cycle_state.name
        self.life_cycle_state.name = name
        self.__events__.append([[args, kargs], f'fil.change_life_cycle_state("{name}") from "{tmp}" to "{name}"'])

    def emulFunction(self, msg, ret=None):
        return lambda *args, **kargs: ret if self.addEventDebug([args, kargs], msg) else ret

    def emulOperation(self, msg, ret=None):
        return Object(run=self.emulFunction(msg, ret))

    def loggerBuilder(self, template='%i'):
        return lambda a='': self.__logContent__.append(reduce(lambda x, y: x.replace(*y), {
            '%input': a,
            '%filename': self.filename,
            '%st': self.life_cycle_state.name,
            '%id': str(self.uuid),
            '%f': self.filename,
            '%t': str(time()),
            '%i': a,
        }.items(), template))

    def addEventDebug(self, args, event):
        self.__events__.append([args, event])
        return True

    def getDebugData(self):
        return self.__events__

    def debug(self, additionalData):
        msg = additionalData['msg'] if 'msg' in additionalData else ''
        msg_type = additionalData['msg_type'] if 'msg_type' in additionalData else ''
        ret_redirect = additionalData['redirect'] if 'redirect' in additionalData else ''
        return {
            'filename': self.filename,
            'uuid': str(self.uuid),
            **self.__dict__['__meta__'],
            'initialState': self.__initialState__,
            'finalState': self.life_cycle_state.name,
            'internalExecutions': '\n'.join(d.replace('()', f'({", ".join([*[qs(a) for a in args[0]], *[k+"="+qs(v) for k, v in args[1].items()]])})') for args, d in self.__events__),
            'log': '\n'.join(self.__logContent__),
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
