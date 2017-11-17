import io
import os
import csv
import json
import collections
from collections import OrderedDict

from jsonpointer import resolve_pointer

from docutils import nodes
from recommonmark.transform import AutoStructify
from docutils.parsers.rst import directives, Directive
from docutils.parsers.rst.directives.tables import CSVTable


class AutoStructifyLowPriority(AutoStructify):
    """
    We need this low priority copy of AutoStructify to apply some transforms
    after translations.
    """
    default_priority = 1000


def flatten_dict(obj, path, result, recursive=False):
    if hasattr(obj, 'items'):
        for key, value in obj.items():
            if isinstance(value, dict):
                if recursive:
                    flatten_dict(value, path + '/' +key, result, recursive=recursive)
            elif isinstance(value, list):
                if isinstance(value[0], dict):
                    if recursive:
                        for num, sub_value in enumerate(value):
                            flatten_dict(value, path + '/' + key + '/' + str(num), result, recursive=recursive)
                else:
                    result[path + '/' + key] = ", ".join(value)
            else:
                result[path + '/' + key] = value


class JSONIncludeFlat(CSVTable):
    option_spec = {
        'jsonpointer': directives.unchanged,
        'title': directives.unchanged,
        'exclude': directives.unchanged,
        'recursive': directives.flag,
        'include_only': directives.unchanged,
        'ignore_path': directives.unchanged,
    }

    def make_title(self):
        return None, []

    def get_csv_data(self):
        file_path = self.arguments[0]
        with open(file_path) as fp:
            json_obj = json.load(fp, object_pairs_hook=OrderedDict)
        filename = str(file_path).split("/")[-1].replace(".json","")
        pointed = resolve_pointer(json_obj, self.options['jsonpointer'])
        if(self.options.get('exclude')):
            for item in self.options['exclude'].split(","):
                try:
                    del pointed[item.strip()]
                except KeyError as e:
                    pass
        if(self.options.get('include_only')):
            for node in list(pointed):
                if not (node in self.options.get('include_only')):
                    del pointed[node]
        csv_data = []

        ignore_path = self.options.get('ignore_path', ' ')

        if isinstance(pointed, dict):
            result = collections.OrderedDict()
            flatten_dict(pointed, self.options['jsonpointer'], result, 'recursive' in self.options)
            if ignore_path:
                csv_data.append([heading.replace(ignore_path, "") for heading in result.keys()])
            else:
                csv_data.append(result.keys())
            csv_data.append(list(result.values()))

        if isinstance(pointed, list):
            for row in pointed:
                result = collections.OrderedDict()
                flatten_dict(row, self.options['jsonpointer'], result, 'recursive' in self.options)
                csv_data.append(list(result.values()))
            if ignore_path:
                csv_data.insert(0, [heading.replace(ignore_path, "") for heading in result.keys()])
            else:
                csv_data.insert(0, result.keys())


        output = io.StringIO()
        output_csv = csv.writer(output)
        for line in csv_data:
            output_csv.writerow(line)
        self.options['header-rows'] = 1
        return output.getvalue().splitlines(), file_path


class CSVTableNoTranslate(CSVTable):
    def get_csv_data(self):
        lines, source = super().get_csv_data()
        return lines, None


class DirectoryListDirective(Directive):
    option_spec = {
        'path': directives.unchanged,
        'url': directives.unchanged,
    }

    def run(self):
        bl = nodes.bullet_list()
        for fname in os.listdir(self.options.get('path')):
            bl += nodes.list_item('', nodes.paragraph('', '', nodes.reference('', '',
                    nodes.Text(fname),
                    internal=False,
                    refuri=self.options.get('url') + fname, anchorname='')))
        return [bl]