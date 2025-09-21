import pytest
from models import Match, MatchInput


class TestMatchModel:
    """Test cases for Match model creation and transformation."""

    def test_match_creation_from_input(self):
        """Test creating a Match model from input data with field transformations."""
        input_data = {
            "Tutor Available Time Slots": [
                "recGyyimRlFL5WNef",
                "recrwA7wQpzpESeTz",
                "rec9kuDnlIaqJK2AG",
                "recNLxPl4eYkoNi4K",
                "recT3C7YOJlfwNvEd",
                "rechBC3L6PvVaoIwe",
                "recXL2u0eUWvkthXg"
            ],
            "Learner Available Time Slots": [
                "rec4TUVd3TYRGE285",
                "recCBSSr64Kyqy3am",
                "recOlfnwC3UYr23Km",
                "rec3bKtWNsMduSi9T",
                "rechBC3L6PvVaoIwe",
                "rec5zA7r36PtPjNbU",
                "recwtZpVQrUEPyrv7",
                "recPYsta40j55OxcX",
                "recBjcd1xpS2qoArR",
                "recT3C7YOJlfwNvEd",
                "recXL2u0eUWvkthXg",
                "rececl8J0UtxHDhmL",
                "recXUyrUQAp8cBZto",
                "recNLxPl4eYkoNi4K",
                "recZE5fulw04AoVZ4",
                "recqJR3YzRotNrwon"
            ],
            "Tutor": "recuUhUFHYIQ6B3De",
            "Learner": "recJpeIQuMnAlfJ1R",
            "Approval Status": "Requested"
        }

        match_input = MatchInput.model_validate(input_data)
        match = Match.from_input(match_input)

        assert match.approval_status == "Requested"
        assert match.learner == ["recJpeIQuMnAlfJ1R"]
        assert match.tutor == ["recuUhUFHYIQ6B3De"]

        expected_overlapping = [
            "rechBC3L6PvVaoIwe",
            "recT3C7YOJlfwNvEd",
            "recXL2u0eUWvkthXg",
            "recNLxPl4eYkoNi4K"
        ]
        assert set(match.overlapping_available_time_slots) == set(expected_overlapping)
        assert len(match.overlapping_available_time_slots) == 4

    def test_match_input_validation_with_string_time_slots(self):
        """Test that single string time slots are converted to lists."""
        input_data = {
            "Tutor Available Time Slots": "recGyyimRlFL5WNef",
            "Learner Available Time Slots": "rec4TUVd3TYRGE285",
            "Tutor": "recuUhUFHYIQ6B3De",
            "Learner": "recJpeIQuMnAlfJ1R",
            "Approval Status": "Approved"
        }

        match_input = MatchInput.model_validate(input_data)
        match = Match.from_input(match_input)

        assert match.learner == ["recJpeIQuMnAlfJ1R"]
        assert match.tutor == ["recuUhUFHYIQ6B3De"]
        assert match.overlapping_available_time_slots == []

    def test_no_overlapping_time_slots(self):
        """Test case where there are no overlapping time slots."""
        input_data = {
            "Tutor Available Time Slots": ["recGyyimRlFL5WNef", "recrwA7wQpzpESeTz"],
            "Learner Available Time Slots": ["rec4TUVd3TYRGE285", "recCBSSr64Kyqy3am"],
            "Tutor": "recuUhUFHYIQ6B3De",
            "Learner": "recJpeIQuMnAlfJ1R",
            "Approval Status": "Pending"
        }

        match_input = MatchInput.model_validate(input_data)
        match = Match.from_input(match_input)

        assert match.overlapping_available_time_slots == []
