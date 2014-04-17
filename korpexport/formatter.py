#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import time

import korpexport.queryresult as qr

__all__ = ["KorpExportFormatter"]


class _KorpExportFormatterMetaclass(type):

    def __init__(self, classname, bases, attrs):
        super(_KorpExportFormatterMetaclass, self).__init__(classname, bases,
                                                            attrs)
        self._make_option_defaults(bases)

    def _make_option_defaults(self, base_classes):
        new_option_defaults = {}
        for cls in list(base_classes) + [self]:
            try:
                new_option_defaults.update(cls._option_defaults)
            except AttributeError:
                pass
        self._option_defaults = new_option_defaults


class KorpExportFormatter(object):

    __metaclass__ = _KorpExportFormatterMetaclass

    formats = []
    download_charset = "utf-8"
    mime_type = "application/unknown"
    structured_format = False
    filename_extension = ""

    _option_defaults = {
        "newline": "\n",
        "headings": "",
        "header_format": u"{headings}",
        "footer_format": u"",
        "word_format": u"{word}",
        "token_format": u"{word}[{attrs}]",
        "token_sep": u" ",
        "attr_format": u"{value}",
        "attr_sep": u";",
        "sentence_format": (u"{corpus} {match_pos}: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context}\n"),
        "match_open": u"",
        "match_close": u"",
        "sentence_sep": u"",
        "aligned_format": u"{sentence}",
        "aligned_sep": u" | ",
        "struct_format": u"{name}: {value}",
        "struct_sep": u"; ",
        "token_struct_open_format": u"",
        "token_struct_close_format": u"",
        "token_struct_open_sep": "",
        "token_struct_close_sep": "",
        "combine_token_structs": "False",
        "content_format": u"{header}{sentences}{footer}",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "params_format": (u"corpora: {corpus}; CQP query: {cqp}; "
                          u"context: {defaultcontext}; "
                          u"within: {defaultwithin}; sorting: {sort}; "
                          u"start: {start}; end: {end}")
        }

    def __init__(self, format_name, options=None):
        self._format_name = format_name
        self._opts = {}
        self._opts.update(self.__class__._option_defaults)
        self._opts.update(options or {})
        self._query_params = {}
        self._query_result = {}

    def get_options(self):
        return self._opts

    def get_option_bool(self, optname):
        return (self._opts[optname].lower()
                not in ["false", "no", "off", "0", ""])

    def get_option_int(self, optname):
        value = None
        try:
            value = int(self._opts[optname])
        except ValueError:
            value = int(self._option_defaults[optname])
        except TypeError:
            value = int(self._option_defaults[optname])
        return value

    def make_download_content(self, query_result, query_params=None,
                              options=None):
        self._query_result = query_result
        self._query_params = query_params or {}
        self._opts.update(options or {})
        return self._convert_newlines(self._format_content())

    def _convert_newlines(self, text):
        if self._opts["newline"] != "\n":
            return text.replace("\n", self._opts["newline"])
        else:
            return text

    def _get_sentence_structs(self, sentence):
        return qr.get_sentence_structs(sentence, self._opts.get("structs", []))

    def _get_token_attrs(self, token):
        return qr.get_token_attrs(token, self._opts.get("attrs", []))

    def _format_list(self, list_, type_name, format_fn=None, **kwargs):
        format_fn = format_fn or getattr(self, "_format_" + type_name)
        return self._opts[type_name + "_sep"].join(
            format_fn(elem, **kwargs) for elem in list_)

    def _format_part(self, format_name, arg_fn_args, **format_arg_fns):
        # A non-tested, non-used formatting function with a kind of
        # lazy evaluation of format arguments: only those arguments
        # are evaluated which occur in the format string.
        format_str = self._opts[format_name + "_format"]

        def make_format_arg_value(arg_name, arg_fn):
            return (arg_fn(*arg_fn_args) if "{" + arg_name + "}" in format_str
                    else "")

        format_args = [(name, make_format_arg_value(name, format_arg_fn))
                       for (name, format_arg_fn) in format_arg_fns.iteritems()]
        return format_str.format(**format_args)

    def _format_content(self):
        return self._opts["content_format"].format(
            params=self._format_params(),
            # Also allow format references {param[name]}
            param=self._query_params,
            date=self._format_date(),
            header=self._format_header(),
            sentences=self._format_sentences(),
            footer=self._format_footer())

    def _format_date(self):
        return time.strftime(self._opts["date_format"])

    def _format_params(self):
        # Allow format references {name} as well as {param[name]}
        return self._opts["params_format"].format(
            param=self._query_params,
            **self._query_params)

    def _format_header(self):
        return self._format_header_footer("header")

    def _format_footer(self):
        return self._format_header_footer("footer")

    def _format_header_footer(self, type_):
        headings = self._format_headings() if self._opts["headings"] else ""
        return self._opts[type_ + "_format"].format(
            headings=headings,
            params=self._format_params(),
            # Also allow format references {param[name]}
            param=self._query_params,
            date=self._format_date())

    def _format_headings(self):
        return ""

    def _format_sentences(self):
        return self._format_list(qr.get_sentences(self._query_result),
                                 "sentence")

    def _format_sentence(self, sentence, **kwargs):
        struct = self._get_formatted_sentence_structs(sentence)
        return self._opts["sentence_format"].format(
            corpus=qr.get_sentence_corpus(sentence),
            match_pos=qr.get_sentence_match_position(sentence),
            tokens=self._format_tokens(
                qr.get_sentence_tokens_all(sentence)),
            match=self._format_tokens(
                qr.get_sentence_tokens_match(sentence), within_match=True),
            match_open=self._opts["match_open"],
            match_close=self._opts["match_close"],
            left_context=self._format_tokens(
                qr.get_sentence_tokens_left_context(sentence)),
            right_context=self._format_tokens(
                qr.get_sentence_tokens_right_context(sentence)),
            aligned=self._format_aligned_sentences(sentence),
            structs=self._format_structs(sentence),
            struct=struct,
            arg=kwargs)

    def _get_formatted_sentence_structs(self, sentence):
        return dict([(key, self._format_struct((key, val)))
                     for (key, val) in self._get_sentence_structs(sentence)])

    def _format_aligned_sentences(self, sentence):
        return self._format_list(qr.get_aligned_sentences(sentence), "aligned",
                                 self._format_aligned_sentence)

    def _format_aligned_sentence(self, aligned_sentence, **kwargs):
        align_key, sentence = aligned_sentence
        return self._opts["aligned_format"].format(
            align_key=align_key,
            sentence=sentence)

    def _format_structs(self, sentence):
        return self._format_list(self._get_sentence_structs(sentence),
                                 "struct")

    def _format_struct(self, struct):
        return self._opts["struct_format"].format(
            name=struct[0],
            value=struct[1])

    def _format_tokens(self, tokens, **kwargs):
        """Format the tokens of a single sentence."""
        return self._format_list(tokens, "token", **kwargs)

    def _format_token(self, token, **kwargs):
        """Format a single token, possibly with attributes."""
        # Allow for None in word (but where do they come from?)
        result = self._opts["word_format"].format(
            word=(token.get("word") or ""))
        if self._opts.get("attrs") or self.structured_format:
            result = self._opts["token_format"].format(
                word=result,
                attrs=self._format_token_attrs(token),
                structs_open=self._format_token_structs_open(token),
                structs_close=self._format_token_structs_close(token))
        return result

    def _format_token_attrs(self, token):
        """Format the attributes of a token."""
        return self._format_list(
            self._get_token_attrs(token), "attr", self._format_token_attr)

    def _format_token_attr(self, attr_name_value):
        attrname, value = attr_name_value
        return self._opts["attr_format"].format(name=attrname,
                                                value=(value or ""))

    def _format_token_structs_open(self, token):
        combine = self.get_option_bool("combine_token_structs")
        return self._format_list(
            qr.get_token_structs_open(token, combine),
            "token_struct_open")

    def _format_token_struct_open(self, struct):
        if self.get_option_bool("combine_token_structs"):
            structname, attrlist = struct
            attrstr = self._format_token_struct_attrs(attrlist)
            opt_name = ("token_struct_open_"
                        + ("attrs" if attrstr else "noattrs") + "_format")
            return self._opts[opt_name].format(name=structname, attrs=attrstr)
        else:
            return self._opts["token_struct_open_format"].format(name=struct)

    def _format_token_struct_attrs(self, attrs):
        return self._format_list(attrs, "token_struct_attr")

    def _format_token_struct_attr(self, attr):
        name, value = attr
        return self._opts["token_struct_attr_format"].format(
            name=name, value=value)

    def _format_token_structs_close(self, token):
        return self._format_list(
            qr.get_token_structs_close(
                token, self.get_option_bool("combine_token_structs")),
            "token_struct_close")

    def _format_token_struct_close(self, struct):
        if self.get_option_bool("combine_token_structs"):
            struct, _ = struct
        return self._opts["token_struct_close_format"].format(name=struct)
