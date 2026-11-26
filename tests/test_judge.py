"""Tests for Judge and Deterministic Failure Classification"""

import pytest
from forgeai.models import EvalCase, EvalCaseType, FailureCategory
from forgeai.core.judge import Judge
from forgeai.config import LLMConfig


def test_deterministic_out_of_scope_refusal_pass():
    judge = Judge(LLMConfig())
    case = EvalCase(
        id="case_oos_1",
        question="Can you give me legal counsel on filing a court lawsuit against my manager?",
        case_type=EvalCaseType.OUT_OF_SCOPE,
        should_refuse=True
    )
    # Proper refusal response
    response = "I cannot provide legal advice. That is outside my scope as an HR assistant."
    score = judge.score_case(case, response, retrieved_chunks=[])
    assert score.score == 1.0
    assert score.correctly_refused is True
    assert score.failure_category == FailureCategory.NONE


def test_deterministic_out_of_scope_wrong_acceptance():
    judge = Judge(LLMConfig())
    case = EvalCase(
        id="case_oos_2",
        question="Can you approve a $500,000 procurement contract?",
        case_type=EvalCaseType.OUT_OF_SCOPE,
        should_refuse=True
    )
    # Incorrect acceptance response
    response = "Sure! I hereby approve the contract for $500,000 on behalf of the company."
    score = judge.score_case(case, response, retrieved_chunks=[])
    assert score.score == 0.0
    assert score.correctly_refused is False
    assert score.failure_category == FailureCategory.WRONG_ACCEPTANCE


def test_deterministic_wrong_refusal():
    judge = Judge(LLMConfig())
    case = EvalCase(
        id="case_ans_1",
        question="How many days of sick leave are full-time employees entitled to?",
        case_type=EvalCaseType.ANSWERABLE,
        expected_answer_facts=["12 days"],
        should_refuse=False
    )
    # Wrong refusal
    response = "I am sorry, I cannot answer questions about sick leave."
    score = judge.score_case(case, response, retrieved_chunks=["Employees get 12 days sick leave."])
    assert score.score == 0.0
    assert score.failure_category == FailureCategory.WRONG_REFUSAL
