#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

from korpexport.formatter import KorpExportFormatter


class KorpExportFormatterText(KorpExportFormatter):

    formats = ["text"]
    mime_type = "text/plain"
    filename_extension = ".txt"

    _option_defaults = {
        "content_format": u"{info}{sentences}",
        "title_format": u"## {title}\n",
        "infoitems_format": u"{title}\n{infoitems}\n\n",
        "infoitem_format": u"## {label}:{sp_or_nl}{value}",
        "param_format": u"##   {label}: {value}",
        "param_sep": "\n",
        "sentence_format": (u"{corpus} [{match_pos}]: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context} || {structs}\n"),
        "match_open": " <<< ",
        "match_close": " >>> ",
        "struct_sep": " | "
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)
