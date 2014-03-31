#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import os.path
import time
import pkgutil
import json
import urllib, urllib2
import logging


__all__ = ['make_download_file', 'KorpExportError', 'KorpExporter']


def make_download_file(*args, **kwargs):
    """Format query results and return them in a downloadable format."""
    return KorpExporter.make_download_file(*args, **kwargs)


class KorpExportError(Exception):

    pass


class KorpExporterMetaclass(type):

    def __init__(self, classname, bases, attrs):
        super(KorpExporterMetaclass, self).__init__(classname, bases, attrs)
        self._make_option_defaults(bases)

    def _make_option_defaults(self, base_classes):
        new_option_defaults = {}
        for cls in list(base_classes) + [self]:
            try:
                new_option_defaults.update(cls._option_defaults)
            except AttributeError:
                pass
        self._option_defaults = new_option_defaults


class KorpExporter(object):

    __metaclass__ = KorpExporterMetaclass

    _formats = []
    _download_charset = "utf-8"
    _mime_type = "application/unknown"
    _filename_extension = ""
    _filename_base_default = "korp_kwic_"
    _option_defaults = {
        "newline": "\n",
        "headings": "",
        "header_format": "{headings}",
        "footer_format": "# {date}: {params}\n",
        "word_format": u"{word}",
        "token_format": u"{word}[{attrs}]",
        "token_separator": u" ",
        "attr_format": u"{value}",
        "attr_separator": u";",
        "sentence_format": (u"{corpus} {match_pos}: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context}\n"),
        "sentence_separator": u"",
        "aligned_format": u"{sentence}",
        "aligned_separator": u" | ",
        "struct_format": u"{name}: {value}",
        "struct_separator": u"; ",
        "content_format": u"{header}{sentences}{footer}",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "params_format": (u"Corpora: {corpus}; CQP query: {cqp}; "
                          u"start: {start}; end: {end}")
        }

    def __init__(self, format_name, form, options=None, filename_base=None):
        self._format_name = format_name
        self._form = form
        self._option_defaults = self.__class__._option_defaults
        self._option_defaults.update(options or {})
        self._filename_base = filename_base or self._filename_base_default
        self._opts = {}
        self._query_params = {}
        self._query_result = {}

    @classmethod
    def make_download_file(cls, form, korp_server_url, **kwargs):
        """Format query results and return them in a downloadable format."""
        result = {}
        exporter = cls._get_exporter(form, **kwargs)
        logging.debug('exporter: %s', exporter)
        exporter.process_query(korp_server_url)
        result["download_charset"] = exporter._download_charset
        result["download_content"] = (exporter.make_download_content()
                                      .encode(exporter._download_charset))
        result["download_content_type"] = exporter._mime_type
        result["download_filename"] = exporter.get_filename()
        logging.debug('make_download_file result: %s', result)
        return result

    @classmethod
    def _get_exporter(cls, form, **kwargs):
        format_name = form.get("format", "json").lower()
        exporter_class = cls._find_exporter_class(format_name)
        return exporter_class(format_name, form, **kwargs)

    @classmethod
    def _find_exporter_class(cls, format_name):
        pkgpath = os.path.dirname(__file__)
        for _, module_name, _ in pkgutil.iter_modules([pkgpath]):
            try:
                module = __import__(module_name, globals())
            except ImportError as e:
                continue
            for name in dir(module):
                try:
                    module_class = getattr(module, name)
                    if format_name in module_class._formats:
                        return module_class
                except AttributeError as e:
                    pass
        raise KorpExportError("No exporter found for format '{0}'"
                              .format(format_name))

    def process_query(self, korp_server_url, query_params=None):
        """Get the query result in form or perform query via the Korp server.

        If form contains query_result, return it. Otherwise return the
        result obtained by performing a query to Korp server at
        korp_server_url using query_params. The returned value is a
        dictionary converted from JSON.
        """
        if "query_result" in self._form:
            query_result_json = self._form.get("query_result", "{}")
        else:
            if query_params:
                self._query_params = query_params
            elif "query_params" in self._form:
                self._query_params = json.loads(self._form.get("query_params"))
            else:
                self._query_params = self._form
            logging.debug("query_params: %s", self._query_params)
            query_result_json = (
                urllib2.urlopen(korp_server_url,
                                urllib.urlencode(self._query_params))
                .read())
        self._query_result = json.loads(query_result_json)
        self._opts = self._extract_options()
        logging.debug("opts: %s", self._opts)

    def _extract_options(self):
        """Extract formatting options from form, affected by query_params."""
        opts = {}

        def extract_show_opt(opt_name, query_param_name,
                             query_result_struct_name):
            if opt_name in self._form:
                val = orig_val = self._form[opt_name]
                if val in ["*", "+"]:
                    val = self._query_params[query_param_name].split(",")
                    if orig_val == "+":
                        val = get_occurring_keys(val, query_result_struct_name)
                else:
                    val = val.split(",")
                opts[opt_name] = val

        def get_occurring_keys(keys, struct_name):
            # FIXME: This does not take into account attributes in aligned
            # sentences
            occurring_keys = set()
            for sent in self._query_result["kwic"]:
                if isinstance(sent[struct_name], list):
                    for item in sent[struct_name]:
                        occurring_keys |= set(item.keys())
                else:
                    occurring_keys |= set(sent[struct_name].keys())
            return [key for key in keys if key in occurring_keys]

        extract_show_opt("attrs", "show", "tokens")
        extract_show_opt("structs", "show_struct", "structs")
        for opt_name, default_val in self._option_defaults.iteritems():
            opts[opt_name] = self._form.get(opt_name, default_val)
        return opts

    def get_filename(self):
        return self._form.get(
            "filename",
            self._filename_base + time.strftime("%Y%m%d%H%M%S")
            + self._filename_extension)

    def get_sentences(self):
        return self._query_result["kwic"]

    def get_sentence_corpus(self, sentence):
        return sentence["corpus"]

    def get_sentence_tokens(self, sentence, start, end):
        return sentence["tokens"][start:end]

    def get_sentence_tokens_match(self, sentence):
        return self.get_sentence_tokens(sentence, sentence["match"]["start"],
                                        sentence["match"]["end"])

    def get_sentence_tokens_left_context(self, sentence):
        return self.get_sentence_tokens(sentence, None,
                                        sentence["match"]["start"])

    def get_sentence_tokens_right_context(self, sentence):
        return self.get_sentence_tokens(sentence, sentence["match"]["end"],
                                        None)

    def get_sentence_match_position(self, sentence):
        return sentence["match"]["position"]

    def get_aligned_sentences(self, sentence):
        return sorted(sentence.get("aligned", {}).iteritems())

    def get_sentence_structs(self, sentence):
        # Value may be None; convert them to empty strings
        return [(struct, sentence["structs"].get(struct) or "")
                for struct in self._opts.get("structs", [])]

    def get_sentence_struct_values(self, sentence):
        return [value for name, value in self.get_sentence_structs(sentence)]

    def is_parallel_corpus(self):
        # FIXME: This does not work if the script gets the query result
        # from frontend instead of redoing the query, since the frontend
        # has processed the corpus names not to contain the vertical bar.
        return "|" in self._query_result["kwic"][0]["corpus"]

    def _format_list(self, list_, type_name, format_fn=None):
        format_fn = format_fn or getattr(self, "format_" + type_name)
        return self._opts[type_name + "_separator"].join(
            format_fn(elem) for elem in list_)

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

    def make_download_content(self):
        return self._convert_newlines(self.format_content())

    def _convert_newlines(self, text):
        if self._opts["newline"] != "\n":
            return text.replace("\n", self._opts["newline"])
        else:
            return text

    def format_content(self):
        return self._opts["content_format"].format(
            params=self.format_params(),
            # Also allow format references {param[name]}
            param=self._query_params,
            date=self.format_date(),
            header=self.format_header(),
            sentences=self.format_sentences(),
            footer=self.format_footer())

    def format_date(self):
        return time.strftime(self._opts["date_format"])

    def format_params(self):
        # Allow format references {name} as well as {param[name]}
        return self._opts["params_format"].format(
            param=self._query_params,
            **self._query_params)

    def format_header(self):
        return self._format_header_footer("header")

    def format_footer(self):
        return self._format_header_footer("footer")

    def _format_header_footer(self, type_):
        headings = self.format_headings() if self._opts["headings"] else ""
        return self._opts[type_ + "_format"].format(
            headings=headings,
            params=self.format_params(),
            # Also allow format references {param[name]}
            param=self._query_params,
            date=self.format_date())

    def format_headings(self):
        return ""

    def format_sentences(self):
        return self._format_list(self.get_sentences(), "sentence")

    def format_sentence(self, sentence):
        return self._opts["sentence_format"].format(
            corpus=self.get_sentence_corpus(sentence),
            position=self.get_sentence_match_position(sentence),
            tokens=self.format_tokens(
                self.get_sentence_tokens(sentence, None, None)),
            match=self.format_tokens(
                self.get_sentence_tokens_match(sentence)),
            left_context=self.format_tokens(
                self.get_sentence_tokens_left_context(sentence)),
            right_context=self.format_tokens(
                self.get_sentence_tokens_right_context(sentence)),
            aligned=self.format_aligned_sentences(sentence),
            structs=self.format_structs(sentence))

    def format_aligned_sentences(self, sentence):
        return self._format_list(self.get_aligned_sentences(sentence),
                                 "aligned", self.format_aligned_sentence)

    def format_aligned_sentence(self, aligned_sentence):
        align_key, sentence = aligned_sentence
        return self._opts["aligned_format"].format(
            align_key=align_key,
            sentence=sentence)

    def format_structs(self, sentence):
        return self._format_list(self.get_sentence_structs(sentence), "struct")

    def format_struct(self, struct):
        return self._opts["struct_format"].format(
            name=struct[0],
            value=struct[1])

    def format_tokens(self, tokens):
        """Format the tokens of a single sentence."""
        return self._format_list(tokens, "token")

    def format_token(self, token):
        """Format a single token, possibly with attributes."""
        # Allow for None in word (but where do they come from?)
        result = self._opts["word_format"].format(
            word=(token.get("word") or ""))
        if self._opts.get("attrs"):
            result = self._opts["token_format"].format(
                word=result, attrs=self.format_token_attrs(token))
        return result

    def get_token_attrs(self, token):
        return [(attrname, token.get(attrname) or "")
                for attrname in self._opts["attrs"]]

    def format_token_attrs(self, token):
        """Format the attributes of a token."""
        return self._opts["attr_separator"].join(
            self._opts["attr_format"].format(name=attrname,
                                             value=(token.get(attrname) or ""))
            for attrname in self._opts["attrs"])

    def format_token_attrs(self, token):
        """Format the attributes of a token."""
        return self._format_list(self.get_token_attrs(token), "attr",
                                 self.format_token_attr)

    def format_token_attr(self, attr_name_value):
        attrname, value = attr_name_value
        return self._opts["attr_separator"].join(
            self._opts["attr_format"].format(name=attrname,
                                             value=(token.get(attrname) or ""))
            for attrname in self._opts["attrs"])


if __name__ == "__main__":
    print KorpExporter._find_exporter_class('json')
