import uuid
import random
import time

import alfzf


def gen_case(n):
    candidates = [uuid.uuid4().hex for _ in range(n)]
    query = random.choice(candidates)
    return query, [{'title': x} for x in candidates]


def make_test_case(n, timeout):
    def _test_case():
        query, items = gen_case(n)
        tic = time.perf_counter()
        _, sel_items, _ = alfzf.fzf_filter(query, items)
        toc = time.perf_counter()
        assert sel_items
        assert toc - tic < timeout

        query, items = gen_case(n)
        tic = time.perf_counter()
        _, sel_items, _ = alfzf.fzf_filter(query, items, exact=True)
        toc = time.perf_counter()
        assert sel_items
        assert toc - tic < timeout

    return _test_case


test_100 = make_test_case(100, 0.01)
test_500 = make_test_case(500, 0.01)
test_1000 = make_test_case(1000, 0.01)
test_5000 = make_test_case(5000, 0.02)
test_20000 = make_test_case(20000, 0.05)


def measure_perf(n, exact):
    query, items = gen_case(n)
    tic = time.perf_counter()
    _ = alfzf.fzf_filter(query, items, exact=exact)
    toc = time.perf_counter()
    return toc - tic


def make_table():
    import numpy as np
    from joblib import Parallel, delayed
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt

    ns = np.around(np.logspace(0, 4, 100) * 100).astype(int)
    Ts = Parallel(
        n_jobs=6, verbose=5)(
            delayed(measure_perf)(i, False) for i in ns)
    exact_Ts = Parallel(
        n_jobs=6, verbose=5)(
            delayed(measure_perf)(i, True) for i in ns)
    with open('benchmark/perf.csv', 'w', encoding='utf-8') as outfile:
        for n, t in zip(ns, Ts):
            outfile.write('{},{}\n'.format(n, t))
    with open('benchmark/perf_exact.csv', 'w', encoding='utf-8') as outfile:
        for n, t in zip(ns, exact_Ts):
            outfile.write('{},{}\n'.format(n, t))
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 8))
    ax1.plot(ns, Ts)
    ax1.set_title('exact=False')
    ax1.set_ylabel('seconds')
    ax1.grid()
    ax2.plot(ns, exact_Ts)
    ax2.set_title('exact=True')
    ax2.set_xlabel('number of items')
    ax2.set_ylabel('seconds')
    ax2.grid()
    fig.savefig('benchmark/time_consumed.png')
    plt.close(fig)
