#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import os.path
import time
import pkgutil
import json
import urllib, urllib2
import logging


def make_download_file(*args):
    """Format query results and return them in a downloadable format."""
    return KorpExporter.make_download_file(*args)


class KorpExportError(Exception):

    pass


class KorpExporter(object):

    _formats = []
    _download_charset = "utf-8"
    _mime_type = "application/unknown"
    _filename_extension = ""
    _option_default_defaults = {"headings": "",
                                "word_format": u"{word}",
                                "token_format": u"{word}[{attrs}]",
                                "token_separator": u" ",
                                "attr_format": u"{value}",
                                "attr_separator": u";",
                                "sentence_separator": ""}
    _option_defaults = {}

    def __init__(self, form, query_params, query_result, filename_base=None):
        self._form = form
        self._query_params = query_params
        self._query_result = query_result
        self._filename_base = filename_base or "korp_kwic_"
        self.__class__._option_defaults.update(self._option_default_defaults)
        self._opts = self._extract_options()

    @classmethod
    def get_formats(cls):
        return cls._formats

    @classmethod
    def get_download_charset(cls):
        return cls._download_charset

    @classmethod
    def get_content_mimetype(cls):
        return cls._mime_type

    @classmethod
    def get_filename_extension(cls):
        return cls._filename_extension

    @classmethod
    def make_download_file(cls, form, korp_server_url):
        """Format query results and return them in a downloadable format."""
        result = {}
        format_name = form.get("format", "json").lower()
        query_params = json.loads(form.get("query_params", "{}"))
        query_result = cls.get_query_result(form, query_params, korp_server_url)
        exporter = cls._get_exporter(format_name, form, query_params,
                                    query_result)
        logging.info('exporter: %s', exporter)
        charset = exporter.get_download_charset()
        result["download_charset"] = charset
        result["download_content"] = (exporter.make_download_content()
                                      .encode(charset))
        result["download_content_type"] = exporter.get_content_mimetype()
        result["download_filename"] = exporter.get_filename()
        # logging.info('result: %s', result)
        return result

    @classmethod
    def get_query_result(cls, form, query_params, korp_server_url):
        """Get the query result in form or perform query via the Korp server.

        If form contains query_result, return it. Otherwise return the
        result obtained by performing a query to Korp server at
        korp_server_url using query_params. The returned value is a
        dictionary converted from JSON.
        """
        if "query_result" in form:
            query_result_json = form.get("query_result", "{}")
        else:
            query_result_json = (urllib2.urlopen(korp_server_url,
                                                 urllib.urlencode(query_params))
                                 .read())
        return json.loads(query_result_json)

    @classmethod
    def _get_exporter(cls, format_name, form, query_params, query_result):
        exporter_class = cls._find_exporter_class(format_name)
        return exporter_class(form, query_params, query_result)

    @classmethod
    def _find_exporter_class(cls, format_name):
        pkgpath = os.path.dirname(__file__)
        for _, module_name, _ in pkgutil.iter_modules([pkgpath]):
            try:
                # print pkgpath, module_name, repr(__package__)
                module = __import__(module_name, globals())
                # print module, dir(module)
            except ImportError as e:
                continue
            for name in dir(module):
                try:
                    # print name, name[0].isupper(), getattr(module, name)
                    # if (name[0].isupper()
                    #     and issubclass(getattr(module, name), cls)):
                    module_class = getattr(module, name)
                        # print module_class, module_class.get_formats()
                    if format_name in module_class.get_formats():
                        return module_class
                except AttributeError as e:
                    pass
        raise KorpExportError("No exporter found for format '{0}'"
                              .format(format_name))

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

    def is_parallel_corpus(self):
        # FIXME: This does not work if the script gets the query result
        # from frontend instead of redoing the query, since the frontend
        # has processed the corpus names not to contain the vertical bar.
        return "|" in self._query_result["kwic"][0]["corpus"]

    def make_download_content(self):
        return (self.format_header()
                + self.format_sentences()
                + self.format_footer())

    def format_header(self):
        if self._opts["headings"]:
            return self.format_headings()

    def format_headings(self):
        return ""

    def format_sentences(self):
        return self._opts["sentence_separator"].join(
            self.format_sentence(sentence)
            for sentence in self._query_result["kwic"])

    def format_sentence(self, sentence):
        return ""

    def format_footer(self):
        return ""


if __name__ == "__main__":
    print KorpExporter._find_exporter_class('json')
