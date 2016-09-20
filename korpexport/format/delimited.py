# -*- coding: utf-8 -*-

"""
Format Korp query results in various delimited-fields formats.

This module contains Korp result formatters for logical content in
both sentence per line and token per line, and for concrete
representation as CSV (comma-separated values) and TSV (tab-separated
values).

:Author: Jyrki Niemi <jyrki.niemi@helsinki.fi> for FIN-CLARIN
:Date: 2014
"""


from __future__ import absolute_import

import korpexport.queryresult as qr
from korpexport.formatter import KorpExportFormatter


__all__ = ['KorpExportFormatterDelimitedSentence',
           'KorpExportFormatterDelimitedToken',
           'KorpExportFormatterDelimitedReference',
           'KorpExportFormatterCSV',
           'KorpExportFormatterTSV']


class KorpExportFormatterDelimited(KorpExportFormatter):

    """
    Format Korp query results in a delimited-fields format.

    The base class of actual formatters for delimited-fields formats.

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
        "infoitem_format": u"## {label}:{sp_or_nl}{value}",
        "title_format": u"## {title}\n",
        "param_format": u"##   {label}: {value}",
        "param_sep": "\n",
        "sentence_fields": ("corpus,urn,metadata_link,licence_name,"
                            "licence_link,match_pos,left_context,match,"
                            "right_context,?aligned,*structs"),
        "delimiter": "\t",
        "quote": "",
        "replace_quote": "",
        }

    def __init__(self, **kwargs):
        super(KorpExportFormatterDelimited, self).__init__(**kwargs)

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


class KorpExportFormatterDelimitedSentence(KorpExportFormatterDelimited):

    """
    Format Korp results in a delimited-fields format, sentence per line.

    A logical content formatter class for delimited-fields formats
    with a sentence per line. The sentence fields contain corpus name,
    match position, the match and contexts and structural attributes.
    
    This class does not specify the concrete delimiters; they need to
    be specified in the subclass or in a mix-in class.
    """

    formats = ["sentence_line", "sentences", "fields_sentence"]

    _option_defaults = {
        "content_format": u"{sentence_field_headings}{sentences}\n\n{info}",
        "sentence_format": u"{fields}",
        "sentence_sep": "\n",
        "sentence_fields": ("corpus,?urn,?metadata_link,?licence_name,"
                            "?licence_link,match_pos,left_context,match,"
                            "right_context,?aligned,*structs"),
        "sentence_field_sep": "\t",
    }

    _subformat_options = {
        "lemmas-resultinfo": {
            "show_info": "false",
            "infoitem_format": u"{value}",
            "param_format": u"{key}={value}",
            "param_sep": "; ",
            "infoitems": "date,korp_url",
            "sentence_fields": ("hit_num,corpus,tokens,lemmas_all,?aligned,"
                                "*structs,?urn,?metadata_link,?licence_name,"
                                "date,hitcount,?korp_url,params"),
            "sentence_token_attrs": "lemma",
            "token_format": u"{match_open}{word}{match_close}",
            # "match_open": u"<<<",
            # "match_close": u">>>",
        },
        # Similar to "lemmas-resultinfo" above, but separate columns
        # for matching tokens and context tokens. To combine with
        # lemmas-resultinfo, specify "lemmas-resultinfo,lemmas-kwic"
        # as the subformat.
        "lemmas-kwic": {
            "sentence_fields": (
                "hit_num,corpus,left_context,match,right_context,"
                "lemmas_left_context,lemmas_match,lemmas_right_context,"
                "?aligned,*structs,?urn,?metadata_link,?licence_name,date,"
                "hitcount,?korp_url,params"),
            "sentence_token_attrs": "lemma",
        },
    }

    def __init__(self, **kwargs):
        super(KorpExportFormatterDelimitedSentence, self).__init__(**kwargs)


class KorpExportFormatterDelimitedToken(KorpExportFormatterDelimited):

    r"""
    Format Korp results in a delimited-fields format, token per line.

    A logical content formatter class for delimited-fields formats
    with a token per line. The token fields contain the word and its
    attributes and a possible match marker.

    This class does not specify the concrete delimiters; they need to
    be specified in the subclass or in a mix-in class.

    The formatter uses the following additional option:
        match_field (int): The position of the match marker field: if
            empty, no match marker field; if 0, as the first field;
            otherwise as the last field
    """

    formats = ["token_line", "tokens", "fields_token", "annotations", "annot"]

    _option_defaults = {
        "content_format": u"{info}{token_field_headings}{sentences}",
        "infoitems_format": u"{title}\n{infoitems}\n\n",
        "field_headings_format": u"{field_headings}\n\n",
        "sentence_format": u"{info}{fields}",
        "sentence_info_format": (u"# {corpus}"
                                 u" ({corpus_info}):"
                                 u" sentence {sentence_id},"
                                 u" position {match_pos};"
                                 u" text attributes: {structs}\n"),
        "sentence_fields": "left_context,match,right_context",
        "sentence_field_format": u"{value}",
        "sentence_field_sep": "",
        # Skip empty fields or fields containing only spaces
        "sentence_field_skip": r"\s*",
        "corpus_info_format": (u"URN {urn};"
                               u" licence {licence_name}: {licence_link};"
                               u" metadata {metadata_link}"),
        "token_format": u"{fields}\n",
        "token_noattrs_format": u"{fields}\n",
        "token_sep": "",
        "token_fields": "word,*attrs",
        "token_field_sep": "\t",
        "struct_format": u"{name}: {value}",
        "match_marker": "*",
        "match_field": "0"
        }

    def __init__(self, **kwargs):
        super(KorpExportFormatterDelimitedToken, self).__init__(**kwargs)

    def _adjust_opts(self):
        """Add a match field to ``token_fields`` based on ``match_field``."""
        super(KorpExportFormatterDelimitedToken, self)._adjust_opts()
        if self._opts["match_field"]:
            if self._opts["match_field"] == "0":
                self._opts["token_fields"][0:0] = ["match_mark"]
            else:
                self._opts["token_fields"].append("match_mark")


class KorpExportFormatterDelimitedReference(KorpExportFormatterDelimited):

    r"""
    Format Korp results as a delimited-fields bibliographical reference.

    A logical content formatter class for delimited-fields formats
    with information relevant to bibliographical references. The
    output contains two columns: headings and values. The sentence is
    on its own line with the match marked, and the following lines
    contain corpus information and the structural attributes for the
    sentence. Sentences are separated by blank lines.

    This class does not specify the concrete delimiters; they need to
    be specified in a subclass or in a mix-in class.
    """

    formats = ["reference", "biblio", "bibref", "ref"]

    _option_defaults = {
        "content_format": u"{info}\n{sentences}",
        "title_format": u"## {title}\n",
        "infoitem_format": u"## {label}{sp_or_nl}{value}",
        "infoitem_spacechar": "\t",
        "param_format": u"##   {label}\t{value}",
        "sentence_format": u"sentence\t{tokens}\n{corpus_info}\n{structs}\n",
        "sentence_sep": "\n",
        "corpus_info_fields": (
            "corpus_name,urn,licence_name,licence_link,metadata_link"),
        "corpus_info_field_format": u"{label}\t{value}",
        "corpus_info_field_sep": "\n",
        "struct_format": u"{name}\t{value}",
        "struct_sep": "\n",
        "token_format": u"{match_open}{word}{match_close}",
        "match_open": u"<<< ",
        "match_close": u" >>>",
        }

    def __init__(self, **kwargs):
        super(KorpExportFormatterDelimitedReference, self).__init__(**kwargs)


class KorpExportFormatterCSV(KorpExportFormatterDelimited):

    r"""
    Format Korp results in a comma-separated values format.

    A mix-in class of actual formatters for comma-separated values
    formats. The result contains commas as field separators, and all
    fields are enclosed in double quotes, with internal double quotes
    doubled. The result uses \r\n as newlines, as it is specified in
    RFC 4180.

    This class does not specify the content of the fields.
    """

    mime_type = "text/csv"
    filename_extension = ".csv"
    formats = ["csv"]

    _option_defaults = {
        "newline": "\r\n",
        "delimiter": u",",
        "quote": u"\"",
        "replace_quote": u"\"\"",
        }

    def __init__(self, **kwargs):
        super(KorpExportFormatterCSV, self).__init__(**kwargs)


class KorpExportFormatterTSV(KorpExportFormatterDelimited):

    """
    Format Korp results in a tab-separated values format.

    A mix-in class for actual formatters for tab-separated values
    formats. The result contains tabs as field separators and no
    quotes around fied values.

    This class does not specify the content of the fields.
    """

    mime_type = "text/tsv"
    filename_extension = ".tsv"
    formats = ["tsv"]

    _option_defaults = {
        "delimiter": u"\t",
        "quote": u"",
        "replace_quote": u""
        }

    def __init__(self, **kwargs):
        super(KorpExportFormatterTSV, self).__init__(**kwargs)
