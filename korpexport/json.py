#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import json

import korpexport.queryresult as qr
from .formatter import KorpExportFormatter


class KorpExportFormatterJSON(KorpExportFormatter):

    formats = ['json']
    mime_type = 'application/json'
    filename_extension = '.json'

    _option_defaults = {
        "sort_keys": "True",
        "indent": "4"
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)

    def _format_content(self):
        """Convert query_result to JSON."""
        return (json.dumps(qr.get_sentences(self._query_result),
                           sort_keys=self.get_option_bool("sort_keys"),
                           indent=self.get_option_int("indent"))
                + "\n")
