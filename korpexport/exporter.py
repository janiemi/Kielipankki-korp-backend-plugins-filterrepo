#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

import os.path
import time
import pkgutil
import json
import urllib, urllib2
import re
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

    _FORMATTER_SUBPACKAGE = "format"
    _filename_format_default = u"korp_kwic_{cqpwords:.60}_{date}_{time}{ext}"

    def __init__(self, form, options=None, filename_format=None,
                 filename_encoding="utf-8"):
        self._form = form
        self._filename_format = filename_format or self._filename_format_default
        self._filename_encoding = filename_encoding
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
        pkgpath = os.path.join(os.path.dirname(__file__),
                               self._FORMATTER_SUBPACKAGE)
        for _, module_name, _ in pkgutil.iter_modules([pkgpath]):
            try:
                subpkg = __import__(
                    self._FORMATTER_SUBPACKAGE + "." + module_name, globals())
            except ImportError as e:
                continue
            module = getattr(subpkg, module_name)
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
        self._opts = self._extract_options(korp_server_url)
        logging.debug("opts: %s", self._opts)
        logging.debug("query result: %s", self._query_result)

    def _extract_options(self, korp_server_url=None):
        """Extract formatting options from form, affected by query_params."""
        opts = {}

        def extract_show_opt(opt_name, query_param_name,
                             query_result_struct_name):
            """Set the show option opt_name based on query params and result.

            If the form contains parameter opt_name, set the option
            opt_name to be a list of attributes or structures to be
            shown. The value of the form parameter may be a
            comma-separated string of attribute names; * for all the
            attributes listed in the query parameter query_param_name;
            + for all of those that actually occur in query result
            structure query_result_struct_name; -attr for excluding
            attr (used following with * or +).
            """
            if opt_name in self._form:
                vals = self._form[opt_name].split(",")
                new_vals = []
                for valnum, val in enumerate(vals):
                    if val in ["*", "+"]:
                        all_vals = (
                            self._query_params[query_param_name].split(","))
                        if val == "+":
                            add_vals = qr.get_occurring_attrnames(
                                self._query_result, all_vals,
                                query_result_struct_name)
                        else:
                            add_vals = all_vals
                        new_vals.extend(add_vals)
                    elif val.startswith("-"):
                        valname = val[1:]
                        if valname in new_vals:
                            new_vals.remove(valname)
                    else:
                        new_vals.append(val)
                opts[opt_name] = new_vals

        extract_show_opt("attrs", "show", "tokens")
        extract_show_opt("structs", "show_struct", "structs")
        for opt_name, default_val in self._formatter.get_options().iteritems():
            opts[opt_name] = self._form.get(opt_name, default_val)
        if self._form.get("korp_url"):
            opts["korp_url"] = self._form.get("korp_url")
        # FIXME: This does not make sense to the user if
        # korp_server_url uses localhost.
        opts["korp_server_url"] = (korp_server_url
                                   or self._form.get("korp_server_url", ""))
        return opts

    def _get_filename(self):
        return (self._form.get(
                "filename",
                self._filename_format.format(
                    date=time.strftime("%Y%m%d"),
                    time=time.strftime("%H%M%S"),
                    ext=self._formatter.filename_extension,
                    cqpwords=self._make_cqp_filename_repr(),
                    start=self._query_params["start"],
                    end=self._query_params["end"]))
                .encode(self._filename_encoding))

    def _make_cqp_filename_repr(self, attrs=False, keep_chars=None,
                                replace_char='_'):
        # TODO: If attrs is True, include attribute names. Could we
        # encode somehow the operator which could be != or contains?
        words = re.findall(r'\"((?:[^\\\"]|\\.)*?)\"',
                           self._query_params["cqp"])
        replace_chars_re = re.compile(
            r'[^\w' + re.escape(keep_chars or "") + ']+', re.UNICODE)
        return replace_char.join(replace_chars_re.sub(replace_char, word)
                                 for word in words)


if __name__ == "__main__":
    print KorpExporter._find_formatter_class('json')
