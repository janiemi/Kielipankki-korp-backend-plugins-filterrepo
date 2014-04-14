#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

from .formatter import KorpExportFormatter


class KorpExportFormatterText(KorpExportFormatter):

    formats = ["text"]
    mime_type = "text/plain"
    filename_extension = ".txt"

    _option_defaults = {
        "header_format": u"## Date: {date}\n## Query parameters: {params}\n",
        "footer_format": "",
        "sentence_format": (u"{corpus} [{match_pos}]: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context} || {structs}\n"),
        "match_open": " <<< ",
        "match_close": " >>> ",
        "struct_sep": " | "
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)
