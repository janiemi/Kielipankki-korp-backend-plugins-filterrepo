#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import os.path
import time
import pkgutil
import json
import urllib, urllib2
import logging

import korpexport.queryresult as qr


__all__ = ['make_download_file',
           'KorpExportError',
           'KorpExporter']


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
        result["download_charset"] = self._formatter.download_charset
        result["download_content"] = (
            self._formatter.make_download_content(
                self._query_result, self._query_params, self._opts)
            .encode(self._formatter.download_charset))
        result["download_content_type"] = self._formatter.mime_type
        result["download_filename"] = self._get_filename()
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
            if module_name in ['exporter', 'formatter', 'queryresult']:
                continue
            try:
                module = __import__(module_name, globals())
            except ImportError as e:
                continue
            for name in dir(module):
                try:
                    module_class = getattr(module, name)
                    if format_name in module_class.formats:
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
            if self._formatter.structured_format:
                self._query_params["show"] += self._query_params["show_struct"]
            logging.debug("query_params: %s", self._query_params)
            # Encode the query parameters in UTF-8 for Korp server
            query_params_utf8 = dict(
                (key, val.encode("utf-8"))
                for key, val in self._query_params.iteritems())
            query_result_json = (
                urllib2.urlopen(korp_server_url,
                                urllib.urlencode(query_params_utf8))
                .read())
            # Support "sort" in format params even if not specified
            if "sort" not in self._query_params:
                self._query_params["sort"] = "none"
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
                        val = qr.get_occurring_attrnames(
                            self._query_result, val, query_result_struct_name)
                else:
                    val = val.split(",")
                opts[opt_name] = val

        extract_show_opt("attrs", "show", "tokens")
        extract_show_opt("structs", "show_struct", "structs")
        for opt_name, default_val in self._formatter.get_options().iteritems():
            opts[opt_name] = self._form.get(opt_name, default_val)
        return opts

    def _get_filename(self):
        return self._form.get(
            "filename",
            self._filename_base + time.strftime("%Y%m%d%H%M%S")
            + self._formatter.filename_extension)


if __name__ == "__main__":
    print KorpExporter._find_formatter_class('json')
