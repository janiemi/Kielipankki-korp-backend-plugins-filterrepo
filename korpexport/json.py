#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import json

from .exporter import KorpExporter


class KorpExporterJSON(KorpExporter):

    _formats = ['json']
    _mime_type = 'application/json'
    _filename_extension = '.json'

    def __init__(self, *args, **kwargs):
        KorpExporter.__init__(self, *args, **kwargs)

    def make_download_content(self):
        """Convert query_result to JSON."""
        return json.dumps(self._query_result["kwic"], sort_keys=True, indent=4)
