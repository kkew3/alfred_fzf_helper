"""
``fzf_filter`` function to fuzzy filter items given query.
Also included cache-related helper function ``read_cache``.
"""
import collections
import json
import os
import re
import subprocess

__all__ = [
    'fzf_filter',
    'read_cache',
]


def test_fzf_filter():
    q, s, sc = fzf_filter(
        '^my', [{
            'title': 'my blog'
        }], [{
            'title': 'new blog',
            'match': 'newblog'
        }, {
            'title': 'edit blog',
            'match': 'editblog'
        }],
        cmd_prefix=':')
    assert q == 'my'
    assert s == [{'title': 'my blog'}]
    assert sc is None

    q, s, sc = fzf_filter(
        'hello world$ :^n', [{
            'title': 'my blog'
        }], [{
            'title': 'new blog',
            'match': 'newblog'
        }, {
            'title': 'edit blog',
            'match': 'editblog'
        }],
        cmd_prefix=':')
    assert q == 'hello world'
    assert s is None
    assert sc == [{'title': 'new blog', 'match': 'newblog'}]

    q, s, sc = fzf_filter(
        'hello world$ :', [{
            'title': 'my blog'
        }], [{
            'title': 'new blog',
            'match': 'newblog'
        }, {
            'title': 'edit blog',
            'match': 'editblog'
        }],
        cmd_prefix=':')
    assert q == 'hello world'
    assert s is None
    assert sc == [{
        'title': 'new blog',
        'match': 'newblog'
    }, {
        'title': 'edit blog',
        'match': 'editblog'
    }]


def fzf_filter(query,
               items,
               cmd_items=None,
               cmd_prefix=None,
               cmd_suffix=None,
               exact=False,
               strip_space_before_match=True):
    """
    Request process ``fzf`` to fuzzy filter items with query. The keywords to
    be matched against will be the ``match`` key of items, or the ``title``
    key if ``match`` is not present.

    Examples::

        fzf_filter(query,
                   [{'title': 'my blog'}],
                   [{'title': 'new blog named `{}`', 'match': 'newblog'}],
                   cmd_prefix=':')

    will return::

        ('my', [{'title': 'my blog'}], None)

    on query ``'^my'``, and will return::

        ('hello world', None,
         [{'title': 'new blog named `{}`', 'match': 'newblog'}])

    on query ``'hello world$ :^n'``.

    :param query: the query
    :type query: str
    :param items: Alfred 5 JSON responses
    :type items: List[Dict[str, Any]]
    :param cmd_items: Alfred 5 JSON responses; within the 'title' and
           'subtitle' of the responses one bracket-style placeholder may be
           used to fill the query in
    :type cmd_items: Optional[List[Dict[str, Any]]]
    :param cmd_prefix: if not ``None``, should be the prefix (non-empty) of the
           commands; assigning non-``None`` implies that each command is a
           suffix of the entire query. Needless to say, this argument is
           contradictory with ``cmd_suffix``
    :param cmd_suffix: if not ``None``, should be the suffix (non-empty) of the
           commands; assigning non-``None`` implies that each command is a
           prefix of the entire query. Needless to say, this argument is
           contradictory with ``cmd_prefix``
    :param exact: if ``True``, switch to ``fzf``'s exact match mode
    :type exact: bool
    :param strip_space_before_match: if ``True``, strip out the space around
           the query before matching against items
    :type strip_space_before_match: bool
    :return: the space-stripped query with neither ``fzf`` search
             meta-characters nor affix commands, the selected responses and
             the selected command responses. Only one of the two selected
             responses is non-``None``
    :rtype: Tuple[str, Optional[List[str]], Optional[List[str]]]
    """
    if cmd_prefix and cmd_suffix:
        raise ValueError(
            '`cmd_prefix` and `cmd_suffix` must not be non-empty at the '
            'same time')
    if cmd_items and (not cmd_prefix and not cmd_suffix):
        raise ValueError(
            'either `cmd_prefix` or `cmd_suffix` must be specified if '
            '`cmd_items` is non-empty')

    orig_query, query, candidates, query_mode = _init_fzf_filter(
        query, items, cmd_items, cmd_prefix, cmd_suffix,
        strip_space_before_match)
    selected_items = [
        candidates[k] for k in _request_fzf(query, list(candidates), exact)
    ]
    if query_mode:
        return orig_query, selected_items, None
    return orig_query, None, selected_items


def _init_fzf_filter(query, items, cmd_items, cmd_prefix, cmd_suffix,
                     strip_space_before_match):
    """
    Returns ``orig_query`` (the space-stripped query part of the entire query),
    ``query`` (the real search query), ``candidates`` (the strings to be
    matched against mapped to the item dictionaries), and whether is to match
    against queries (``True``) or commands (``False``).

    :rtype: Tuple[str, str, List[Dict[str, Dict[str, Any]]], bool]
    """
    initialized = False

    if cmd_items:
        if cmd_prefix:
            try:
                i = query.index(cmd_prefix)
            except ValueError:
                pass
            else:
                orig_query = _remove_metachar_from_query(query[:i].strip())
                query = query[i + 1:]
                if strip_space_before_match:
                    query = query.strip()
                candidates = collections.OrderedDict(
                    (x.get('match', x['title']), x) for x in cmd_items)
                initialized = True
        elif cmd_suffix:
            try:
                i = query.rindex(cmd_suffix)
            except ValueError:
                pass
            else:
                orig_query = _remove_metachar_from_query(query[i + 1:].strip())
                query = query[:i]
                if strip_space_before_match:
                    query = query.strip()
                candidates = collections.OrderedDict(
                    (x.get('match', x['title']), x) for x in cmd_items)
                initialized = True

    if not initialized:
        orig_query = _remove_metachar_from_query(query.strip())
        if strip_space_before_match:
            query = query.strip()
        candidates = collections.OrderedDict(
            (x.get('match', x['title']), x) for x in items)

    return orig_query, query, candidates, not initialized


def test__request_fzf():
    assert _request_fzf('x', ['x'], False) == ['x']
    assert _request_fzf('x', ['x1', 'x2'], False) == ['x1', 'x2']
    assert _request_fzf('', [''], False) == ['']
    assert _request_fzf('', ['', ''], False) == ['', '']


def _request_fzf(query, candidates, exact):
    fzf_args = ['fzf']
    if exact:
        fzf_args.append('--exact')
    fzf_args.append('--filter')
    fzf_args.append(query)

    stdin = ''.join(x + '\n' for x in candidates)
    try:
        resp = subprocess.run(
            fzf_args,
            text=True,
            input=stdin,
            stdout=subprocess.PIPE,
            check=True)
    except subprocess.CalledProcessError as err:
        if err.returncode != 1:
            raise
        return []
    else:
        return re.findall(r'([^\n]*)\n', resp.stdout)


def _remove_metachar_from_query(query):
    query = re.sub(r"(^|\s)'", r'\1', query)
    query = re.sub(r'(^|\s)\^', r'\1', query)
    query = re.sub(r'\$($|\s)', r'\1', query)
    query = re.sub(r'(^|\s)!', r'\1', query)
    query = query.replace('|', '')
    query = query.replace(r'\ ', ' ')
    query = re.sub(r' +', ' ', query)
    query = query.strip()
    return query


def read_cache(cachedir,
               cache_token,
               genresp,
               ensure_modified_later_than=None,
               delete_all_other_caches_on_write=False):
    """
    Read cache from ``cachedir/cache_token.json``. If not present, write cache
    to ``cachedir/cache_token.json`` using dictionary generated by
    ``genresp()``. If ``ensure_modified_later_than`` is specified as a list
    of file paths, ``cachedir/cache_token.json`` will be rewritten unless it's
    modification time is later than all files in the list. If
    ``delete_all_other_caches_on_write`` is specified as ``True``, all other
    existing caches under ``cachedir`` will be removed when writing to
    ``cachedir/cache_token.json``.

    :param cachedir: the cache directory; will be created if not exists
    :type cachedir: str
    :param cache_token: the cache name to retrieve
    :type cache_token: str
    :param genresp: function to be called to produce responses if cache is not
           present
    :type genresp: Callable[[], Any]
    :param ensure_modified_later_than: a list of files whose modification time
           should be later than the cache retrieved
    :type ensure_modified_later_than: Optional[List[str]]
    :param delete_all_other_caches_on_write: ``True`` to delete other caches
           when writing current cache
    :type delete_all_other_caches_on_write: bool
    :return: the object in the cache
    :rtype: Any
    """
    cachefile = os.path.join(cachedir, cache_token + '.json')
    need_write = False
    if not os.path.isdir(cachedir):
        os.mkdir(cachedir)
        need_write = True
    if not need_write and not os.path.isfile(cachefile):
        need_write = True
    if not need_write and ensure_modified_later_than:
        if os.path.getmtime(cachefile) <= max(
                map(os.path.getmtime, ensure_modified_later_than)):
            need_write = True
    if not need_write:
        try:
            with open(cachefile, encoding='utf-8') as infile:
                return json.load(infile)
        except json.JSONDecodeError:
            need_write = True

    resp = genresp()
    if delete_all_other_caches_on_write:
        for name in os.listdir(cachedir):
            os.remove(os.path.join(cachedir, name))
    with open(cachefile, 'w', encoding='utf-8') as outfile:
        json.dump(resp, outfile)
    return resp
