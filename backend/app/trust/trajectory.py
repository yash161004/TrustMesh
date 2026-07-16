"""
TrustMesh Trajectory Monitor Scaffolding
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field


class TrajectoryPoint(BaseModel):
    """A point in time representing a deviation score for a specific message."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_index: int
    deviation_score: float


class SessionTrajectory(BaseModel):
    """An ordered list of trajectory points for a session."""
    session_id: str
    points: List[TrajectoryPoint] = Field(default_factory=list)


def compute_rolling_deviation(trajectory: SessionTrajectory, window_size: int = 3) -> list[float]:
    """
    Computes a simple moving average of deviation scores using a sliding window.
    Returns a list of averages corresponding to each point in the trajectory.
    """
    scores = [p.deviation_score for p in trajectory.points]
    if not scores:
        return []
    
    averages = []
    for i in range(len(scores)):
        start = max(0, i - window_size + 1)
        window = scores[start:i + 1]
        averages.append(sum(window) / len(window))
        
    return averages
