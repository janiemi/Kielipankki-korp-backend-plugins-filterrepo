# -*- coding: utf-8 -*-

"""
Format Korp query results in various delimited fields formats.

This module contains Korp result formatters for CSV (sentence per
line), CSV tokens (token per line), TSV (sentence per line).

:Author: Jyrki Niemi <jyrki.niemi@helsinki.fi> for FIN-CLARIN
:Date: 2014
"""


from __future__ import absolute_import

import korpexport.queryresult as qr
from korpexport.formatter import KorpExportFormatter


__all__ = ['KorpExportFormatterCSV',
           'KorpExportFormatterCSVTokens',
           'KorpExportFormatterTSV']


# TODO: Reorganize the classes so that we could more easily have both
# comma- and tab-separated versions of both sentence per line and
# token per line formats.


class KorpExportFormatterDelimited(KorpExportFormatter):

    """
    Format Korp query results in a delimited fields format.

    The superclass for actual formatters of delimited-fields formats.

    The formatter uses the following options (in `_option_defaults`)
    in addition to those specified in :class:`KorpExportFormatter`:
        delimiter (str): The delimiter with which to separate fields
        quote (str): The quote character around fields
        replace_quote (str): The string with which to replace quote
            characters occurring in field values

    The fields returned by the formatting methods should be delimited
    by tabs; they are converted to the final delimiter in
    `_postprocess`.
    """

    _option_defaults = {
        "content_format": u"{sentence_field_headings}{sentences}\n\n{info}",
        "infoitem_format": u"## {label}:{sp_or_nl}{value}",
        "title_format": u"## {title}\n",
        "param_format": u"##   {label}: {value}",
        "param_sep": "\n",
        "sentence_format": u"{fields}",
        "sentence_sep": "\n",
        "sentence_fields": ("corpus,match_pos,left_context,match,"
                            "right_context,?aligned,*structs"),
        "sentence_field_sep": "\t",
        "delimiter": u",",
        "quote": u"\"",
        "replace_quote": u"\"\"",
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)

    def _postprocess(self, text):
        """Add quotes around fields in `text` if specified.

        Add the quotes specified with option ``quotes`` and convert
        tabs to the final field separator.
        """
        # FIXME: This does not work correctly if fields are not quoted
        # but the field separator is other than the tab
        if self._opts["quote"]:
            return "\n".join(self._quote_line(line)
                             for line in text.split("\n"))
        else:
            return text

    def _quote_line(self, line):
        """Add quotes around the fields (separated by tabs) in `line`."""
        if line == "":
            return line
        else:
            return self._opts["delimiter"].join(self._quote_field(field)
                                                for field in line.split("\t"))

    def _quote_field(self, text):
        """Add quotes around `text` and replace quotes within `text`."""
        quote = self._opts["quote"]
        return quote + text.replace(quote, self._opts["replace_quote"]) + quote


class KorpExportFormatterCSV(KorpExportFormatterDelimited):

    r"""
    Format Korp results in comma-separated values format, sentence per line.

    Handle the format type ``csv``.

    The result uses \r\n as newlines, as it is specified in RFC 4180.
    """

    formats = ["csv"]
    mime_type = "text/csv"
    filename_extension = ".csv"

    _option_defaults = {
        "newline": "\r\n",
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatterDelimited.__init__(self, *args, **kwargs)


class KorpExportFormatterCSVTokens(KorpExportFormatterCSV):

    r"""
    Format Korp results in comma-separated values format, token per line.

    Handle the format type ``csv_tokens`` == ``csvp``.

    The formatter uses the following additional option:
        match_field (int): The position of the match marker field: if
            empty, no match marker field; if 0, as the first field;
            otherwise as the last field
    """

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
        # Skip empty fields or fields containing only spaces
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
        """Add a match field to ``token_fields`` based on ``match_field``."""
        super(KorpExportFormatterCSVTokens, self)._adjust_opts()
        if self._opts["match_field"]:
            if self._opts["match_field"] == "0":
                self._opts["token_fields"][0:0] = ["match_mark"]
            else:
                self._opts["token_fields"].append("match_mark")


class KorpExportFormatterTSV(KorpExportFormatterDelimited):

    """
    Format Korp results in tab-separated values format, sentence per line.

    Handle the format type ``tsv``.
    """

    formats = ["tsv"]
    mime_type = "text/tsv"
    filename_extension = ".tsv"

    _option_defaults = {
        "delimiter": u"\t",
        "quote": u"",
        "replace_quote": u""}

    def __init__(self, *args, **kwargs):
        KorpExportFormatterDelimited.__init__(self, *args, **kwargs)
