# -*- coding: utf-8 -*-

"""
Format Korp query results in HTML.

:Author: Jyrki Niemi <jyrki.niemi@helsinki.fi> for FIN-CLARIN
:Date: 2016
"""


from __future__ import absolute_import

from xml.sax.saxutils import escape

from korpexport.formatter import KorpExportFormatter


class KorpExportFormatterHtml(KorpExportFormatter):

    """
    Format Korp query results in HTML.

    A mix-in class of actual formatters for HTML formats. The class
    does not specify the content of the fields. The class overrides
    `_postprocess` to produce the HTML file. The class can be combined
    (via multiple inheritance) with content formatting classes
    producing sentence-per-line output to produce meaningful output.

    The formatter uses the following options (in `_option_defaults`)
    in addition to those specified in :class:`KorpExportFormatter`:
        match_elem (str): The HTML element in which to enclose mathces
        match_attrs (str): The HTML attributes to add to the start tag
            of match_elem
        html_title_format: Format string for the HTML title, without
            the title start and end tag; the format keys are the same
            as for ``infoitems_format``
        html_opener_format: Format for the page heading and possibly
            other information before the actual content; the format
            should include all the needed HTML tags; the format keys
            are the same as for ``infoitems_format``
        html_line_format: Format
        skip_leading_lines (int): The number of lines to skip in the
            content before formatting content lines, typically some
            kind of header lines
    """

    formats = ["html"]
    mime_type = "text/html"
    filename_extension = ".html"

    _option_defaults = {
        "match_elem": "strong",
        "match_attrs": "",
        "html_title_format": u"{title} {date}",
        "html_opener_format": (
            u"<h1>{title} {date}</h1>\n"
            u"<p><a href=\"{korp_url}\" target=\"_blank\">{korp_url}</a></p>"
            u"<hr/>\n"),
    }

    def __init__(self, **kwargs):
        super(KorpExportFormatterHtml, self).__init__(**kwargs)
        if self._opts["match_attrs"]:
            self._opts["match_attrs"] = " " + self._opts["match_attrs"]
        self._match_open = escape(self._opts.get("match_open"))
        self._match_close = escape(self._opts.get("match_close"))
        self._match_starttag = ""
        self._match_endtag = ""
        self._tag_matches = False
        if self._match_open and self._match_close and self._opts["match_elem"]:
            self._match_starttag = ("<" + self._opts["match_elem"]
                                    + self._opts["match_attrs"] + ">")
            self._match_endtag = "</" + self._opts["match_elem"] + ">"
            self._tag_matches = True
        for html_format in ["html_title_format", "html_opener_format"]:
            self._opts[html_format] = self._protect_html_tags(
                self._opts[html_format])
        self._skip_leading_lines = (self.get_option_int("skip_leading_lines")
                                    or 0)

    def _protect_html_tags(self, html_text):
        return html_text.replace("<", "\x01").replace(">", "\x02")

    def _restore_html_tags(self, html_text):
        return html_text.replace("\x01", "<").replace("\x02", ">")

    def _postprocess(self, text):
        title = self._format_html("title", **self._infoitems)
        opener = self._format_html("opener", **self._infoitems)
        result = [u"<!DOCTYPE html>\n<html>\n"
                  + u"<head>\n<meta charset=\"utf-8\"/>\n<title>"
                  + title + u"</title>\n</head>\n<body>\n" + opener]
        for linenr, line in enumerate(text.rstrip("\n").split("\n")):
            if linenr >= self._skip_leading_lines:
                result.append(u"<p>" + self._mark_matches(escape(line))
                              + u"</p>\n")
        result.append(u"</body>\n</html>\n")
        return "".join(result)

    def _format_html(self, itemname, **format_args):
        return self._restore_html_tags(escape(self._format_item(
            "html_" + itemname, **format_args)))

    def _mark_matches(self, line):
        if self._tag_matches:
            return (line.replace(self._match_open, self._match_starttag)
                    .replace(self._match_close, self._match_endtag))
        else:
            return line
