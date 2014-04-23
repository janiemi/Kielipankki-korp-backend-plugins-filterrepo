#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

from korpexport.formatter import KorpExportFormatter


__all__ = ["KorpExportFormatterVRT"]


class KorpExportFormatterVRT(KorpExportFormatter):

    formats = ["vrt"]
    mime_type = "text/plain"
    filename_extension = ".vrt"
    structured_format = True

    _option_defaults = {
        # Currently no XML declaration since the result is not
        # necessarily even well-formed XML
        "content_format": (u"{info}\n<!-- {token_field_headings} -->\n"
                           u"<korp_kwic>\n{sentences}</korp_kwic>\n"),
        "infoitem_format": u"<!-- {label}:{sp_or_nl}{value} -->",
        "param_format": u"       {label}: {value}",
        "param_sep": "\n",
        "token_format": u"{structs_open}{fields}\n{structs_close}",
        "token_field_sep": "\t",
        "token_sep": "",
        "attr_sep": u"\t",
        # FIXME: This adds MATCH tags before any opening tags and
        # aftore any closing tags in match. It might require a
        # customized _format_sentence to get it right.
        "sentence_format": (u"{left_context}<MATCH position=\"{match_pos}\">\n"
                            u"{match}</MATCH>\n{right_context}"),
        "token_struct_open_noattrs_format": u"<{name}>\n",
        "token_struct_open_attrs_format": u"<{name} {attrs}>\n",
        "token_struct_close_format": u"</{name}>\n",
        "token_struct_attr_format": u"{name}=\"{value}\"",
        "token_struct_attr_sep": u" ",
        "combine_token_structs": "True"
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)

    # FIXME: Close open tags if the struct attribute value for a
    # sentence is different from the currently open one. Maybe also
    # add start tags for such struct attribute values; but how to know
    # the order of structures as structs is a dict?
