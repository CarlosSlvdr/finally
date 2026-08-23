from app.db import snapshots


def test_record_and_list_snapshots_oldest_first():
    snapshots.record_snapshot(10000.0)
    snapshots.record_snapshot(10500.0)
    result = snapshots.list_snapshots()
    assert [s.total_value for s in result] == [10000.0, 10500.0]
