import collections
import re
import typing as ty
import subprocess


def fzf_filter(
    query: str,
    items: ty.List[ty.Dict[str, ty.Any]],
    exact: bool,
) -> ty.List[ty.Dict[str, ty.Any]]:
    """
    Request process ``fzf`` to fuzzy filter items with query. The keywords to
    be matched against will be the ``match`` key of each item, or the ``title``
    key if ``match`` is absent. The ``match`` key may be a list of strings.

    :param query: the fzf query
    :param items: the items to filter
    :param exact: ``True`` to pass '--exact' to ``fzf``
    :return: a list of matched items
    """
    candidates = parse_items_into_candidates(items)
    indices = request_fzf(query, candidates, exact)
    return [items[j] for j in indices]


def request_fzf(
    query: str,
    candidates: ty.Dict[str, int],
    exact: bool,
) -> ty.List[int]:
    """
    :param query: the fzf query
    :param candidates: a mapping from fzf candidates to index into items
    :param exact: ``True`` to pass '--exact' to fzf
    :return: a list of unique selected indices
    """
    fzf_args = ['fzf']
    if exact:
        fzf_args.append('--exact')
    fzf_args.extend(['--filter', query])
    stdin = ''.join(x + '\n' for x in candidates)
    try:
        proc = subprocess.run(
            fzf_args, text=True, input=stdin, capture_output=True, check=True)
        res = re.findall(r'(.*)\n', proc.stdout)
    except subprocess.CalledProcessError as err:
        if err.returncode != 1:
            raise
        res = []
    uniq = []
    uniq_set = set()
    for s in res:
        i = candidates[s]
        if i not in uniq_set:
            uniq.append(i)
            uniq_set.add(i)
    return uniq


def parse_items_into_candidates(
        items: ty.List[ty.Dict[str, ty.Any]]) -> ty.OrderedDict[str, int]:
    candidates = collections.OrderedDict()
    for j, item in enumerate(items):
        match = item.get('match', item['title'])
        if isinstance(match, str):
            candidates[match] = j
        else:
            for m in match:
                candidates[m] = j
    return candidates
