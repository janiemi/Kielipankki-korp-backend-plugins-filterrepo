#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import json

import korpexport.queryresult as qr
from .formatter import KorpFormatter


class KorpFormatterJSON(KorpFormatter):

    _formats = ['json']
    _mime_type = 'application/json'
    _filename_extension = '.json'
    _option_defaults = {
        "sort_keys": "True",
        "indent": "4"
        }

    def __init__(self, *args, **kwargs):
        KorpFormatter.__init__(self, *args, **kwargs)

    def format_content(self):
        """Convert query_result to JSON."""
        return (json.dumps(qr.get_sentences(self._query_result),
                           sort_keys=self._get_option_bool("sort_keys"),
                           indent=self._get_option_int("indent"))
                + "\n")
