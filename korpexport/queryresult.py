#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import



def get_sentences(query_result):
    return query_result["kwic"]


def get_hitcount(query_result):
    return query_result["hits"]


def get_corpus_hitcount(query_result, corpus=None):
    if corpus is None:
        return query_result["corpus_hits"]
    else:
        return query_result["corpus_hits"].get(corpus)


def get_occurring_attrnames(query_result, keys, struct_name):
    # FIXME: This does not take into account attributes in aligned
    # sentences
    occurring_keys = set()
    for sent in get_sentences(query_result):
        if isinstance(sent[struct_name], list):
            for item in sent[struct_name]:
                occurring_keys |= set(item.keys())
        else:
            occurring_keys |= set(sent[struct_name].keys())
    return [key for key in keys if key in occurring_keys]


def get_sentence_corpus(sentence):
    return sentence["corpus"]


def get_sentence_tokens(sentence, start, end):
    return sentence["tokens"][start:end]


def get_sentence_tokens_all(sentence):
    return get_sentence_tokens(sentence, None, None)


def get_sentence_tokens_match(sentence):
    return get_sentence_tokens(sentence, sentence["match"]["start"],
                               sentence["match"]["end"])


def get_sentence_tokens_left_context(sentence):
    return get_sentence_tokens(sentence, None, sentence["match"]["start"])


def get_sentence_tokens_right_context(sentence):
    return get_sentence_tokens(sentence, sentence["match"]["end"], None)


def get_sentence_match_position(sentence):
    return sentence["match"]["position"]


def get_aligned_sentences(sentence):
    return sorted(sentence.get("aligned", {}).iteritems())


def get_sentence_structs(sentence, structnames=None):
    # Value may be None; convert them to empty strings
    if structnames is None:
        return list(sentence["structs"].iteritems())
    else:
        return [(structname, sentence["structs"].get(structname) or "")
                for structname in structnames]


def get_sentence_struct_values(sentence, structnames=None):
    return [value for name, value in
            get_sentence_structs(sentence, structnames)]


def get_token_attrs(token, attrnames=None):
    if attrnames is None:
        return [(attrname, val) for attrname, val in token.iteritems()
                if attrname != "structs"]
    else:
        return [(attrname, token.get(attrname) or "") for attrname in attrnames]


def get_token_structs_open(token, combine_attrs=False):
    return _get_token_structs(token, "open", combine_attrs)


def get_token_structs_close(token, combine_attrs=False):
    return _get_token_structs(token, "close", combine_attrs)


def _get_token_structs(token, struct_type, combine_attrs=False):
    try:
        structs = token["structs"][struct_type]
    except KeyError:
        return []
    if combine_attrs:
        structs = _combine_struct_attrs(structs, struct_type)
    return structs


def _combine_struct_attrs(structs, struct_type):
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


def is_parallel_corpus(query_result):
    # FIXME: This does not work if the script gets the query result
    # from frontend instead of redoing the query, since the frontend
    # has processed the corpus names not to contain the vertical bar.
    try:
        return "|" in query_result["kwic"][0]["corpus"]
    except (KeyError, IndexError):
        return False
