from backend.app.services.agents import (
    ATTACK_INSTRUCTIONS,
    DEBATE_INSTRUCTIONS,
    JUDGE_INSTRUCTIONS,
)


def test_attack_template_formats():
    out = ATTACK_INSTRUCTIONS.format(document_text="DOC BODY")
    assert "DOC BODY" in out
    assert '"findings"' in out


def test_debate_template_formats():
    out = DEBATE_INSTRUCTIONS.format(
        other_agent="CFO", other_category="burn", severity=7, claim="c", evidence_quote="q"
    )
    assert '"stance"' in out


def test_judge_template_formats():
    out = JUDGE_INSTRUCTIONS.format(findings_json=[], debate_json=[])
    assert '"final_risks"' in out
