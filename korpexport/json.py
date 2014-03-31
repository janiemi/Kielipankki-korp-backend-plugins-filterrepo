#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import json

from .exporter import KorpExporter


class KorpExporterJSON(KorpExporter):

    _formats = ['json']
    _mime_type = 'application/json'
    _filename_extension = '.json'
    _option_defaults = {
        "sort_keys": "True",
        "indent": "4"
        }

    def __init__(self, *args, **kwargs):
        KorpExporter.__init__(self, *args, **kwargs)

    def format_content(self):
        """Convert query_result to JSON."""
        return json.dumps(self._query_result["kwic"],
                          sort_keys=self._get_option_bool("sort_keys"),
                          indent=self._get_option_int("indent"))
