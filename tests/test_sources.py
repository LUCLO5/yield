"""Parsing tests against trimmed copies of real API responses (no network)."""

from datetime import datetime, timezone

from pmscan.models import Candidate
from pmscan.sources import kalshi, polymarket
from pmscan.sources.common import Filters

NOW = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
F = Filters(min_prob=0.96, max_prob=0.995, max_days=30, min_volume=1000, now=NOW)


def pm_market(**kw):
    m = {
        "conditionId": "0xabc", "question": "Will BTC be above $58,000 on November 20?",
        "outcomes": '["Yes", "No"]', "outcomePrices": '["0.965", "0.035"]',
        "bestBid": 0.964, "bestAsk": 0.966, "endDate": "2026-11-20T17:00:00Z",
        "active": True, "closed": False, "acceptingOrders": True,
        "volumeNum": 250000, "liquidityNum": 40000, "clobTokenIds": '["111", "222"]',
        "feesEnabled": True, "feeSchedule": {"rate": 0.07, "exponent": 1, "takerOnly": True},
    }
    m.update(kw)
    return m


def test_polymarket_yes_side():
    out = polymarket.scan(F, events=[{"slug": "btc-nov-20", "markets": [pm_market()]}])
    assert len(out) == 1
    c = out[0]
    assert (c.side, c.ask, c.book_ref, c.fee_rate) == ("Yes", 0.966, "111", 0.07)
    assert c.url == "https://polymarket.com/event/btc-nov-20"


def test_polymarket_no_side_uses_one_minus_bid():
    m = pm_market(bestBid=0.03, bestAsk=0.032, outcomePrices='["0.031", "0.969"]')
    (c,) = polymarket.scan(F, events=[{"slug": "s", "markets": [m]}])
    assert c.side == "No" and c.ask == 0.97 and c.book_ref == "222"


def test_polymarket_filters():
    events = [{"slug": "s", "markets": [
        pm_market(closed=True),
        pm_market(volumeNum=10),
        pm_market(endDate="2027-06-01T00:00:00Z"),
        pm_market(bestAsk=0.80, bestBid=0.79),
    ]}]
    assert polymarket.scan(F, events=events) == []


def kx_market(**kw):
    m = {
        "ticker": "KXBTCD-26NOV20-T58000", "event_ticker": "KXBTCD-26NOV20", "status": "active",
        "title": "Bitcoin price on Nov 20, 2026?", "yes_sub_title": "$58,000 or above",
        "yes_ask_dollars": "0.9600", "yes_bid_dollars": "0.9500",
        "no_ask_dollars": "0.0500", "no_bid_dollars": "0.0400",
        "yes_ask_size_fp": "800.00",
        "expected_expiration_time": "2026-11-20T22:00:00Z", "close_time": "2026-11-20T22:00:00Z",
        "volume_fp": "50000.00", "open_interest_fp": "12000.00",
    }
    m.update(kw)
    return m


def test_kalshi_parse():
    (c,) = kalshi.scan(F, markets=[kx_market()])
    assert c.side == "Yes" and c.ask == 0.96 and c.ask_size == 800
    assert c.fee_rate == 0.07 and c.fee_round_cent
    assert "$58,000 or above" in c.title
    assert c.url == "https://kalshi.com/markets/kxbtcd"


def test_kalshi_legacy_cents_fields():
    m = kx_market()
    for k in ["yes_ask_dollars", "no_ask_dollars", "volume_fp"]:
        m.pop(k)
    m.update({"yes_ask": 3, "no_ask": 97, "volume": 5000})
    (c,) = kalshi.scan(F, markets=[m])
    assert c.side == "No" and c.ask == 0.97


def test_kalshi_book_inverts_opposite_bids(monkeypatch):
    book = {"orderbook_fp": {"yes_dollars": [["0.0300", "50"]], "no_dollars": [["0.0200", "10"], ["0.0400", "100"]]}}
    monkeypatch.setattr(kalshi.http, "get_json", lambda *a, **k: book)
    c = Candidate("kalshi", "T", "t", "Yes", 0.96, NOW, "u", book_ref="T")
    # Buying YES = hitting NO bids: 0.04 bid -> 0.96 ask, 0.02 bid -> 0.98 ask
    assert kalshi.fetch_book(c) == [(0.96, 100.0), (0.98, 10.0)]


def test_polymarket_us_parse_and_book(monkeypatch):
    from pmscan.sources import polymarket_us
    ev = {"slug": "fed-dec", "title": "Fed decision in December", "category": "economics", "markets": [{
        "slug": "fed-dec-hold", "question": "Fed decision in December", "title": "Hold",
        "endDate": "2026-12-10T19:00:00Z", "active": True, "closed": False, "status": "MARKET_STATUS_OPEN",
        "feeCoefficient": 0.095, "bestBidQuote": {"value": "0.0300"}, "bestAskQuote": {"value": "0.0400"},
    }]}
    (c,) = polymarket_us.scan(F, events=[ev])
    assert (c.side, c.ask, c.fee_rate, c.category) == ("No", 0.97, 0.095, "Economy")
    assert c.url == "https://polymarket.us/event/fed-dec"
    book = {"bids": [{"px": {"value": "0.0300"}, "qty": "500"}, {"px": {"value": "0.0200"}, "qty": "900"}],
            "offers": [{"px": {"value": "0.0400"}, "qty": "100"}]}
    assert polymarket_us._asks_for(book, "No") == [(0.97, 500.0), (0.98, 900.0)]
    assert polymarket_us._asks_for(book, "Yes") == [(0.04, 100.0)]
