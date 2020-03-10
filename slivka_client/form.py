import enum
import io
from collections import defaultdict
from typing import Iterable, Iterator

import attr
import requests


class Form:
    def __init__(self,
                 name: str,
                 fields: Iterable['_BaseField'],
                 url: str):
        self._name = name
        self._fields = {field.name: field for field in fields}
        self._url = url
        self._is_template = True
        self._values = defaultdict(list)

    name = property(lambda self: self._name)
    url = property(lambda self: self._url)
    fields = property(lambda self: self._fields.values())

    def __iter__(self) -> Iterator['_BaseField']:
        return iter(self.fields)

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        del self._values[key]

    def copy(self) -> 'Form':
        return Form(self.name, self.fields, self.url)

    def reset(self):
        for _list in self._values.values():
            _list.clear()

    def set(self, key, value):
        if key not in self._fields.keys():
            raise KeyError(key)
        self._values[key] = value

    def append(self, key, value):
        if key not in self._fields.keys():
            raise KeyError(key)
        self._values[key].append(value)

    def extend(self, key, iterable):
        if key not in self._fields.keys():
            raise KeyError(key)
        self._values[key].extend(iterable)

    def submit(self, items, **kwargs) -> str:
        data = self._values.copy()
        data.update(items)
        data.update(kwargs)
        files = {}
        for key, val in data.items():
            if isinstance(val, io.IOBase):
                files[key] = data.pop(key)
        response = requests.post(self._url, data=data, files=files)
        response.raise_for_status()
        return response.json()['uuid']

    def __repr__(self):
        return 'Form(%s)' % self.name


class FieldType(enum.Enum):
    UNDEFINED = 'undefined'
    INTEGER = 'integer'
    INT = 'integer'
    DECIMAL = 'decimal'
    FLOAT = 'decimal'
    BOOLEAN = 'boolean'
    FLAG = 'boolean'
    TEXT = 'text'
    FILE = 'file'
    CHOICE = 'choice'


@attr.s(slots=True, frozen=True)
class _BaseField:
    type = attr.ib(type=FieldType, repr=False)
    name = attr.ib(type=bool)
    label = attr.ib(type=str, default="")
    description = attr.ib(type=str, default="")
    required = attr.ib(type=bool, default=True)
    default = attr.ib(default=None)
    multiple = attr.ib(type=bool, default=False)


@attr.s(slots=True, frozen=True)
class UndefinedField(_BaseField):
    type = attr.ib(default=FieldType.UNDEFINED, init=False, repr=False)
    raw = attr.ib(type=dict, factory=dict)


@attr.s(slots=True, frozen=True)
class IntegerField(_BaseField):
    type = attr.ib(default=FieldType.INTEGER, init=False, repr=False)
    min = attr.ib(type=int, default=None)
    max = attr.ib(type=int, default=None)


@attr.s(slots=True, frozen=True)
class DecimalField(_BaseField):
    type = attr.ib(default=FieldType.DECIMAL, init=False, repr=False)
    min = attr.ib(type=float, default=None)
    max = attr.ib(type=float, default=None)
    min_exclusive = attr.ib(type=bool, default=False)
    max_exclusive = attr.ib(type=bool, default=False)


@attr.s(slots=True, frozen=True)
class TextField(_BaseField):
    type = attr.ib(default=FieldType.TEXT, init=False, repr=False)
    min_length = attr.ib(type=int, default=None)
    max_length = attr.ib(type=int, default=None)


@attr.s(slots=True, frozen=True)
class BooleanField(_BaseField):
    type = attr.ib(default=FieldType.BOOLEAN, init=False, repr=False)


@attr.s(slots=True, frozen=True)
class ChoiceField(_BaseField):
    type = attr.ib(default=FieldType.CHOICE, init=False, repr=False)
    choices = attr.ib(type=list, default=())


@attr.s(slots=True, frozen=True)
class FileField(_BaseField):
    type = attr.ib(default=FieldType.FILE, init=False, repr=False)
    media_type = attr.ib(type=str, default=None)
    media_type_parameters = attr.ib(type=dict, factory=dict)


def _build_form(data_dict, url_factory) -> 'Form':
    return Form(
        name=data_dict['name'],
        fields=map(_build_field, data_dict['fields']),
        url=url_factory(data_dict['URI'])
    )


def _build_field(data_dict):
    field_type = FieldType[data_dict['type'].upper()]
    kwargs = {
        'name': data_dict['name'],
        'required': data_dict['required'],
        'default': data_dict.get('default'),
        'label': data_dict.get('label', ''),
        'description': data_dict.get('description', ''),
        'multiple': data_dict.get('multiple', False)
    }
    if field_type == FieldType.UNDEFINED:
        return UndefinedField(
            **kwargs,
            raw=data_dict
        )
    if field_type == FieldType.INTEGER:
        return IntegerField(
            **kwargs,
            min=data_dict.get('min'),
            max=data_dict.get('max')
        )
    if field_type == FieldType.DECIMAL:
        return DecimalField(
            **kwargs,
            min=data_dict.get('min'),
            max=data_dict.get('max'),
            min_exclusive=data_dict.get('minExclusive', False),
            max_exclusive=data_dict.get('maxExclusive', False)
        )
    if field_type == FieldType.TEXT:
        return TextField(
            **kwargs,
            min_length=data_dict.get('minLength'),
            max_length=data_dict.get('maxLength')
        )
    if field_type == FieldType.BOOLEAN:
        return BooleanField(**kwargs)
    if field_type == FieldType.CHOICE:
        return ChoiceField(
            **kwargs, choices=data_dict['choices']
        )
    if field_type == FieldType.FILE:
        return FileField(
            **kwargs,
            media_type=data_dict.get('mediaType'),
            media_type_parameters=data_dict.get('mediaTypeParameters', {})
        )