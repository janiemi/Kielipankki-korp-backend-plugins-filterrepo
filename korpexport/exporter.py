# -*- coding: utf-8 -*-

"""
The main module for exporting Korp search results to downloadable formats.

It should generally be sufficient to call func:`make_download_file` to
generate downloadable file contents.

:Author: Jyrki Niemi <jyrki.niemi@helsinki.fi> for FIN-CLARIN
:Date: 2014
"""


from __future__ import absolute_import

import os.path
import time
import pkgutil
import json
import urllib, urllib2
import re
import logging

from subprocess import Popen, PIPE

import korpexport.queryresult as qr


__all__ = ['make_download_file',
           'KorpExportError',
           'KorpExporter']


def make_download_file(form, korp_server_url, **kwargs):
    """Format Korp query results and return them in a downloadable format.

    Arguments:
        form (dict): Input form containing CGI (query string)
            parameters
        korp_server_url (str): Korp server URL

    Keyword arguments:
        **kwargs: Passed to class:`KorpExporter` constructor and its
            method:`make_download_file`

    Returns:
        dict: The downloadable file content and meta information;
            contains the following information (strings):

            - download_content: The actual file content
            - download_charset: The character encoding of the file
              content
            - download_content_type: MIME type for the content
            - download_filename: Name of the file
    """
    exporter = KorpExporter(form, **kwargs)
    return exporter.make_download_file(korp_server_url, **kwargs)


class KorpExportError(Exception):

    """An exception class for errors in exporting Korp query results."""

    pass


class KorpExporter(object):

    """A class for exporting Korp query results to a downloadable file."""

    _FORMATTER_SUBPACKAGE = "format"
    """The `korpexport` subpackage containing actual formatter modules"""

    _filename_format_default = u"korp_kwic_{cqpwords:.60}_{date}_{time}{ext}"
    """Default filename format"""

    def __init__(self, form, options=None, filename_format=None,
                 filename_encoding="utf-8"):
        """Construct a KorpExporter.

        Arguments:
            form (dict): CGI (query string) parameters

        Keyword arguments:
            options (dict): Options passed to formatter
            filename_format (unicode): A format specification for the
                resulting filename; may contain the following format
                keys: cqpwords, start, end, date, time, ext
            filename_encoding (str): The encoding to use for the
                filename
        """
        self._form = form
        self._filename_format = (filename_format
                                 or form.get("filename_format")
                                 or self._filename_format_default)
        self._filename_encoding = filename_encoding
        self._opts = options or {}
        self._query_params = {}
        self._query_result = None
        self._formatter = None

    def make_download_file(self, korp_server_url, **kwargs):
        """Format query results and return them in a downloadable format.

        Arguments:
            korp_server_url (str): The Korp server to query

        Keyword arguments:
            form (dict): Use the parameters in here instead of those
                provided to the constructor
            **kwargs: Passed on to formatter

        Returns:
            dict: As described above in :func:`make_download_file`
        """
        result = {}
        if "form" in kwargs:
            self._form = kwargs["form"]
        self._formatter = self._formatter or self._get_formatter(**kwargs)
        self.process_query(korp_server_url)
        if "ERROR" in self._query_result:
            return self._query_result
        logging.debug('formatter: %s', self._formatter)
        result["download_charset"] = self._formatter.download_charset
        content = self._formatter.make_download_content(
            self._query_result, self._query_params, self._opts, **kwargs)
        if isinstance(content, unicode) and self._formatter.download_charset:
            content = content.encode(self._formatter.download_charset)
        result["download_content"] = content
        result["download_content_type"] = self._formatter.mime_type
        result["download_filename"] = self._get_filename()
        logging.debug('make_download_file result: %s', result)
        return result

    def _get_formatter(self, **kwargs):
        """Get a formatter instance for the format specified in self._form.

        Keyword arguments:
            **kwargs: Passed to formatter constructor; "options"
                override the options passed to exporter constructor

        Returns:
            An instance of a korpexport.KorpExportFormatter subclass
        """
        format_name = self._form.get("format", "json").lower()
        formatter_class = self._find_formatter_class(format_name)
        # Options passed to _get_formatter() override those passed to
        # the KorpExporter constructor
        opts = {}
        opts.update(self._opts)
        opts.update(kwargs.get("options", {}))
        kwargs["format"] = format_name
        kwargs["options"] = opts
        return formatter_class(**kwargs)

    def _find_formatter_class(self, format_name):
        """Find a formatter class for the specified format.
        
        Arguments:
            format_name: The name of the format for which to find a
                formatter class

        Returns:
            class: The formatter class for `format_name`

        Raises:
            KorpExportError: If no formatter found for `format_name`

        Searches for a formatter in the classes of
        package:`korpexport.format` modules, and returns the first
        whose `format` attribute contains `format_name`.
        """
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
        """Get the query result in form or perform query via a Korp server.

        Arguments:
            korp_server_url (str): The Korp server to query
            query_params (dict): Korp query parameters

        If `self._form` contains `query_result`, use it. Otherwise use
        the result obtained by performing a query to the Korp server
        at `korp_server_url`. The query parameters are retrieved from
        argument `query_params`, form field `query_params` (as JSON)
        or the form as a whole.

        Set a private attribute to contain the result, a dictionary
        converted from the JSON returned by Korp.
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
            if "debug" in self._form and "debug" not in self._query_params:
                self._query_params["debug"] = self._form["debug"]
            # If the format uses structural information, add the
            # structs in param "show_struct" to "show", so that tokens
            # are associated with information on opening and closing
            # those structures. Param "show_struct" only gives us
            # struct attribute values for a whole sentence.
            if self._formatter.structured_format:
                self._query_params["show"] += self._query_params["show_struct"]
            logging.debug("query_params: %s", self._query_params)
            query_result_json = self._query_korp_server(korp_server_url)
            # Support "sort" in format params even if not specified
            if "sort" not in self._query_params:
                self._query_params["sort"] = "none"
        self._query_result = json.loads(query_result_json)
        logging.debug("query result: %s", self._query_result)
        if "ERROR" in self._query_result or "kwic" not in self._query_result:
            return
        self._opts = self._extract_options(korp_server_url)
        logging.debug("opts: %s", self._opts)

    def _query_korp_server(self, url_or_progname):
        """Query a Korp server, either via HTTP or as a subprocess.

        If url_or_progname begins with "http", make a query via HTTP.
        Otherwise assume it as program name and call it directly as a
        subprocess but make it believe that it is run via CGI. The
        latter approach passes the environment variable values of this
        script to the Korp server, so it gets e.g. the Sibboleth
        authentication informatin. (Could the authentication
        information be passed when using HTTP by adding appropriate
        request headers?)
        """

        def adjust_path(name_src, ref_name_src, ref_name_dst):
            """Make a name that is to name_src as ref_name_dst is to
            ref_name_src."""
            # FIXME: This works only if path separator is a slash
            src_common_prefix = os.path.commonprefix([name_src, ref_name_src])
            ref_name_suffix_len = len(ref_name_src) - len(src_common_prefix)
            name_suffix_len = len(name_src) - len(src_common_prefix)
            return (ref_name_dst[:-ref_name_suffix_len]
                    + name_src[-name_suffix_len:])

        # Encode the query parameters in UTF-8 for Korp server
        logging.debug("Korp server: %s", url_or_progname)
        logging.debug("Korp query params: %s", self._query_params)
        query_params_encoded = urllib.urlencode(
            dict((key, val.encode("utf-8"))
                 for key, val in self._query_params.iteritems()))
        logging.debug("Encoded query params: %s", query_params_encoded)
        logging.debug("Env: %s", os.environ)
        if url_or_progname.startswith("http"):
            return urllib2.urlopen(url_or_progname, query_params_encoded).read()
        else:
            env = {}
            # Pass the environment of this scropt appropriately
            # modified, so that Korp server script thinks it is run
            # via CGI.
            env.update(os.environ)
            # Adjusting the script names is perhaps not necessary but
            # we do it for completeness sake.
            script_name = adjust_path(
                url_or_progname, env.get("SCRIPT_FILENAME", ""),
                env.get("SCRIPT_NAME", ""))
            env.update(
                {"SCRIPT_FILENAME": url_or_progname,
                 "SCRIPT_NAME": script_name,
                 "REQUEST_URI": script_name,
                 "REQUEST_METHOD": "POST",
                 "QUERY_STRING": "",
                 "CONTENT_TYPE": "application/x-www-form-urlencoded",
                 "CONTENT_LENGTH": str(len(query_params_encoded))})
            logging.debug("Env modified: %s", env)
            p = Popen(url_or_progname, stdin=PIPE, stdout=PIPE, env=env)
            output = p.communicate(query_params_encoded)[0]
            logging.debug("Korp server output: %s", output)
            # Remove HTTP headers from the result
            return re.sub(r"(?s)^.*?\n\n", "", output, count=1)

    def _extract_options(self, korp_server_url=None):
        """Extract formatting options from form, affected by query params.

        Arguments:
            korp_server_url: The default Korp server URL; may be
                overridden by options on the form.

        Returns:
            dict: The extracted options.

        Extract options from the form: take the values of all
        parameters for which `_default_options` contains an option
        with the same name.

        In addition, the values of the CGI parameters `attrs` and
        `structs` control the attributes and structures to be shown in
        the result. Their values may be comma-separated lists of the
        following:

        - attribute or structure names;
        - ``*`` for those listed in the corresponding query parameter
          (`show` or `show_struct`);
        - ``+`` for all of those that actually occur in the
          corresponding query result structure; and
        - ``-attr`` for excluding the attribute or structure ``attr``
          (used following ``*`` or ``+``).
        """
        opts = {}

        def extract_show_opt(opt_name, query_param_name,
                             query_result_struct_name):
            """Set the show option opt_name based on query params and result.
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
        """Return the filename for the result, from form or formatted.

        If the form contains parameter `filename`, return it;
        otherwise format using `self._filename_format`. The filename
        format may contain the following keys (specified as
        ``{key}``):

        - date: Current date in *yyyymmdd* format
        - time: Current time in *hhmmss* format
        - ext: Filename extension, including the period
        - cqpwords: The words in the CQP query for the Korp result to
          be exported
        - start: The number of the first result
        - end: The number of the last result
        """
        # FIXME: Get a time first and then format it, to avoid the
        # unlikely possibility of date changing between formatting the
        # date and time.
        # TODO: User-specified date and time formatting
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
        """Make a representation of the CQP query for the filename

        Arguments:
            attrs (bool): Whether to include attribute names in the
                result (unimplemented)
            keep_chars (str): The (punctuation) characters to retain
                in the CQP query
            replace_char (str): The character with which to replace
                characters removed from the CQP query

        Returns:
            unicode: A representation of the CQP query 
        """
        # TODO: If attrs is True, include attribute names. Could we
        # encode somehow the operator which could be != or contains?
        words = re.findall(r'\"((?:[^\\\"]|\\.)*?)\"',
                           self._query_params["cqp"])
        replace_chars_re = re.compile(
            r'[^\w' + re.escape(keep_chars or "") + ']+', re.UNICODE)
        return replace_char.join(replace_chars_re.sub(replace_char, word)
                                 for word in words)


# For testing: find formatter class for format "json".

if __name__ == "__main__":
    print KorpExporter._find_formatter_class('json')
