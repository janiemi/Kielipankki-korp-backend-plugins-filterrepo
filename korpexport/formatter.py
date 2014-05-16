# -*- coding: utf-8 -*-

"""
Module containing a base class for Korp search result formatters.

This module contains :class:`KorpExportFormatter`, which implements
basic formatting of Korp query results. The class should be subclassed
for actual export formats; please see the class documentation for more
information.

:Author: Jyrki Niemi <jyrki.niemi@helsinki.fi> for FIN-CLARIN
:Date: 2014
"""


from __future__ import absolute_import

import time
import string
import re

import korpexport.queryresult as qr

__all__ = ["KorpExportFormatter"]


class _PartialStringFormatter(string.Formatter):

    """
    A string formatter handling missing keys.

    A string formatter that outputs an empty (or other specified)
    string when a format key would cause a `KeyError` or
    `AttributeError`.

    Adapted from
    http://stackoverflow.com/questions/20248355/how-to-get-python-to-gracefully-format-none-and-non-existing-fields
    https://gist.github.com/navarroj/7689682
    """

    def __init__(self, missing=""):
        self.missing = missing

    def get_field(self, field_name, args, kwargs):
        # Handle missing fields
        try:
            return super(_PartialStringFormatter, self).get_field(
                field_name, args, kwargs)
        except (KeyError, AttributeError):
            return None, field_name

    def format_field(self, value, spec):
        if value is None:
            return self.missing
        else:
            return super(_PartialStringFormatter, self).format_field(
                value, spec)


class KorpExportFormatter(object):

    r"""
    The base class for formatting a Korp query result for export.

    This class needs to be subclassed for actual formats. The
    subclasses should override at least the following class
    attributes:

        formats (list[str]): The names or ids (in lowercase) of the
            formats that the class handles
        mime_type (str): The MIME type of the output file
        filename_extension (str): The extension (including the dot) of
            the output file name

    In addition, a subclass often overrides various values in the
    class attribute `_option_defaults` (dict). If a key in
    `_option_defaults` is not specified, the value from a superclass
    is used. Subclasses may also add options of their own. See below
    for the option keys.

    A subclass may also need to override or extend some `_format_*`
    methods, in particular if the structure of the output file is
    complex. Most of the default `_format_*` methods use the string
    format strings specified in options (`_option_defaults` or
    overriden in an instance) to control the output format.

    All the formatting methods have a keyword argument dictionary
    (``kwargs`` or ``format_args``), whose contents is passed
    recursively to the methods formatting the subcomponents of a query
    result component (item). The keyword arguments can be used to pass
    additional arguments to formatting methods overridden or extended
    in a subclass.

    Another approach is to override the method `_format_content` and
    to implement a formatting machinery independent of the other
    `_format_*` methods and `_option_defaults`.

    The names of the `_format_*` methods begin with an underscore to
    indicate that they are not public, even though they are intended
    to be used or overridden by subclasses.

    The `_option_defaults` contains the following keys. Values are
    strings (`unicode`) unless otherwise specified. In `bool` options,
    the strings ``false``, ``off``, ``no``, ``0`` (case-insensitively)
    and the empty string are interpreted as `False`.

    Keys:
        list_valued_opts (list[str] | str): The names of options with
            values that can be lists of strings or strings of
            comma-separated items, to be converted to proper lists
        newline: The character sequence for a newline. This allows
            using \n for newline in format strings, and convert to the
            final only later. Use \r\n for DOS/Windows-style newlines
            for formats which need them.
        show_info (bool): Whether to show info about the query and
            results
        show_field_headings (bool): Whether to show field (column)
            headings
        content_format: Format string for the whole content
        infoitems_format: Format string for the query and results info
        infoitems (list[str] | str): The info items to show in the
            query and results info
        infoitem_labels (dict[str->str]): Mapping from info item names
            (as in `infoitems`) to possibly more human-readable labels
        infoitem_format: Format string for a single info item
        infoitem_sep: Separator of individual formatted info items
        title_format: Format string for the file "title"
        title: A "title" for the exported file
        date_format: A `strftime` format string for current date and
            time
        hitcount_format: Format string for the total number of hits
        params_format: Format string for query parameters as a whole
        params (list[str] | str): Names of the query parameters (as in
            the CGI query string) to show in the info
        param_labels (dict[str->str]): Mapping from query parameter
            names to more human-readable labels
        param_format: Format string for a single query parameter
        param_sep: Separator of individual formatted query parameters
        field_headings_format: Format string for field (column)
            headings
        sentence_format: Format string for a single sentence
        sentence_sep: Separator of individual sentences
        sentence_info_format: Format string for sentence info
        sentence_fields (list[str] | str): Names of the fields of
            sentences to be shown
        sentence_field_labels (dict[str->str]): Mapping from sentence
            field names to more human-readable labels
        sentence_field_format: Format string for a single sentence
            field
        sentence_field_sep: Separator of individual formatted sentence
            fields 
        aligned_format: Format string for an aligned sentence
        aligned_sep: Separator of formatted aligned sentences
        struct_format: Format string for a structural attribute
        struct_sep: Separator of individual formatted structural
            attributes
        token_format: Format string for a single token
        token_noattrs_format: Format string for a single token without
            (token) attributes
        token_sep: Separator of individual formatted tokens
        word_format: Format string for a word (word form)
        token_fields (list[str] | str): Names of the fields (word and
            attributes) of a token to be shown
        token_field_labels (dict[str->str]): Mapping from token field
            names to more human-readable labels
        token_field_format: Format string for a single token field
        token_field_sep: Separator of individual formatted token
            fields
        attr_format: Format string for a token attribute
        attr_sep: Separator of individual formatted token attributes
        token_struct_open_format: Format string for an structural
            attribute opening immediately before a token
        token_struct_close_format: Format string for an structural
            attribute opening immediately after a token
        token_struct_open_sep: Separator of individual structural
            attributes opening immediately before a token
        token_struct_close_sep: Separator of individual structural
            attributes closing immediately after a token
        combine_token_structs (bool): Whether to combine structural
            attributes opening immediately before or closing
            immediately after a token, so that each structure (element
            in XML) is represented only once, with attributes and
            their values in a list. If false, use the Corpus Workbench
            representation: a structural attribute *elem*_*attr* for
            the attribute *attr* of element *elem*.
        match_open: The string with which to precede the match
        match_close: The string with which to follow the match
        match_marker: The string with which to mark a match (in a
            separate match field of a token)
    """

    formats = []
    """The names (ids) of the formats that the class handles."""
    download_charset = "utf-8"
    """The character encoding for the output file."""
    mime_type = "application/unknown"
    """The MIME type of the output file."""
    filename_extension = ""
    """The extension of the output file, inculding a possible dot."""
    # Is this needed any more?
    structured_format = False
    """Set to `True`, if the format uses struct open/close info in tokens."""

    # Default values for options; see the class docstring for
    # documentation
    # TODO: More consistent handling of list-valued items: format for
    # each item, their separator and a format for the whole list
    _option_defaults = {
        "list_valued_opts": [
            "infoitems",
            "params",
            "sentence_fields",
            "token_fields"
            ],
        "newline": "\n",
        "show_info": "True",
        "show_field_headings": "True",
        "content_format": u"{info}{sentence_field_headings}{sentences}",
        "infoitems_format": "{title}{infoitems}\n",
        "infoitems": "date,korp_url,params,hitcount",
        "infoitem_labels": {
            "date": "Date",
            "params": "Query parameters",
            "hitcount": "Total hits",
            "korp_url": "Korp URL",
            "korp_server_url": "Korp server URL"
            },
        "infoitem_format": u"{label}:{sp_or_nl}{value}",
        "infoitem_sep": "\n",
        "title_format": u"{title}\n",
        "title": "Korp search results",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "hitcount_format": u"{hitcount}",
        "params_format": u"{params}",
        "params": "corpus,cqp,defaultcontext,defaultwithin,sort,start,end",
        "param_labels": {
            "corpus": "corpora",
            "cqp": "CQP query",
            "defaultcontext": "context",
            "defaultwithin": "within",
            "sort": "sorting"
            },
        "param_format": u"{label}: {value}", 
        "param_sep": "; ",
        "field_headings_format": u"{field_headings}\n",
        "sentence_format": (u"{info}: {left_context}"
                            u"{match_open}{match}{match_close}"
                            u"{right_context}\n"),
        "sentence_sep": u"",
        "sentence_info_format": u"{corpus} {match_pos}",
        "sentence_fields": "",
        "sentence_field_labels": {
            "match_pos": "match position",
            "left_context": "left context",
            "right_context": "right context",
            "aligned": "aligned text"
            },
        "sentence_field_format": u"{value}",
        "sentence_field_sep": "",
        "aligned_format": u"{sentence}",
        "aligned_sep": u" | ",
        "struct_format": u"{name}: {value}",
        "struct_sep": u"; ",
        "token_format": u"{word}[{attrs}]",
        "token_noattrs_format": u"{word}",
        "token_sep": u" ",
        "word_format": u"{word}",
        "token_fields": "word,*attrs",
        "token_field_labels": {
            "match_mark": "match"
            },
        "token_field_format": u"{value}",
        "token_field_sep": ";",
        "attr_format": u"{value}",
        "attr_sep": u";",
        "token_struct_open_format": u"",
        "token_struct_close_format": u"",
        "token_struct_open_sep": "",
        "token_struct_close_sep": "",
        "combine_token_structs": "False",
        "match_open": u"",
        "match_close": u"",
        "match_marker": u"*",
        }
    """Default values for options; subclasses can override individually."""

    _formatter = _PartialStringFormatter("[none]")
    """A string formatter: missing keys in formats shown as ``[none]``."""

    def __init__(self, **kwargs):
        """Construct a formatter instance.

        Construct a formatter instance for format `kwargs["format"]`.
        The options `kwargs["options"]` override the values in the
        class attribute `_option_defaults` for the instance attribute
        `_opts`. Other keyword arguments `kwargs` are currently
        ignored.

        Subclass constructors should call this constructor to ensure
        that all the relevant instance attributes are defined.
        """
        self._format_name = kwargs.get("format")
        self._opts = {}
        self._opts.update(self._get_combined_option_defaults())
        self._opts.update(kwargs.get("options", {}))
        self._query_params = {}
        self._query_result = {}

    @classmethod
    def _get_combined_option_defaults(cls):
        """Get `_option_defaults` also containing inherited values.

        The returned dict contains values of the class attribute
        `_option_defaults` from all superclasses so that values from
        classes earlier in the MRO override values from those later.
        """
        option_defaults_combined = {}
        # Skip the last class in MRO, since it is `object`, which does
        # not contain `_option_defaults`.
        for superclass in reversed(cls.__mro__[:-1]):
            try:
                option_defaults_combined.update(superclass._option_defaults)
            except AttributeError:
                pass
        return option_defaults_combined

    def get_options(self):
        """Get the options in effect (a dict)."""
        return self._opts

    def get_option_bool(self, optname):
        """Get the value of the Boolean option `optname`.

        String values ``false``, ``no``, ``off``, ``0``
        (case-insensitively) and the empty string are considered as
        `False`, other values as `True`.
        """
        # TODO: Allow the option to have a bool value in addition to a
        # str interpreted as a bool
        return (self._opts[optname].lower()
                not in ["false", "no", "off", "0", ""])

    def get_option_int(self, optname):
        """Get the value of the integer option `optname`.

        If the option value cannot be converted to an `int`, try the
        value in `_option_defaults`.
        """
        value = None
        try:
            value = int(self._opts[optname])
        except (ValueError, TypeError):
            value = int(self._option_defaults[optname])
        return value

    def make_download_content(self, query_result, query_params=None,
                              options=None, **kwargs):
        """Generate downloadable content from a Korp query result.

        Return downloadable file content from Korp query result
        `query_result`, given `query_params` and `options`. `options`
        overrides options given when constructing the class. The
        return value has newlines converted if necessary.
        """
        self._query_result = query_result
        self._query_params = query_params or {}
        self._opts.update(options or {})
        self._adjust_opts()
        self._init_infoitems()
        return self._convert_newlines(
            self._postprocess(self._format_content(**kwargs)))

    def _adjust_opts(self):
        """Adjust formatting options in effect.

        This method may be overridden or extended in subclasses.
        """
        self._make_opt_lists()

    def _make_opt_lists(self):
        """Convert comma-separated strings in list-valued options to lists."""

        def adjust_item(item):
            """Handle special markers in a list item.

            If `item` is of the form ``*name``, replace it with a list
            containing the items in the option ``name``; if `item` is
            ``?aligned``, add ``aligned`` only if the corpus is a
            parallel corpus. The return value is a list.
            """
            if item.startswith("*"):
                return self._opts.get(item[1:], [])
            elif item == "?aligned":
                return ([item[1:]] if qr.is_parallel_corpus(self._query_result)
                        else [])
            else:
                return [item]

        for optkey in self._opts.get("list_valued_opts", []):
            if isinstance(self._opts.get(optkey), basestring):
                self._opts[optkey] = self._opts.get(optkey, "").split(",")
                adjusted_list = []
                for item in self._opts[optkey]:
                    adjusted_list.extend(adjust_item(item))
                self._opts[optkey] = adjusted_list

    def _init_infoitems(self):
        """Initialize query result info items used in several format methods.

        Initialize a dictionary for the following format keys (query
        and result info items) to be used in the format strings of
        several different components:

        ``params``: formatted query parameters as a list
        ``param``: a dictionary of unformatted query parameters
        ``date``: current date
        ``hitcount``: the total number of hits
        ``sentence_field_headings``: headings for fields of a sentence
        ``token_field_headings``: headings for fields of a token
        ``title``: a "title" for the file
        ``korp_url``: URL of the Korp service (frontend) used
        ``korp_server_url``: URL of the Korp server (backend) used
        """
        self._infoitems = dict(
            params=self._format_params(),
            # Also allow format references {param[name]}
            param=self._query_params,
            date=self._format_date(),
            hitcount=self._format_hitcount(),
            sentence_field_headings=self._format_field_headings("sentence"),
            token_field_headings=self._format_field_headings("token"),
            title=self._format_title(),
            korp_url=self._opts.get("korp_url"),
            korp_server_url=self._opts.get("korp_server_url"))

    def _convert_newlines(self, text):
        """Return `text` with newlines as specified in option ``newline``."""
        if self._opts["newline"] != "\n":
            return text.replace("\n", self._opts["newline"])
        else:
            return text

    def _postprocess(self, text):
        """Return the formatted content `text` post-processed.

        This method is designed to be overridden in subclasses. The
        default is to return `text` as is.
        """
        return text

    def _get_sentence_structs(self, sentence, all_structs=False):
        """Get the structural attributes of a sentence.

        Get the structural attributes of `sentence` as a list of pairs
        (struct name, value). If `all_structs` is `False` (the
        default), get the structs specified in the option ``structs``;
        otherwise get all structs.
        """
        return qr.get_sentence_structs(
            sentence, None if all_structs else self._opts.get("structs", []))

    def _get_formatted_sentence_structs(self, sentence, **kwargs):
        """Get all the formatted structural attributes of a sentence.

        Return a dict with structural attribute names as keys and
        formatted values as values.
        """
        return dict([(key, self._format_struct((key, val), **kwargs))
                     for (key, val)
                     in self._get_sentence_structs(sentence, all_structs=True)])

    def _get_token_attrs(self, token, all_attrs=False):
        """Get the (positional) attributes of a token.

        Get the positional attributes of `token` as a list of pairs
        (attr name, value). If `all_attrs` is `False` (the default),
        get the attributes specified in the option ``attrs`` otherwise
        get all attributes.
        """
        return qr.get_token_attrs(
            token, None if all_attrs else self._opts.get("attrs", []))

    # Generic formatter methods used by the concrete formatter methods
    # for formatting individual components of a query result. These
    # methods typically need not be extended or overridden in
    # subclasses.

    def _format_item(self, item_type, **format_args):
        """Format an item of `item_type` in the query result.

        Use the format string for `item_type` in the options as a
        template, filled with keys in `format_args`. Uses the string
        formatter handling missing keys in the format string. (The
        *item* in *item_type* does not refer to (only) list items, but
        to any component of a query result.)
        """
        return self._formatter.format(self._opts[item_type + "_format"],
                                      **format_args)

    def _format_list(self, item_type, list_, format_fn=None, **kwargs):
        """Format the list `list_` of items of `item_type`.

        Format list items using a formatting function (method)
        `format_fn`. If `format_fn` is not specified, use the method
        ``_format_``*item_type* in the class of `self`. `kwargs` is
        passed to `format_fn`. Separate list items with the separator
        specified by the option *item_type*``_sep``.

        Supports the option *item_type*``_skip``, which specifies a
        regular expression. If specified and if a formatted list item
        as a whole matches the regular expression, the list item is
        not included in the result.
        """
        format_fn = format_fn or getattr(self, "_format_" + item_type)
        skip_re = self._opts.get(item_type + "_skip")
        if skip_re:
            skip_re = re.compile(r"^" + skip_re + r"$", re.UNICODE)
        return self._opts[item_type + "_sep"].join(
            formatted_elem for elem in list_
            for formatted_elem in [format_fn(elem, **kwargs)]
            if not (skip_re and skip_re.match(formatted_elem)))

    def _format_label_list_item(self, item_type, key, value, **format_args):
        """Format an item of a list whose items have labels.

        Format a list item of `item_type`, having `key` and `value`.
        The options must contain a label dictionary for `item_type`
        (*item_type*``_labels``) that maps keys to labels.

        Format keys in *item_type*``_format``: ``key``, ``value``,
        ``label``, ``sp_or_nl`` (a newline if `value` contains
        newlines, otherwise a space).
        """
        return self._format_item(
            item_type,
            key=key,
            label=self._opts[item_type + "_labels"].get(key, key),
            value=value,
            sp_or_nl="\n" if "\n" in unicode(value) else " ",
            **format_args)

    def _format_field_headings(self, item_type, **kwargs):
        """Format field headings for `item_type`.

        Format headings for the fields specified in the option
        *item_type*``_fields``. Format each item as a labelled list
        item of the item type *item_type*``_field``. If the option
        ``show_field_headings`` is `False`, return an empty string.

        Format keys in ``field_headings_format``: ``field_headings``
        (the list of headings formatted).
        """
        if not self.get_option_bool("show_field_headings"):
            return ""
        fields = self._opts.get(item_type + "_fields")
        if fields:
            headings = self._format_list(
                item_type + "_field",
                fields,
                lambda item, **kwargs: (
                    self._format_label_list_item(
                        item_type + "_field", item,
                        self._opts[item_type + "_field_labels"]
                        .get(item, item))),
                **kwargs)
        else:
            headings = ""
        return self._format_item(
            "field_headings", field_headings=headings, **kwargs)

    # def _format_part(self, format_name, arg_fn_args, **format_arg_fns):
    #     # An untested, unused formatting function with a kind of lazy
    #     # evaluation of format arguments: only those arguments are
    #     # evaluated which occur in the format string.
    #     format_str = self._opts[format_name + "_format"]

    #     def make_format_arg_value(arg_name, arg_fn):
    #         return (arg_fn(*arg_fn_args) if "{" + arg_name + "}" in format_str
    #                 else "")

    #     format_args = [(name, make_format_arg_value(name, format_arg_fn))
    #                    for (name, format_arg_fn)
    #                    in format_arg_fns.iteritems()]
    #     return self._format_item(format_name, **format_args)

    # Concrete formatter methods, designed to be overridden in
    # subclasses as necessary.

    def _format_content(self, **kwargs):
        """Format a query result as the content of an exportable file.

        Format keys in ``content_format``: ``info`` (query result meta
        information), ``sentences`` (the sentences in the result).

        This is the main content-formatting method that may be
        overridden in subclasses if they do not need the formatting
        facilities of KorpExportFormatter.
        """
        return self._format_item(
            "content",
            info=self._format_infoitems(**kwargs),
            sentences=self._format_sentences(**kwargs),
            **self._infoitems)

    # Formatting methods for query and result information items (meta
    # information)

    def _format_infoitems(self, **kwargs):
        """Format query and result information items.

        If the option ``show_info`` is `False`, return an empty
        string. The pieces of information can be formatted directly
        here or as a list of the items specified in the option
        ``infoitems``.

        Format keys in ``infoitems_format``: ``infoitems`` (all info
        items formatted); those listed in :method:`_init_infoitems`.
        """
        if self.get_option_bool("show_info"):
            format_args = kwargs
            format_args.update(self._infoitems)
            return self._format_item(
                "infoitems",
                infoitems=self._format_infoitem_fields(),
                **format_args)
        else:
            return ""

    def _format_infoitem_fields(self, **kwargs):
        """Format query and result information items as a list.

        Format the information items listed in the option
        ``infoitems`` as a list. Use ``infoitem_format`` to format the
        individual info fields and ``infoitem_sep`` to separate them.
        """
        return self._format_list(
            "infoitem",
            self._opts.get("infoitems", []),
            **kwargs)

    def _format_infoitem(self, key, **format_args):
        """Format an individual query and result information field.

        Format keys in ``infoitem_format``: those listed in
        :method:`_format_label_list_item`. ``value`` is formatted if
        the formatting method ``_format_``*key* exists, otherwise it
        is the value of the option *key*.
        """
        try:
            value = getattr(self, "_format_" + key)()
        except AttributeError:
            value = self._opts.get(key)
        return self._format_label_list_item(
            "infoitem", key, value, **format_args)

    def _format_title(self, **format_args):
        """Format query result title.

        Format keys in ``title_format``: ``title`` (the value of the
        option ``title``). If ``title`` is empty, return an empty
        string.
        """
        title = title=self._opts.get("title")
        if title is None:
            return ""
        else:
            return self._format_item("title", title=title, **format_args)

    def _format_date(self, **kwargs):
        """Format the current date.

        Format the current date using the `strftime` format in the
        option ``date_format``.
        """
        return time.strftime(self._opts["date_format"])

    def _format_hitcount(self, **format_args):
        """Format the total number of hits.

        Format keys in ``hitcount_format``: ``hitcount`` (the number
        of hits as a string).
        """
        return self._format_item(
            "hitcount",
            hitcount=qr.get_hitcount(self._query_result),
            **format_args)

    def _format_params(self, **format_args):
        """Format query parameters.

        Format keys in ``params_format``: ``param`` (a dictionary of
        unformatted query parameters), ``params`` (a formatted list of
        query parameter fields), all parameter names as such.
        """
        # Allow format references {name} as well as {param[name]}
        format_args.update(self._query_params)
        return self._format_item(
            "params",
            param=self._query_params,
            params=self._format_param_fields(),
            **format_args)

    def _format_param_fields(self, **format_args):
        """Format query parameters as a list.

        Format the parameters listed in the option ``params`` as a
        list. Use ``param_format`` to format the individual parameters
        and ``param_sep`` to separate them.
        """
        return self._format_list(
            "param",
            self._opts.get("params", []),
            **format_args)

    def _format_param(self, key, **format_args):
        """Format an individual query parameter.

        Format keys in ``param_format``: those listed in
        :method:`_format_label_list_item`.
        """
        return self._format_label_list_item(
            "param", key, self._query_params.get(key), **format_args)

    # Formatting methods for the query result proper

    def _format_sentences(self, **kwargs):
        """Format the sentences of a query result.

        Format all the sentences of a query result as a list. Use
        ``sentence_format`` to format the individual sentences and
        ``sentence_sep`` to separate them.
        """
        return self._format_list(
            "sentence", qr.get_sentences(self._query_result), **kwargs)

    def _format_sentence(self, sentence, **kwargs):
        """Format a single sentence.

        Format keys in ``sentence_format``: ``corpus`` (the name (id)
        of the corpus), ``match_pos`` (corpus position (the number of
        the first token) of the match), ``tokens`` (all tokens in the
        sentence), ``match`` (the tokens that are part of the match),
        ``left_context`` (the tokens that precede the match),
        ``right_context`` (the tokens that follow the match),
        ``aligned`` (aligned sentences in a parallel corpus),
        ``structs`` (formatted structural attributes of the sentence),
        ``struct`` (a dict of the structural attributes, unformatted),
        ``arg`` (a dict of additional keyword arguments passed),
        ``info`` (formatted sentence information), ``fields``
        (formatted sentence fields as specified in the option
        ``sentence_fields``); names of structural attributes
        (unformatted); those listed in :method:`_init_infoitems`.
        """
        struct = self._get_formatted_sentence_structs(sentence, **kwargs)
        format_args = dict(
            corpus=qr.get_sentence_corpus(sentence),
            match_pos=qr.get_sentence_match_position(sentence),
            tokens=self._format_tokens(
                qr.get_sentence_tokens_all(sentence)),
            match=self._format_tokens(
                qr.get_sentence_tokens_match(sentence),
                match_mark=self._opts.get("match_marker", "")),
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
        # Allow direct format references to struct names (unformatted
        # values)
        format_args.update(dict(self._get_sentence_structs(sentence)))
        format_args.update(self._infoitems)
        format_args.update(dict(info=self._format_item("sentence_info",
                                                       **format_args)))
        return self._format_item(
            "sentence",
            fields=self._format_list("sentence_field",
                                     self._opts.get("sentence_fields", []),
                                     **format_args),
            **format_args)

    def _format_sentence_field(self, key, **format_args):
        """Format a single sentence field with the key `key`.

        Format keys in ``sentence_field_format``: those listed in
        :method:`_format_label_list_item`. ``value`` is the value of
        `key` in `format_args`, containing the format keys for
        ``sentence_format``, if exists; otherwise the value of
        ``struct[key]``.
        """
        value = format_args.get(key)
        if value is None:
            value = format_args.get("struct", {}).get(key, "")
        return self._format_label_list_item(
            "sentence_field", key, value, **format_args)

    def _format_aligned_sentences(self, sentence, **kwargs):
        """Format the aligned sentences of `sentence`.

        Format the sentences aligned with `sentence` (in a parallel
        corpus) as a list. Use ``aligned_format`` to format individual
        sentences and ``aligned_sep`` to separate them.
        """
        # In practice, currently Korp returns only a single aligned
        # sentence, but CWB supports multiple alignments, so support
        # it here as well.
        return self._format_list("aligned",
                                 qr.get_aligned_sentences(sentence),
                                 self._format_aligned_sentence,
                                 **kwargs)

    def _format_aligned_sentence(self, aligned_sentence, **format_args):
        """Format a single aligned sentence.

        Format keys in ``aligned_format``: ``align_key`` (the name of
        the alignment attribute; in practice, the id of the aligned
        corpus in lowercase), ``sentence`` (the aligned sentence as a
        formatted string of tokens).
        """
        align_key, sentence = aligned_sentence
        return self._format_item(
            "aligned",
            align_key=align_key,
            sentence=self._format_tokens(sentence, **format_args),
            **format_args)

    def _format_structs(self, sentence, **kwargs):
        """Format the strucutral attributes of `sentence`.

        Format the structural attributes of `sentence` as a list. Use
        ``struct_format`` to format individual structural attributes
        and ``struct_sep`` to separate them.
        """
        return self._format_list("struct",
                                 self._get_sentence_structs(sentence),
                                 **kwargs)

    def _format_struct(self, struct, **format_args):
        """Format a single structural attribute `struct`.

        Format keys in ``struct_format``: ``name`` (the name of the
        attribute), ``value`` (its value).
        """
        return self._format_item(
            "struct", name=struct[0], value=struct[1], **format_args)

    def _format_tokens(self, tokens, **kwargs):
        """Format the tokens of a single sentence.

        Format `tokens` as a list. Use ``token_format`` to format the
        individual tokens and ``token_sep`` to separate them.
        """
        return self._format_list("token", tokens, **kwargs)

    def _format_token(self, token, **kwargs):
        """Format a single token `token`, possibly with attributes.
        
        Format a single token using the format ``token_format``, or
        ``token_noattrs_format`` if no (positional) token attributes
        have been specified in option ``attrs``, `structured_format`
        is `False` and the option ``token_fields`` contains at most
        one item.

        Format keys: ``word`` (formatted wordform), ``attrs``
        (formatted token attributes), ``structs_open`` (structural
        attributes opening immediately before the token, formatted),
        ``structs_close`` (structural attributes closing immediately
        after the token, formatted), ``fields`` (all the token fields
        specified in the option ``token_fields``, formatted); all the
        token attribute names (unformatted values).
        """
        # Allow for None in word (but where do they come from?)
        word = self._format_item("word", word=(token.get("word") or ""))
        if (self._opts.get("attrs") or self.structured_format
            or len(self._opts.get("token_fields")) > 1):
            format_name = "token"
        else:
            format_name = "token_noattrs"
        format_args = dict(
            word=word,
            attrs=self._format_token_attrs(token),
            structs_open=self._format_token_structs_open(token),
            structs_close=self._format_token_structs_close(token))
        # Allow direct format references to attr names
        format_args.update(dict(self._get_token_attrs(token)))
        format_args.update(kwargs)
        result = self._format_item(
            format_name,
            fields=self._format_list("token_field",
                                     self._opts.get("token_fields", []),
                                     **format_args),
            **format_args)
        return result

    def _format_token_field(self, key, **format_args):
        """Format a single token field having the key `key`.

        Format keys in ``token_field_format``: those listed in
        :method:`_format_label_list_item`. ``value`` is the value of
        `key` in `format_args`, containing the format keys for
        ``_format_token``, if exists; otherwise the value of
        ``attr[key]`` or ``struct[key]``.
        """
        return self._format_label_list_item(
            "token_field", key,
            (format_args.get(key)
             or format_args.get("attr", {}).get(key, "")
             or format_args.get("struct", {}).get(key, "")),
            **format_args)

    def _format_token_attrs(self, token, **kwargs):
        """Format the attributes of `token` (excluding wordform) as a list.

        Use ``attr_format`` to format the individual attributes and
        ``attr_sep`` to separate them."""
        return self._format_list(
            "attr",
            self._get_token_attrs(token),
            self._format_token_attr,
            **kwargs)

    def _format_token_attr(self, attr_name_value, **format_args):
        """Format a single token attribute (name, value) pair.

        Format keys in ``attr_format``: ``name``, ``value``.
        """
        attrname, value = attr_name_value
        return self._format_item(
            "attr", name=attrname, value=(value or ""), **format_args)

    def _format_token_structs_open(self, token, **kwargs):
        """Format the structural attributes opening at `token`.

        Format as a list the structural attributes opening immediately
        before `token`. Use ``token_struct_open_format`` to format
        individual attributes and ``token_struct_open_sep`` to
        separate them.

        The option ``combine_token_structs`` affects the result:
        whether to combine structural attributes representing the
        attributes of the same element or not.
        """
        combine = self.get_option_bool("combine_token_structs")
        return self._format_list(
            "token_struct_open",
            qr.get_token_structs_open(token, combine),
            **kwargs)

    def _format_token_struct_open(self, struct, **format_args):
        """Format a single structural attribute opening at `token`.

        If the option ``combine_token_structs`` is `False`, use the
        format string ``token_struct_open``. If it is `True`, use
        ``token_struct_open_attrs`` if the structural attribute has
        attribute values (XML attributes), else (XML element)
        ``token_struct_open_noattrs``. All these recognize the format
        key ``name`` (name of the structure (XML element));
        ``token_struct_open_attrs`` also recognizes ``attrs``
        containing a formatted list of attributes (in XML sense).
        """
        if self.get_option_bool("combine_token_structs"):
            structname, attrlist = struct
            attrstr = self._format_token_struct_attrs(attrlist, **format_args)
            format_name = (
                "token_struct_open_" + ("attrs" if attrstr else "noattrs"))
            return self._format_item(
                format_name, name=structname, attrs=attrstr, **format_args)
        else:
            return self._format_item(
                "token_struct_open", name=struct, **format_args)

    def _format_token_struct_attrs(self, attrs, **kwargs):
        """Format the attributes `attrs` of a structure.

        Format as a list the attributes (in XML sense) of a structure
        (XML element) opening immediately before a token. Use
        ``token_struct_attr_format`` to format the individual
        attributes and ``token_struct_attr_sep`` to separate them.
        """
        return self._format_list("token_struct_attr", attrs, **kwargs)

    def _format_token_struct_attr(self, attr, **format_args):
        """Format a single attribute `attr` of a structure.

        Format a single attribute `attr` of a structure (XML element)
        opening immediately before a token. Format keys in
        ``token_struct_attr_format``: ``name``, ``value``.
        """
        name, value = attr
        return self._format_item(
            "token_struct_attr", name=name, value=value, **format_args)

    def _format_token_structs_close(self, token, **kwargs):
        """Format the structural attributes closing at `token`.

        Format as a list the structural attributes closing immediately
        after `token`. Use ``token_struct_close_format`` to format
        individual attributes and ``token_struct_close_sep`` to
        separate them.

        The option ``combine_token_structs`` affects the result:
        whether to combine structural attributes associated with the
        same (XML) element or not.
        """
        return self._format_list(
            "token_struct_close",
            qr.get_token_structs_close(
                token, self.get_option_bool("combine_token_structs")),
            **kwargs)

    def _format_token_struct_close(self, struct, **format_args):
        """Format a single structural attribute closing at `token`.

        Format keys in ``token_struct_close_format``: ``name`` (name
        of the structural attribute, or if ``combine_token_structs``
        is `True`, the XML element name in the structural attribute).
        """
        if self.get_option_bool("combine_token_structs"):
            struct, _ = struct
        return self._format_item(
            "token_struct_close", name=struct, **format_args)
