from pydantic import BaseModel, Field, field_validator, computed_field
from typing import List, Optional, Any


class MatchInput(BaseModel):
    """Input model for Match data with field transformations."""
    approval_status: str = Field(alias="Approval Status")
    learner: str = Field(alias="Learner")
    tutor: str = Field(alias="Tutor")
    learner_available_time_slots: List[str] = Field(alias="Learner Available Time Slots")
    tutor_available_time_slots: List[str] = Field(alias="Tutor Available Time Slots")

    @field_validator('learner_available_time_slots', 'tutor_available_time_slots', mode='before')
    @classmethod
    def validate_time_slots(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [v]
        elif isinstance(v, list):
            return v
        else:
            raise ValueError("Time slots must be a string or list of strings")


class Match(BaseModel):
    """Pydantic model for Matches table records."""
    approval_status: str = Field(alias="Approval Status")
    learner: List[str] = Field(alias="Learner")
    tutor: List[str] = Field(alias="Tutor")
    overlapping_available_time_slots: List[str] = Field(alias="Overlapping Available Time Slots")

    @classmethod
    def from_input(cls, input_data: MatchInput) -> "Match":
        """Create a Match instance from MatchInput with field transformations."""
        # Convert single strings to lists for learner and tutor
        learner_list = [input_data.learner]
        tutor_list = [input_data.tutor]

        # Calculate overlapping time slots
        overlapping_slots = list(set(input_data.learner_available_time_slots) &
                                set(input_data.tutor_available_time_slots))

        return cls(**{
            "Approval Status": input_data.approval_status,
            "Learner": learner_list,
            "Tutor": tutor_list,
            "Overlapping Available Time Slots": overlapping_slots
        })
