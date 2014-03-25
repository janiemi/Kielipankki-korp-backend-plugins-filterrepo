#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

from .exporter import KorpExporter


class KorpExporterDelimited(KorpExporter):

    _option_defaults = {}
    _delimit_opts = {}

    def __init__(self, *args, **kwargs):
        KorpExporter.__init__(self, *args, **kwargs)

    def format_headings(self):
        return self.format_delimited_fields(
            ["corpus", "position", "left context", "match", "right context"]
            + (["aligned text"] if self.is_parallel_corpus() else [])
            + self._opts.get("structs", []))

    def format_sentence(self, sentence):
        """Format a single delimited sentence.

        The result contains the following fields:
        - corpus ID (in upper case)
        - corpus position of the start of the match
        - tokens in left context, separated with spaces
        - tokens in match, separated with spaces
        - tokens in right context, separated with spaces
        - for parallel corpora only: tokens in aligned sentence
        """
        # Match start and end positions in tokens
        match_start = sentence["match"]["start"]
        match_end = sentence["match"]["end"]
        fields = [sentence["corpus"],
                  str(sentence["match"]["position"]),
                  self.format_sentence_tokens(sentence["tokens"][:match_start]),
                  self.format_sentence_tokens(sentence["tokens"]
                                              [match_start:match_end]),
                  self.format_sentence_tokens(sentence["tokens"][match_end:])]
        if "aligned" in sentence:
            for align_key, tokens in sorted(sentence["aligned"].iteritems()):
                fields.append(self.format_sentence_tokens(tokens))
        # Value may be None; convert them to empty strings
        fields.extend(sentence["structs"].get(struct) or ""
                      for struct in self._opts.get("structs", []))
        return self.format_delimited_fields(fields)

    def format_sentence_tokens(self, tokens):
        """Format the tokens of a single sentence."""
        return self._opts["token_separator"].join(
            self.format_token(token) for token in tokens)

    def format_token(self, token):
        """Format a single token, possibly with attributes."""
        # Allow for None in word (but where do they come from?)
        result = self._opts["word_format"].format(
            word=(token.get("word") or ""))
        if self._opts.get("attrs"):
            result = self._opts["token_format"].format(
                word=result, attrs=self.format_token_attrs(token))
        return result

    def format_token_attrs(self, token):
        """Format the attributes of a token."""
        return self._opts["attr_separator"].join(
            self._opts["attr_format"].format(name=attrname,
                                             value=(token.get(attrname) or ""))
            for attrname in self._opts["attrs"])

    def format_delimited_fields(self, fields):
        """Format fields according to the options in self._delimit_opts.

        self._delimit_opts may contain the following keyword arguments:
        - delim: field delimiter (default: ,)
        - quote: quotes surrounding fields (default: ")
        - escape_quote: string to precede a quote with in a field value to
          escape it (default: ")
        - newline: end-of-record string (default: \r\n)
        """
        delim = self._delimit_opts.get("delimiter", u",")
        quote = self._delimit_opts.get("quote", u"\"")
        escape_quote = self._delimit_opts.get("escape_quote", quote)
        newline = self._delimit_opts.get("newline", u"\n")
        return (delim.join((quote + field.replace(quote, escape_quote + quote)
                            + quote)
                           for field in fields)
                + newline)


class KorpExporterCSV(KorpExporterDelimited):

    _formats = ["csv"]
    _mime_type = "text/csv"
    _filename_extension = ".csv"
    _delimit_opts = {"delimiter": u",",
                     "quote": u"\"",
                     "escape_quote": u"\"",
                     "newline": u"\r\n"}

    def __init__(self, *args, **kwargs):
        KorpExporterDelimited.__init__(self, *args, **kwargs)


class KorpExporterTSV(KorpExporterDelimited):

    _formats = ["tsv"]
    _mime_type = "text/tsv"
    _filename_extension = ".tsv"
    _delimit_opts = {"delimiter": u"\t",
                     "quote": u"",
                     "escape_quote": u"",
                     "newline": u"\r\n"}

    def __init__(self, *args, **kwargs):
        KorpExporterDelimited.__init__(self, *args, **kwargs)
