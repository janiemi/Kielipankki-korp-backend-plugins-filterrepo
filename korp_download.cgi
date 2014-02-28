#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
korp_download.cgi

A CGI script to convert Korp query results to downloadable formats

The script requires the following CGI parameters:
- query_result: the Korp query result to format

The following CGI parameters are optional
- format: the format to which to convert the result (json (default),
  csv, tsv, ...)
- filename: the (suggested) name of the file to generate (default:
  korp_kwic_TIME.FMT, where time is the current time (YYYYMMDDhhmmss)
  and FMT the format)
- query_params: korp.cgi parameters for generating query_result
"""


from collections import defaultdict

import sys
import os
import time
import cgi
import json
import urllib, urllib2
import logging


# Korp server URL
KORP_SERVER = "http://localhost/cgi-bin/korp/korp.cgi"

# Path to log file; use /dev/null to disable logging
LOG_FILE = "/v/korp/log/korp-cgi.log"
# Log level: set to logging.DEBUG for also logging actual CQP
# commands, logging.WARNING for only warnings and errors,
# logging.CRITICAL to disable logging
LOG_LEVEL = logging.INFO


def main():
    """The main CGI handler, modified from that of korp.cgi.

    Converts CGI parameters to a dictionary and initializes logging.
    The actual work is done in make_download_file its helper functions
    below.
    """
    starttime = time.time()
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # Open unbuffered stdout
    # Convert form fields to regular dictionary
    form_raw = cgi.FieldStorage()
    form = dict((field, form_raw.getvalue(field)) for field in form_raw.keys())
    # Configure logging
    loglevel = logging.DEBUG if "debug" in form else LOG_LEVEL
    logging.basicConfig(filename=LOG_FILE,
                        format=('[%(filename)s %(process)d' +
                                ' %(levelname)s @ %(asctime)s]' +
                                ' %(message)s'),
                        level=loglevel)
    # Log remote IP address and CGI parameters
    logging.info('IP: %s', cgi.os.environ.get('REMOTE_ADDR'))
    # Limit the length of query_result written to the log
    logging.info("Params: {'format': '%s', 'filename': '%s', "
                 "'query_params': '%s', 'query_result': '%.800s'}",
                 form.get("format"), form.get("filename"),
                 form.get("query_params"), form.get("query_result"))
    try:
        result = make_download_file(form)
    except Exception, e:
        import traceback
        exc = sys.exc_info()
        result = {"ERROR": {"type": exc[0].__name__,
                            "value": str(exc[1])}
                  }
        result["ERROR"]["traceback"] = traceback.format_exc().splitlines()
        logging.error("%s", result["ERROR"])
        # Show traceback only if the parameter debug is specified
        if "debug" not in form:
            del result["ERROR"]["traceback"]
    # Print HTTP header and content
    print_header(result)
    print_object(result)
    # Log elapsed time
    logging.info("Elapsed: %s", str(time.time() - starttime))


def make_download_file(form):
    """Format query results and return them in a downloadable format.

    For format FMT, the function calls the global function
    make_download_content_FMT with the result returned by query() as
    the argument. The function should return a triple (file content,
    file MIME type, filename extension).
    """
    result = {}
    format_type = form.get("format", "json").lower()
    query_params = json.loads(form.get("query_params", "{}"))
    query_result = get_query_result(form, query_params)
    content, content_type, filename_ext = \
        globals()["make_download_content_" + format_type](query_result)
    result["download_charset"] = form.get("encoding", "utf-8")
    result["download_content"] = content.encode(result["download_charset"])
    result["download_content_type"] = content_type
    result["download_filename"] = form.get(
        "filename", "korp_kwic_" + time.strftime("%Y%m%d%H%M%S") + filename_ext)
    return result


def get_query_result(form, query_params):
    """Get the query result in form or perform query via the Korp server.

    If form contains query_result, return it. Otherwise return the
    result obtained by performing a query to Korp server using
    query_params. The returned value is a dictionary converted from
    JSON.
    """
    if "query_result" in form:
        query_result_json = form.get("query_result", "{}")
    else:
        query_result_json = (urllib2.urlopen(KORP_SERVER, 
                                             urllib.urlencode(query_params))
                             .read())
    return json.loads(query_result_json)


def make_download_content_json(query_result):
    """Convert query_result to JSON."""
    return (json.dumps(query_result["kwic"], sort_keys=True, indent=4),
            "application/json", ".json")


def make_download_content_csv(query_result):
    """Convert query_result to comma-separated-values format."""
    return (format_download_content_delimited(query_result, delimiter=u",",
                                              quote=u"\"", escape_quote=u"\"",
                                              newline=u"\r\n"),
            "text/csv", ".csv")


def make_download_content_tsv(query_result):
    """Convert query_result to tab-separated-values format."""
    return (format_download_content_delimited(query_result, delimiter=u"\t",
                                              quote=u"", escape_quote=u"",
                                              newline=u"\r\n"),
            "text/tsv", ".tsv")


def format_download_content_delimited(query_result, **opts):
    """Return query_result in a delimited format specified by opts."""
    content = ""
    for sentence in query_result["kwic"]:
        content += format_sentence_delimited(sentence, **opts)
    return content


def format_sentence_delimited(sentence, **opts):
    """Format a single delimited sentence with the delimiter options opts.

    The result contains the following fields:
    - corpus ID (in upper case)
    - corpus position of the start of the Match
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
              format_sentence_tokens(sentence["tokens"][:match_start]),
              format_sentence_tokens(sentence["tokens"][match_start:match_end]),
              format_sentence_tokens(sentence["tokens"][match_end:])]
    if "aligned" in sentence:
        for align_key, tokens in sorted(sentence["aligned"].iteritems()):
            fields.append(format_sentence_tokens(tokens))
    return format_delimited_fields(fields, **opts)


def format_sentence_tokens(tokens):
    """Format the tokens of a single sentence."""
    # Allow for None in word
    return u" ".join(token.get("word", "") or "" for token in tokens)


def format_delimited_fields(fields, **opts):
    """Format fields according to the options in opts.

    opts may contain the following keyword arguments:
    - delim: field delimiter (default: ,)
    - quote: quotes surrounding fields (default: ")
    - escape_quote: string to precede a quote with in a field value to
      escape it (default: ")
    - newline: end-of-record string (default: \r\n)
    """
    delim = opts.get("delimiter", u",")
    quote = opts.get("quote", u"\"")
    escape_quote = opts.get("escape_quote", quote)
    newline = opts.get("newline", u"\n")
    return (delim.join((quote + field.replace(quote, escape_quote + quote)
                        + quote)
                       for field in fields)
            + newline)


def print_header(obj):
    """Print header for the downloadable file (or error message) in obj.

    obj may contain the following keys affecting the output headers:
    - download_content_type => Content-Type (default: text/plain)
    - download_charset => Charset (default: utf-8)
    - download_filename => Content-Disposition filename
    - download_content => Length to Content-Length
    """
    charset = obj.get("download_charset", "utf-8")
    print "Content-Type: " + (obj.get("download_content_type", "text/plain")
                              if "ERROR" not in obj
                              else "text/plain")
    print "Charset: " + charset
    if "ERROR" not in obj:
        # Default filename 
        print ("Content-Disposition: attachment; filename="
               + obj.get("download_filename", "korp_kwic"))
        print "Content-Length: " + str(len(obj["download_content"]))
    print


def print_object(obj):
    """Print the downloadable content (or error message) in obj."""
    if "ERROR" in obj:
        error = obj["ERROR"]
        print "Error when trying to download results:"
        print error["type"] + ": " + error["value"]
        if "traceback" in error:
            print error["traceback"]
    else:
        print obj["download_content"],


if __name__ == "__main__":
    main()
