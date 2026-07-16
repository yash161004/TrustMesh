import pytest
from app.trust.trajectory import TrajectoryPoint, SessionTrajectory, compute_rolling_deviation

def test_compute_rolling_deviation_empty():
    trajectory = SessionTrajectory(session_id="test_session", points=[])
    averages = compute_rolling_deviation(trajectory)
    assert averages == []

def test_compute_rolling_deviation_single_element():
    trajectory = SessionTrajectory(
        session_id="test_session",
        points=[TrajectoryPoint(message_index=1, deviation_score=0.5)]
    )
    averages = compute_rolling_deviation(trajectory, window_size=3)
    assert averages == [0.5]

def test_compute_rolling_deviation_window_3():
    scores = [0.1, 0.2, 0.8, 0.3, 0.1]
    points = [
        TrajectoryPoint(message_index=i, deviation_score=score)
        for i, score in enumerate(scores)
    ]
    trajectory = SessionTrajectory(session_id="test_session", points=points)
    
    averages = compute_rolling_deviation(trajectory, window_size=3)
    
    # Expected:
    # i=0: [0.1] -> 0.1
    # i=1: [0.1, 0.2] -> 0.15
    # i=2: [0.1, 0.2, 0.8] -> 1.1 / 3 = 0.3666...
    # i=3: [0.2, 0.8, 0.3] -> 1.3 / 3 = 0.4333...
    # i=4: [0.8, 0.3, 0.1] -> 1.2 / 3 = 0.4
    
    assert len(averages) == 5
    assert averages[0] == pytest.approx(0.1)
    assert averages[1] == pytest.approx(0.15)
    assert averages[2] == pytest.approx(1.1 / 3)
    assert averages[3] == pytest.approx(1.3 / 3)
    assert averages[4] == pytest.approx(0.4)

def test_compute_rolling_deviation_window_2():
    scores = [0.1, 0.2, 0.8]
    points = [
        TrajectoryPoint(message_index=i, deviation_score=score)
        for i, score in enumerate(scores)
    ]
    trajectory = SessionTrajectory(session_id="test_session", points=points)
    
    averages = compute_rolling_deviation(trajectory, window_size=2)
    
    # Expected:
    # i=0: [0.1] -> 0.1
    # i=1: [0.1, 0.2] -> 0.15
    # i=2: [0.2, 0.8] -> 0.5
    
    assert len(averages) == 3
    assert averages[0] == pytest.approx(0.1)
    assert averages[1] == pytest.approx(0.15)
    assert averages[2] == pytest.approx(0.5)
