#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import korpexport.queryresult as qr
from .formatter import KorpExportFormatter


__all__ = ['KorpExportFormatterCSV', 'KorpExportFormatterTSV']


class KorpExportFormatterDelimited(KorpExportFormatter):

    _option_defaults = {
        "delimiter": u",",
        "quote": u"\"",
        "replace_quote": u"\"\""
        }

    def __init__(self, *args, **kwargs):
        KorpExportFormatter.__init__(self, *args, **kwargs)

    def _format_headings(self):
        return self._format_fields(
            ["corpus", "position", "left context", "match", "right context"]
            + (["aligned text"] if qr.is_parallel_corpus(self._query_result)
               else [])
            + self._opts.get("structs", []))

    def _format_footer(self):
        return (self._format_fields(["## Date:", self._format_date()])
                + self._format_fields(["## Query parameters:",
                                       self._format_params()]))

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
