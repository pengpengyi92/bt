from datetime import datetime

import mock
import pandas as pd
import numpy as np
from nose.tools import assert_almost_equal as aae

import bt
import bt.algos as algos


def test_algo_name():
    class TestAlgo(algos.Algo):
        pass

    actual = TestAlgo()

    assert actual.name == 'TestAlgo'


class DummyAlgo(algos.Algo):

    def __init__(self, return_value=True):
        self.return_value = return_value
        self.called = False

    def __call__(self, target):
        self.called = True
        return self.return_value


def test_algo_stack():
    algo1 = DummyAlgo(return_value=True)
    algo2 = DummyAlgo(return_value=False)
    algo3 = DummyAlgo(return_value=True)

    target = mock.MagicMock()

    stack = bt.AlgoStack(algo1, algo2, algo3)

    actual = stack(target)
    assert not actual
    assert algo1.called
    assert algo2.called
    assert not algo3.called


def test_run_once():
    algo = algos.RunOnce()
    assert algo(None)
    assert not algo(None)
    assert not algo(None)


def test_run_weekly():
    algo = algos.RunWeekly()

    target = mock.MagicMock()

    target.now = None
    assert not algo(target)

    target.now = datetime(2010, 1, 1)
    assert not algo(target)

    target.now = datetime(2010, 1, 15)
    assert algo(target)

    target.now = datetime(2010, 2, 15)
    assert algo(target)

    # sat
    target.now = datetime(2014, 1, 4)
    assert algo(target)

    # sun
    target.now = datetime(2014, 1, 5)
    assert not algo(target)

    # mon - week change
    target.now = datetime(2014, 1, 6)
    assert algo(target)


def test_run_monthly():
    algo = algos.RunMonthly()

    target = mock.MagicMock()

    target.now = None
    assert not algo(target)

    target.now = datetime(2010, 1, 1)
    assert not algo(target)

    target.now = datetime(2010, 1, 15)
    assert not algo(target)

    target.now = datetime(2010, 2, 15)
    assert algo(target)

    target.now = datetime(2010, 2, 25)
    assert not algo(target)

    target.now = datetime(2010, 12, 25)
    assert algo(target)

    target.now = datetime(2011, 1, 25)
    assert algo(target)


def test_run_yearly():
    algo = algos.RunYearly()

    target = mock.MagicMock()

    target.now = datetime(2010, 1, 1)
    actual = algo(target)
    assert not actual

    target.now = datetime(2010, 5, 1)
    actual = algo(target)
    assert not actual

    target.now = datetime(2011, 1, 1)
    actual = algo(target)
    assert actual


def test_run_on_date():
    target = mock.MagicMock()
    target.now = pd.to_datetime('2010-01-01')

    algo = algos.RunOnDate('2010-01-01', '2010-01-02')
    assert algo(target)

    target.now = pd.to_datetime('2010-01-02')
    assert algo(target)

    target.now = pd.to_datetime('2010-01-03')
    assert not algo(target)


def test_rebalance():
    algo = algos.Rebalance()

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100)
    data['c1'][dts[1]] = 105
    data['c2'][dts[1]] = 95

    s.setup(data)
    s.adjust(1000)
    s.update(dts[0])

    s.algo_data['weights'] = {'c1': 1}

    assert algo(s)
    assert s.value == 999
    assert s.capital == -1
    c1 = s['c1']
    assert c1.value == 1000
    assert c1.position == 10
    assert c1.weight == 1000.0 / 999

    s.algo_data['weights'] = {'c2': 1}

    assert algo(s)
    assert s.value == 997
    assert s.capital == 97
    c2 = s['c2']
    assert c1.value == 0
    assert c1.position == 0
    assert c1.weight == 0
    assert c2.value == 900
    assert c2.position == 9
    assert c2.weight == 900.0 / 997


def test_select_all():
    algo = algos.SelectAll()

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)
    data['c1'][dts[1]] = np.nan
    data['c2'][dts[1]] = 95

    s.setup(data)
    s.update(dts[0])

    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 2
    assert 'c1' in selected
    assert 'c2' in selected

    # make sure don't keep nan
    s.update(dts[1])

    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 1
    assert 'c2' in selected

    # if specify include_no_data then 2
    algo = algos.SelectAll(include_no_data=True)

    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 2
    assert 'c1' in selected
    assert 'c2' in selected


def test_weight_equally():
    algo = algos.WeighEqually()

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100)
    data['c1'][dts[1]] = 105
    data['c2'][dts[1]] = 95

    s.setup(data)
    s.update(dts[0])
    s.algo_data['selected'] = ['c1', 'c2']

    assert algo(s)
    weights = s.algo_data['weights']
    assert len(weights) == 2
    assert 'c1' in weights
    assert weights['c1'] == 0.5
    assert 'c2' in weights
    assert weights['c2'] == 0.5


def test_weight_specified():
    algo = algos.WeighSpecified(c1=0.6, c2=0.4)

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100)
    data['c1'][dts[1]] = 105
    data['c2'][dts[1]] = 95

    s.setup(data)
    s.update(dts[0])

    assert algo(s)
    weights = s.algo_data['weights']
    assert len(weights) == 2
    assert 'c1' in weights
    assert weights['c1'] == 0.6
    assert 'c2' in weights
    assert weights['c2'] == 0.4


def test_select_has_data():
    algo = algos.SelectHasData(min_count=3, lookback=pd.DateOffset(days=3))

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)
    data['c1'].ix[dts[0]] = np.nan
    data['c1'].ix[dts[1]] = np.nan

    s.setup(data)
    s.update(dts[2])

    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 1
    assert 'c2' in selected


def test_select_has_data_preselected():
    algo = algos.SelectHasData(min_count=3, lookback=pd.DateOffset(days=3))

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)
    data['c1'].ix[dts[0]] = np.nan
    data['c1'].ix[dts[1]] = np.nan

    s.setup(data)
    s.update(dts[2])
    s.algo_data['selected'] = ['c1']

    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 0


def test_weigh_inv_vol():
    algo = algos.WeighInvVol(lookback=pd.DateOffset(days=5))

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=5)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)

    # high vol c1
    data['c1'].ix[dts[1]] = 105
    data['c1'].ix[dts[2]] = 95
    data['c1'].ix[dts[3]] = 105
    data['c1'].ix[dts[4]] = 95

    # low vol c2
    data['c2'].ix[dts[1]] = 100.1
    data['c2'].ix[dts[2]] = 99.9
    data['c2'].ix[dts[3]] = 100.1
    data['c2'].ix[dts[4]] = 99.9

    s.setup(data)
    s.update(dts[4])
    s.algo_data['selected'] = ['c1', 'c2']

    assert algo(s)
    weights = s.algo_data['weights']
    assert len(weights) == 2
    assert weights['c2'] > weights['c1']
    aae(weights['c1'], 0.020, 3)
    aae(weights['c2'], 0.980, 3)


@mock.patch('bt.finance.calc_mean_var_weights')
def test_weigh_mean_var(mock_mv):
    algo = algos.WeighMeanVar(lookback=pd.DateOffset(days=5))

    mock_mv.return_value = {'c1': 0.3, 'c2': 0.7}

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=5)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)

    s.setup(data)
    s.update(dts[4])
    s.algo_data['selected'] = ['c1', 'c2']

    assert algo(s)
    assert mock_mv.called
    rets = mock_mv.call_args[0][0]
    assert len(rets) == 4
    assert 'c1' in rets
    assert 'c2' in rets

    weights = s.algo_data['weights']
    assert len(weights) == 2
    assert weights['c1'] == 0.3
    assert weights['c2'] == 0.7


def test_stat_total_return():
    algo = algos.StatTotalReturn(lookback=pd.DateOffset(days=3))

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)
    data['c1'].ix[dts[2]] = 105
    data['c2'].ix[dts[2]] = 95

    s.setup(data)
    s.update(dts[2])
    s.algo_data['selected'] = ['c1', 'c2']

    assert algo(s)
    stat = s.algo_data['stat']
    assert len(stat) == 2
    assert stat['c1'] == 105.0 / 100 - 1
    assert stat['c2'] == 95.0 / 100 - 1


def test_select_n():
    algo = algos.SelectN(n=1, sort_descending=True)

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)
    data['c1'].ix[dts[2]] = 105
    data['c2'].ix[dts[2]] = 95

    s.setup(data)
    s.update(dts[2])
    s.algo_data['stat'] = data.calc_total_return()

    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 1
    assert 'c1' in selected

    algo = algos.SelectN(n=1, sort_descending=False)
    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 1
    assert 'c2' in selected

    # return 2 we have if all_or_none false
    algo = algos.SelectN(n=3, sort_descending=False)
    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 2
    assert 'c1' in selected
    assert 'c2' in selected

    # return 0 we have if all_or_none true
    algo = algos.SelectN(n=3, sort_descending=False, all_or_none=True)
    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 0


def test_select_n_perc():
    algo = algos.SelectN(n=0.5, sort_descending=True)

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)
    data['c1'].ix[dts[2]] = 105
    data['c2'].ix[dts[2]] = 95

    s.setup(data)
    s.update(dts[2])
    s.algo_data['stat'] = data.calc_total_return()

    assert algo(s)
    selected = s.algo_data['selected']
    assert len(selected) == 1
    assert 'c1' in selected


def test_select_momentum():
    algo = algos.SelectMomentum(n=1, lookback=pd.DateOffset(days=3))

    s = bt.Strategy('s')

    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)
    data['c1'].ix[dts[2]] = 105
    data['c2'].ix[dts[2]] = 95

    s.setup(data)
    s.update(dts[2])
    s.algo_data['selected'] = ['c1', 'c2']

    assert algo(s)
    actual = s.algo_data['selected']
    assert len(actual) == 1
    assert 'c1' in actual


def test_limit_deltas():
    algo = algos.LimitDeltas(0.1)

    s = bt.Strategy('s')
    dts = pd.date_range('2010-01-01', periods=3)
    data = pd.DataFrame(index=dts, columns=['c1', 'c2'], data=100.)

    s.setup(data)
    s.algo_data['weights'] = {'c1': 1}

    algo = algos.LimitDeltas(0.1)
    assert algo(s)
    w = s.algo_data['weights']
    assert w['c1'] == 0.1

    s.algo_data['weights'] = {'c1': 0.05}
    algo = algos.LimitDeltas(0.1)
    assert algo(s)
    w = s.algo_data['weights']
    assert w['c1'] == 0.05

    s.algo_data['weights'] = {'c1': 0.5, 'c2': 0.5}
    algo = algos.LimitDeltas(0.1)
    assert algo(s)
    w = s.algo_data['weights']
    assert len(w) == 2
    assert w['c1'] == 0.1
    assert w['c2'] == 0.1

    s.algo_data['weights'] = {'c1': 0.5, 'c2': -0.5}
    algo = algos.LimitDeltas(0.1)
    assert algo(s)
    w = s.algo_data['weights']
    assert len(w) == 2
    assert w['c1'] == 0.1
    assert w['c2'] == -0.1

    s.algo_data['weights'] = {'c1': 0.5, 'c2': -0.5}
    algo = algos.LimitDeltas({'c1': 0.1})
    assert algo(s)
    w = s.algo_data['weights']
    assert len(w) == 2
    assert w['c1'] == 0.1
    assert w['c2'] == -0.5

    s.algo_data['weights'] = {'c1': 0.5, 'c2': -0.5}
    algo = algos.LimitDeltas({'c1': 0.1, 'c2': 0.3})
    assert algo(s)
    w = s.algo_data['weights']
    assert len(w) == 2
    assert w['c1'] == 0.1
    assert w['c2'] == -0.3

    # set exisitng weight
    s.children['c1'] = bt.core.SecurityBase('c1')
    s.children['c1']._weight = 0.3
    s.children['c2'] = bt.core.SecurityBase('c2')
    s.children['c2']._weight = -0.7

    s.algo_data['weights'] = {'c1': 0.5, 'c2': -0.5}
    algo = algos.LimitDeltas(0.1)
    assert algo(s)
    w = s.algo_data['weights']
    assert len(w) == 2
    assert w['c1'] == 0.4
    assert w['c2'] == -0.6


def test_rebalance_over_time():
    target = mock.MagicMock()
    rb = mock.MagicMock()

    algo = algos.RebalanceOverTime(days=2)
    # patch in rb function
    algo._rb = rb

    target.algo_data = {}
    target.algo_data['weights'] = {'a': 1, 'b': 0}

    a = mock.MagicMock()
    a.weight = 0.
    b = mock.MagicMock()
    b.weight = 1.
    target.children = {'a': a, 'b': b}

    assert algo(target)
    w = target.algo_data['weights']
    assert len(w) == 2
    assert w['a'] == 0.5
    assert w['b'] == 0.5

    assert rb.called
    called_tgt = rb.call_args[0][0]
    called_tgt_w = called_tgt.algo_data['weights']
    assert len(called_tgt_w) == 2
    assert called_tgt_w['a'] == 0.5
    assert called_tgt_w['b'] == 0.5

    # update weights for next call
    a.weight = 0.5
    b.weight = 0.5

    # clear out algo_data - same as would Strategy
    target.algo_data = {}

    assert algo(target)
    w = target.algo_data['weights']
    assert len(w) == 2
    assert w['a'] == 1.
    assert w['b'] == 0.

    assert rb.call_count == 2

    # update weights for next call
    # should do nothing now
    a.weight = 1
    b.weight = 0

    # clear out algo_data - same as would Strategy
    target.algo_data = {}

    assert algo(target)
    # no diff in call_count since last time
    assert rb.call_count == 2


def test_require():
    target = mock.MagicMock()
    target.algo_data = {}

    pred = lambda x: len(x) > 0
    algo = algos.Require(pred, 'selected')
    assert not algo(target)

    target.algo_data['selected'] = []
    assert not algo(target)

    target.algo_data['selected'] = ['a', 'b']
    assert algo(target)