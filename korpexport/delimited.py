#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import korpexport.queryresult as qr
from .formatter import KorpExportFormatter


__all__ = ['KorpExportFormatterCSV',
           'KorpExportFormatterCSVTokens',
           'KorpExportFormatterTSV']


class KorpExportFormatterDelimited(KorpExportFormatter):

    _option_defaults = {
        "delimiter": u",",
        "quote": u"\"",
        "replace_quote": u"\"\"",
        "metainfo_item_format": u"## {key}: {value}"
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)

    def _format_headings(self):
        return self._format_fields(
            ["corpus", "position", "left context", "match", "right context"]
            + (["aligned text"] if qr.is_parallel_corpus(self._query_result)
               else [])
            + self._opts.get("structs", []))

    def _format_metainfo(self):
        # TODO: Extract the query param labels and keys from
        # self._opts["params_format"]. Or maybe rather add options
        # listing the parameters and for formatting a single
        # parameter.
        query_params = [("  " + label, self._query_params.get(param, "[none]"))
                        for label, param in
                        [("corpora", "corpus"),
                         ("CQP query", "cqp"),
                         ("context", "defaultcontext"),
                         ("within", "defaultwithin"),
                         ("sorting", "sort"),
                         ("start", "start"),
                         ("end", "end")]]
        return ''.join(
            self._format_fields(
                [self._format_item("metainfo_item", key=key, value=value)
                 .strip()])
            for key, value in ([("Date", self._format_date()),
                                ("Query parameters", "")]
                               + query_params))

    def _format_footer(self):
        return self._format_metainfo()

    def _format_sentence(self, sentence):
        """Format a single delimited sentence.

        The result contains the following fields:
        - corpus ID (in upper case)
        - corpus position of the start of the match
        - tokens in left context, separated with spaces
        - tokens in match, separated with spaces
        - tokens in right context, separated with spaces
        - for parallel corpora only: tokens in aligned sentence
        """
        fields = ([qr.get_sentence_corpus(sentence),
                   str(qr.get_sentence_match_position(sentence))]
                  + [self._format_tokens(field_get_func(sentence))
                     for field_get_func in
                     [qr.get_sentence_tokens_left_context,
                      qr.get_sentence_tokens_match,
                      qr.get_sentence_tokens_right_context]])
        for _, tokens in qr.get_aligned_sentences(sentence):
            fields.append(self._format_tokens(tokens))
        fields.extend(qr.get_sentence_struct_values(
                sentence, self._opts.get("structs", [])))
        return self._format_fields(fields)

    def _format_fields(self, fields):
        """Format fields according to the options in self._opts.

        self._opts may contain the following keys:
        - delim: field delimiter (default: ,)
        - quote: quotes surrounding fields (default: ")
        - replace_quote: string to replace a quote with in a field value to
          escape it (default: "")
        """
        delim = self._opts["delimiter"]
        quote = self._opts["quote"]
        replace_quote = self._opts["replace_quote"]
        return (delim.join((quote + field.replace(quote, replace_quote) + quote)
                           for field in fields)
                + "\n")


class KorpExportFormatterCSV(KorpExportFormatterDelimited):

    formats = ["csv"]
    mime_type = "text/csv"
    filename_extension = ".csv"

    _option_defaults = {
        "newline": "\r\n",
        "delimiter": u",",
        "quote": u"\"",
        "replace_quote": u"\"\""
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatterDelimited.__init__(self, *args, **kwargs)


class KorpExportFormatterCSVTokens(KorpExportFormatterCSV):

    # csvp is an alias for csv_tokens
    formats = ["csv_tokens", "csvp"]

    _option_defaults = {
        "sentence_header_format": (u"# {corpus}:"
                                   u" sentence {struct[sentence_id]},"
                                   u" position {match_pos}"),
        "sentence_format": (u"{arg[header]}{left_context}{match}"
                            u"{right_context}\n"),
        "struct_format": u"{value}",
        "token_sep": "",
        "match_marker": "*",
        "match_field": "0"
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatterCSV.__init__(self, *args, **kwargs)
        self._opts["match_field"] = self.get_option_int("match_field")

    def _format_headings(self):
        field_names = ["word"] + self._opts.get("attrs", [])
        self._insert_match_field(field_names, "match")
        return (self._format_metainfo() + "\n"
                + self._format_fields(field_names) + "\n")

    def _insert_match_field(self, fields, content):
        if self._opts["match_field"] is not None:
            fields.insert(self._opts["match_field"], content)

    def _format_footer(self):
        return ""

    def _format_sentence_header(self, sentence):
        struct = self._get_formatted_sentence_structs(sentence)
        return self._format_fields([
                self._format_item(
                    "sentence_header",
                    corpus=qr.get_sentence_corpus(sentence),
                    match_pos=qr.get_sentence_match_position(sentence),
                    aligned=self._format_aligned_sentences(sentence),
                    structs=self._format_structs(sentence),
                    struct=struct)])

    def _format_sentence(self, sentence):
        return KorpExportFormatter._format_sentence(
            self, sentence, header=self._format_sentence_header(sentence))

    def _format_token(self, token, within_match=False):
        fields = ([token.get("word")]
                  + [self._format_token_attr(attr)
                     for attr in self._get_token_attrs(token)])
        self._insert_match_field(
            fields, self._opts["match_marker"] if within_match else "")
        return self._format_fields(fields)


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
