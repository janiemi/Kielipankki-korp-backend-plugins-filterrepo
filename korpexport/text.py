#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

from .exporter import KorpFormatter


class KorpFormatterText(KorpFormatter):

    _formats = ["text"]
    _mime_type = "text/plain"
    _filename_extension = ".txt"
    _option_defaults = {
        "header_format": u"## Date: {date}\n## Query parameters: {params}\n",
        "footer_format": "",
        "sentence_format": (u"{corpus} [{match_pos}]: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context} || {structs}\n"),
        "match_open": " <<< ",
        "match_close": " >>> ",
        "struct_separator": " | "}

    def __init__(self, *args, **kwargs):
        KorpFormatter.__init__(self, *args, **kwargs)
