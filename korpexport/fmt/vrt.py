#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

from .formatter import KorpExportFormatter


__all__ = ["KorpExportFormatterVRT"]


class KorpExportFormatterVRT(KorpExportFormatter):

    formats = ["vrt"]
    mime_type = "text/plain"
    filename_extension = ".vrt"
    structured_format = True

    _option_defaults = {
        "header_format": (u"<?xml version=\"1.0\" encoding=\"UTF-8\" "
                          u"standalone=\"yes\"?>\n"
                          u"<!-- Date: {date} -->\n"
                          u"<!-- Query parameters: {params} -->\n"
                          u"<!-- Total hits: {hitcount} -->\n"
                          u"<korp_kwic>\n"),
        "footer_format": u"</korp_kwic>\n",
        "token_format": u"{structs_open}{word}\t{attrs}\n{structs_close}",
        "token_sep": "",
        "attr_sep": u"\t",
        # FIXME: This adds MATCH tags before any opening tags and
        # aftore any closing tags in match.
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
