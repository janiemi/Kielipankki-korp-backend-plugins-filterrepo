#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import os.path
import time
import pkgutil
import json
import urllib, urllib2
import logging

__all__ = ['make_download_file',
           'KorpExportError',
           'KorpExporter',
           'KorpFormatter']


def make_download_file(form, korp_server_url, **kwargs):
    """Format query results and return them in a downloadable format."""
    exporter = KorpExporter(form, **kwargs)
    return exporter.make_download_file(korp_server_url, **kwargs)


class KorpExportError(Exception):

    pass


class KorpExporter(object):

    _filename_base_default = "korp_kwic_"

    def __init__(self, form, options=None, filename_base=None):
        self._form = form
        self._filename_base = filename_base or self._filename_base_default
        self._opts = options or {}
        self._query_params = {}
        self._query_result = None
        self._formatter = None

    def make_download_file(self, korp_server_url, **kwargs):
        """Format query results and return them in a downloadable format."""
        result = {}
        if "form" in kwargs:
            self._form = kwargs["form"]
        self._formatter = self._formatter or self._get_formatter(**kwargs)
        self.process_query(korp_server_url)
        logging.debug('formatter: %s', self._formatter)
        result["download_charset"] = self._formatter._download_charset
        result["download_content"] = (
            self._formatter.make_download_content(
                self._query_result, self._query_params, self._opts)
            .encode(self._formatter._download_charset))
        result["download_content_type"] = self._formatter._mime_type
        result["download_filename"] = self.get_filename()
        logging.debug('make_download_file result: %s', result)
        return result

    def _get_formatter(self, **kwargs):
        format_name = self._form.get("format", "json").lower()
        formatter_class = self._find_formatter_class(format_name)
        # Options passed to _get_formatter() override those passed to
        # the KorpExporter constructor
        opts = {}
        opts.update(self._opts)
        opts.update(kwargs.get("options", {}))
        kwargs["options"] = opts
        return formatter_class(format_name, **kwargs)

    def _find_formatter_class(self, format_name):
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
        raise KorpExportError("No formatter found for format '{0}'"
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
            # If the format uses structural information, add the
            # structs in param "show_struct" to "show", so that tokens
            # are associated with information on opening and closing
            # those structures. Param "show_struct" only gives us
            # struct attribute values for a whole sentence.
            if self._formatter._structured_format:
                self._query_params["show"] += self._query_params["show_struct"]
            logging.debug("query_params: %s", self._query_params)
            query_result_json = (
                urllib2.urlopen(korp_server_url,
                                urllib.urlencode(self._query_params))
                .read())
            # Support "sort" in format params even if not specified
            if "sort" not in self._query_params:
                self._query_params["sort"] = "none"
        self._query_result = KorpQueryResult(query_result_json)
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
                        val = self._query_result.get_occurring_attrnames(
                            val, query_result_struct_name)
                else:
                    val = val.split(",")
                opts[opt_name] = val

        extract_show_opt("attrs", "show", "tokens")
        extract_show_opt("structs", "show_struct", "structs")
        for opt_name, default_val in self._formatter.get_options().iteritems():
            opts[opt_name] = self._form.get(opt_name, default_val)
        return opts

    def get_filename(self):
        return self._form.get(
            "filename",
            self._filename_base + time.strftime("%Y%m%d%H%M%S")
            + self._formatter._filename_extension)


class KorpQueryResult(object):

    def __init__(self, query_result):
        if isinstance(query_result, basestring):
            self._query_result = json.loads(query_result)
        else:
            self._query_result = query_result

    def get_sentences(self):
        return self._query_result["kwic"]

    def get_occurring_attrnames(self, keys, struct_name):
        # FIXME: This does not take into account attributes in aligned
        # sentences
        occurring_keys = set()
        for sent in self.get_sentences():
            if isinstance(sent[struct_name], list):
                for item in sent[struct_name]:
                    occurring_keys |= set(item.keys())
            else:
                occurring_keys |= set(sent[struct_name].keys())
        return [key for key in keys if key in occurring_keys]

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

    def get_sentence_structs(self, sentence, structnames):
        # Value may be None; convert them to empty strings
        return [(struct, sentence["structs"].get(struct) or "")
                for struct in structnames]

    def get_sentence_struct_values(self, sentence, structnames):
        return [value for name, value in
                self.get_sentence_structs(sentence, structnames)]

    def get_token_attrs(self, token, attrnames):
        return [(attrname, token.get(attrname) or "") for attrname in attrnames]

    def get_token_structs_open(self, token, combine_attrs=False):
        return self._get_token_structs(token, "open", combine_attrs)

    def get_token_structs_close(self, token, combine_attrs=False):
        return self._get_token_structs(token, "close", combine_attrs)

    def _get_token_structs(self, token, struct_type, combine_attrs=False):
        try:
            structs = token["structs"][struct_type]
        except KeyError:
            return []
        if combine_attrs:
            structs = self._combine_struct_attrs(structs, struct_type)
        return structs

    def _combine_struct_attrs(self, structs, struct_type):
        result_structs = []
        for struct in structs:
            if struct_type == "open":
                struct, sp, attrval = struct.partition(" ")
                if not sp:
                    attrval = None
            else:
                attrval = None
            # NOTE: This assumes that element names do not contain
            # underscores.
            struct, _, attrname = struct.partition("_")
            if not result_structs or result_structs[-1][0] != struct:
                result_structs.append((struct, []))
            if attrval is not None:
                result_structs[-1][1].append((attrname, attrval))
        return result_structs

    def is_parallel_corpus(self):
        # FIXME: This does not work if the script gets the query result
        # from frontend instead of redoing the query, since the frontend
        # has processed the corpus names not to contain the vertical bar.
        return "|" in self._query_result["kwic"][0]["corpus"]
    

class KorpFormatterMetaclass(type):

    def __init__(self, classname, bases, attrs):
        super(KorpFormatterMetaclass, self).__init__(classname, bases, attrs)
        self._make_option_defaults(bases)

    def _make_option_defaults(self, base_classes):
        new_option_defaults = {}
        for cls in list(base_classes) + [self]:
            try:
                new_option_defaults.update(cls._option_defaults)
            except AttributeError:
                pass
        self._option_defaults = new_option_defaults


class KorpFormatter(object):

    __metaclass__ = KorpFormatterMetaclass

    _formats = []
    _download_charset = "utf-8"
    _mime_type = "application/unknown"
    _structured_format = False
    _filename_extension = ""
    _option_defaults = {
        "newline": "\n",
        "headings": "",
        "header_format": u"{headings}",
        "footer_format": u"",
        "word_format": u"{word}",
        "token_format": u"{word}[{attrs}]",
        "token_separator": u" ",
        "attr_format": u"{value}",
        "attr_separator": u";",
        "sentence_format": (u"{corpus} {match_pos}: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context}\n"),
        "match_open": u"",
        "match_close": u"",
        "sentence_separator": u"",
        "aligned_format": u"{sentence}",
        "aligned_separator": u" | ",
        "struct_format": u"{name}: {value}",
        "struct_separator": u"; ",
        "token_struct_open_format": u"",
        "token_struct_close_format": u"",
        "token_struct_open_separator": "",
        "token_struct_close_separator": "",
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

    def _get_option_bool(self, optname):
        return (self._opts[optname].lower()
                not in ["false", "no", "off", "0", ""])

    def _get_option_int(self, optname):
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
        return self._convert_newlines(self.format_content())

    def _convert_newlines(self, text):
        if self._opts["newline"] != "\n":
            return text.replace("\n", self._opts["newline"])
        else:
            return text

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
        return self._format_list(self._query_result.get_sentences(), "sentence")

    def format_sentence(self, sentence):
        qresult = self._query_result
        return self._opts["sentence_format"].format(
            corpus=qresult.get_sentence_corpus(sentence),
            match_pos=qresult.get_sentence_match_position(sentence),
            tokens=self.format_tokens(
                qresult.get_sentence_tokens(sentence, None, None)),
            match=self.format_tokens(
                qresult.get_sentence_tokens_match(sentence)),
            match_open=self._opts["match_open"],
            match_close=self._opts["match_close"],
            left_context=self.format_tokens(
                qresult.get_sentence_tokens_left_context(sentence)),
            right_context=self.format_tokens(
                qresult.get_sentence_tokens_right_context(sentence)),
            aligned=self.format_aligned_sentences(sentence),
            structs=self.format_structs(sentence))

    def format_aligned_sentences(self, sentence):
        return self._format_list(
            self._query_result.get_aligned_sentences(sentence), "aligned",
            self.format_aligned_sentence)

    def format_aligned_sentence(self, aligned_sentence):
        align_key, sentence = aligned_sentence
        return self._opts["aligned_format"].format(
            align_key=align_key,
            sentence=sentence)

    def format_structs(self, sentence):
        return self._format_list(
            self._query_result.get_sentence_structs(
                sentence, self._opts.get("structs", [])),
            "struct")

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
        if self._opts.get("attrs") or self._structured_format:
            result = self._opts["token_format"].format(
                word=result,
                attrs=self.format_token_attrs(token),
                structs_open=self.format_token_structs_open(token),
                structs_close=self.format_token_structs_close(token))
        return result

    def format_token_attrs(self, token):
        """Format the attributes of a token."""
        return self._format_list(
            self._query_result.get_token_attrs(
                token, self._opts.get("attrs", [])), "attr",
            self.format_token_attr)

    def format_token_attr(self, attr_name_value):
        attrname, value = attr_name_value
        return self._opts["attr_format"].format(name=attrname,
                                                value=(value or ""))

    def format_token_structs_open(self, token):
        combine = self._get_option_bool("combine_token_structs")
        return self._format_list(
            self._query_result.get_token_structs_open(token, combine),
            "token_struct_open")

    def format_token_struct_open(self, struct):
        if self._get_option_bool("combine_token_structs"):
            structname, attrlist = struct
            attrstr = self.format_token_struct_attrs(attrlist)
            opt_name = ("token_struct_open_"
                        + ("attrs" if attrstr else "noattrs") + "_format")
            return self._opts[opt_name].format(name=structname, attrs=attrstr)
        else:
            return self._opts["token_struct_open_format"].format(name=struct)

    def format_token_struct_attrs(self, attrs):
        return self._format_list(attrs, "token_struct_attr")

    def format_token_struct_attr(self, attr):
        name, value = attr
        return self._opts["token_struct_attr_format"].format(
            name=name, value=value)

    def format_token_structs_close(self, token):
        return self._format_list(
            self._query_result.get_token_structs_close(
                token, self._get_option_bool("combine_token_structs")),
            "token_struct_close")

    def format_token_struct_close(self, struct):
        if self._get_option_bool("combine_token_structs"):
            struct, _ = struct
        return self._opts["token_struct_close_format"].format(name=struct)


if __name__ == "__main__":
    print KorpExporter._find_formatter_class('json')
