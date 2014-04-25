# -*- coding: utf-8 -*-


from __future__ import absolute_import

import korpexport.queryresult as qr
from korpexport.formatter import KorpExportFormatter


__all__ = ['KorpExportFormatterCSV',
           'KorpExportFormatterCSVTokens',
           'KorpExportFormatterTSV']


class KorpExportFormatterDelimited(KorpExportFormatter):

    _option_defaults = {
        "content_format": u"{sentence_field_headings}{sentences}\n\n{info}",
        "infoitem_format": u"## {label}:{sp_or_nl}{value}",
        "title_format": u"## {title}\n",
        "param_format": u"##   {label}: {value}",
        "param_sep": "\n",
        "sentence_format": u"{fields}",
        "sentence_sep": "\n",
        "sentence_fields": ("corpus,match_pos,left_context,match,"
                            "right_context,?aligned_text,*structs"),
        "sentence_field_sep": "\t",
        "delimiter": u",",
        "quote": u"\"",
        "replace_quote": u"\"\"",
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)

    def _postprocess(self, text):
        if self._opts["quote"]:
            return "\n".join(self._quote_line(line)
                             for line in text.split("\n"))
        else:
            return text

    def _quote_line(self, line):
        if line == "":
            return line
        else:
            return self._opts["delimiter"].join(self._quote_field(field)
                                                for field in line.split("\t"))

    def _quote_field(self, text):
        quote = self._opts["quote"]
        return quote + text.replace(quote, self._opts["replace_quote"]) + quote


class KorpExportFormatterCSV(KorpExportFormatterDelimited):

    formats = ["csv"]
    mime_type = "text/csv"
    filename_extension = ".csv"

    _option_defaults = {
        "newline": "\r\n",
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatterDelimited.__init__(self, *args, **kwargs)


class KorpExportFormatterCSVTokens(KorpExportFormatterCSV):

    # csvp is an alias for csv_tokens
    formats = ["csv_tokens", "csvp"]

    _option_defaults = {
        "newline": "\r\n",
        "content_format": u"{info}{token_field_headings}{sentences}",
        "infoitems_format": u"{title}\n{infoitems}\n\n",
        "field_headings_format": u"{field_headings}\n\n",
        "sentence_format": u"{info}{fields}",
        "sentence_info_format": (u"# {corpus}:"
                                 u" sentence {sentence_id},"
                                 u" position {match_pos};"
                                 u" text attributes: {structs}\n"),
        "sentence_fields": "left_context,match,right_context",
        "sentence_field_format": u"{value}",
        "sentence_field_sep": "",
        "sentence_field_skip": r"\s*",
        "token_format": u"{fields}\n",
        "token_noattrs_format": u"{fields}\n",
        "token_sep": "",
        "token_fields": "word,*attrs",
        "token_field_sep": "\t",
        "struct_format": u"{name}: {value}",
        "match_marker": "*",
        "match_field": "0"
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatterCSV.__init__(self, *args, **kwargs)

    def _adjust_opts(self):
        super(KorpExportFormatterCSVTokens, self)._adjust_opts()
        if self._opts["match_field"]:
            if self._opts["match_field"] == "0":
                self._opts["token_fields"][0:0] = ["match_mark"]
            else:
                self._opts["token_fields"].append("match_mark")


class KorpExportFormatterTSV(KorpExportFormatterDelimited):

    formats = ["tsv"]
    mime_type = "text/tsv"
    filename_extension = ".tsv"

    _option_defaults = {
        "delimiter": u"\t",
        "quote": u"",
        "replace_quote": u""}

    def __init__(self, *args, **kwargs):
        KorpExportFormatterDelimited.__init__(self, *args, **kwargs)
